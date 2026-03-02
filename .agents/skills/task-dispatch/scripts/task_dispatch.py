#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]+")


@dataclass
class Task:
    id: str
    title: str
    depends_on: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    effort: str = "M"
    parallel_safe: bool = True


def _normalize_task(raw: dict[str, Any], idx: int) -> Task:
    title = str(raw.get("title", "")).strip()
    if not title:
        raise ValueError(f"task[{idx}] missing required field: title")

    task_id = str(raw.get("id") or f"T{idx + 1}").strip()
    depends_on = [str(x).strip() for x in raw.get("depends_on", []) if str(x).strip()]
    tags = [str(x).strip().lower() for x in raw.get("tags", []) if str(x).strip()]
    effort = str(raw.get("effort", "M")).strip().upper() or "M"
    parallel_safe = bool(raw.get("parallel_safe", True))

    return Task(
        id=task_id,
        title=title,
        depends_on=depends_on,
        tags=tags,
        effort=effort,
        parallel_safe=parallel_safe,
    )


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _build_correlation(tasks: list[Task]) -> dict[str, dict[str, float]]:
    title_tokens = {t.id: _tokenize(t.title) for t in tasks}
    tag_tokens = {t.id: set(t.tags) for t in tasks}
    matrix: dict[str, dict[str, float]] = {}

    for t1 in tasks:
        row: dict[str, float] = {}
        for t2 in tasks:
            if t1.id == t2.id:
                row[t2.id] = 1.0
                continue
            title_score = _jaccard(title_tokens[t1.id], title_tokens[t2.id])
            tag_score = _jaccard(tag_tokens[t1.id], tag_tokens[t2.id])
            row[t2.id] = round((0.6 * title_score + 0.4 * tag_score), 4)
        matrix[t1.id] = row
    return matrix


def _validate_graph(tasks: list[Task]) -> None:
    ids = {t.id for t in tasks}
    if len(ids) != len(tasks):
        raise ValueError("duplicate task id detected")

    for t in tasks:
        unknown = [dep for dep in t.depends_on if dep not in ids]
        if unknown:
            raise ValueError(f"task {t.id} depends on unknown ids: {unknown}")


def _topological_batches(tasks: list[Task]) -> list[list[str]]:
    indegree: dict[str, int] = {t.id: 0 for t in tasks}
    outgoing: dict[str, list[str]] = defaultdict(list)

    for t in tasks:
        for dep in t.depends_on:
            outgoing[dep].append(t.id)
            indegree[t.id] += 1

    queue = deque(sorted([tid for tid, deg in indegree.items() if deg == 0]))
    batches: list[list[str]] = []
    visited = 0

    while queue:
        level_size = len(queue)
        batch: list[str] = []
        for _ in range(level_size):
            node = queue.popleft()
            batch.append(node)
            visited += 1
            for nxt in sorted(outgoing[node]):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        batches.append(batch)

    if visited != len(tasks):
        raise ValueError("dependency graph contains cycle; cannot derive top-down batches")

    return batches


def _execution_batches(tasks: list[Task], topo_levels: list[list[str]]) -> list[list[str]]:
    task_map = {t.id: t for t in tasks}
    batches: list[list[str]] = []

    for level in topo_levels:
        parallel_group: list[str] = []
        for tid in level:
            if task_map[tid].parallel_safe:
                parallel_group.append(tid)
                continue

            if parallel_group:
                batches.append(parallel_group)
                parallel_group = []
            batches.append([tid])

        if parallel_group:
            batches.append(parallel_group)

    return batches


def _select_primary_parent(task: Task, correlation: dict[str, dict[str, float]]) -> str | None:
    if not task.depends_on:
        return None
    return max(task.depends_on, key=lambda dep: correlation[task.id].get(dep, 0.0))


def _build_tree(tasks: list[Task], correlation: dict[str, dict[str, float]]) -> dict[str, Any]:
    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []

    for task in tasks:
        parent = _select_primary_parent(task, correlation)
        if parent is None:
            roots.append(task.id)
        else:
            children[parent].append(task.id)

    for key in children:
        children[key] = sorted(children[key])
    roots.sort()

    def build_node(task_id: str) -> dict[str, Any]:
        return {
            "id": task_id,
            "children": [build_node(cid) for cid in children.get(task_id, [])],
        }

    return {
        "id": "ROOT",
        "children": [build_node(rid) for rid in roots],
    }


def _agent_for_task(task: Task) -> str:
    # Current workspace only declares Explore as subagent.
    return "Explore"


def _effort_to_thoroughness(effort: str) -> str:
    mapping = {"S": "quick", "M": "medium", "L": "thorough"}
    return mapping.get(effort, "medium")


def _build_subagent_plan(tasks: list[Task], batches: list[list[str]]) -> list[dict[str, Any]]:
    task_map = {t.id: t for t in tasks}
    plan: list[dict[str, Any]] = []

    for index, batch in enumerate(batches, start=1):
        assignments = []
        for tid in batch:
            task = task_map[tid]
            assignments.append(
                {
                    "task_id": tid,
                    "task_title": task.title,
                    "agent": _agent_for_task(task),
                    "recommended_thoroughness": _effort_to_thoroughness(task.effort),
                    "can_run_parallel": task.parallel_safe,
                    "runSubagent_payload": {
                        "agentName": _agent_for_task(task),
                        "description": f"Task {tid}",
                        "prompt": (
                            f"请处理子任务 {tid}: {task.title}。"
                            "按仓库上下文收集证据，输出结论、风险与下一步建议。"
                        ),
                    },
                }
            )
        plan.append({"batch": index, "assignments": assignments})

    return plan


def _build_mermaid(tasks: list[Task]) -> str:
    lines = ["flowchart TD", "  ROOT([ROOT])"]

    for task in tasks:
        label = task.title.replace('"', "'")
        lines.append(f"  {task.id}[\"{task.id}: {label}\"]")

    for task in tasks:
        if task.depends_on:
            for dep in task.depends_on:
                lines.append(f"  {dep} --> {task.id}")
        else:
            lines.append(f"  ROOT --> {task.id}")

    return "\n".join(lines)


def _build_business_plan(tasks: list[Task], batches: list[list[str]]) -> dict[str, Any]:
    task_map = {t.id: t for t in tasks}
    stage_lines: list[str] = []

    for idx, batch in enumerate(batches, start=1):
        titles = [task_map[tid].title for tid in batch]
        stage_lines.append(f"阶段{idx}: {'；'.join(titles)}")

    return {
        "goal": "以最少人工介入完成任务拆解、并行执行与最终成果汇总。",
        "human_view": "仅查看最终成果与本业务计划，无需参与中间调度细节。",
        "stages": stage_lines,
        "success_criteria": [
            "全部批次执行完成并无阻塞依赖",
            "输出最终成果摘要与风险清单",
            "形成可直接复用的后续行动项",
        ],
    }


def _build_agent_execution_bundle(
    tasks: list[Task],
    batches: list[list[str]],
    workflow_mode: str,
) -> dict[str, Any]:
    task_map = {t.id: t for t in tasks}
    batch_items: list[dict[str, Any]] = []

    for idx, batch in enumerate(batches, start=1):
        assignments: list[dict[str, Any]] = []
        for tid in batch:
            task = task_map[tid]
            assignments.append(
                {
                    "task_id": tid,
                    "agentName": _agent_for_task(task),
                    "description": f"Task {tid}",
                    "thoroughness": _effort_to_thoroughness(task.effort),
                    "prompt": (
                        f"请处理子任务 {tid}: {task.title}。"
                        "按仓库上下文收集证据，输出可复核结论、关键风险和下一步建议。"
                    ),
                }
            )
        batch_items.append(
            {
                "batch": idx,
                "parallel": all(task_map[tid].parallel_safe for tid in batch),
                "assignments": assignments,
            }
        )

    return {
        "mode": workflow_mode,
        "copilot_tooling": {
            "delegation_tool": "agent",
            "execution_api": "runSubagent",
            "default_subagent": "Explore",
        },
        "human_policy": {
            "show_intermediate_details": False,
            "show_final_result_only": True,
            "show_compact_business_plan": True,
        },
        "batch_execution": batch_items,
        "final_synthesis_prompt": (
            "汇总所有子任务输出，生成最终结果、关键风险、决策建议，"
            "并附一份不超过 8 行的精简业务计划。"
        ),
    }


def generate_plan(tasks: list[Task], workflow_mode: str = "all-agent") -> dict[str, Any]:
    _validate_graph(tasks)
    correlation = _build_correlation(tasks)
    topo_levels = _topological_batches(tasks)
    batches = _execution_batches(tasks, topo_levels)
    tree = _build_tree(tasks, correlation)
    business_plan = _build_business_plan(tasks, batches)
    execution_bundle = _build_agent_execution_bundle(tasks, batches, workflow_mode)

    return {
        "workflow_mode": workflow_mode,
        "human_output": {
            "final_result_only": True,
            "compact_business_plan": business_plan,
        },
        "agent_execution_bundle": execution_bundle,
        "tasks": [t.__dict__ for t in tasks],
        "correlation_matrix": correlation,
        "tree": tree,
        "topological_levels": topo_levels,
        "parallel_batches": batches,
        "subagent_plan": _build_subagent_plan(tasks, batches),
        "mermaid": _build_mermaid(tasks),
    }


def _load_tasks(path: Path) -> list[Task]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("tasks file must be a JSON array")
    return [_normalize_task(raw, idx) for idx, raw in enumerate(data)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate top-down tree and parallel subagent dispatch plan from task dependencies."
    )
    parser.add_argument("--tasks-file", required=True, help="Path to task JSON array file.")
    parser.add_argument("--output", help="Optional output file path. If omitted, print JSON to stdout.")
    parser.add_argument(
        "--workflow-mode",
        choices=["all-agent", "hybrid"],
        default="all-agent",
        help="Dispatch mode. all-agent hides intermediate details for humans and emphasizes final-only delivery.",
    )
    args = parser.parse_args()

    tasks = _load_tasks(Path(args.tasks_file))
    plan = generate_plan(tasks, workflow_mode=args.workflow_mode)
    output_text = json.dumps(plan, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text + "\n", encoding="utf-8")
        print(f"dispatch plan written to: {output_path}")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
