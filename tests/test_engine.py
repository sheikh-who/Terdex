from terdex.engine import TERDEX_SYSTEM_PROMPT, TerdexEngine


def test_engine_build_messages_includes_context():
    engine = TerdexEngine()
    messages = engine.build_messages("set up git", termux=True)
    assert messages[0]["content"] == TERDEX_SYSTEM_PROMPT
    assert "Termux" in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert "set up git" in messages[-1]["content"]
    assert "Termux" in messages[-1]["content"]


def test_engine_chain_of_thought_instruction():
    engine = TerdexEngine(enable_chain_of_thought=True)
    messages = engine.build_messages("install python", termux=False)
    user_content = messages[-1]["content"]
    assert "Think step-by-step" in user_content
