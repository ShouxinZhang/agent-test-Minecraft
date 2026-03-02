from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs" / "copilotChatHistory"
DEFAULT_WORKSPACE_STORAGE = Path("~/.config/Code/User/workspaceStorage").expanduser()
SQLITE_KEYS = ("interactive.sessions", "memento/interactive-session")
SQLITE_CHAT_INDEX_KEY = "chat.ChatSessionStore.index"


def _parse_args() -> argparse.Namespace:
    today = dt.datetime.now().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(
        description=(
            "Export GitHub Copilot Chat history and archive by day into "
            "docs/copilotChatHistory/YYYY-MM-DD/."
        )
    )
    parser.add_argument("--day", default=today, help="target day, format YYYY-MM-DD")
    parser.add_argument(
        "--workspace-storage",
        default=str(DEFAULT_WORKSPACE_STORAGE),
        help="VS Code workspaceStorage root path",
    )
    parser.add_argument(
        "--no-workspace-scan",
        action="store_true",
        help="disable scanning state.vscdb from workspaceStorage",
    )
    parser.add_argument(
        "--chat-json",
        action="append",
        default=[],
        help="extra exported chat session json file path, repeatable",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="output root directory, default docs/copilotChatHistory",
    )
    parser.add_argument(
        "--include-undated",
        action="store_true",
        help="keep messages without timestamp",
    )
    parser.add_argument(
        "--write-raw",
        action="store_true",
        help="write normalized json output alongside markdown",
    )
    parser.add_argument(
        "--latest-session",
        action="store_true",
        help="export the latest session only (ignore day filter)",
    )
    parser.add_argument(
        "--copy-to-clipboard",
        action="store_true",
        help="copy exported markdown to system clipboard",
    )
    return parser.parse_args()


def _safe_json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return None


def _extract_sessions(node: Any) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            requests = value.get("requests")
            if isinstance(requests, list):
                sessions.append(value)
            for child in value.values():
                walk(child)
            return
        if isinstance(value, list):
            for child in value:
                walk(child)

    walk(node)
    return sessions


def _read_sqlite_payloads(state_db: Path) -> list[Any]:
    payloads: list[Any] = []
    if not state_db.exists():
        return payloads

    try:
        with sqlite3.connect(state_db) as conn:
            for key in SQLITE_KEYS:
                cursor = conn.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                row = cursor.fetchone()
                if not row:
                    continue
                raw_value = row[0]
                if isinstance(raw_value, bytes):
                    try:
                        raw_value = raw_value.decode("utf-8")
                    except Exception:
                        continue
                if not isinstance(raw_value, str):
                    continue
                parsed = _safe_json_loads(raw_value)
                if parsed is not None:
                    payloads.append(parsed)
    except Exception:
        return payloads

    return payloads


def _read_sqlite_json_value(state_db: Path, key: str) -> Any | None:
    if not state_db.exists():
        return None

    try:
        with sqlite3.connect(state_db) as conn:
            cursor = conn.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return None
            raw_value = row[0]
            if isinstance(raw_value, bytes):
                raw_value = raw_value.decode("utf-8", errors="ignore")
            if not isinstance(raw_value, str):
                return None
            return _safe_json_loads(raw_value)
    except Exception:
        return None


def _extract_chat_session_titles(index_payload: Any) -> dict[str, str]:
    titles: dict[str, str] = {}
    if not isinstance(index_payload, dict):
        return titles
    entries = index_payload.get("entries")
    if not isinstance(entries, dict):
        return titles

    for session_id, meta in entries.items():
        if not isinstance(session_id, str) or not isinstance(meta, dict):
            continue
        title = meta.get("title")
        if isinstance(title, str) and title.strip():
            titles[session_id] = title.strip()

    return titles


def _ensure_path_for_set(root: dict[str, Any], path: list[Any]) -> tuple[Any, Any] | None:
    current: Any = root
    for idx, key in enumerate(path[:-1]):
        next_key = path[idx + 1]
        if isinstance(key, int):
            if not isinstance(current, list):
                return None
            while len(current) <= key:
                current.append([] if isinstance(next_key, int) else {})
            current = current[key]
            continue

        if not isinstance(current, dict):
            return None
        child = current.get(key)
        if not isinstance(child, (dict, list)):
            child = [] if isinstance(next_key, int) else {}
            current[key] = child
        current = child

    return current, path[-1] if path else None


def _apply_jsonl_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    kind = event.get("kind")
    path = event.get("k")
    value = event.get("v")

    if not isinstance(path, list):
        return
    if not path:
        if kind == 1 and isinstance(value, dict):
            state.clear()
            state.update(value)
        return

    target = _ensure_path_for_set(state, path)
    if target is None:
        return
    parent, leaf = target

    if kind == 1:
        if isinstance(leaf, int):
            if not isinstance(parent, list):
                return
            while len(parent) <= leaf:
                parent.append(None)
            parent[leaf] = value
            return
        if isinstance(parent, dict):
            parent[leaf] = value
        return

    if kind == 2:
        if isinstance(leaf, int):
            if not isinstance(parent, list):
                return
            while len(parent) <= leaf:
                parent.append([])
            if not isinstance(parent[leaf], list):
                parent[leaf] = []
            if isinstance(value, list):
                parent[leaf].extend(value)
            else:
                parent[leaf].append(value)
            return

        if not isinstance(parent, dict):
            return
        existing = parent.get(leaf)
        if not isinstance(existing, list):
            existing = []
            parent[leaf] = existing
        if isinstance(value, list):
            existing.extend(value)
        else:
            existing.append(value)


def _parse_chat_session_jsonl(path: Path) -> dict[str, Any] | None:
    state: dict[str, Any] = {}
    try:
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if not isinstance(event, dict):
            continue
        _apply_jsonl_event(state, event)

    requests = state.get("requests")
    if not isinstance(requests, list):
        return None

    return state


def _collect_from_chat_sessions_jsonl(workspace_dir: Path, state_db: Path) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    chat_sessions_dir = workspace_dir / "chatSessions"
    if not chat_sessions_dir.exists():
        return sessions

    index_payload = _read_sqlite_json_value(state_db, SQLITE_CHAT_INDEX_KEY)
    title_map = _extract_chat_session_titles(index_payload)

    for jsonl_path in chat_sessions_dir.glob("*.jsonl"):
        state = _parse_chat_session_jsonl(jsonl_path)
        if state is None:
            continue
        session_id = jsonl_path.stem
        session = {
            "customTitle": title_map.get(session_id, state.get("customTitle", "untitled")),
            "requests": state.get("requests", []),
            "_source": str(jsonl_path),
            "_workspace_id": workspace_dir.name,
            "_session_id": session_id,
        }
        sessions.append(session)

    return sessions


def _collect_from_workspace_storage(workspace_storage: Path) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    if not workspace_storage.exists():
        return sessions

    for workspace_dir in workspace_storage.iterdir():
        state_db = workspace_dir / "state.vscdb"

        # VS Code historical format from state.vscdb keys.
        payloads = _read_sqlite_payloads(state_db)
        for payload in payloads:
            extracted = _extract_sessions(payload)
            for session in extracted:
                session_copy = dict(session)
                session_copy.setdefault("_source", str(state_db))
                session_copy.setdefault("_workspace_id", workspace_dir.name)
                sessions.append(session_copy)

        # VS Code newer format where sessions are persisted in chatSessions/*.jsonl.
        sessions.extend(_collect_from_chat_sessions_jsonl(workspace_dir, state_db))

    return sessions


def _collect_from_chat_json(paths: list[str]) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for item in paths:
        path = Path(item).expanduser().resolve()
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        extracted = _extract_sessions(payload)
        for session in extracted:
            session_copy = dict(session)
            session_copy.setdefault("_source", str(path))
            sessions.append(session_copy)
    return sessions


def _extract_user_text(request: dict[str, Any]) -> str:
    message = request.get("message")
    if isinstance(message, dict):
        text = message.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        parts = message.get("parts")
        if isinstance(parts, list):
            collected: list[str] = []
            for part in parts:
                if isinstance(part, dict):
                    part_text = part.get("text")
                    if isinstance(part_text, str) and part_text.strip():
                        collected.append(part_text.strip())
            if collected:
                return "\n".join(collected)
    return ""


def _extract_assistant_text(request: dict[str, Any]) -> str:
    response = request.get("response")
    collected: list[str] = []
    if isinstance(response, list):
        for item in response:
            if isinstance(item, dict):
                kind = item.get("kind")
                # Skip internal progress/thinking events and keep only user-visible answer payloads.
                if kind in {"thinking", "progressTaskSerialized", "mcpServersStarting"}:
                    continue
                value = item.get("value")
                if not isinstance(value, str) or not value:
                    continue
                if kind is None or kind in {"text", "markdown", "message", "final"}:
                    collected.append(value)
                    continue
                if "supportThemeIcons" in item or "supportHtml" in item:
                    collected.append(value)
            elif isinstance(item, str) and item.strip():
                collected.append(item)

    if not collected:
        return ""
    return "".join(collected).strip()


def _to_day_and_time(timestamp_ms: Any) -> tuple[str, str]:
    if isinstance(timestamp_ms, (int, float)):
        value = float(timestamp_ms)
        dt_value = dt.datetime.fromtimestamp(value / 1000.0)
        return dt_value.strftime("%Y-%m-%d"), dt_value.strftime("%H:%M:%S")
    return "", ""


def _extract_timestamp_ms(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _session_latest_timestamp(session: dict[str, Any]) -> float:
    requests = session.get("requests")
    if not isinstance(requests, list):
        return float("-inf")

    latest = float("-inf")
    for request in requests:
        if not isinstance(request, dict):
            continue
        ts = _extract_timestamp_ms(request.get("timestamp"))
        if ts is not None and ts > latest:
            latest = ts
    return latest


def _normalize_entries(
    sessions: list[dict[str, Any]],
    target_day: str | None,
    include_undated: bool,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for session in sessions:
        title = session.get("customTitle")
        if not isinstance(title, str) or not title.strip():
            title = "untitled"
        source = session.get("_source")
        if not isinstance(source, str):
            source = "unknown"

        requests = session.get("requests")
        if not isinstance(requests, list):
            continue

        for request in requests:
            if not isinstance(request, dict):
                continue

            day, time_text = _to_day_and_time(request.get("timestamp"))
            if target_day is not None:
                if day != target_day:
                    if not (include_undated and not day):
                        continue

            user_text = _extract_user_text(request)
            assistant_text = _extract_assistant_text(request)
            if not user_text and not assistant_text:
                continue

            request_id = request.get("requestId", "")
            if not isinstance(request_id, str):
                request_id = ""
            if not request_id and not user_text:
                continue

            entries.append(
                {
                    "day": day or target_day or "unknown",
                    "time": time_text or "unknown",
                    "title": title,
                    "source": source,
                    "requestId": request_id,
                    "user": user_text,
                    "assistant": assistant_text,
                }
            )

    entries.sort(key=lambda item: (item["time"], item["requestId"]))
    return entries


def _copy_text_to_clipboard(text: str) -> bool:
    candidates = [
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ]
    for cmd in candidates:
        try:
            completed = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                check=False,
                timeout=1,
            )
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue
        if completed.returncode == 0:
            return True
    return False


def _render_markdown(target_day: str, entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append(f"# Copilot Chat History {target_day}")
    lines.append("")
    lines.append("> Auto-generated by `.agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py`.")
    lines.append("")
    lines.append(f"- Entries: {len(entries)}")
    lines.append("")

    if not entries:
        lines.append("暂无匹配记录。")
        lines.append("")
        return "\n".join(lines)

    for idx, entry in enumerate(entries, start=1):
        lines.append(f"## {idx}. {entry['time']} | {entry['title']}")
        lines.append("")
        lines.append(f"- Source: `{entry['source']}`")
        if entry["requestId"]:
            lines.append(f"- RequestId: `{entry['requestId']}`")
        lines.append("")

        lines.append("### User")
        lines.append("")
        lines.append("~~~text")
        lines.append(entry["user"] or "(empty)")
        lines.append("~~~")
        lines.append("")

        lines.append("### Copilot")
        lines.append("")
        lines.append("~~~text")
        lines.append(entry["assistant"] or "(empty)")
        lines.append("~~~")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    target_day = args.day
    out_root = Path(args.output_root).expanduser().resolve()

    sessions: list[dict[str, Any]] = []
    if not args.no_workspace_scan:
        workspace_storage = Path(args.workspace_storage).expanduser().resolve()
        sessions.extend(_collect_from_workspace_storage(workspace_storage))

    sessions.extend(_collect_from_chat_json(args.chat_json))

    normalized_target_day: str | None = args.day
    selected_sessions = sessions
    if args.latest_session:
        selected_sessions = []
        latest = max(sessions, key=_session_latest_timestamp, default=None)
        if latest is not None:
            selected_sessions = [latest]
        normalized_target_day = None

    entries = _normalize_entries(
        sessions=selected_sessions,
        target_day=normalized_target_day,
        include_undated=args.include_undated,
    )

    out_dir = out_root / target_day
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = dt.datetime.now().strftime("%H%M%S")
    md_path = out_dir / f"copilot-chat-history-{stamp}.md"
    markdown_text = _render_markdown(target_day, entries)
    md_path.write_text(markdown_text, encoding="utf-8")

    print(f"markdown: {md_path}")
    print(f"entries: {len(entries)}")

    if args.copy_to_clipboard:
        copied = _copy_text_to_clipboard(markdown_text)
        print(f"clipboard: {'copied' if copied else 'unavailable'}")

    if args.write_raw:
        json_path = out_dir / f"copilot-chat-history-{stamp}.json"
        json_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"raw-json: {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
