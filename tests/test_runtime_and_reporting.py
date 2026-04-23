from src.reflexion_lab.llm_runtime import get_runtime_mode, set_runtime_mode
from src.reflexion_lab.reporting import build_report
from src.reflexion_lab.schemas import RunRecord


def make_record(agent_type: str, is_correct: bool, failure_mode: str) -> RunRecord:
    return RunRecord(
        qid=f"{agent_type}-1",
        question="Question?",
        gold_answer="Gold",
        agent_type=agent_type,
        predicted_answer="Gold" if is_correct else "Wrong",
        is_correct=is_correct,
        attempts=1,
        token_estimate=10,
        latency_ms=5,
        failure_mode=failure_mode,
        reflections=[],
        traces=[],
    )


def test_get_runtime_mode_uses_mock_when_flag_enabled(monkeypatch):
    set_runtime_mode(None)
    monkeypatch.setenv("USE_MOCK", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert get_runtime_mode() == "mock"


def test_get_runtime_mode_requires_api_key_for_real_mode(monkeypatch):
    set_runtime_mode(None)
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        get_runtime_mode("real")
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected real mode to fail without OPENAI_API_KEY")


def test_get_runtime_mode_uses_real_when_api_key_present(monkeypatch):
    set_runtime_mode(None)
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert get_runtime_mode("real") == "real"


def test_runtime_mode_override_takes_priority(monkeypatch):
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    set_runtime_mode("mock")

    assert get_runtime_mode() == "mock"
    set_runtime_mode(None)


def test_build_report_uses_caller_supplied_metadata():
    records = [
        make_record("react", True, "none"),
        make_record("reflexion", False, "wrong_final_answer"),
    ]

    report = build_report(
        records,
        dataset_name="sample.json",
        mode="real",
        extensions=["structured_evaluator", "reflection_memory"],
        discussion="Custom discussion",
    )

    assert report.meta["mode"] == "real"
    assert report.extensions == ["structured_evaluator", "reflection_memory"]
    assert report.discussion == "Custom discussion"


def test_build_report_generates_non_placeholder_discussion():
    records = [
        make_record("react", True, "none"),
        make_record("reflexion", True, "none"),
    ]

    report = build_report(records, dataset_name="sample.json", mode="mock")

    assert "students should explain" not in report.discussion.lower()
    assert "ReAct EM" in report.discussion
