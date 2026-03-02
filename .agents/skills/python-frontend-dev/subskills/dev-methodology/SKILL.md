---
name: python-frontend-dev-methodology
description: 'Python GUI 模块化开发方法论：可读、可测、可由 agent 精准修改。'
---

# Python GUI Development Methodology

## 目标

让 GUI 代码与界面结构一致，便于人类维护，也便于 agent 自动修改。

## 推荐架构（最小可行）

1. `core/`：纯业务规则，不依赖 GUI 框架。
2. `ui/viewmodels/`：状态映射与展示逻辑。
3. `ui/views/`：控件创建与渲染。
4. `ui/actions/`：用户动作命令（点击、按键、切换）。
5. `ui/theme.py`：字体、间距、颜色等设计令牌。

## 工程约束

1. 视图层不写业务规则，只发动作。
2. 动作层不直接操作控件树，只改状态并触发重绘。
3. 业务层不依赖 tkinter/qt/flet 包。
4. 每个 UI 组件保持稳定命名，避免匿名散落。
5. 新增交互时同步补充结构断言与行为测试。

## 对 Agent 友好的规范

1. 函数名表达 UI 意图，如 `_toggle_optimal_path`、`_restart_game`。
2. 控件句柄在初始化时集中声明，避免动态隐式创建。
3. 把魔法数字抽到常量，减少 agent 修改时的误伤。
4. 提供单一入口脚本，方便 gate 和 subagent 调用。

## 最小落地清单

1. 抽离 `actions` 与 `renderer`。
2. 统一 theme 常量。
3. 增加 UI 快照门禁并纳入 CI。
