#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


COMMON_TARGET_DIRS = ("src", "sandbox", "app", "apps", "lib", "tests", "pixel_coin_game")


def _project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent.parent.parent


def _discover_targets(project_root: Path) -> list[str]:
    targets = [name for name in COMMON_TARGET_DIRS if (project_root / name).is_dir()]

    skills_dir = project_root / ".agents" / "skills"
    if skills_dir.is_dir():
        targets.append(".agents/skills")

    return targets if targets else ["."]


def _run(cmd: list[str], cwd: Path) -> int:
    completed = subprocess.run(cmd, cwd=str(cwd), check=False)
    return completed.returncode


def _check_tool_installed(tool: str) -> bool:
    return shutil.which(tool) is not None


def _is_ci_env() -> bool:
    return os.getenv("CI", "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run generic Python quality gates (Ruff + Pyright).")
    parser.add_argument(
        "--targets",
        nargs="+",
        help="Directories/files to check. If omitted, auto-discover common Python source folders.",
    )
    parser.add_argument("--skip-ruff", action="store_true", help="Skip Ruff linting.")
    parser.add_argument("--skip-pyright", action="store_true", help="Skip Pyright type checking.")
    parser.add_argument(
        "--skip-functional",
        action="store_true",
        help="Skip repository functional checks (unittest and project-specific runtime gates).",
    )
    parser.add_argument(
        "--skip-skill-gates",
        action="store_true",
        help="Skip additional skill-specific gates (compileall and UI quality gate).",
    )
    parser.add_argument(
        "--skip-ui-gate",
        action="store_true",
        help="Skip python-frontend-dev UI gate if the script exists.",
    )
    parser.add_argument(
        "--strict-skills",
        action="store_true",
        help="Force-enable strict Pyright gate for selected skill scripts.",
    )
    parser.add_argument(
        "--skip-strict-skills",
        action="store_true",
        help="Skip strict Pyright gate for skill scripts.",
    )
    parser.add_argument(
        "--functional-cmd",
        action="append",
        default=[],
        help=(
            "Additional functional gate command executed by agent-driven workflow. "
            "Can be passed multiple times. Example: --functional-cmd 'python -m pytest -q'"
        ),
    )
    args = parser.parse_args()

    if args.skip_ruff and args.skip_pyright:
        print("No checks selected: both Ruff and Pyright are skipped.", file=sys.stderr)
        return 2

    root = _project_root()
    targets = args.targets if args.targets else _discover_targets(root)
    strict_skills_enabled = (args.strict_skills or _is_ci_env()) and not args.skip_strict_skills

    print(f"Quality gate targets: {' '.join(targets)}")

    overall_status = 0

    if not args.skip_ruff:
        if not _check_tool_installed("ruff"):
            print("Ruff is not installed or not in PATH.", file=sys.stderr)
            overall_status = 1
        else:
            print("Running Ruff linter...")
            ruff_status = _run(["ruff", "check", *targets], cwd=root)
            overall_status = max(overall_status, ruff_status)

    if not args.skip_pyright:
        if not _check_tool_installed("pyright"):
            print("Pyright is not installed or not in PATH.", file=sys.stderr)
            overall_status = 1
        else:
            print("Running Pyright type checker...")
            pyright_status = _run(["pyright", *targets], cwd=root)
            overall_status = max(overall_status, pyright_status)

            if strict_skills_enabled:
                strict_config = root / ".agents" / "skills" / "python-quality-gate" / "pyrightconfig.skills-strict.json"
                if strict_config.is_file():
                    print("Running strict Pyright gate for skills...")
                    strict_status = _run(["pyright", "--project", str(strict_config)], cwd=root)
                    overall_status = max(overall_status, strict_status)
                else:
                    print("Strict skills gate skipped: strict config not found.")

    if not args.skip_skill_gates:
        skills_root = root / ".agents" / "skills"
        if skills_root.is_dir():
            print("Running skill scripts compile gate...")
            compile_status = _run([sys.executable, "-m", "compileall", ".agents/skills"], cwd=root)
            overall_status = max(overall_status, compile_status)

            if not args.skip_ui_gate:
                ui_gate_script = (
                    root
                    / ".agents"
                    / "skills"
                    / "python-frontend-dev"
                    / "subskills"
                    / "quality-gate"
                    / "scripts"
                    / "ui_quality_gate.py"
                )
                if ui_gate_script.is_file():
                    print("Running frontend UI quality gate via skill...")
                    ui_status = _run([sys.executable, str(ui_gate_script)], cwd=root)
                    overall_status = max(overall_status, ui_status)

    if not args.skip_functional:
        functional_status = 0
        unit_test_file = root / "tests" / "test_pixel_coin_game.py"
        module_test_file = root / "pixel_coin_game" / "tests" / "test_pixel_coin_game.py"
        game_module_entry = root / "pixel_coin_game" / "__main__.py"
        is_game_project = (root / "pixel_coin_game").is_dir() or game_module_entry.is_file()
        ran_any_functional = False

        mechanical_skill_script = root / "pixel_coin_game" / "skills" / "scripts" / "mechanical_gate.py"
        dynamic_skill_script = root / "pixel_coin_game" / "skills" / "scripts" / "dynamic_agent_playtest.py"

        if is_game_project:
            if mechanical_skill_script.is_file():
                print("Running mechanical gate via module skill...")
                ran_any_functional = True
                functional_status = max(
                    functional_status,
                    _run([sys.executable, "-m", "pixel_coin_game.skills.scripts.mechanical_gate"], cwd=root),
                )
            elif module_test_file.is_file():
                print("Running module functional tests (unittest)...")
                ran_any_functional = True
                functional_status = max(
                    functional_status,
                    _run(
                        [sys.executable, "-m", "unittest", "pixel_coin_game.tests.test_pixel_coin_game", "-v"],
                        cwd=root,
                    ),
                )
            elif unit_test_file.is_file():
                print("Running functional tests (unittest)...")
                ran_any_functional = True
                functional_status = max(
                    functional_status,
                    _run(
                        [sys.executable, "-m", "unittest", "tests/test_pixel_coin_game.py", "-v"],
                        cwd=root,
                    ),
                )
            else:
                print(
                    "Functional gate failed: missing module mechanical skill and module/root functional tests.",
                )
                functional_status = max(functional_status, 1)

            if dynamic_skill_script.is_file():
                print("Running dynamic gameplay test via module skill...")
                ran_any_functional = True
                functional_status = max(
                    functional_status,
                    _run([sys.executable, "-m", "pixel_coin_game.skills.scripts.dynamic_agent_playtest"], cwd=root),
                )
            elif game_module_entry.is_file():
                print("Running gameplay gate (headless autoplay clear)...")
                ran_any_functional = True
                functional_status = max(
                    functional_status,
                    _run(
                        [sys.executable, "-m", "pixel_coin_game", "--autoplay", "--no-gui", "--assert-optimal"],
                        cwd=root,
                    ),
                )
            else:
                print(
                    "Functional gate failed: missing module dynamic skill and pixel_coin_game module entry.",
                )
                functional_status = max(functional_status, 1)

        if not is_game_project and unit_test_file.is_file():
            print("Running functional tests (unittest)...")
            ran_any_functional = True
            functional_status = max(
                functional_status,
                _run(
                    [sys.executable, "-m", "unittest", "tests/test_pixel_coin_game.py", "-v"],
                    cwd=root,
                ),
            )

        for cmd_text in args.functional_cmd:
            parsed = shlex.split(cmd_text)
            if not parsed:
                continue
            print(f"Running agent functional command: {cmd_text}")
            ran_any_functional = True
            functional_status = max(functional_status, _run(parsed, cwd=root))

        if not ran_any_functional:
            print("No functional gate target found; skipping functional stage.")

        overall_status = max(overall_status, functional_status)

    if overall_status == 0:
        print("No errors found.")
        return 0

    print("Errors found. Please fix them before committing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
