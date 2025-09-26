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
from typing import Dict, List, Optional

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
    "llm": {
        "provider": "heuristic",
        "model": "",
        "api_base": "",
        "api_key_env": "",
        "options": {},
    },
}


@dataclass
class LLMSettings:
    """Configuration describing the preferred language model provider.

    :param provider: Identifier for the integration to use (heuristic, ollama, openrouter, etc.).
    :param model: Optional default model identifier for the provider.
    :param api_base: Optional base URL overriding the provider default.
    :param api_key_env: Name of an environment variable that stores the secret key.
    :param options: Additional provider-specific parameters to pass through.
    """

    provider: str = "heuristic"
    model: Optional[str] = None
    api_base: Optional[str] = None
    api_key_env: Optional[str] = None
    options: Dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    """Persisted settings for Terdex.

    :param path: Absolute path to the configuration file backing the instance.
    :param profile: Active profile name for display purposes.
    :param workspace: Directory path used for per-project workspaces.
    :param playbooks: Mapping of playbook names to ordered shell commands.
    :param llm: Provider preferences for plan generation.
    """

    path: Path
    profile: str = "default"
    workspace: Path = Path("workspace")
    playbooks: Dict[str, List[str]] = field(default_factory=dict)
    llm: LLMSettings = field(default_factory=LLMSettings)

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
        llm_data = data.get("llm", {})
        llm_options = {
            key: str(value)
            for key, value in llm_data.get("options", {}).items()
            if isinstance(key, str) and isinstance(value, (str, int, float, bool))
        }
        return cls(
            path=config_path,
            profile=data.get("profile", "default"),
            workspace=workspace,
            playbooks=playbooks,
            llm=LLMSettings(
                provider=str(llm_data.get("provider", "heuristic")),
                model=(llm_data.get("model") or None),
                api_base=(llm_data.get("api_base") or None),
                api_key_env=(llm_data.get("api_key_env") or None),
                options=llm_options,
            ),
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
                    "llm": {
                        "provider": self.llm.provider,
                        "model": self.llm.model or "",
                        "api_base": self.llm.api_base or "",
                        "api_key_env": self.llm.api_key_env or "",
                        "options": self.llm.options,
                    },
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

