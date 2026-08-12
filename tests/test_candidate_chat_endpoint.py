"""
Unit tests for the POST /candidate-chat endpoint in app/dashboard.py
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dashboard import CANDIDATE_STORE, EVALUATION_STORE, app
from app.schemas import CandidateProfile


@pytest.fixture
def client():
    CANDIDATE_STORE.clear()
    EVALUATION_STORE.clear()
    yield TestClient(app)
    CANDIDATE_STORE.clear()
    EVALUATION_STORE.clear()


def _seed_candidate(candidate_id: str, name: str, match_score: float, matched_skills: list[str], missing_skills: list[str]) -> None:
    CANDIDATE_STORE[candidate_id] = {
        "candidate": CandidateProfile(
            name=name,
            skills=matched_skills,
            experience_years=3.0,
            education="Bachelor of Science",
            certifications=[],
            raw_resume_text=f"{name} resume",
        )
    }
    EVALUATION_STORE[candidate_id] = {
        "match_result": {
            "match_score": match_score,
            "confidence": "high" if match_score >= 70 else "medium",
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "experience_gap": 1.0,
        },
        "growth_recommendation": None,
        "resume_formatting_check": {"issues": [], "suggestions": []},
    }


def test_candidate_chat_does_not_require_recruiter_auth(client, monkeypatch):
    """Unlike /batch-chat and /send-email, this endpoint is candidate-facing and
    must work with no recruiter token at all."""

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
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Some answer."))])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.candidate_chat.OpenAI", DummyOpenAI)

    _seed_candidate("1", "Ava Patel", 82.0, ["Python", "SQL"], ["Kubernetes"])

    response = client.post(
        "/candidate-chat",
        json={"candidate_id": "1", "question": "Why did I get this score?"},
    )

    assert response.status_code == 200


def test_candidate_chat_returns_404_for_unknown_candidate(client):
    response = client.post(
        "/candidate-chat",
        json={"candidate_id": "does-not-exist", "question": "Why did I get this score?"},
    )

    assert response.status_code == 404


def test_candidate_chat_context_includes_only_this_candidates_data(client, monkeypatch):
    """Two candidates exist in the store; asking about candidate 1 must never
    leak candidate 2's name, score, or skills into the model context."""
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
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content="You matched Python and SQL, which contributed to your score."
                ))]
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.candidate_chat.OpenAI", DummyOpenAI)

    _seed_candidate("1", "Ava Patel", 82.0, ["Python", "SQL"], ["Kubernetes"])
    _seed_candidate("2", "Ben Ortiz", 41.0, ["Excel"], ["Python", "SQL", "Kubernetes"])

    response = client.post(
        "/candidate-chat",
        json={"candidate_id": "1", "question": "Why did I get this score?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "You matched Python and SQL, which contributed to your score."

    system_message = captured["messages"][0]["content"]
    assert "Ava Patel" in system_message
    assert "82.0" in system_message

    # Candidate 2's data must never appear in candidate 1's context.
    assert "Ben Ortiz" not in system_message
    assert "41.0" not in system_message
    assert captured["messages"][1] == {"role": "user", "content": "Why did I get this score?"}


def test_candidate_chat_system_prompt_forbids_predictions_and_comparisons(client, monkeypatch):
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

    _seed_candidate("1", "Ava Patel", 82.0, ["Python", "SQL"], ["Kubernetes"])

    response = client.post(
        "/candidate-chat",
        json={"candidate_id": "1", "question": "Will I get the job?"},
    )

    assert response.status_code == 200
    system_message = captured["messages"][0]["content"].lower()
    assert "hiring predictions" in system_message
    assert "other candidate" in system_message
    assert "i don't have that information" in system_message
