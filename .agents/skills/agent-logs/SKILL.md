---
name: agent-logs
description: '面向 agents 的执行日志技能。记录时间、用户原始 prompt、上下文摘要、文件改动、git 操作、模块化隔离与备份检查信息。'
---

# Agent Logs Skill

这个技能用于记录 agent 执行过程的关键审计信息，便于回溯、复盘和交接。

日志主存储为 Markdown 文件，直接落地在仓库根目录：`docs/agent-logs/`。
并按天做分区（文件夹分层），作为一个小型日志数仓。

数据库存储约定：
- `skills` 目录中的 `agent_logs.db` 仅作为空模板库（schema 模板）。
- 实际运行数据库位于 `docs/agent-logs/agent_logs.db`。

## 记录要点

1. 时间（通过 Linux `date` 命令获取）
2. 用户完整原始 prompt（不截断）
3. LLM 执行上下文精简总结
4. 改动文件列表
5. 是否执行 git 操作
6. 是否模块化隔离
7. 是否执行备份，以及备份三特性检查
8. 用户业务目标（便于回滚时理解“为什么改”）
9. 关键代码片段（复制粘贴的 Markdown，便于回滚时定位“改了什么”）
10. 关键代码上下文（位于哪个模块/文件、用于做什么）

## 备份三特性定义

这里默认采用以下三项检查：

1. `integrity_ok`：备份数据完整性通过（如校验和）
2. `consistency_ok`：备份数据一致性通过（逻辑一致）
3. `recoverability_ok`：备份可恢复性通过（可演练恢复）

## 命令用法

所有操作通过脚本完成：
`python3 .agents/skills/agent-logs/scripts/agent_logs.py <command> ...`

## 存储位置

- 分区目录：`docs/agent-logs/YYYY-MM-DD/`
- 单条日志：`docs/agent-logs/YYYY-MM-DD/log-xxxx-<HHMMSS>.md`
- 索引文件：`docs/agent-logs/INDEX.md`
- 分区索引：`docs/agent-logs/YYYY-MM-DD/INDEX.md`
- 总览导出：`docs/agent-logs/AGENT_LOGBOOK.md`

### 1. 新增日志

```bash
python3 .agents/skills/agent-logs/scripts/agent_logs.py add \
  --prompt "用户完整原始prompt" \
  --summary "本次LLM上下文摘要" \
  --biz-goal "让自动玩家能在无GUI模式下验证默认关卡可通关" \
  --key-change-module ".agents/skills/python-quality-gate/scripts/python_gate.py" \
  --key-change-purpose "在质量门禁里执行功能测试与自动通关验证，保证游戏规则与可通关性" \
  --key-change-md "### 关键改动1: 自动通关断言\n\n```python\nresult = run_autoplay(assert_optimal=True)\nassert result.success\n```" \
  --git-op yes \
  --git-detail "执行了 git add 和 git commit" \
  --isolated yes \
  --backup yes \
  --integrity-ok yes \
  --consistency-ok yes \
  --recoverability-ok no \
  --backup-note "未做恢复演练" \
    --auto-files \
    --new-changes-only
```

说明：
- `--auto-files`：自动抓取当前 git 变更文件（已跟踪变更+未跟踪文件）
  - `--new-changes-only`：仅记录相对最近一条日志“新增”的变更文件（差集），避免把历史遗留脏文件反复写入每条日志
- 也可用 `--files` 手工传入文件列表
- `--biz-goal`：记录本次改动的用户业务目标
- `--key-change-module`：关键代码所在模块/文件（建议写仓库相对路径）
- `--key-change-purpose`：关键代码用途（解决什么业务目标）
- `--key-change-md`：直接粘贴关键代码片段（Markdown）
- `--key-change-md-file`：从文件读取关键代码片段（Markdown）

建议：关键代码片段必须同时填写 `--key-change-module` 和 `--key-change-purpose`，否则回滚时仍需要二次定位。

校验规则：当传入 `--key-change-md` 或 `--key-change-md-file` 时，脚本会强制要求同时传入 `--key-change-module` 与 `--key-change-purpose`。

### 2. 查看单条日志

```bash
python3 .agents/skills/agent-logs/scripts/agent_logs.py get 1
```

### 3. 列出最近日志

```bash
python3 .agents/skills/agent-logs/scripts/agent_logs.py list --limit 20
```

### 4. 导出 Markdown 总览

```bash
python3 .agents/skills/agent-logs/scripts/agent_logs.py export
```

默认导出到：`docs/agent-logs/AGENT_LOGBOOK.md`
