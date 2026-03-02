---
name: task-dispatch
description: '基于任务相关性分析，生成自上而下 tree 结构与并行分发批次，并映射到 subagents 执行计划。'
---

# Task Dispatch Skill

这个技能用于把一个复杂任务拆解为可执行的子任务图，并给出：

1. 任务相关性分析（关键词/标签重合度）
2. 自上而下的 Tree 结构（主依赖树）
3. 可并行执行批次（Topological Levels）
4. Subagents 分发建议（默认映射到 `Explore`）

默认面向 GitHub Copilot Chat 的工具链：
- 委派工具：`agent`
- 子代理执行：`runSubagent`
- 默认子代理：`Explore`

## 工作流模式

1. `all-agent`（默认）
- 人类只看最终成果 + 精简业务计划。
- 中间拆解与调度细节由 agent 自动处理。

2. `hybrid`
- 保留 agent 自动分发，但允许人工查看更多中间信息。

## 适用场景

1. 一个需求同时涉及多个模块，需要并行探索。
2. 你希望先建“任务树”，再按层次推进。
3. 你要把任务自动转换为可执行的 `runSubagent` 调用清单。

## 输入格式

脚本接收一个 JSON 文件，结构如下：

```json
[
  {
    "id": "T1",
    "title": "梳理数据模型",
    "depends_on": [],
    "tags": ["db", "schema"],
    "effort": "M",
    "parallel_safe": true
  },
  {
    "id": "T2",
    "title": "验证接口读取路径",
    "depends_on": ["T1"],
    "tags": ["api", "read"],
    "effort": "S",
    "parallel_safe": true
  }
]
```

字段说明：
- `id`: 任务 ID（可选，缺省自动生成）
- `title`: 任务标题（必填）
- `depends_on`: 依赖任务 ID 列表（可选）
- `tags`: 标签列表（可选）
- `effort`: 规模（可选，`S/M/L`）
- `parallel_safe`: 是否允许并行（可选，默认 `true`）

## 运行命令

```bash
python3 .agents/skills/task-dispatch/scripts/task_dispatch.py \
  --tasks-file /tmp/tasks.json \
  --workflow-mode all-agent \
  --output /tmp/dispatch-plan.json
```

一键编排器（生成调度产物 + 人类最终简报）：

```bash
python3 .agents/skills/task-dispatch/scripts/orchestrate_workflow.py \
  --tasks-file /tmp/tasks.json \
  --workflow-mode all-agent \
  --out-dir /tmp/orchestrated
```

## 输出内容

输出 JSON 包含：
- `workflow_mode`: 当前工作流模式
- `human_output`: 给人类看的最终输出层（默认仅最终成果 + 精简业务计划）
- `agent_execution_bundle`: 面向 Copilot `agent/runSubagent` 的执行载荷
- `correlation_matrix`: 任务相关性矩阵
- `tree`: `ROOT` 为根的主依赖树
- `topological_levels`: 原始拓扑层（仅依赖关系）
- `parallel_batches`: 可执行批次（会将 `parallel_safe=false` 任务拆分为串行批次）
- `subagent_plan`: 每个批次的 subagent 分发建议
- `mermaid`: 可视化图（flowchart）

## 建议用法

1. 先用该技能产出任务树与并行批次。
2. 按 `parallel_batches` 分批调用 `runSubagent`。
3. 每批结束后回填新发现依赖，再重新规划一次。
