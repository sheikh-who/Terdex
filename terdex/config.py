"""Configuration helpers for the Terdex CLI.

This module centralizes configuration loading and environment detection so the
command handlers can focus on orchestration. The functions include
Sphinx-style docstrings to support automatic API documentation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

CONFIG_FILE = ".terdex.json"
DEFAULT_CONFIG = {
    "profile": "default",
    "workspace": "workspace",
    "playbooks": {
        "bootstrap-termux": [
            "pkg update -y",
            "pkg install -y git python",
        ],
        "run-tests": [
            "pytest",
        ],
    },
}


@dataclass
class AppConfig:
    """Persisted settings for Terdex.

    :param path: Absolute path to the configuration file backing the instance.
    :param profile: Active profile name for display purposes.
    :param workspace: Directory path used for per-project workspaces.
    :param playbooks: Mapping of playbook names to ordered shell commands.
    """

    path: Path
    profile: str = "default"
    workspace: Path = Path("workspace")
    playbooks: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, directory: Path) -> "AppConfig":
        """Return an :class:`AppConfig` from ``directory``.

        :param directory: Target directory that should contain ``.terdex.json``.
        :raises FileNotFoundError: If the configuration file is missing.
        :return: Parsed configuration data.
        """

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
        """Create a default configuration in ``directory``.

        :param directory: Destination directory for ``.terdex.json``.
        :param overwrite: Whether to replace an existing configuration file.
        :raises FileExistsError: If the file exists and ``overwrite`` is ``False``.
        :return: A loaded configuration after initialization.
        """

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
        """Persist the configuration to disk."""

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
    """Return ``True`` when running under Termux.

    The check is intentionally lightweight and uses environment variables that
    are set by Termux out of the box.

    :return: ``True`` if Termux-specific environment variables are present.
    """

    return "TERMUX_VERSION" in os.environ or "com.termux" in os.environ.get(
        "PREFIX", ""
    )

