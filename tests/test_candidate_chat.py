"""
Unit tests for app/candidate_chat.py
"""

from types import SimpleNamespace

import pytest

from app.candidate_chat import _format_candidate_context, answer_candidate_question


def _sample_evaluation():
    return {
        "match_result": {
            "match_score": 82.0,
            "confidence": "high",
            "matched_skills": ["Python", "SQL"],
            "missing_skills": ["Kubernetes"],
            "experience_gap": 1.0,
        },
        "growth_recommendation": {
            "suggested_project": "Deploy a small service on Kubernetes.",
            "resume_tip": "Add a 'Cloud & DevOps' section highlighting container experience.",
        },
        "resume_formatting_check": {
            "issues": ["Resume uses tables which some ATS parsers cannot read."],
            "suggestions": ["Use standard section headings like 'Experience' and 'Education'."],
        },
    }


def test_format_candidate_context_includes_own_data_only():
    context = _format_candidate_context(_sample_evaluation(), "Ava Patel")

    assert "Ava Patel" in context
    assert "82.0" in context
    assert "Python, SQL" in context
    assert "Kubernetes" in context
    assert "Deploy a small service on Kubernetes." in context
    assert "tables" in context


def test_format_candidate_context_is_not_raw_json():
    context = _format_candidate_context(_sample_evaluation(), "Ava Patel")

    assert "{" not in context
    assert "}" not in context


def test_answer_candidate_question_returns_model_answer(monkeypatch):
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
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content="You matched 2 of 3 required skills, which is why you scored 82.0."
                ))]
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.candidate_chat.OpenAI", DummyOpenAI)

    answer = answer_candidate_question(_sample_evaluation(), "Ava Patel", "Why did I get this score?")

    assert answer == "You matched 2 of 3 required skills, which is why you scored 82.0."
    assert captured["model"] == "gpt-4o-mini"
    system_message = captured["messages"][0]["content"]
    assert "Ava Patel" in system_message
    assert "82.0" in system_message
    assert captured["messages"][1] == {"role": "user", "content": "Why did I get this score?"}


def test_answer_candidate_question_system_prompt_forbids_predictions_and_comparisons(monkeypatch):
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
    monkeypatch.setattr("app.candidate_chat.OpenAI", DummyOpenAI)

    answer_candidate_question(_sample_evaluation(), "Ava Patel", "Will I get the job?")

    system_message = captured["messages"][0]["content"].lower()
    assert "never make hiring predictions" in system_message or "hiring predictions" in system_message
    assert "other candidate" in system_message
    assert "i don't have that information" in system_message


def test_answer_candidate_question_system_prompt_permits_threshold_reasoning(monkeypatch):
    """Regression test: the model must be told that comparing the candidate's own
    score/experience against a number they ask about is legitimate analysis, not
    fabrication -- not a reason to fall back to "I don't have that information."."""
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
    monkeypatch.setattr("app.candidate_chat.OpenAI", DummyOpenAI)

    answer_candidate_question(_sample_evaluation(), "Ava Patel", "Did I score above 90?")

    system_message = captured["messages"][0]["content"].lower()
    assert "should compare, filter" in system_message
    assert "not fabrication" in system_message


def test_answer_candidate_question_raises_when_evaluation_empty():
    with pytest.raises(ValueError, match="No evaluation data"):
        answer_candidate_question({}, "Ava Patel", "Why did I get this score?")


def test_answer_candidate_question_raises_when_question_empty():
    with pytest.raises(ValueError, match="Question cannot be empty"):
        answer_candidate_question(_sample_evaluation(), "Ava Patel", "   ")


def test_answer_candidate_question_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        answer_candidate_question(_sample_evaluation(), "Ava Patel", "Why did I get this score?")
