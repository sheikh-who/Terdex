import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from terdex.config import AppConfig, LLMSettings
from terdex.ollama_support import OllamaUnavailableError
from terdex.planner import Plan, PlanStep, generate_plan
from terdex.providers import ProviderUnavailableError


def test_generate_plan_basic():
    description = "create api endpoint. add tests. update docs."
    plan = generate_plan(description)
    assert isinstance(plan, Plan)
    assert plan.steps[0].title.startswith("Create api endpoint")
    assert plan.environment_note.startswith("Environment:")


def test_config_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_dir = tmp_path
    config = AppConfig.initialize(config_dir)
    config.profile = "termux"
    config.playbooks["custom"] = ["echo hello"]
    config.llm = LLMSettings(
        provider="openrouter",
        model="meta-llama",
        api_base="https://example.com",
        api_key_env="OPENROUTER_KEY",
        options={"routing": "priority"},
    )
    config.save()

    loaded = AppConfig.load(config_dir)
    assert loaded.profile == "termux"
    assert loaded.playbooks["custom"] == ["echo hello"]
    assert loaded.llm.provider == "openrouter"
    assert loaded.llm.model == "meta-llama"
    assert loaded.llm.api_base == "https://example.com"
    assert loaded.llm.api_key_env == "OPENROUTER_KEY"
    assert loaded.llm.options == {"routing": "priority"}


def test_detect_termux(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TERMUX_VERSION", "0.118")
    plan = generate_plan("simple step")
    assert plan.environment_note.startswith("Environment: Detected Termux")

    monkeypatch.delenv("TERMUX_VERSION")
    plan = generate_plan("simple step")
    assert "Non-Termux" in plan.environment_note


def test_generate_plan_with_stubbed_ollama():
    def fake_chat(*, model, messages, stream):
        assert model == "stub-model"
        assert not stream
        assert "do the thing" in messages[-1]["content"]
        return SimpleNamespace(message=SimpleNamespace(content="1. gather tools\n2. run build"))

    plan = generate_plan(
        "do the thing",
        ollama_model="stub-model",
        ollama_chat_fn=fake_chat,
    )

    assert [step.title for step in plan.steps] == ["Gather tools", "Run build"]
    assert plan.environment_note.startswith("Environment:")


def test_generate_plan_ollama_missing():
    with pytest.raises(OllamaUnavailableError):
        generate_plan("do things", ollama_model="gemma3")


def test_generate_plan_openrouter_with_stub_http():
    captured = {}

    def fake_http(url: str, data: bytes, headers):
        captured["url"] = url
        captured["payload"] = json.loads(data.decode("utf-8"))
        captured["headers"] = headers
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "1. gather data\n2. summarise results",
                        }
                    }
                ]
            }
        )

    plan = generate_plan(
        "gather data",
        provider="openrouter",
        model="meta/llama",
        provider_options={"api_key": "stub"},
        http_post=fake_http,
    )

    assert plan.steps[0].title == "Gather data"
    assert plan.steps[1].title == "Summarise results"
    assert captured["url"].startswith("https://openrouter.ai")
    assert captured["payload"]["model"] == "meta/llama"
    assert captured["headers"]["Authorization"] == "Bearer stub"


def test_generate_plan_openrouter_missing_key():
    with pytest.raises(ProviderUnavailableError):
        generate_plan(
            "analyse code",
            provider="openrouter",
            model="meta/llama",
            provider_options={},
            http_post=lambda *_: "{}",
        )


def test_generate_plan_with_json_payload():
    payload = {
        "task_summary": "Install dependencies",
        "steps": [
            {
                "title": "Update package lists",
                "command": "pkg update -y",
                "notes": "Ensure repositories are reachable",
            },
            {
                "title": "Install git",
                "command": "pkg install -y git",
                "notes": "",
            },
        ],
        "environment": "Environment: Termux detected"
    }

    def fake_chat(*, model, messages, stream):
        assert model == "json-model"
        assert not stream
        assert messages[-1]["role"] == "user"
        return SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))

    plan = generate_plan(
        "install git",
        ollama_model="json-model",
        ollama_chat_fn=fake_chat,
    )

    assert plan.summary == "Install dependencies"
    assert plan.steps[0] == PlanStep(
        title="Update package lists",
        command="pkg update -y",
        notes="Ensure repositories are reachable",
    )
    assert plan.steps[1].title == "Install git"
    assert plan.environment_note == "Environment: Termux detected"
