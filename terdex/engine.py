"""Prompt engineering utilities for Terdex."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence

TERDEX_SYSTEM_PROMPT = """
You are Terdex, a Termux-aware planning assistant. You help developers working on
Android devices craft concise, actionable plans that can be executed inside the
Termux shell. Always consider:
- Package management relies on `pkg`/`apt` rather than `sudo` or Homebrew.
- Devices often have limited RAM and CPU resources, so prefer lightweight tools.
- File paths should avoid hard-coded `/data/data` prefixes and assume a POSIX shell.
- Networking may be unreliable; cache downloads when possible.

When asked for help you must respond with a single JSON object using the schema:
{
  "task_summary": "Short description of the task in 1 sentence",
  "steps": [
    {
      "title": "High-level action title",
      "command": "Specific Termux-friendly shell command, if relevant",
      "notes": "Optional clarifications or cautions"
    }
  ],
  "environment": "One sentence reminder about Termux constraints"
}

If a shell command is not required for a step, use an empty string for the
"command" field. Keep responses focused and avoid markdown outside the JSON.
""".strip()


@dataclass
class TerdexEngine:
    """Utility to generate structured chat prompts for Terdex."""

    enable_chain_of_thought: bool = False

    def build_messages(
        self,
        description: str,
        *,
        termux: Optional[bool] = None,
        history: Optional[Sequence[Mapping[str, str]]] = None,
    ) -> List[Mapping[str, str]]:
        """Construct a chat message list suitable for the Ollama client."""

        messages: List[Mapping[str, str]] = [{"role": "system", "content": TERDEX_SYSTEM_PROMPT}]
        if history:
            for message in history:
                role = message.get("role")
                content = message.get("content")
                if isinstance(role, str) and isinstance(content, str):
                    messages.append({"role": role, "content": content})

        environment_hint = (
            "The user is running inside Termux on Android."
            if termux
            else "The user may be on a standard Linux distribution but wants Termux-compatible steps."
        )

        user_instructions = [
            "Plan the work before execution and output valid JSON only.",
            environment_hint,
            f"Task: {description.strip()}",
        ]
        if self.enable_chain_of_thought:
            user_instructions.insert(
                1,
                "Think step-by-step to ensure the plan is safe, then provide only the JSON object in the final response.",
            )

        messages.append({"role": "user", "content": "\n".join(user_instructions)})
        return messages
