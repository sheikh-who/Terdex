"""Command line interface for the Terdex assistant."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from .ollama_support import (
    OllamaUnavailableError,
    request_plan_from_ollama,
)

CONFIG_FILE = ".terdex.json"
DEFAULT_CONFIG = {
    "profile": "default",
    "workspace": "workspace",
    "playbooks": {
        "bootstrap-termux": [
            "pkg update -y",
            "pkg install -y git python"
        ],
        "run-tests": [
            "pytest"
        ],
    },
}


@dataclass
class AppConfig:
    """Configuration used by Terdex."""

    path: Path
    profile: str = "default"
    workspace: Path = Path("workspace")
    playbooks: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, directory: Path) -> "AppConfig":
        config_path = directory / CONFIG_FILE
        if not config_path.exists():
            raise FileNotFoundError(
                f"No {CONFIG_FILE} configuration found in {directory}. "
                "Run `terdex init` first."
            )
        data = json.loads(config_path.read_text())
        workspace = Path(data.get("workspace", DEFAULT_CONFIG["workspace"]))
        playbooks = {
            name: list(commands)
            for name, commands in data.get("playbooks", {}).items()
        }
        return cls(
            path=config_path,
            profile=data.get("profile", "default"),
            workspace=workspace,
            playbooks=playbooks,
        )

    @classmethod
    def initialize(cls, directory: Path, overwrite: bool = False) -> "AppConfig":
        config_path = directory / CONFIG_FILE
        if config_path.exists() and not overwrite:
            raise FileExistsError(
                f"{CONFIG_FILE} already exists. Use --overwrite to replace it."
            )
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        workspace_dir = directory / DEFAULT_CONFIG["workspace"]
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return cls.load(directory)

    def save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "profile": self.profile,
                    "workspace": str(self.workspace),
                    "playbooks": self.playbooks,
                },
                indent=2,
            )
        )


def detect_termux() -> bool:
    """Return True if the current environment appears to be Termux."""

    return "TERMUX_VERSION" in os.environ or "com.termux" in os.environ.get("PREFIX", "")


@dataclass
class PlanStep:
    """A single actionable step in a generated plan."""

    title: str
    command: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        data: Dict[str, str] = {"title": self.title}
        if self.command:
            data["command"] = self.command
        if self.notes:
            data["notes"] = self.notes
        return data

    def format_lines(self, index: int) -> List[str]:
        lines = [f" - Step {index}: {self.title}"]
        if self.command:
            lines.append(f"   Command: {self.command}")
        if self.notes:
            lines.append(f"   Notes: {self.notes}")
        return lines


@dataclass
class Plan:
    """A structured representation of an execution plan."""

    summary: str
    steps: List[PlanStep]
    environment_note: str

    def truncated(self, max_steps: Optional[int]) -> "Plan":
        if max_steps is None or max_steps >= len(self.steps):
            return Plan(self.summary, list(self.steps), self.environment_note)
        return Plan(self.summary, self.steps[:max_steps], self.environment_note)

    def is_empty(self) -> bool:
        return not self.steps and not self.summary.strip()

    def to_dict(self) -> Dict[str, object]:
        return {
            "summary": self.summary,
            "steps": [step.to_dict() for step in self.steps],
            "environment": self.environment_note,
        }

    def formatted_output(self) -> List[str]:
        lines: List[str] = []
        for index, step in enumerate(self.steps, start=1):
            lines.extend(step.format_lines(index))
        if self.environment_note:
            if lines:
                lines.append("")
            lines.append(self.environment_note)
        return lines


def generate_plan(
    description: str,
    max_steps: Optional[int] = None,
    *,
    ollama_model: Optional[str] = None,
    stream: bool = False,
    ollama_chat_fn: Optional[Callable[..., object]] = None,
    chain_of_thought: bool = False,
) -> Plan:
    """Generate an execution plan from a plain language description."""

    normalized = description.replace("\n", " ").strip()
    environment_is_termux = detect_termux()
    environment_message = _environment_message(environment_is_termux)
    if not normalized:
        return Plan(summary="", steps=[], environment_note=environment_message)

    summary = _derive_summary(normalized)

    if ollama_model:
        raw_plan = request_plan_from_ollama(
            normalized,
            model=ollama_model,
            stream=stream,
            chat_fn=ollama_chat_fn,
            termux=environment_is_termux,
            chain_of_thought=chain_of_thought,
        )
        parsed_plan = _parse_plan_json(raw_plan)
        if parsed_plan:
            if not parsed_plan.summary:
                parsed_plan.summary = summary
            if not parsed_plan.environment_note:
                parsed_plan.environment_note = environment_message
            plan = parsed_plan
        else:
            steps = _normalize_ollama_output(raw_plan)
            if not steps:
                steps = _fallback_steps(normalized)
            plan = Plan(summary=summary, steps=steps, environment_note=environment_message)
    else:
        steps = _fallback_steps(normalized)
        plan = Plan(summary=summary, steps=steps, environment_note=environment_message)

    if max_steps:
        plan = plan.truncated(max_steps)

    if not plan.environment_note:
        plan.environment_note = environment_message

    return plan


def _fallback_steps(normalized_description: str) -> List[PlanStep]:
    sentences = [
        sentence.strip()
        for sentence in normalized_description.replace("?", ".")
        .replace("!", ".")
        .split(".")
        if sentence.strip()
    ]

    plan: List[PlanStep] = []
    for index, sentence in enumerate(sentences, start=1):
        title = _capitalize(sentence)
        plan.append(PlanStep(title=title))
    return plan


_LISTING_PREFIX = re.compile(r"^(?:[-*•]\s*|\d+[).:-]\s*|step\s+\d+[:.-]\s*)", re.I)


def _parse_plan_json(raw_plan: str) -> Optional[Plan]:
    try:
        payload = json.loads(raw_plan)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    summary_field = payload.get("task_summary")
    summary = summary_field.strip() if isinstance(summary_field, str) else ""

    environment_text = _normalize_environment_text(payload.get("environment"))

    steps_field = payload.get("steps")
    steps: List[PlanStep] = []
    if isinstance(steps_field, list):
        for entry in steps_field:
            step = _parse_step_entry(entry)
            if step:
                steps.append(step)

    if not steps and not summary and not environment_text:
        return None

    return Plan(summary=summary, steps=steps, environment_note=environment_text)


def _normalize_ollama_output(raw_plan: str) -> List[PlanStep]:
    lines: List[str] = []
    for raw_line in raw_plan.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        stripped = _LISTING_PREFIX.sub("", stripped)
        if not stripped:
            continue
        lines.append(stripped)

    normalized: List[PlanStep] = []
    for line in lines:
        normalized.append(PlanStep(title=_capitalize(line)))
    return normalized


def _environment_message(is_termux: Optional[bool] = None) -> str:
    if is_termux is None:
        is_termux = detect_termux()
    if is_termux:
        return (
            "Environment: Detected Termux. Prefer `pkg` for package management and avoid sudo."
        )
    return (
        "Environment: Non-Termux detected. If targeting Termux, ensure commands are `pkg` compatible."
    )


def _derive_summary(description: str) -> str:
    parts = re.split(r"[.!?]", description)
    for part in parts:
        cleaned = part.strip()
        if cleaned:
            return _capitalize(cleaned)
    return _capitalize(description[:120].strip())


def _normalize_environment_text(value: object) -> str:
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            return (
                candidate
                if candidate.lower().startswith("environment:")
                else f"Environment: {candidate}"
            )
    return ""


def _parse_step_entry(entry: object) -> Optional[PlanStep]:
    if isinstance(entry, dict):
        title_field = entry.get("title") or entry.get("summary") or entry.get("action")
        command_field = entry.get("command")
        notes_field = entry.get("notes") or entry.get("note") or entry.get("details")

        title = _clean_text(title_field)
        command = _clean_text(command_field)
        notes = _clean_text(notes_field)

        if not title and command:
            title = command

        if title:
            return PlanStep(title=_capitalize(title), command=command, notes=notes)
        return None

    if isinstance(entry, str):
        cleaned = _clean_text(entry)
        if cleaned:
            return PlanStep(title=_capitalize(cleaned))

    return None


def _clean_text(value: object) -> Optional[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _capitalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def execute_playbook(commands: Iterable[str], *, shell: bool = True) -> int:
    """Execute a series of shell commands sequentially."""

    for command in commands:
        print(f"$ {command}")
        completed = subprocess.run(command, shell=shell, check=False)
        if completed.returncode != 0:
            print(f"Command failed with exit code {completed.returncode}")
            return completed.returncode
    return 0


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

    show_parser = subparsers.add_parser(
        "show", help="Display loaded configuration and environment info"
    )
    show_parser.add_argument(
        "--playbooks",
        action="store_true",
        help="Also show available playbooks",
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
    return 0


def command_run(args: argparse.Namespace) -> int:
    config = AppConfig.load(args.config)
    if args.playbook not in config.playbooks:
        print(
            f"Playbook '{args.playbook}' not found. Available: {', '.join(sorted(config.playbooks)) or 'none'}"
        )
        return 1
    commands = config.playbooks[args.playbook]
    if args.dry_run:
        print("Dry run – commands to execute:")
        for command in commands:
            print(f" - {command}")
        return 0
    return execute_playbook(commands)


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


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    commands = {
        "init": command_init,
        "plan": command_plan,
        "run": command_run,
        "show": command_show,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
