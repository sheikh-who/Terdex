import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from terdex.cli import AppConfig, generate_plan
from terdex.ollama_support import OllamaUnavailableError


def test_generate_plan_basic():
    description = "create api endpoint. add tests. update docs."
    plan = generate_plan(description)
    assert plan[0].startswith("Step 1: Create api endpoint")
    assert any("Environment" in step for step in plan)


def test_config_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_dir = tmp_path
    config = AppConfig.initialize(config_dir)
    config.profile = "termux"
    config.playbooks["custom"] = ["echo hello"]
    config.save()

    loaded = AppConfig.load(config_dir)
    assert loaded.profile == "termux"
    assert loaded.playbooks["custom"] == ["echo hello"]


def test_detect_termux(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TERMUX_VERSION", "0.118")
    plan = generate_plan("simple step")
    assert plan[-1].startswith("Environment: Detected Termux")

    monkeypatch.delenv("TERMUX_VERSION")
    plan = generate_plan("simple step")
    assert "Non-Termux" in plan[-1]


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

    assert plan[0] == "Step 1: Gather tools"
    assert plan[1] == "Step 2: Run build"
    assert plan[-1].startswith("Environment:")


def test_generate_plan_ollama_missing():
    with pytest.raises(OllamaUnavailableError):
        generate_plan("do things", ollama_model="gemma3")


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

    assert plan[0].startswith("Step 1: Update package lists")
    assert "Command: pkg update -y" in plan[0]
    assert plan[-1] == "Environment: Termux detected"
