"""Planning utilities and data structures for Terdex."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Optional

from .config import detect_termux
from .providers import request_plan_from_provider


@dataclass
class PlanStep:
    """A single actionable step in a generated plan.

    :param title: Short description of the action to perform.
    :param command: Optional shell command associated with the step.
    :param notes: Optional free-form notes clarifying the step.
    """

    title: str
    command: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        """Return the step as a JSON-serialisable dictionary."""

        data: Dict[str, str] = {"title": self.title}
        if self.command:
            data["command"] = self.command
        if self.notes:
            data["notes"] = self.notes
        return data

    def format_lines(self, index: int) -> List[str]:
        """Format the step for console output.

        :param index: One-based index used for numbering in the console.
        :return: Lines containing a summary, command, and notes.
        """

        lines = [f" - Step {index}: {self.title}"]
        if self.command:
            lines.append(f"   Command: {self.command}")
        if self.notes:
            lines.append(f"   Notes: {self.notes}")
        return lines


@dataclass
class Plan:
    """Structured representation of an execution plan."""

    summary: str
    steps: List[PlanStep]
    environment_note: str

    def truncated(self, max_steps: Optional[int]) -> "Plan":
        """Return a copy limited to ``max_steps`` entries."""

        if max_steps is None or max_steps >= len(self.steps):
            return Plan(self.summary, list(self.steps), self.environment_note)
        return Plan(self.summary, self.steps[:max_steps], self.environment_note)

    def is_empty(self) -> bool:
        """Return ``True`` when no summary or steps were produced."""

        return not self.steps and not self.summary.strip()

    def to_dict(self) -> Dict[str, object]:
        """Return the plan as a JSON-serialisable structure."""

        return {
            "summary": self.summary,
            "steps": [step.to_dict() for step in self.steps],
            "environment": self.environment_note,
        }

    def formatted_output(self) -> List[str]:
        """Produce a list of lines representing the plan for console display."""

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
    provider: Optional[str] = None,
    model: Optional[str] = None,
    stream: bool = False,
    provider_options: Optional[Dict[str, str]] = None,
    ollama_model: Optional[str] = None,
    ollama_chat_fn: Optional[Callable[..., object]] = None,
    chain_of_thought: bool = False,
    http_post: Optional[Callable[[str, bytes, Mapping[str, str]], str]] = None,
) -> Plan:
    """Return an actionable plan for ``description``.

    :param description: Natural language task description supplied by the user.
    :param max_steps: Optional cap on the number of generated steps.
    :param provider: Provider identifier (e.g. heuristic, ollama, openrouter).
    :param model: Preferred remote model name when using an integration.
    :param stream: Whether the provider should stream responses when supported.
    :param provider_options: Mapping of provider specific configuration values.
    :param ollama_model: Backwards compatible alias for ``model`` when
        ``provider`` is omitted and Ollama is desired.
    :param ollama_chat_fn: Alternative chat callable used for testing or
        dependency injection.
    :param chain_of_thought: Request structured reasoning from the model.
    :param http_post: Optional callable for mocking HTTP interactions in tests.
    :raises OllamaUnavailableError: If the Ollama backend cannot be reached.
    :raises ProviderUnavailableError: When the selected provider is not
        correctly configured.
    :return: A :class:`Plan` describing the derived steps.
    """

    normalized = description.replace("\n", " ").strip()
    environment_is_termux = detect_termux()
    environment_message = _environment_message(environment_is_termux)
    if not normalized:
        return Plan(summary="", steps=[], environment_note=environment_message)

    summary = _derive_summary(normalized)

    resolved_provider = provider or ("ollama" if ollama_model else "heuristic")
    resolved_model = model or ollama_model
    options = dict(provider_options or {})

    if resolved_provider and resolved_provider.lower() != "heuristic":
        raw_plan = request_plan_from_provider(
            resolved_provider,
            normalized,
            model=resolved_model,
            termux=environment_is_termux,
            chain_of_thought=chain_of_thought,
            stream=stream,
            options=options,
            chat_fn=ollama_chat_fn if resolved_provider == "ollama" else None,
            http_post=http_post,
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
    for sentence in sentences:
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
        "Environment: Non-Termux detected. If targeting Termux, ensure commands "
        "are `pkg` compatible."
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

