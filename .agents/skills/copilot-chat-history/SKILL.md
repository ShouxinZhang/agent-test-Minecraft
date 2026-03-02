---
name: copilot-chat-history
description: '导出 VS Code GitHub Copilot Chat 会话并按天归档到 docs/copilotChatHistory。支持 chat.json、workspaceStorage/state.vscdb 与 chatSessions/*.jsonl。'
---

# Copilot Chat History Skill

这个技能用于把 GitHub Copilot Chat 记录按天导出到：`docs/copilotChatHistory/YYYY-MM-DD/`。

默认支持 Linux 下 VS Code 存储目录：`~/.config/Code/User/workspaceStorage/`，兼容 `state.vscdb` 与 `chatSessions/*.jsonl` 两种会话格式，也支持你手动导出的 `chat.json`。

## 何时使用

1. 每天收工前导出当天 Copilot 对话，便于写日报/周报。
2. 需要把会话归档进仓库文档目录，方便检索与回溯。
3. 想把多个 `chat.json` 合并为同一天的一份 Markdown 摘要。

## 命令

统一命令入口：

```bash
python3 .agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py [options]
```

### 0) 一键复制最新 Session（推荐）

```bash
./.agents/skills/copilot-chat-history/scripts/copy_latest_session.sh
```

这个命令会：
- 自动选择最新会话（latest session）
- 生成 markdown/json 归档到 `docs/copilotChatHistory/YYYY-MM-DD/`
- 尝试复制 markdown 到系统剪贴板

### 1) 导出“今天”聊天（默认）

```bash
python3 .agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py
```

### 2) 指定导出日期

```bash
python3 .agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py --day 2026-03-02
```

### 3) 仅从手工导出的 chat.json 导出

```bash
python3 .agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py \
  --no-workspace-scan \
  --chat-json chat.json
```

### 4) 同时保留原始 JSON 汇总

```bash
python3 .agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py --write-raw
```

### 5) 只导出最新 Session（可组合复制）

```bash
python3 .agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py \
  --latest-session \
  --copy-to-clipboard \
  --write-raw
```

## 输出文件

每次执行会在 `docs/copilotChatHistory/<day>/` 生成（`<day>` 为 `YYYY-MM-DD`）：

- `copilot-chat-history-<HHMMSS>.md`：可读 Markdown 汇总
- `copilot-chat-history-<HHMMSS>.json`：结构化条目（仅在 `--write-raw` 时）

## 说明

1. 若 VS Code 版本变更导致底层存储键名变化，脚本可能只导出到部分记录；建议并行提供 `--chat-json`。
2. 若某条记录没有时间戳，默认跳过；可加 `--include-undated` 兜底保留。
3. 脚本会尽量兼容不同会话 JSON 结构，不依赖固定单一格式。
