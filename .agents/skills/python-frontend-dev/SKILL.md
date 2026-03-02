---
name: python-frontend-dev
description: 'Python 前端开发总技能：模块化开发方法论 + UI 质量门禁（快照/交互/布局一致性）。'
---

# Python Frontend Development Skill

该技能面向 Python GUI 项目，提供两类可组合子技能：

1. 开发方法论（subskills/dev-methodology）
2. 质量门禁（subskills/quality-gate）

## 适用场景

1. 你希望把 GUI 开发从“事件回调堆积”改造成可维护模块。
2. 你希望 agent 能自动、精准地修改 UI，而不是“碰运气改代码”。
3. 你希望在现有后端门禁之外，加入前端可回归质量门禁。

## 子技能入口

1. `subskills/dev-methodology/SKILL.md`
2. `subskills/quality-gate/SKILL.md`

## 快速执行

```bash
python3 .agents/skills/python-frontend-dev/subskills/quality-gate/scripts/ui_quality_gate.py --update-baseline
python3 .agents/skills/python-frontend-dev/subskills/quality-gate/scripts/ui_quality_gate.py
```

说明：
- 第 1 条命令用于创建/更新 UI 基线快照。
- 第 2 条命令用于日常门禁校验，发现回归会返回非 0。
