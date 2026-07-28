"""
Stage 1: Resume Parsing.
"""

import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.schemas import CandidateProfile

load_dotenv()

logger = logging.getLogger(__name__)


def _sanitize_log_text(text: str) -> str:
    """
    Sanitize text for logging by stripping obvious PII (emails, phone numbers, addresses, SSNs).
    """
    # Mask email addresses
    sanitized = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", text)
    # Mask phone numbers
    sanitized = re.sub(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]", sanitized)
    # Truncate log output to prevent dumping entire resume text
    if len(sanitized) > 100:
        sanitized = sanitized[:100] + "... [TRUNCATED]"
    return sanitized


def parse_resume(text: str) -> CandidateProfile:
    """
    Parse raw resume text into a structured CandidateProfile using OpenAI API.

    Args:
        text: Raw resume text extracted from plain text or PDF.

    Returns:
        CandidateProfile: Validated structured candidate profile.

    Raises:
        ValueError: If input text is empty or invalid.
        RuntimeError: If OpenAI API call fails or returns invalid response.
    """
    if not text or not text.strip():
        raise ValueError("Resume text cannot be empty.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    # Log action with sanitized input (never log full raw resume text)
    sanitized_preview = _sanitize_log_text(text)
    logger.info(f"Parsing resume text preview: {sanitized_preview}")

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are an expert HR recruitment assistant. "
        "Your task is to parse raw resume text and extract candidate profile information matching "
        "the exact schema: name, skills (list of strings), experience_years (numeric total years of experience), "
        "education (degree/university details), certifications (list of strings, default to empty list if none), "
        "and raw_resume_text (the raw input text).\n"
        "Handle missing sections gracefully (e.g. if certifications or education are omitted, provide empty list or 'Not specified')."
    )

    try:
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format=CandidateProfile,
            )
            parsed_profile = completion.choices[0].message.parsed
            if parsed_profile is None:
                raise ValueError("OpenAI structured output returned None.")

            parsed_profile.raw_resume_text = text.strip()

            return parsed_profile

        except AttributeError:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt + " Respond with valid JSON matching the schema."},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI API returned an empty response.")

            profile = CandidateProfile.model_validate_json(content)
            profile.raw_resume_text = text.strip()
            return profile

    except ValidationError as ve:
        raise RuntimeError(f"Failed to validate OpenAI response into CandidateProfile: {ve}") from ve
    except OpenAIError as oe:
        raise RuntimeError(f"OpenAI API error occurred while parsing resume: {oe}") from oe
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"An unexpected error occurred while parsing resume: {e}") from e
