"""
Unit tests for app/emailer.py
"""

import json
import os
from unittest.mock import patch

import pytest
import resend

from app.emailer import (
    RESEND_FROM_ADDRESS,
    build_interview_invite_email,
    build_rejection_email,
    log_sent_email,
    send_email,
)


@patch.dict(os.environ, {"RESEND_API_KEY": "re_test_key"})
@patch("app.emailer.resend.Emails.send")
def test_send_email_sends_via_resend_api(mock_send):
    send_email("candidate@example.com", "Subject line", "Body text")

    assert resend.api_key == "re_test_key"
    mock_send.assert_called_once_with(
        {
            "from": RESEND_FROM_ADDRESS,
            "to": ["candidate@example.com"],
            "subject": "Subject line",
            "text": "Body text",
        }
    )


@patch.dict(os.environ, {}, clear=True)
def test_send_email_raises_clear_error_when_api_key_missing():
    with pytest.raises(ValueError, match="RESEND_API_KEY"):
        send_email("candidate@example.com", "Subject", "Body")


@patch.dict(os.environ, {"RESEND_API_KEY": "re_test_key"})
@patch("app.emailer.resend.Emails.send")
def test_send_email_wraps_resend_api_errors_in_runtime_error(mock_send):
    mock_send.side_effect = resend.exceptions.ResendError(
        code=422,
        error_type="validation_error",
        message="Invalid `to` field",
        suggested_action="Check the recipient address.",
    )

    with pytest.raises(RuntimeError, match="Failed to send email"):
        send_email("candidate@example.com", "Subject", "Body")


@patch.dict(os.environ, {"RESEND_API_KEY": "re_test_key"})
@patch("app.emailer.resend.Emails.send")
def test_send_email_wraps_network_failures_in_runtime_error(mock_send):
    """The Resend SDK itself wraps network-level failures (e.g. DNS/connection
    errors) in a RuntimeError -- this must still surface as a clear RuntimeError
    from send_email, not be left unhandled."""
    mock_send.side_effect = RuntimeError("Request failed: connection error")

    with pytest.raises(RuntimeError, match="Failed to send email"):
        send_email("candidate@example.com", "Subject", "Body")


def test_build_interview_invite_email_uses_candidate_and_job_placeholders():
    subject, body = build_interview_invite_email("Ava Patel", "Backend Engineer")

    assert "Backend Engineer" in subject
    assert "Ava Patel" in body
    assert "Backend Engineer" in body


def test_build_rejection_email_uses_candidate_and_job_placeholders():
    subject, body = build_rejection_email("Ava Patel", "Backend Engineer")

    assert "Backend Engineer" in subject
    assert "Ava Patel" in body
    assert "Backend Engineer" in body


def test_log_sent_email_appends_entry_with_expected_fields(tmp_path, monkeypatch):
    monkeypatch.setattr("app.emailer.DATA_DIR", tmp_path)

    log_sent_email(recipient="candidate@example.com", subject="Interview Invitation: Backend Engineer", template_type="interview_invite")

    log_path = tmp_path / "sent_email_log.json"
    assert log_path.exists()
    entries = json.loads(log_path.read_text())
    assert len(entries) == 1
    assert entries[0]["recipient"] == "candidate@example.com"
    assert entries[0]["subject"] == "Interview Invitation: Backend Engineer"
    assert entries[0]["template_type"] == "interview_invite"
    assert "timestamp" in entries[0]


def test_log_sent_email_appends_to_existing_log(tmp_path, monkeypatch):
    monkeypatch.setattr("app.emailer.DATA_DIR", tmp_path)

    log_sent_email(recipient="first@example.com", subject="Subject 1", template_type="interview_invite")
    log_sent_email(recipient="second@example.com", subject="Subject 2", template_type="rejection")

    entries = json.loads((tmp_path / "sent_email_log.json").read_text())
    assert len(entries) == 2
    assert entries[0]["recipient"] == "first@example.com"
    assert entries[1]["recipient"] == "second@example.com"
