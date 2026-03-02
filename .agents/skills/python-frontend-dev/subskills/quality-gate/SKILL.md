---
name: python-frontend-ui-quality-gate
description: 'Python GUI 质量门禁：结构快照 + 交互回放 + 布局一致性。'
---

# Python Frontend UI Quality Gate

该子技能用于建立前端回归门禁，目标是把 GUI 改动变为可自动验证。

## 三层门禁

1. 结构快照：检查控件与画布元素是否存在，状态是否符合预期。
2. 交互回放：模拟按键/按钮，验证状态变化链路。
3. 布局一致性：检查关键控件尺寸与画布规格是否稳定。

## 入口脚本

`subskills/quality-gate/scripts/ui_quality_gate.py`

## 执行方式

1. 初始化或更新基线：
```bash
python3 .agents/skills/python-frontend-dev/subskills/quality-gate/scripts/ui_quality_gate.py --update-baseline
```

2. 日常门禁校验：
```bash
python3 .agents/skills/python-frontend-dev/subskills/quality-gate/scripts/ui_quality_gate.py
```

3. 通过仓库总门禁联动执行（推荐）：
```bash
python3 .agents/skills/python-quality-gate/scripts/python_gate.py
```

## CI 建议

Linux 无桌面环境时，使用 Xvfb：

```bash
xvfb-run -a -s "-screen 0 1280x720x24" python3 .agents/skills/python-frontend-dev/subskills/quality-gate/scripts/ui_quality_gate.py
```

## 失败产物

脚本会输出失败原因与当前快照内容，便于 agent 自动定位 UI 回归点。
