"""
Recruiter-initiated candidate email sending and templates.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import resend
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Resend's shared sandbox sender -- works immediately with no domain verification.
# Once a custom domain is verified with Resend, swap this for an address on that
# domain (e.g. "recruiting@yourcompany.com") for better deliverability/branding.
RESEND_FROM_ADDRESS = "onboarding@resend.dev"


def send_email(to_email: str, subject: str, body: str) -> None:
    """Send a plain-text email via the Resend HTTP API.

    Uses Resend's HTTPS API rather than raw SMTP because many hosting platforms
    (e.g. Render's free tier) block outbound SMTP connections entirely; a normal
    HTTPS API call is not affected by that restriction.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.

    Raises:
        ValueError: If the RESEND_API_KEY environment variable is not set.
        RuntimeError: If the Resend API call fails.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise ValueError("RESEND_API_KEY environment variable is not set.")

    resend.api_key = api_key

    try:
        resend.Emails.send(
            {
                "from": RESEND_FROM_ADDRESS,
                "to": [to_email],
                "subject": subject,
                "text": body,
            }
        )
    except (resend.exceptions.ResendError, RuntimeError) as exc:
        raise RuntimeError(f"Failed to send email to '{to_email}': {exc}") from exc


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
