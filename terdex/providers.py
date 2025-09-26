"""LLM provider helpers used by the planner."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from .engine import TerdexEngine
from .ollama_support import request_plan_from_ollama


class ProviderUnavailableError(RuntimeError):
    """Raised when an external provider cannot be reached or configured."""


_OPENAI_COMPATIBLE_PROVIDERS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "huggingface": "https://api-inference.huggingface.co/v1/chat/completions",
}


def request_plan_from_provider(
    provider: str,
    description: str,
    *,
    model: Optional[str],
    termux: Optional[bool],
    chain_of_thought: bool,
    stream: bool,
    options: Optional[Dict[str, str]] = None,
    chat_fn: Optional[Callable[..., Any]] = None,
    http_post: Optional[Callable[[str, bytes, Mapping[str, str]], str]] = None,
) -> str:
    """Return the raw plan text using the requested provider."""

    normalized_provider = provider.lower().strip()
    if normalized_provider in {"", "heuristic"}:
        raise ProviderUnavailableError("The heuristic provider does not produce remote responses.")

    options = options or {}
    engine = TerdexEngine(enable_chain_of_thought=chain_of_thought)

    if normalized_provider == "ollama":
        if not model:
            raise ProviderUnavailableError("Specify --model when using the Ollama provider.")
        return request_plan_from_ollama(
            description,
            model=model,
            stream=stream,
            chat_fn=chat_fn,
            termux=termux,
            chain_of_thought=chain_of_thought,
        )

    messages = engine.build_messages(description, termux=termux)

    if normalized_provider in _OPENAI_COMPATIBLE_PROVIDERS:
        base_url = options.get("api_base") or _OPENAI_COMPATIBLE_PROVIDERS[normalized_provider]
        api_key = _resolve_api_key(options)
        if not api_key:
            raise ProviderUnavailableError(
                "An API key is required for OpenAI-compatible providers. Set --api-key "
                "or configure llm.api_key_env."
            )
        if not model:
            raise ProviderUnavailableError("Specify --model for the selected provider.")
        payload = {"model": model, "messages": messages}
        response = _post_json(
            base_url,
            payload,
            {"Authorization": f"Bearer {api_key}"},
            http_post=http_post,
        )
        return _extract_openai_content(response)

    if normalized_provider == "gemini":
        api_key = _resolve_api_key(options)
        if not api_key:
            raise ProviderUnavailableError(
                "Gemini requires an API key. Configure llm.api_key_env or pass --api-key."
            )
        gemini_model = model or "gemini-1.5-flash"
        base_url = options.get("api_base") or "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base_url.rstrip('/')}/models/{gemini_model}:generateContent"
        url = f"{url}?{urllib.parse.urlencode({'key': api_key})}"
        payload = _build_gemini_payload(messages)
        response = _post_json(url, payload, {}, http_post=http_post)
        return _extract_gemini_content(response)

    if normalized_provider == "cohere":
        api_key = _resolve_api_key(options)
        if not api_key:
            raise ProviderUnavailableError(
                "Cohere requires an API key. Configure llm.api_key_env or pass --api-key."
            )
        if not model:
            raise ProviderUnavailableError("Specify --model for the Cohere provider.")
        base_url = options.get("api_base") or "https://api.cohere.com/v1/chat"
        payload = _build_cohere_payload(messages, model)
        response = _post_json(
            base_url,
            payload,
            {
                "Authorization": f"Bearer {api_key}",
                "Cohere-Version": options.get("cohere_version", "2024-10-22"),
            },
            http_post=http_post,
        )
        return _extract_cohere_content(response)

    raise ProviderUnavailableError(f"Unknown provider '{provider}'.")


def _resolve_api_key(options: Mapping[str, str]) -> Optional[str]:
    direct = options.get("api_key")
    if direct:
        return direct
    env_name = options.get("api_key_env")
    if env_name:
        return os.getenv(env_name)
    return None


def _post_json(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    *,
    http_post: Optional[Callable[[str, bytes, Mapping[str, str]], str]] = None,
) -> str:
    data = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json", **headers}
    if http_post:
        return http_post(url, data, merged_headers)
    request = urllib.request.Request(url, data=data, headers=merged_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - intentional HTTPS call
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # pragma: no cover - depends on network
        detail = exc.read().decode("utf-8", "ignore")
        raise ProviderUnavailableError(f"Provider returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - depends on network
        raise ProviderUnavailableError(f"Failed to reach provider endpoint: {exc.reason}") from exc


def _extract_openai_content(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderUnavailableError("Unable to parse provider response as JSON.") from exc
    choices = data.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            message = choice.get("message") if isinstance(choice, dict) else None
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
    raise ProviderUnavailableError("Provider response did not include message content.")


def _build_gemini_payload(messages: Iterable[Mapping[str, str]]) -> Mapping[str, Any]:
    system_prompt = ""
    contents: List[Mapping[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_prompt = content
            continue
        mapped_role = "user" if role != "assistant" else "model"
        contents.append({"role": mapped_role, "parts": [{"text": content}]})
    payload: Dict[str, Any] = {"contents": contents}
    if system_prompt:
        payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
    return payload


def _extract_gemini_content(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderUnavailableError("Unable to parse Gemini response.") from exc
    candidates = data.get("candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            content = candidate.get("content") if isinstance(candidate, dict) else None
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list):
                    for part in parts:
                        text = part.get("text") if isinstance(part, dict) else None
                        if isinstance(text, str):
                            return text
    raise ProviderUnavailableError("Gemini response did not include text content.")


def _build_cohere_payload(
    messages: Iterable[Mapping[str, str]],
    model: str,
) -> Mapping[str, Any]:
    system_prompt = ""
    chat_history: List[Mapping[str, str]] = []
    user_message = ""

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_prompt = content
            continue
        if role == "user":
            if user_message:
                chat_history.append({"role": "USER", "message": user_message})
            user_message = content
        elif role == "assistant":
            chat_history.append({"role": "CHATBOT", "message": content})

    payload: Dict[str, Any] = {
        "model": model,
        "message": user_message,
        "chat_history": chat_history,
    }
    if system_prompt:
        payload["preamble"] = system_prompt
    return payload


def _extract_cohere_content(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderUnavailableError("Unable to parse Cohere response.") from exc
    text = data.get("text")
    if isinstance(text, str):
        return text
    generations = data.get("generations")
    if isinstance(generations, list):
        for generation in generations:
            gen_text = generation.get("text") if isinstance(generation, dict) else None
            if isinstance(gen_text, str):
                return gen_text
    raise ProviderUnavailableError("Cohere response did not include text content.")

