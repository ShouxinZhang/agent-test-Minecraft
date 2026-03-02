# AGENTS 指南（agent-test-Minecraft 仓库版）

## 1. 语言与沟通
- 默认使用中文（zh-cn）。
- 输出优先给可运行结果，不只给方案。

## 2. 适用范围
- 本指南适用于 `agent-test-Minecraft`，当前主技术栈为 Node.js（Mineflayer + PaperMC）。
- 默认目标：优先保证 Minecraft 服务器、Agent 脚本、RL 脚本可运行与可复现。

## 3. 技能入口
- 技能目录：`.agents/skills/`
- 不在本文件维护技能清单；执行时由 agent 按任务语义自主发现并调用。
- 仅在新增“强约束”能力时，在本指南补充必要入口与约束说明。

## 4. 通用执行流程
1. 明确任务范围：先阅读 `README.md`、根目录配置文件与主要入口文件。
2. 识别技术栈：根据仓库实际语言与工具链选择命令，不假设固定框架。
3. 并行优先：对彼此独立的检索、阅读、分析任务，优先并行调用 `runSubagent`；仅在存在前后依赖时串行执行。
4. 最小化改动：只修改与任务直接相关的文件，避免无关重构。
5. 先验证后交付：至少执行一次与改动相关的本地检查或运行命令。

## 5. 本仓库入口命令
- 启动服务器：`./scripts/start-server.sh`
- 启动交互式 Agent：`./scripts/start-agent.sh`
- 运行自动研究：`./scripts/start-research.sh`
- Agent 语法检查：`cd agent && npm run check`
- RL 训练：`cd agent && npm run rl:train`
- RL 评估：`cd agent && npm run rl:eval`
- RL 可视化：`cd agent && npm run rl:viz`

## 6. 质量门禁（按技术栈执行）
- Node.js 代码改动：
	- `cd agent && npm run gate`
- 若涉及运行时逻辑（Agent 行为、RL）：
	- 服务器已启动时，执行至少一条 smoke 命令（`npm run research` 或 `npm run rl:eval`）。
- Python 脚本改动（仅限 `.agents/skills` 内工具）：
	- `python3 .agents/skills/python-quality-gate/scripts/python_gate.py --targets .agents/skills`
- 若门禁失败：先修复再继续功能开发或提交。

## 7. 架构与文档门禁（建议执行）
- 架构检查：
	- `python3 .agents/skills/architecture-guard/scripts/architecture_guard.py check-all`
- 导出架构报告：
	- `python3 .agents/skills/architecture-guard/scripts/architecture_guard.py report`
- 修改或新增文件后，更新工作区文档：
	- `python3 .agents/skills/workspace-docs/scripts/agent_docs.py set <path> -d "说明" -n "备注"`
	- `python3 .agents/skills/workspace-docs/scripts/agent_docs.py export`

## 8. 执行日志门禁（必须执行）
- 触发时机：
	- 接到任务并开始实际改动后，记录 1 条日志。
	- 完成改动并验证后，执行日志总览导出。
- 记录命令模板：
	- `python3 .agents/skills/agent-logs/scripts/agent_logs.py add --prompt "<用户原始prompt>" --summary "<上下文摘要与处理结果>" --git-op <yes|no> --git-detail "<git动作或未执行原因>" --isolated <yes|no> --backup <yes|no> --integrity-ok <yes|no> --consistency-ok <yes|no> --recoverability-ok <yes|no> --backup-note "<备份说明>" --auto-files`
- 导出命令：
	- `python3 .agents/skills/agent-logs/scripts/agent_logs.py export`
- 日志路径：
	- `docs/agent-logs/YYYY-MM-DD/log-xxxx-<HHMMSS>.md`
	- `docs/agent-logs/INDEX.md`
	- `docs/agent-logs/AGENT_LOGBOOK.md`

## 9. 提交前最小检查清单
- 关键入口命令至少成功运行一次（例如 `run`、`test`、`build` 中相关项）。
- 与技术栈对应的质量门禁已通过。
- README 与相关文档已同步。
- 执行日志已新增且已导出总览（`agent_logs.py add` + `agent_logs.py export`）。
- 若涉及架构调整，已输出 `docs/architecture/architecture_guard_report.md`。
