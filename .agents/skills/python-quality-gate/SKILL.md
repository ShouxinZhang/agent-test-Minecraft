---
name: python-quality-gate
description: '通用 Python 开发门禁技能。统一执行 Ruff 与 Pyright，并支持多目录目标与自动发现。'
---

# Python Quality Gate Skill

这个技能用于统一执行 Python 质量门禁，默认一次性执行：
- `ruff check`
- `pyright`
- skills strict 类型门禁（CI 默认开启，使用独立配置）
- skills 专项门禁（若存在 `.agents/skills/`）：
  - `python -m compileall .agents/skills`
  - 前端 UI 门禁脚本（若存在）
- 功能门禁（两段式）：
  - 机械门禁单元测试
  - 智能动态测试（agent 模拟人类使用软件）

## LLM Agent 自主功能测试要求（强制）

1. 质量门禁不仅检查静态质量，还要由 agent 自主执行功能测试。
2. 对游戏项目，必须覆盖全部核心规则并验证可正常通关。
3. 游戏项目门禁至少包含：
  - 规则测试（移动、碰撞、奖励收集、状态判定）
  - 自动玩家无 GUI 通关验证
  - 最短路径或最优性校验（若规则要求）
4. 若游戏项目缺失上述测试入口，门禁应失败而非跳过。
5. 项目应在模块层级内置可调用技能脚本，不应仅依赖 `.agents/`。

## 模块内置技能约定（游戏）

推荐在游戏模块内提供：
- `<game_module>/skills/SKILL.md`
- `<game_module>/skills/scripts/mechanical_gate.py`
- `<game_module>/skills/scripts/dynamic_agent_playtest.py`
- `<game_module>/skills/scripts/build_subagent_test_plan.py`
- `<game_module>/tests/test_*.py`

测试目录约束：
- 游戏模块应保持自封闭，测试默认放在 `<game_module>/tests/`。
- 根目录 `tests/` 仅用于跨模块或工作区级集成测试。

其中动态测试脚本应支持主 agent 将任务分发给 subagents（如 `runSubagent`）并汇总结果。

## 何时使用

1. 提交代码前做质量门禁检查。
2. 新建模块后快速验证 lint 与类型检查。
3. 在 CI 前本地预检。

## 命令

### 1) 默认执行全部门禁

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py
```

### 2) 指定检测文件夹

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py --targets src sandbox
```

说明：
- `--targets` 支持一个或多个目录，例如 `--targets src` 或 `--targets src sandbox`。
- 默认同时执行 Ruff、Pyright、skills 专项门禁与功能门禁，任一失败即返回非 0。

### 3) 跳过功能门禁（仅在必要时）

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py --skip-functional
```

### 4) 跳过 Skills 专项门禁（仅在必要时）

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py --skip-skill-gates
```

### 5) 跳过前端 UI 门禁（仅在必要时）

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py --skip-ui-gate
```

### 6) skills strict 类型门禁（CI 默认开启）

配置文件：
- `.agents/skills/python-quality-gate/pyrightconfig.skills-strict.json`

本地手动开启：

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py --strict-skills
```

临时跳过：

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py --skip-strict-skills
```

说明：
- 当环境变量 `CI=1/true/yes/on` 时，strict 类型门禁默认开启。
- strict 配置与常规 pyright 分离，便于按脚本成熟度逐步扩展覆盖范围。

### 7) 增加 agent 自定义功能命令

```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py \
  --functional-cmd "python -m unittest pixel_coin_game.tests.test_pixel_coin_game -v" \
  --functional-cmd "python -m pixel_coin_game --autoplay --no-gui --assert-optimal"
```

## 兼容入口

- 项目内可继续使用 `./check_errors.sh`，其已委托到本技能脚本。
