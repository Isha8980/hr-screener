"""
Unit tests for app/batch_chat.py
"""

from types import SimpleNamespace

import pytest

from app.batch_chat import _format_batch_context, answer_batch_question


def _sample_results():
    return [
        {
            "candidate_name": "Ava Patel",
            "match_score": 88.0,
            "routing_decision": "auto_ranked",
            "detail": {
                "match_result": {
                    "matched_skills": ["Python", "SQL"],
                    "missing_skills": ["Kubernetes"],
                    "experience_gap": 1.0,
                }
            },
        },
        {
            "candidate_name": "Ben Ortiz",
            "match_score": 52.0,
            "routing_decision": "needs_review",
            "detail": {
                "match_result": {
                    "matched_skills": ["Python"],
                    "missing_skills": ["SQL", "Kubernetes"],
                    "experience_gap": -1.0,
                }
            },
        },
    ]


def test_format_batch_context_includes_readable_per_candidate_summary():
    context = _format_batch_context(_sample_results(), "Backend Engineer")

    assert "Backend Engineer" in context
    assert "Total candidates screened: 2" in context
    assert "Ava Patel" in context
    assert "Ben Ortiz" in context
    assert "88.0" in context
    assert "auto_ranked" in context
    assert "Python, SQL" in context
    assert "Kubernetes" in context


def test_format_batch_context_is_not_raw_json():
    context = _format_batch_context(_sample_results(), "Backend Engineer")

    assert "{" not in context
    assert "}" not in context


def test_answer_batch_question_returns_model_answer(monkeypatch):
    captured = {}

    class DummyOpenAI:
        def __init__(self, api_key):
            self.api_key = api_key

        @property
        def chat(self):
            return self

        @property
        def completions(self):
            return self

        def create(self, model, temperature, messages, **kwargs):
            captured["model"] = model
            captured["messages"] = messages
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Ava Patel scored 88.0."))]
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.batch_chat.OpenAI", DummyOpenAI)

    answer = answer_batch_question(_sample_results(), "Backend Engineer", "Who scored above 70?")

    assert answer == "Ava Patel scored 88.0."
    assert captured["model"] == "gpt-4o-mini"
    system_message = captured["messages"][0]["content"]
    assert "Ava Patel" in system_message
    assert "Ben Ortiz" in system_message
    assert "I don't have that information" in system_message
    assert captured["messages"][1] == {"role": "user", "content": "Who scored above 70?"}


def test_answer_batch_question_system_prompt_permits_threshold_reasoning(monkeypatch):
    """Regression test: the model must be told that filtering/comparing/counting
    over the given scores (e.g. "who scored above 70?") is legitimate analysis,
    not fabrication -- and that "zero candidates qualify" is a valid, sayable
    answer rather than a reason to respond "I don't have that information."."""
    captured = {}

    class DummyOpenAI:
        def __init__(self, api_key):
            pass

        @property
        def chat(self):
            return self

        @property
        def completions(self):
            return self

        def create(self, model, temperature, messages, **kwargs):
            captured["messages"] = messages
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Some answer."))])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.batch_chat.OpenAI", DummyOpenAI)

    answer_batch_question(_sample_results(), "Backend Engineer", "Who scored above 70?")

    system_message = captured["messages"][0]["content"].lower()
    assert "filter, compare, count" in system_message
    assert "zero candidates qualify" in system_message
    assert "not fabrication" in system_message


def test_answer_batch_question_raises_when_results_empty():
    with pytest.raises(ValueError, match="No batch results"):
        answer_batch_question([], "Backend Engineer", "Who scored above 70?")


def test_answer_batch_question_raises_when_question_empty():
    with pytest.raises(ValueError, match="Question cannot be empty"):
        answer_batch_question(_sample_results(), "Backend Engineer", "   ")


def test_answer_batch_question_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        answer_batch_question(_sample_results(), "Backend Engineer", "Who scored above 70?")
