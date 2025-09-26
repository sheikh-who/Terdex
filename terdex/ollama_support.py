"""Helpers for interacting with the local Ollama runtime."""

from __future__ import annotations

from typing import Any, Callable, Optional

from .engine import TerdexEngine


class OllamaUnavailableError(RuntimeError):
    """Raised when the Ollama Python package is not available."""


def _load_chat_callable() -> Callable[..., Any]:
    try:
        from ollama import chat as ollama_chat  # type: ignore import-not-found
    except ImportError as exc:  # pragma: no cover - explicit error message
        raise OllamaUnavailableError(
            "The `ollama` package is required. Install it with `pip install ollama` "
            "or `pip install .[ollama]`, and ensure the Ollama service is running."
        ) from exc
    return ollama_chat


def request_plan_from_ollama(
    description: str,
    *,
    model: str,
    stream: bool = False,
    chat_fn: Optional[Callable[..., Any]] = None,
    termux: Optional[bool] = None,
    chain_of_thought: bool = False,
) -> str:
    """Request a plan from an Ollama model and return the combined text."""

    engine = TerdexEngine(enable_chain_of_thought=chain_of_thought)
    messages = engine.build_messages(description, termux=termux)

    chat = chat_fn or _load_chat_callable()
    response = chat(model=model, messages=messages, stream=stream)
    if stream:
        chunks: list[str] = []
        for part in response:  # type: ignore[not-an-iterable]
            content = _extract_content(part)
            if content:
                chunks.append(content)
        return "".join(chunks)
    return _extract_content(response)


def _extract_content(result: Any) -> str:
    """Best-effort extraction of the response text from Ollama outputs."""

    if isinstance(result, dict):
        message = result.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
    message = getattr(result, "message", None)
    if message is not None:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
    if hasattr(result, "__getitem__"):
        try:
            message = result["message"]
            content = message["content"]
            if isinstance(content, str):
                return content
        except Exception:  # pragma: no cover - fall through to default handling
            pass
    if isinstance(result, str):
        return result
    return ""
