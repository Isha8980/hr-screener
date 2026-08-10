"""
Unit tests for the POST /send-email endpoint in app/dashboard.py
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dashboard import CANDIDATE_STORE, VALID_TOKENS, app
from app.schemas import CandidateProfile


@pytest.fixture
def client():
    CANDIDATE_STORE.clear()
    VALID_TOKENS.clear()
    yield TestClient(app)
    CANDIDATE_STORE.clear()
    VALID_TOKENS.clear()


def _seed_candidate(candidate_id: str, email: str | None, name: str = "Ava Patel") -> None:
    CANDIDATE_STORE[candidate_id] = {
        "candidate": CandidateProfile(
            name=name,
            skills=["Python"],
            experience_years=3.0,
            education="Bachelor of Science",
            certifications=[],
            raw_resume_text="Ava Patel resume",
            email=email,
        )
    }


def test_send_email_requires_recruiter_auth(client):
    _seed_candidate("1", email="ava@example.com")

    response = client.post(
        "/send-email",
        json={"candidate_id": "1", "template_type": "interview_invite", "job_title": "Backend Engineer"},
    )

    assert response.status_code == 401


@patch.dict(os.environ, {"SMTP_EMAIL": "recruiter@example.com", "SMTP_APP_PASSWORD": "app-password"})
@patch("app.emailer.smtplib.SMTP")
def test_send_email_succeeds_and_logs_for_candidate_with_email(mock_smtp_class, client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.emailer.DATA_DIR", tmp_path)
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    _seed_candidate("1", email="ava@example.com")
    token = "recruiter-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/send-email",
        json={"candidate_id": "1", "template_type": "interview_invite", "job_title": "Backend Engineer"},
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["recipient"] == "ava@example.com"
    assert "Backend Engineer" in payload["subject"]
    mock_server.sendmail.assert_called_once()
    sendmail_args = mock_server.sendmail.call_args[0]
    assert sendmail_args[1] == ["ava@example.com"]
    assert "Ava Patel" in sendmail_args[2]

    log_path = tmp_path / "sent_email_log.json"
    assert log_path.exists()
    entries = json.loads(log_path.read_text())
    assert len(entries) == 1
    assert entries[0]["recipient"] == "ava@example.com"
    assert entries[0]["template_type"] == "interview_invite"
    assert "timestamp" in entries[0]


@patch.dict(os.environ, {"SMTP_EMAIL": "recruiter@example.com", "SMTP_APP_PASSWORD": "app-password"})
@patch("app.emailer.smtplib.SMTP")
def test_send_email_allows_subject_and_body_overrides(mock_smtp_class, client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.emailer.DATA_DIR", tmp_path)
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    _seed_candidate("1", email="ava@example.com")
    token = "recruiter-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/send-email",
        json={
            "candidate_id": "1",
            "template_type": "rejection",
            "job_title": "Backend Engineer",
            "subject": "Custom subject line",
            "body": "Custom body text",
        },
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Custom subject line"
    sendmail_args = mock_server.sendmail.call_args[0]
    assert "Custom subject line" in sendmail_args[2]
    assert "Custom body text" in sendmail_args[2]


def test_send_email_returns_clear_error_for_candidate_without_email(client):
    _seed_candidate("1", email=None)
    token = "recruiter-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/send-email",
        json={"candidate_id": "1", "template_type": "interview_invite", "job_title": "Backend Engineer"},
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 400
    assert "No email found" in response.json()["detail"]


def test_send_email_returns_404_for_unknown_candidate(client):
    token = "recruiter-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/send-email",
        json={"candidate_id": "does-not-exist", "template_type": "interview_invite"},
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 404
