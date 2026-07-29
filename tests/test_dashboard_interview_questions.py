from unittest.mock import Mock

import pytest

from app.dashboard import QUEUE_STORE, _run_evaluation
from app.schemas import CandidateProfile, ExplanationResult, FairnessCheckResult, JobRequirements, MatchResult


def _run(monkeypatch, routing_decision, score):
    QUEUE_STORE.clear()
    candidate = CandidateProfile(
        name="Ava",
        skills=["Python"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Ava Python resume",
    )
    job = JobRequirements(
        title="Backend Engineer",
        required_skills=["Python", "FastAPI"],
        preferred_skills=[],
        min_experience_years=3.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    )
    match_result = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=0.0,
        match_score=score,
        confidence="high" if score >= 70 else ("medium" if score >= 45 else "low"),
    )
    questions_mock = Mock(return_value=["Question one?", "Question two?"])

    monkeypatch.setattr("app.dashboard.match_candidate", lambda candidate, job: match_result)
    monkeypatch.setattr("app.dashboard.run_fairness_check", lambda candidate, job: FairnessCheckResult(
        candidate_name="Ava",
        original_score=score,
        masked_score=score,
        score_delta=0.0,
        flagged=routing_decision == "flagged_for_bias",
    ))
    monkeypatch.setattr("app.dashboard.generate_explanation", lambda match: ExplanationResult(
        candidate_name="Ava",
        rationale_text="Evaluation rationale.",
        matched_skills=match.matched_skills,
        missing_skills=match.missing_skills,
        confidence=match.confidence,
    ))
    monkeypatch.setattr("app.dashboard.route_candidate", lambda match, fairness: routing_decision)
    monkeypatch.setattr("app.dashboard.suggest_growth_project", lambda match, candidate: None)
    monkeypatch.setattr("app.dashboard.generate_interview_questions", questions_mock)

    result, _ = _run_evaluation(job, candidate, "candidate-1")
    return result, questions_mock


@pytest.mark.parametrize(
    "routing_decision",
    ["auto_ranked", "needs_review", "flagged_for_bias", "auto_rejected"],
)
def test_interview_questions_generated_for_high_score_regardless_of_routing(monkeypatch, routing_decision):
    """A match_score of 80 (>= 70) must trigger question generation no matter the routing decision."""
    result, questions_mock = _run(monkeypatch, routing_decision, 80.0)

    assert result["interview_questions"] == ["Question one?", "Question two?"]
    questions_mock.assert_called_once()


def test_interview_questions_not_generated_for_low_score_even_when_needs_review(monkeypatch):
    """A match_score of 60 (< 70) must not trigger question generation even when routed to needs_review."""
    result, questions_mock = _run(monkeypatch, "needs_review", 60.0)

    assert result["interview_questions"] is None
    questions_mock.assert_not_called()


@pytest.mark.parametrize(
    ("routing_decision", "score", "expect_questions"),
    [
        ("auto_ranked", 69.9, False),
        ("auto_rejected", 90.0, True),
        ("flagged_for_bias", 70.0, True),
        ("needs_review", 30.0, False),
    ],
)
def test_interview_questions_threshold_is_the_only_deciding_factor(
    monkeypatch, routing_decision, score, expect_questions
):
    result, questions_mock = _run(monkeypatch, routing_decision, score)

    if expect_questions:
        assert result["interview_questions"] == ["Question one?", "Question two?"]
        questions_mock.assert_called_once()
    else:
        assert result["interview_questions"] is None
        questions_mock.assert_not_called()
