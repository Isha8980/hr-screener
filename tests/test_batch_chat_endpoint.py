"""
Unit tests for the POST /batch-chat endpoint in app/dashboard.py
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dashboard import BATCH_STORE, VALID_TOKENS, app


@pytest.fixture
def client():
    BATCH_STORE.clear()
    VALID_TOKENS.clear()
    yield TestClient(app)
    BATCH_STORE.clear()
    VALID_TOKENS.clear()


def _seed_batch(batch_id: str) -> None:
    BATCH_STORE[batch_id] = {
        "job_title": "Backend Engineer",
        "results": [
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
        ],
    }


def test_batch_chat_requires_recruiter_auth(client):
    _seed_batch("1")

    response = client.post("/batch-chat", json={"batch_id": "1", "question": "Who scored above 70?"})

    assert response.status_code == 401


def test_batch_chat_returns_404_for_unknown_batch(client):
    token = "recruiter-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/batch-chat",
        json={"batch_id": "does-not-exist", "question": "Who scored above 70?"},
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 404


def test_batch_chat_formats_batch_data_into_context_and_returns_answer(client, monkeypatch):
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
            captured["messages"] = messages
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content="Ava Patel scored above 70 with a match score of 88.0."
                ))]
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.batch_chat.OpenAI", DummyOpenAI)

    _seed_batch("1")
    token = "recruiter-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/batch-chat",
        json={"batch_id": "1", "question": "Who scored above 70?"},
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Ava Patel scored above 70 with a match score of 88.0."

    system_message = captured["messages"][0]["content"]
    assert "Backend Engineer" in system_message
    assert "Ava Patel" in system_message
    assert "88.0" in system_message
    assert "Ben Ortiz" in system_message
    assert "auto_ranked" in system_message
    assert "needs_review" in system_message
    assert captured["messages"][1] == {"role": "user", "content": "Who scored above 70?"}
