---
name: node-quality-gate
description: Node.js 项目质量门禁技能。用于在本仓库中执行 Agent 与 RL 脚本的语法检查与可选 smoke 检查。
---

# Node 质量门禁

## 适用场景
- 修改 `agent/*.js` 或 `agent/rl/*.js` 后做快速门禁。
- 需要在提交前确认核心脚本至少可通过语法检查。

## 执行命令
- 基础门禁（推荐）：
  - `bash .agents/skills/node-quality-gate/scripts/node_gate.sh`
- 仅语法检查：
  - `cd agent && npm run check`

## 说明
- 脚本会优先执行 `cd agent && npm run gate`。
- 如果检测到 `25565` 端口有 Minecraft 服务器监听，会额外执行一次 `npm run research` 作为 smoke 检查。
- 若未检测到服务器，smoke 检查会自动跳过，不影响门禁通过。
