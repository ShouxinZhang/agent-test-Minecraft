#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict

def _project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent.parent.parent.parent.parent


PROJECT_ROOT = _project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pixel_coin_game.level import DEFAULT_LEVEL_LINES, parse_level  # noqa: E402
from pixel_coin_game.ui_tk import PixelCoinGameApp  # noqa: E402


class CanvasCounts(TypedDict):
    rectangle: int
    oval: int
    line: int
    other: int


class LayoutSnapshot(TypedDict):
    canvas_width: int
    canvas_height: int
    status_height: int
    button_width: int
    button_height: int


class UISnapshot(TypedDict):
    status: str
    button_text: str
    show_optimal_path: bool
    steps: int
    collected: int
    player: list[int]
    canvas_counts: CanvasCounts
    layout: LayoutSnapshot


class GateSnapshot(TypedDict):
    version: int
    level_size: list[int]
    scenarios: dict[str, UISnapshot]


def _count_canvas_items(app: PixelCoinGameApp) -> CanvasCounts:
    rectangle = 0
    oval = 0
    line = 0
    other = 0

    for item in app.canvas.find_all():
        kind = str(app.canvas.type(item))
        if kind == "rectangle":
            rectangle += 1
        elif kind == "oval":
            oval += 1
        elif kind == "line":
            line += 1
        else:
            other += 1

    return {
        "rectangle": rectangle,
        "oval": oval,
        "line": line,
        "other": other,
    }


def _layout_snapshot(app: PixelCoinGameApp) -> LayoutSnapshot:
    app.root.update_idletasks()
    return {
        "canvas_width": int(app.canvas.cget("width")),
        "canvas_height": int(app.canvas.cget("height")),
        "status_height": app.status_label.winfo_height(),
        "button_width": app.path_toggle_btn.winfo_width(),
        "button_height": app.path_toggle_btn.winfo_height(),
    }


def _ui_snapshot(app: PixelCoinGameApp) -> UISnapshot:
    app.root.update_idletasks()
    app.root.update()
    return {
        "status": app.status_var.get(),
        "button_text": app.path_btn_text.get(),
        "show_optimal_path": app.show_optimal_path,
        "steps": app.session.steps,
        "collected": app.session.collected_count,
        "player": list(app.session.player),
        "canvas_counts": _count_canvas_items(app),
        "layout": _layout_snapshot(app),
    }


def _assert_layout_consistency(snap: UISnapshot, expected_canvas_w: int, expected_canvas_h: int) -> None:
    layout = snap["layout"]
    assert layout["canvas_width"] == expected_canvas_w
    assert layout["canvas_height"] == expected_canvas_h
    assert layout["status_height"] > 0
    assert layout["button_width"] > 0
    assert layout["button_height"] > 0


def _simulate_key(app: PixelCoinGameApp, keysym: str, char: str = "") -> None:
    _ = char
    app.root.event_generate(f"<KeyPress-{keysym}>")
    app.root.update_idletasks()
    app.root.update()


def build_scenarios() -> GateSnapshot:
    level = parse_level(DEFAULT_LEVEL_LINES)
    app = PixelCoinGameApp(level)

    try:
        app.root.update_idletasks()
        app.root.update()

        initial = _ui_snapshot(app)
        _assert_layout_consistency(initial, level.width * 40, level.height * 40)

        app.path_toggle_btn.invoke()
        with_path = _ui_snapshot(app)

        _simulate_key(app, "Right")
        _simulate_key(app, "r")
        restarted = _ui_snapshot(app)

        scenarios: dict[str, UISnapshot] = {
            "initial": initial,
            "with_optimal_path": with_path,
            "restarted": restarted,
        }

        # Behavior assertions for deterministic gate.
        assert scenarios["initial"]["show_optimal_path"] is False
        assert scenarios["initial"]["canvas_counts"]["line"] == 0

        assert scenarios["with_optimal_path"]["show_optimal_path"] is True
        assert scenarios["with_optimal_path"]["canvas_counts"]["line"] > 0
        assert scenarios["with_optimal_path"]["button_text"] == "隐藏最优路径"

        assert scenarios["restarted"]["steps"] == 0
        assert scenarios["restarted"]["collected"] == 0
        assert tuple(scenarios["restarted"]["player"]) == level.start
        assert str(scenarios["restarted"]["status"]).startswith("已重开")

        return {
            "version": 1,
            "level_size": [level.width, level.height],
            "scenarios": scenarios,
        }
    finally:
        app.root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Python frontend UI quality gate.")
    parser.add_argument("--update-baseline", action="store_true", help="Write current snapshot as baseline.")
    args = parser.parse_args()

    root = PROJECT_ROOT
    baseline_path = (
        root
        / ".agents"
        / "skills"
        / "python-frontend-dev"
        / "subskills"
        / "quality-gate"
        / "baseline"
        / "pixel_coin_ui_snapshot.json"
    )

    try:
        current = build_scenarios()
    except Exception as exc:  # pragma: no cover - runtime environment dependent.
        print(f"[ui-quality-gate] failed to run scenarios: {exc}", file=sys.stderr)
        return 2

    if args.update_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ui-quality-gate] baseline updated: {baseline_path}")
        return 0

    if not baseline_path.is_file():
        print(
            "[ui-quality-gate] baseline not found, run with --update-baseline first.",
            file=sys.stderr,
        )
        return 2

    expected = json.loads(baseline_path.read_text(encoding="utf-8"))
    if expected != current:
        print("[ui-quality-gate] snapshot mismatch detected.", file=sys.stderr)
        print("[ui-quality-gate] expected:")
        print(json.dumps(expected, ensure_ascii=False, indent=2))
        print("[ui-quality-gate] current:")
        print(json.dumps(current, ensure_ascii=False, indent=2))
        return 1

    print("[ui-quality-gate] passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
