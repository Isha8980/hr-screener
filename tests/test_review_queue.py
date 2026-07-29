from pathlib import Path

from app.review_queue import log_override, route_candidate
from app.schemas import FairnessCheckResult, MatchResult


def test_route_candidate_outcomes(tmp_path, monkeypatch):
    monkeypatch.setattr("app.review_queue.DATA_DIR", tmp_path)

    match_result = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=82.0,
        confidence="high",
    )
    fairness_result = FairnessCheckResult(
        candidate_name="Ava",
        original_score=82.0,
        masked_score=82.0,
        score_delta=0.0,
        flagged=False,
    )

    assert route_candidate(match_result, fairness_result) == "auto_ranked"

    match_result.confidence = "medium"
    fairness_result.flagged = False
    assert route_candidate(match_result, fairness_result) == "needs_review"

    match_result.confidence = "low"
    fairness_result.flagged = True
    assert route_candidate(match_result, fairness_result) == "flagged_for_bias"

    log_override("Ava", "auto_ranked", "needs_review", "Needs more context")
    log_file = tmp_path / "override_log.json"
    assert log_file.exists()
    content = log_file.read_text()
    assert "Ava" in content
    assert "needs_review" in content


def test_medium_confidence_candidate_is_not_auto_ranked():
    match_result = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=57.0,
        confidence="medium",
    )
    fairness_result = FairnessCheckResult(
        candidate_name="Ava",
        original_score=57.0,
        masked_score=57.0,
        score_delta=0.0,
        flagged=False,
    )

    assert route_candidate(match_result, fairness_result) == "needs_review"


def test_low_scoring_unflagged_candidate_is_auto_rejected():
    match_result = MatchResult(
        candidate_name="Low Score",
        matched_skills=[],
        missing_skills=["Python"],
        experience_gap=-2.0,
        match_score=44.99,
        confidence="low",
    )
    fairness_result = FairnessCheckResult(
        candidate_name="Low Score",
        original_score=44.99,
        masked_score=44.99,
        score_delta=0.0,
        flagged=False,
    )

    assert route_candidate(match_result, fairness_result) == "auto_rejected"

    fairness_result.flagged = True
    assert route_candidate(match_result, fairness_result) == "flagged_for_bias"
