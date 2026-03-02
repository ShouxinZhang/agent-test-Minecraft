---
name: shared-python-env
description: '为多仓库复用重型 Python 依赖（如 PyTorch）提供公共环境技能，含主机配置采集、共享环境初始化和项目接入。'
---

# Shared Python Environment Skill

这个技能用于解决“每个仓库重复安装大包”的问题，目标是：

1. 在 `~/Documents/GitHub` 下维护一个公共重包环境
2. 采集本机 CPU/内存/GPU 信息，便于选择合适的 CUDA 与 PyTorch 组合
3. 为任意项目创建轻量 `.venv` 并接入公共重包目录

## 目录约定

- 公共根目录：`~/Documents/GitHub/.shared-python-envs`
- 公共环境目录（默认）：`~/Documents/GitHub/.shared-python-envs/py314-torch-cu130`
- 主机报告目录：`~/Documents/GitHub/.shared-python-envs/reports`

## 本机配置快照

- 已落盘文件：`.agents/skills/shared-python-env/HOST_PROFILE.md`
- 用途：作为该主机的 CPU/内存/GPU/CUDA 基准，指导共享环境默认参数

## 何时使用

1. 新机器初始化 AI/PyTorch 开发环境
2. 多个仓库都要使用相同重型依赖（`torch`、`torchvision` 等）
3. 想固定“统一基础环境 + 项目轻量隔离”的开发模式

## 命令

脚本位置：`.agents/skills/shared-python-env/scripts/setup_shared_env.sh`

### 1) 初始化公共环境（推荐）

```bash
bash .agents/skills/shared-python-env/scripts/setup_shared_env.sh init
```

默认会：

1. 采集并保存主机信息（CPU/内存/GPU/驱动）
2. 使用 `python3.14` 创建共享环境
3. 安装最新稳定组合（默认 `torch torchvision torchaudio` + `cu130` index）

### 2) 仅采集主机信息并更新快照（不安装包）

```bash
bash .agents/skills/shared-python-env/scripts/setup_shared_env.sh inspect
```

该命令会：

1. 在 `~/Documents/GitHub/.shared-python-envs/reports` 生成完整主机报告
2. 更新 `.agents/skills/shared-python-env/HOST_PROFILE.md`
3. 不创建/安装任何 Python 包

### 3) 查看环境状态

```bash
bash .agents/skills/shared-python-env/scripts/setup_shared_env.sh doctor
```

### 4) 为某个项目创建轻量 venv 并接入共享重包

```bash
bash .agents/skills/shared-python-env/scripts/setup_shared_env.sh attach /abs/path/to/project
```

接入后：

1. 项目生成 `project/.venv`
2. 自动写入 `.pth` 指向共享环境 `site-packages`
3. 该项目可直接 `import torch`，无需重复安装

## 可选环境变量

- `SHARED_ROOT`: 共享根目录（默认 `~/Documents/GitHub/.shared-python-envs`）
- `SHARED_ENV_NAME`: 共享环境名（默认 `py314-torch-cu130`）
- `PYTHON_BIN`: Python 可执行路径（默认 `python3.14`）
- `TORCH_INDEX_URL`: PyTorch 轮子源（默认 `https://download.pytorch.org/whl/cu130`）

## 注意事项

1. 若 GPU 驱动不满足 CUDA 13，请切到 `cu128` 或 `cu126`。
2. `torch.jit` 在 Python 3.14 上不建议作为新项目路径，优先 `torch.compile`。
3. `.pth` 共享方案适合“统一重包版本”；若项目版本冲突明显，建议单独环境。
