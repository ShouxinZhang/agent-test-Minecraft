# 仓库结构说明

本文件用于说明 `agent-test-Minecraft` 的模块边界与入口约定。

## 顶层模块
- `agent/`: Mineflayer Agent 与 RL 训练/评估逻辑。
- `server/`: PaperMC 服务器配置与运行时世界数据。
- `.agents/`: Agent 技能与自动化门禁脚本。
- `scripts/`: 统一启动入口脚本（推荐使用）。
- `docs/`: 架构/日志/仓库文档。

## 启动入口约定
- 统一入口：
  - `./scripts/start-server.sh`
  - `./scripts/start-agent.sh`
  - `./scripts/start-research.sh`

## 变更原则
- 新增可执行脚本优先放入 `scripts/`。
- 根目录不放启动脚本，避免入口分散。
- `agent/` 与 `server/` 的运行时代码和配置不要交叉放置。
