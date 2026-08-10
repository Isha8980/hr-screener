"""
Unit tests for app/emailer.py
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from app.emailer import (
    build_interview_invite_email,
    build_rejection_email,
    log_sent_email,
    send_email,
)


@patch.dict(os.environ, {"SMTP_EMAIL": "recruiter@example.com", "SMTP_APP_PASSWORD": "app-password"})
@patch("app.emailer.smtplib.SMTP")
def test_send_email_uses_gmail_smtp_with_starttls(mock_smtp_class):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_email("candidate@example.com", "Subject line", "Body text")

    mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587, timeout=15)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("recruiter@example.com", "app-password")
    mock_server.sendmail.assert_called_once()
    call_args = mock_server.sendmail.call_args
    assert call_args[0][0] == "recruiter@example.com"
    assert call_args[0][1] == ["candidate@example.com"]
    assert "Subject line" in call_args[0][2]
    assert "Body text" in call_args[0][2]


@patch.dict(os.environ, {}, clear=True)
def test_send_email_raises_clear_error_when_smtp_email_missing():
    with pytest.raises(ValueError, match="SMTP_EMAIL"):
        send_email("candidate@example.com", "Subject", "Body")


@patch.dict(os.environ, {"SMTP_EMAIL": "recruiter@example.com"}, clear=True)
def test_send_email_raises_clear_error_when_smtp_app_password_missing():
    with pytest.raises(ValueError, match="SMTP_APP_PASSWORD"):
        send_email("candidate@example.com", "Subject", "Body")


@patch.dict(os.environ, {"SMTP_EMAIL": "recruiter@example.com", "SMTP_APP_PASSWORD": "app-password"})
@patch("app.emailer.smtplib.SMTP")
def test_send_email_wraps_smtp_failures_in_runtime_error(mock_smtp_class):
    import smtplib

    mock_server = MagicMock()
    mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad credentials")
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    with pytest.raises(RuntimeError, match="Failed to send email"):
        send_email("candidate@example.com", "Subject", "Body")


@patch.dict(os.environ, {"SMTP_EMAIL": "recruiter@example.com", "SMTP_APP_PASSWORD": "app-password"})
@patch("app.emailer.smtplib.SMTP")
def test_send_email_wraps_blocked_connection_timeout_in_runtime_error(mock_smtp_class):
    """A hosting platform silently blocking outbound SMTP raises a socket-level
    OSError (e.g. TimeoutError), not an smtplib.SMTPException -- this must still
    be caught and turned into a clear RuntimeError, not left to hang or propagate
    as an unhandled exception."""
    mock_smtp_class.side_effect = TimeoutError("timed out")

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
