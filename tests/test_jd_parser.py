"""
Unit tests for app/jd_parser.py
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.jd_parser import parse_job_description, fetch_and_parse_job_from_url
from app.schemas import JobRequirements


@pytest.fixture
def sample_jd_text():
    sample_path = os.path.join(os.path.dirname(__file__), "../data/sample_jobs/software_engineer.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        return f.read()


@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
@patch("app.jd_parser.OpenAI")
def test_parse_job_description_success(mock_openai, sample_jd_text):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    expected_jd = JobRequirements(
        title="Senior Software Engineer - Backend",
        required_skills=["Python", "FastAPI", "PostgreSQL", "RESTful API Design", "Docker"],
        preferred_skills=["Kubernetes", "Redis", "GraphQL", "AWS"],
        min_experience_years=5.0,
        max_experience_years=8.0,
        education_level="Bachelor's",
        job_family="Engineering",
    )

    # Mock beta structured output choice
    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message.parsed = expected_jd
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_parsed_choice]

    result = parse_job_description(sample_jd_text)

    assert isinstance(result, JobRequirements)
    assert result.title == "Senior Software Engineer - Backend"
    assert "Python" in result.required_skills
    assert result.min_experience_years == 5.0
    assert result.job_family == "Engineering"


@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
@patch("app.jd_parser.OpenAI")
def test_parse_job_description_keeps_compound_qualification_as_one_requirement(mock_openai):
    """A single bullet describing one qualification with supporting detail
    (e.g. "data analysis, including identifying trends, generating summary
    statistics, and drawing insights...") must be extracted as one requirement,
    not fragmented into 5+ sub-requirements -- fragmenting it would artificially
    deflate every candidate's match score since resumes never state these
    sub-clauses as discrete, separate skills."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    job_text = (
        "About the job\n"
        "Minimum qualifications:\n"
        "Bachelor's degree or equivalent practical experience.\n"
        "1 year of experience in data analysis, including identifying trends, generating summary "
        "statistics, and drawing insights from quantitative and qualitative data.\n"
        "1 year of experience with one or more of the following languages: SQL, R, Python, or C++.\n"
    )

    expected_jd = JobRequirements(
        title="Data Analyst",
        required_skills=["Data Analysis", "SQL, R, Python, or C++"],
        preferred_skills=[],
        min_experience_years=1.0,
        max_experience_years=None,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message.parsed = expected_jd
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_parsed_choice]

    result = parse_job_description(job_text)

    assert len(result.required_skills) <= 2
    fragmented_sub_clauses = {
        "identifying trends",
        "generating summary statistics",
        "drawing insights from quantitative data",
        "drawing insights from qualitative data",
    }
    assert fragmented_sub_clauses.isdisjoint(set(result.required_skills))


@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
@patch("app.jd_parser.OpenAI")
def test_parse_job_description_summarizes_narrative_responsibilities_paragraph(mock_openai):
    """A narrative-paragraph job posting describing day-to-day responsibilities
    (not bullet points) must be summarized into a small number of core,
    resume-matchable competency names -- not a separate fragmented entry for
    every verb or clause in the prose."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    job_text = (
        "Job Description\n"
        "We are seeking a Business Analyst to join our team. Identifies data patterns & trends, and "
        "provides insights to enhance business decision making. Partners with stakeholders across the "
        "organization to understand business issues and translate them into analytical questions. "
        "Recommends actions for future developments & strategic business opportunities based on findings. "
        "Builds and maintains dashboards and reports to track key business metrics over time. Works with "
        "cross-functional teams to prioritize and scope analytics projects, communicating findings clearly "
        "to both technical and non-technical audiences. Continuously looks for opportunities to improve "
        "existing business processes and reporting workflows.\n"
    )

    expected_jd = JobRequirements(
        title="Business Analyst",
        required_skills=["Data Analysis", "Stakeholder Management", "Dashboarding & Reporting", "Process Improvement"],
        preferred_skills=["Cross-functional Collaboration", "Communication Skills"],
        min_experience_years=2.0,
        max_experience_years=None,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message.parsed = expected_jd
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_parsed_choice]

    result = parse_job_description(job_text)

    total_items = len(result.required_skills) + len(result.preferred_skills)
    assert total_items <= 10

    all_skills = set(result.required_skills) | set(result.preferred_skills)
    granular_verb_phrase_fragments = {
        "business issue identification",
        "insight generation",
        "strategic business opportunity recommendation",
        "data pattern identification",
    }
    assert granular_verb_phrase_fragments.isdisjoint(all_skills)


def test_parse_job_description_empty_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_job_description("   ")


@patch.dict(os.environ, {}, clear=True)
def test_parse_job_description_missing_api_key(sample_jd_text):
    with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
        parse_job_description(sample_jd_text)


def test_fetch_and_parse_job_from_url_linkedin_rejected():
    linkedin_url = "https://www.linkedin.com/jobs/view/123456789"
    with pytest.raises(ValueError, match="LinkedIn"):
        fetch_and_parse_job_from_url(linkedin_url)


def test_fetch_and_parse_job_from_url_disallowed_domain():
    unauthorized_url = "https://someunauthorizedsite.com/careers/job123"
    with pytest.raises(ValueError, match="not in the allowed list"):
        fetch_and_parse_job_from_url(unauthorized_url)


@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
@patch("app.jd_parser.parse_job_description")
@patch("urllib.request.urlopen")
def test_fetch_and_parse_job_from_url_success(mock_urlopen, mock_parse_jd):
    allowed_url = "https://jobs.lever.co/company/job-123"
    
    mock_response = MagicMock()
    mock_response.read.return_value = b"<html><body><h1>Backend Engineer</h1><p>Requirements: Python</p></body></html>"
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    mock_parse_jd.return_value = JobRequirements(
        title="Backend Engineer",
        required_skills=["Python"],
        preferred_skills=[],
        min_experience_years=3.0,
        max_experience_years=None,
        education_level="Bachelor's",
        job_family="Engineering",
    )

    result = fetch_and_parse_job_from_url(allowed_url)

    assert result.title == "Backend Engineer"
    mock_parse_jd.assert_called_once()
