"""Command line interface for the Terdex assistant."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import List, Optional

from .config import AppConfig, detect_termux
from .ollama_support import OllamaUnavailableError
from .planner import Plan, PlanStep, generate_plan
from .playbooks import execute_playbook
from .plugins.confetti import celebrate_success
from .termux_reference import TERMUX_REFERENCE, lookup_section

__all__ = [
    "AppConfig",
    "Plan",
    "PlanStep",
    "generate_plan",
    "build_parser",
    "command_init",
    "command_plan",
    "command_run",
    "command_show",
    "command_prompts",
    "command_termux",
    "main",
]

CHAIN_OF_THOUGHT_PROMPTS = [
    (
        "Act as a productivity coach. Create a structured, time-blocked schedule for "
        "a project manager juggling meetings, deep work, and admin tasks."
    ),
    (
        "Step by step, outline a project timeline for launching a new product. Include "
        "key milestones, potential roadblocks, and solutions."
    ),
    "Organize this to-do list into high-priority and low-priority tasks.",
    (
        "Suggest a workflow automation strategy for a marketing team handling "
        "multiple campaigns."
    ),
    (
        "Act as a project manager. Design a simple workflow for handling customer "
        "complaints efficiently."
    ),
    (
        "Analyze this weekly schedule and suggest ways to increase efficiency without "
        "compromising work quality."
    ),
    (
        "Act as a time management expert. Given a workload of 10+ daily tasks, multiple "
        "deadlines, and frequent interruptions, suggest a structured prioritization "
        "method to ensure high-impact tasks are completed first while minimizing "
        "stress and decision fatigue."
    ),
    (
        "Act as an executive coach. Provide a 5-minute morning reflection exercise to "
        "help me set clear priorities and focus on high-impact work."
    ),
    (
        "Act as a time management expert. I have five urgent tasks, but only time for "
        "three. Provide a prioritization framework to decide which to complete first."
    ),
    (
        "My to-do list keeps growing, and I feel like I'm always behind. Suggest a "
        "method to ensure I stay proactive instead of reactive."
    ),
]
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Terdex – a lightweight, offline-friendly coding helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              Initialize configuration:  terdex init
              Create a plan:            terdex plan "add REST endpoint"
              Run a playbook:           terdex run bootstrap-termux
            """
        ),
    )
    parser.add_argument(
        "--config",
        default=Path.cwd(),
        type=Path,
        help="Directory that stores the .terdex.json configuration (defaults to CWD).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="Create the default Terdex configuration file"
    )
    init_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing configuration if present",
    )

    plan_parser = subparsers.add_parser(
        "plan", help="Generate a simple execution plan from a description"
    )
    plan_parser.add_argument("description", nargs="*", help="Description to plan")
    plan_parser.add_argument(
        "--max-steps", type=int, default=None, help="Limit the number of generated steps"
    )
    plan_parser.add_argument(
        "--ollama-model",
        dest="ollama_model",
        default=None,
        help=(
            "Use a local Ollama model to draft the plan. Requires the `ollama` package and daemon."
        ),
    )
    plan_parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream responses from Ollama when generating plans",
    )
    plan_parser.add_argument(
        "--chain-of-thought",
        action="store_true",
        dest="chain_of_thought",
        help="Ask the model to reason step-by-step before returning the JSON plan",
    )
    plan_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the generated plan as JSON instead of human-readable text",
    )

    run_parser = subparsers.add_parser(
        "run", help="Execute a named playbook from the configuration"
    )
    run_parser.add_argument("playbook", help="Name of the playbook to execute")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them",
    )
    run_parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run playbook commands using a thread pool for independent tasks",
    )

    show_parser = subparsers.add_parser(
        "show", help="Display loaded configuration and environment info"
    )
    show_parser.add_argument(
        "--playbooks",
        action="store_true",
        help="Also show available playbooks",
    )

    prompts_parser = subparsers.add_parser(
        "prompts", help="List chain-of-thought prompt ideas for smarter planning"
    )
    prompts_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the prompts as JSON for downstream tooling",
    )

    termux_parser = subparsers.add_parser(
        "termux",
        help="Show curated Termux shortcuts, configuration tips, and API commands",
    )
    termux_parser.add_argument(
        "--section",
        help="Limit output to a specific section key (e.g. keyboard, package-management)",
    )
    termux_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the Termux reference guide as JSON",
    )

    return parser


def command_init(args: argparse.Namespace) -> int:
    config_dir = args.config
    try:
        config = AppConfig.initialize(config_dir, overwrite=args.overwrite)
    except FileExistsError as exc:
        print(exc)
        return 1
    print(f"Initialized configuration at {config.path}")
    print(f"Workspace directory: {config.workspace}")
    return 0


def command_plan(args: argparse.Namespace) -> int:
    description = " ".join(args.description)
    try:
        plan = generate_plan(
            description,
            max_steps=args.max_steps,
            ollama_model=args.ollama_model,
            stream=args.stream,
            chain_of_thought=args.chain_of_thought,
        )
    except OllamaUnavailableError as exc:
        print(exc)
        return 1
    if plan.is_empty():
        print("No plan generated. Provide a description.")
        return 1
    if args.json:
        print(json.dumps(plan.to_dict(), indent=2))
        return 0

    print("Generated plan:\n")
    if plan.summary:
        print(f"Summary: {plan.summary}\n")
    for line in plan.formatted_output():
        print(line)
    celebrate_success("Plan ready to execute!")
    return 0


def command_run(args: argparse.Namespace) -> int:
    config = AppConfig.load(args.config)
    if args.playbook not in config.playbooks:
        available = ", ".join(sorted(config.playbooks)) or "none"
        print(f"Playbook '{args.playbook}' not found. Available: {available}")
        return 1
    commands = config.playbooks[args.playbook]
    if args.dry_run:
        print("Dry run – commands to execute:")
        for command in commands:
            print(f" - {command}")
        return 0
    exit_code = execute_playbook(
        commands,
        parallel=args.parallel,
    )
    if exit_code == 0:
        celebrate_success("Playbook completed successfully!")
    return exit_code


def command_show(args: argparse.Namespace) -> int:
    try:
        config = AppConfig.load(args.config)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    environment_lines = [
        f"Configuration path: {config.path}",
        f"Profile: {config.profile}",
        f"Workspace: {config.workspace}",
        f"Detected Termux: {'yes' if detect_termux() else 'no'}",
    ]
    print("\n".join(environment_lines))
    if args.playbooks:
        print("\nPlaybooks:")
        for name, commands in sorted(config.playbooks.items()):
            print(f" - {name}: {', '.join(commands)}")
    return 0


def command_prompts(args: argparse.Namespace) -> int:
    if args.json:
        payload = {
            "title": "Chain-of-thought prompts for smarter decision-making",
            "prompts": CHAIN_OF_THOUGHT_PROMPTS,
        }
        print(json.dumps(payload, indent=2))
        return 0

    intro = textwrap.dedent(
        """
        Chain-of-thought prompt ideas for smarter decision-making and productivity.
        Use these with `terdex plan --chain-of-thought` to encourage step-by-step reasoning.
        """
    ).strip()
    print(intro)
    print("")
    for index, prompt in enumerate(CHAIN_OF_THOUGHT_PROMPTS, start=1):
        print(f"{index}. {prompt}")
    return 0


def command_termux(args: argparse.Namespace) -> int:
    if args.section:
        section = lookup_section(args.section)
        if section is None:
            available = ", ".join(section.key for section in TERMUX_REFERENCE)
            print(f"Unknown section '{args.section}'. Available: {available}")
            return 1
        sections = [section]
    else:
        sections = TERMUX_REFERENCE

    if args.json:
        payload = {
            "title": "Termux quick reference",
            "sections": [section.to_dict() for section in sections],
        }
        print(json.dumps(payload, indent=2))
        return 0

    for index, section in enumerate(sections):
        if index:
            print("")
        print(section.title)
        print("=" * len(section.title))
        print(section.summary)
        print("")
        for entry in section.entries:
            print(f"- {entry.name}: {entry.description}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    commands = {
        "init": command_init,
        "plan": command_plan,
        "run": command_run,
        "show": command_show,
        "prompts": command_prompts,
        "termux": command_termux,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
