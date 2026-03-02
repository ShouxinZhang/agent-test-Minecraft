#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from task_dispatch import _load_tasks, generate_plan


def _build_runbook(plan: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = plan["agent_execution_bundle"]
    runbook: list[dict[str, Any]] = []

    for batch in bundle["batch_execution"]:
        runbook.append(
            {
                "batch": batch["batch"],
                "parallel": batch["parallel"],
                "calls": [
                    {
                        "tool": "runSubagent",
                        "payload": {
                            "agentName": assignment["agentName"],
                            "description": assignment["description"],
                            "prompt": assignment["prompt"],
                        },
                    }
                    for assignment in batch["assignments"]
                ],
            }
        )

    return runbook


def _render_human_brief(plan: dict[str, Any], outputs: dict[str, Any] | None) -> str:
    business = plan["human_output"]["compact_business_plan"]
    lines = [
        "# Final Outcome",
        "",
        "- 目标: " + business["goal"],
        "- 人类视角: " + business["human_view"],
        "",
        "## Business Plan",
        "",
    ]

    for item in business["stages"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Success Criteria", ""])
    for criterion in business["success_criteria"]:
        lines.append(f"- {criterion}")

    lines.extend(["", "## Final Synthesis", ""])
    if outputs is None:
        lines.append("- 尚未提供 subagent 结果，请在完成批次执行后重新生成简报。")
    else:
        lines.append("- 结果摘要: " + str(outputs.get("final_result", "(未提供)")))
        risks = outputs.get("risks", [])
        lines.append("- 关键风险: " + ("；".join(str(x) for x in risks) if risks else "无"))
        next_steps = outputs.get("next_steps", [])
        lines.append("- 下一步: " + ("；".join(str(x) for x in next_steps) if next_steps else "无"))

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "One-click orchestrator for Copilot all-agent workflow: "
            "generate dispatch plan, runbook and concise human brief."
        )
    )
    parser.add_argument("--tasks-file", required=True, help="Path to task JSON array file.")
    parser.add_argument("--out-dir", required=True, help="Output directory for orchestrated artifacts.")
    parser.add_argument(
        "--workflow-mode",
        choices=["all-agent", "hybrid"],
        default="all-agent",
        help="Workflow mode passed to task dispatch planner.",
    )
    parser.add_argument(
        "--results-file",
        help=(
            "Optional JSON file with synthesized subagent outcomes. "
            "Fields: final_result, risks(list), next_steps(list)."
        ),
    )
    args = parser.parse_args()

    tasks = _load_tasks(Path(args.tasks_file))
    plan = generate_plan(tasks, workflow_mode=args.workflow_mode)
    runbook = _build_runbook(plan)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dispatch_path = out_dir / "dispatch_plan.json"
    dispatch_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    runbook_path = out_dir / "copilot_runbook.json"
    runbook_path.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_payload: dict[str, Any] | None = None
    if args.results_file:
        result_payload = json.loads(Path(args.results_file).read_text(encoding="utf-8"))

    brief_path = out_dir / "final_brief.md"
    brief_path.write_text(_render_human_brief(plan, result_payload), encoding="utf-8")

    print(f"orchestration artifacts generated in: {out_dir}")
    print(f"- {dispatch_path.name}")
    print(f"- {runbook_path.name}")
    print(f"- {brief_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
