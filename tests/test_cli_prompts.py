import json
from types import SimpleNamespace

from terdex.cli import CHAIN_OF_THOUGHT_PROMPTS, command_prompts


def test_prompts_json_output(capsys):
    args = SimpleNamespace(json=True)
    assert command_prompts(args) == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["title"].startswith("Chain-of-thought prompts")
    assert payload["prompts"] == CHAIN_OF_THOUGHT_PROMPTS


def test_prompts_text_output(capsys):
    args = SimpleNamespace(json=False)
    assert command_prompts(args) == 0
    captured = capsys.readouterr().out.strip().splitlines()
    assert captured[0].startswith("Chain-of-thought prompt ideas")
    numbered = [line for line in captured if line and line[0].isdigit()]
    assert len(numbered) == len(CHAIN_OF_THOUGHT_PROMPTS)
    assert numbered[0].startswith("1. ")
