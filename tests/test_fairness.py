"""
Unit tests for app/fairness.py
"""

import pytest
from app.fairness import run_fairness_check, BIAS_SCORE_DELTA_THRESHOLD, _mask_candidate_profile
from app.schemas import CandidateProfile, JobRequirements, FairnessCheckResult


@pytest.fixture
def target_job():
    return JobRequirements(
        title="Backend Software Engineer",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Docker"],
        min_experience_years=3.0,
        max_experience_years=6.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    )


def test_fairness_check_identical_skills_different_names(target_job):
    cand_1 = CandidateProfile(
        name="Alex Rivera",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years=4.0,
        education="Bachelor of Science in Computer Science, Stanford University",
        certifications=[],
        raw_resume_text="Alex Rivera - Backend Engineer with 4 years experience...",
    )

    cand_2 = CandidateProfile(
        name="Jordan Smith",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years=4.0,
        education="Bachelor of Science in Computer Science, City College",
        certifications=[],
        raw_resume_text="Jordan Smith - Backend Engineer with 4 years experience...",
    )

    result_1 = run_fairness_check(cand_1, target_job)
    result_2 = run_fairness_check(cand_2, target_job)

    assert isinstance(result_1, FairnessCheckResult)
    assert isinstance(result_2, FairnessCheckResult)

    assert result_1.candidate_name == "Alex Rivera"
    assert result_2.candidate_name == "Jordan Smith"

    # Both candidates have identical skills and experience so masked scores should match
    assert result_1.masked_score == result_2.masked_score
    assert isinstance(result_1.score_delta, float)
    assert isinstance(result_2.score_delta, float)


def test_mask_candidate_profile():
    candidate = CandidateProfile(
        name="John Doe",
        skills=["Python"],
        experience_years=2.0,
        education="Bachelor of Science, Harvard University",
        certifications=[],
        raw_resume_text="John Doe's Resume",
    )

    masked = _mask_candidate_profile(candidate)

    assert masked.name == "Candidate"
    assert "Harvard University" not in masked.education
    assert "University A" in masked.education
    assert "John Doe" not in masked.raw_resume_text


def test_fairness_check_custom_threshold(target_job):
    candidate = CandidateProfile(
        name="Sam Taylor",
        skills=["Python"],
        experience_years=2.0,
        education="BS Computer Science",
        certifications=[],
        raw_resume_text="Sam Taylor",
    )

    # Force threshold = 0.0 to test flagged behavior
    result = run_fairness_check(candidate, target_job, threshold=-1.0)
    assert result.flagged is True
