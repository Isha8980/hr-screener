"""
Recruiter-initiated candidate email sending and templates.
"""

import json
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
# Some hosting platforms (e.g. Render) block outbound SMTP connections entirely.
# Without an explicit timeout, a blocked/blackholed connection hangs the request
# indefinitely instead of failing with a clear error -- bound it so a network-level
# block surfaces as a fast, actionable RuntimeError rather than an infinite hang.
SMTP_CONNECT_TIMEOUT_SECONDS = 15


def send_email(to_email: str, subject: str, body: str) -> None:
    """Send a plain-text email via Gmail SMTP (STARTTLS).

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.

    Raises:
        ValueError: If SMTP_EMAIL or SMTP_APP_PASSWORD environment variables are not set.
        RuntimeError: If the SMTP send fails.
    """
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_app_password = os.getenv("SMTP_APP_PASSWORD")
    if not smtp_email:
        raise ValueError("SMTP_EMAIL environment variable is not set.")
    if not smtp_app_password:
        raise ValueError("SMTP_APP_PASSWORD environment variable is not set.")

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = smtp_email
    message["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_CONNECT_TIMEOUT_SECONDS) as server:
            server.starttls()
            server.login(smtp_email, smtp_app_password)
            server.sendmail(smtp_email, [to_email], message.as_string())
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(
            f"Failed to send email to '{to_email}': {exc}. If this is a timeout, the hosting "
            f"platform may be blocking outbound SMTP connections."
        ) from exc


def build_interview_invite_email(candidate_name: str, job_title: str) -> tuple[str, str]:
    """Return (subject, body) for an interview invitation email."""
    subject = f"Interview Invitation: {job_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Thank you for applying for the {job_title} position. We were impressed with your background "
        f"and would love to schedule an interview to learn more about you.\n\n"
        f"Please reply to this email with a few times that work well for you over the next week, and "
        f"we'll get something set up.\n\n"
        f"Looking forward to speaking with you.\n\n"
        f"Best regards,\n"
        f"The Hiring Team"
    )
    return subject, body


def build_rejection_email(candidate_name: str, job_title: str) -> tuple[str, str]:
    """Return (subject, body) for a warm, professional rejection email."""
    subject = f"Update on Your Application: {job_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Thank you for taking the time to apply for the {job_title} position and for sharing your "
        f"background with us. After careful consideration, we've decided to move forward with other "
        f"candidates whose experience more closely matches what we need for this particular role.\n\n"
        f"This was not an easy decision, and we genuinely appreciate the effort you put into your "
        f"application. We'd encourage you to apply again for future roles that match your skills.\n\n"
        f"We wish you all the best in your job search.\n\n"
        f"Warm regards,\n"
        f"The Hiring Team"
    )
    return subject, body


def log_sent_email(recipient: str, subject: str, template_type: str) -> None:
    """Append a sent-email record to a local JSON log file.

    In production this should be replaced with a real database-backed audit trail.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DATA_DIR / "sent_email_log.json"

    entries: list[dict] = []
    if log_path.exists():
        try:
            entries = json.loads(log_path.read_text())
        except json.JSONDecodeError:
            entries = []

    entries.append(
        {
            "recipient": recipient,
            "subject": subject,
            "template_type": template_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    log_path.write_text(json.dumps(entries, indent=2))
