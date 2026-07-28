"""
Unit tests for app/resume_parser.py and app/pdf_reader.py
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.resume_parser import parse_resume, _sanitize_log_text
from app.pdf_reader import extract_text_from_pdf
from app.schemas import CandidateProfile


@pytest.fixture
def sample_resume_text():
    sample_path = os.path.join(os.path.dirname(__file__), "../data/sample_resumes/candidate_4.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        return f.read()


@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
@patch("app.resume_parser.OpenAI")
def test_parse_resume_success(mock_openai, sample_resume_text):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    expected_profile = CandidateProfile(
        name="Sam Okafor",
        skills=["Python", "FastAPI", "PostgreSQL", "Git", "Docker", "Linux", "REST APIs"],
        experience_years=2.0,
        education="Bachelor of Science in Information Technology, Lakeside University, 2023",
        certifications=[],
        raw_resume_text=sample_resume_text,
    )

    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message.parsed = expected_profile
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_parsed_choice]

    profile = parse_resume(sample_resume_text)

    assert isinstance(profile, CandidateProfile)
    assert profile.name == "Sam Okafor"
    assert "FastAPI" in profile.skills
    assert profile.experience_years == 2.0
    assert profile.certifications == []
    assert profile.raw_resume_text == sample_resume_text.strip()


@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
@patch("app.resume_parser.OpenAI")
def test_parse_resume_overwrites_model_raw_text_with_original_input(mock_openai):
    original_text = "  Name\n\t• Built an ATS parser\n- Preserved whitespace  \n"
    model_profile = CandidateProfile(
        name="Candidate",
        skills=["Python"],
        experience_years=1.0,
        education="Not specified",
        certifications=[],
        raw_resume_text="Model-generated normalized resume text",
    )

    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message.parsed = model_profile
    mock_openai.return_value.beta.chat.completions.parse.return_value.choices = [mock_parsed_choice]

    profile = parse_resume(original_text)

    assert profile.raw_resume_text == original_text.strip()


def test_parse_resume_empty_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_resume("   ")


@patch.dict(os.environ, {}, clear=True)
def test_parse_resume_missing_api_key(sample_resume_text):
    with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
        parse_resume(sample_resume_text)


def test_sanitize_log_text():
    raw_log = "John Doe john.doe@example.com (555) 123-4567 123 Main St"
    sanitized = _sanitize_log_text(raw_log)
    assert "john.doe@example.com" not in sanitized
    assert "(555) 123-4567" not in sanitized
    assert "[EMAIL_REDACTED]" in sanitized
    assert "[PHONE_REDACTED]" in sanitized


def test_extract_text_from_pdf_invalid():
    with pytest.raises(ValueError, match="cannot be empty"):
        extract_text_from_pdf("")


@patch("app.pdf_reader.PdfReader")
def test_extract_text_from_pdf_success(mock_pdf_reader):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Candidate Resume Content"
    mock_reader_inst = MagicMock()
    mock_reader_inst.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader_inst

    extracted = extract_text_from_pdf(b"%PDF-1.4 dummy content")
    assert extracted == "Candidate Resume Content"
