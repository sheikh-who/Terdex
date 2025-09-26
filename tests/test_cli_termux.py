import json
from types import SimpleNamespace

from terdex.cli import command_termux
from terdex.termux_reference import TERMUX_REFERENCE


def test_termux_command_text_output(capsys):
    args = SimpleNamespace(section=None, json=False)
    assert command_termux(args) == 0
    captured = capsys.readouterr().out
    first_section = TERMUX_REFERENCE[0]
    assert first_section.title in captured
    for entry in first_section.entries[:2]:
        assert entry.name in captured


def test_termux_command_json_output(capsys):
    section = TERMUX_REFERENCE[1]
    args = SimpleNamespace(section=section.key, json=True)
    assert command_termux(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["title"] == "Termux quick reference"
    assert len(payload["sections"]) == 1
    assert payload["sections"][0]["key"] == section.key


def test_termux_command_unknown_section(capsys):
    args = SimpleNamespace(section="unknown", json=False)
    assert command_termux(args) == 1
    captured = capsys.readouterr().out
    assert "Unknown section" in captured


def test_termux_command_desktop_section(capsys):
    args = SimpleNamespace(section="desktop", json=False)
    assert command_termux(args) == 0
    captured = capsys.readouterr().out
    assert "Desktop Environments" in captured
    assert "xfce4-session" in captured
