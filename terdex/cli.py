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


def generate_plan(
    description: str,
    max_steps: Optional[int] = None,
    *,
    ollama_model: Optional[str] = None,
    stream: bool = False,
    ollama_chat_fn: Optional[Callable[..., object]] = None,
    chain_of_thought: bool = False,
) -> List[str]:
    """Generate an execution plan from a plain language description."""

    normalized = description.replace("\n", " ").strip()
    if not normalized:
        return []

    environment_is_termux = detect_termux()
    environment_message = _environment_message(environment_is_termux)

    if ollama_model:
        raw_plan = request_plan_from_ollama(
            normalized,
            model=ollama_model,
            stream=stream,
            chat_fn=ollama_chat_fn,
            termux=environment_is_termux,
            chain_of_thought=chain_of_thought,
        )
        steps, ollama_environment = _parse_plan_json(raw_plan)
        if not steps:
            steps = _normalize_ollama_output(raw_plan)
        if not steps:
            steps = _fallback_steps(normalized)
        if ollama_environment:
            environment_message = ollama_environment
    else:
        steps = _fallback_steps(normalized)

    if max_steps:
        steps = steps[:max_steps]

    steps.append(environment_message)
    return steps


def _fallback_steps(normalized_description: str) -> List[str]:
    sentences = [
        sentence.strip()
        for sentence in normalized_description.replace("?", ".")
        .replace("!", ".")
        .split(".")
        if sentence.strip()
    ]

    plan: List[str] = []
    for index, sentence in enumerate(sentences, start=1):
        plan.append(f"Step {index}: {sentence[0].upper() + sentence[1:]}")
    return plan


_LISTING_PREFIX = re.compile(r"^(?:[-*•]\s*|\d+[).:-]\s*|step\s+\d+[:.-]\s*)", re.I)


def _parse_plan_json(raw_plan: str) -> tuple[List[str], Optional[str]]:
    try:
        payload = json.loads(raw_plan)
    except json.JSONDecodeError:
        return [], None

    if not isinstance(payload, dict):
        return [], None

    environment_text: Optional[str] = None
    if isinstance(payload.get("environment"), str):
        env_candidate = payload["environment"].strip()
        if env_candidate:
            environment_text = (
                env_candidate
                if env_candidate.lower().startswith("environment:")
                else f"Environment: {env_candidate}"
            )

    steps_field = payload.get("steps")
    if not isinstance(steps_field, list):
        return [], environment_text

    steps: List[str] = []
    for index, entry in enumerate(steps_field, start=1):
        title: Optional[str] = None
        command: Optional[str] = None
        notes: Optional[str] = None

        if isinstance(entry, dict):
            raw_title = entry.get("title") or entry.get("summary") or entry.get("action")
            if isinstance(raw_title, str) and raw_title.strip():
                title = raw_title.strip()
            raw_command = entry.get("command")
            if isinstance(raw_command, str) and raw_command.strip():
                command = raw_command.strip()
            raw_notes = entry.get("notes") or entry.get("note")
            if isinstance(raw_notes, str) and raw_notes.strip():
                notes = raw_notes.strip()
        elif isinstance(entry, str) and entry.strip():
            title = entry.strip()

        fragments = [fragment for fragment in [title, command, notes] if fragment]
        if not fragments:
            continue
        formatted = fragments[0]
        metadata: List[str] = []
        if command:
            metadata.append(f"Command: {command}")
        if notes:
            metadata.append(f"Notes: {notes}")
        if metadata:
            formatted = f"{formatted}; " + "; ".join(metadata)
        steps.append(f"Step {index}: {formatted}")

    return steps, environment_text


def _normalize_ollama_output(raw_plan: str) -> List[str]:
    lines: List[str] = []
    for raw_line in raw_plan.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        stripped = _LISTING_PREFIX.sub("", stripped)
        if not stripped:
            continue
        lines.append(stripped)

    normalized: List[str] = []
    for index, line in enumerate(lines, start=1):
        formatted = line[0].upper() + line[1:] if line else line
        normalized.append(f"Step {index}: {formatted}")
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
    if not plan:
        print("No plan generated. Provide a description.")
        return 1
    print("Generated plan:\n")
    for entry in plan:
        print(f" - {entry}")
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
