import pytest
from fastapi.testclient import TestClient

from app.dashboard import (
    AVG_MANUAL_REVIEW_MINUTES,
    AVG_RECRUITER_HOURLY_COST_INR,
    CANDIDATE_STORE,
    JOB_STORE,
    QUEUE_STORE,
    VALID_TOKENS,
    app,
)
from app.schemas import CandidateProfile, ExplanationResult, FairnessCheckResult, JobRequirements, MatchResult


@pytest.fixture
def client():
    JOB_STORE.clear()
    CANDIDATE_STORE.clear()
    QUEUE_STORE.clear()
    VALID_TOKENS.clear()
    yield TestClient(app)
    JOB_STORE.clear()
    CANDIDATE_STORE.clear()
    QUEUE_STORE.clear()
    VALID_TOKENS.clear()


@pytest.fixture
def mocked_batch_pipeline(monkeypatch):
    monkeypatch.setattr("app.dashboard.parse_job_description", lambda text: JobRequirements(
        title="Backend Engineer",
        required_skills=["Python", "FastAPI", "Kubernetes"],
        preferred_skills=[],
        min_experience_years=3.0,
        max_experience_years=6.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    ))

    def parse_resume(text):
        name = "Ava" if "Ava" in text else "Ben"
        return CandidateProfile(
            name=name,
            skills=["Python"] if name == "Ava" else ["SQL"],
            experience_years=4.0 if name == "Ava" else 2.0,
            education="Bachelor of Science",
            certifications=[],
            raw_resume_text=text.strip(),
        )

    def match_candidate(candidate, job):
        if candidate.name == "Ava":
            return MatchResult(
                candidate_name="Ava",
                matched_skills=["Python", "FastAPI"],
                missing_skills=["Kubernetes"],
                experience_gap=0.0,
                match_score=88.0,
                confidence="high",
            )
        return MatchResult(
            candidate_name="Ben",
            matched_skills=["Python"],
            missing_skills=["FastAPI", "Kubernetes"],
            experience_gap=1.0,
            match_score=52.0,
            confidence="medium",
        )

    monkeypatch.setattr("app.dashboard.parse_resume", parse_resume)
    monkeypatch.setattr("app.dashboard.match_candidate", match_candidate)
    monkeypatch.setattr("app.dashboard.run_fairness_check", lambda candidate, job: FairnessCheckResult(
        candidate_name=candidate.name,
        original_score=88.0 if candidate.name == "Ava" else 52.0,
        masked_score=88.0 if candidate.name == "Ava" else 52.0,
        score_delta=0.0,
        flagged=False,
    ))
    monkeypatch.setattr("app.dashboard.generate_explanation", lambda match: ExplanationResult(
        candidate_name=match.candidate_name,
        rationale_text=f"Evaluation for {match.candidate_name}",
        matched_skills=match.matched_skills,
        missing_skills=match.missing_skills,
        confidence=match.confidence,
    ))
    monkeypatch.setattr(
        "app.dashboard.route_candidate",
        lambda match, fairness: "auto_ranked" if match.match_score >= 80 else "needs_review",
    )
    monkeypatch.setattr("app.dashboard.suggest_growth_project", lambda match, candidate: None)
    monkeypatch.setattr(
        "app.dashboard.generate_interview_questions",
        lambda match: [
            f"How have you used {match.missing_skills[0]}?",
            f"How would you close your {match.experience_gap}-year experience gap?",
        ],
    )


def create_job(client):
    response = client.post("/jobs", json={"text": "Backend engineer role"})
    assert response.status_code == 200
    return response.json()["job_id"]


def test_batch_evaluate_requires_recruiter_auth(client, mocked_batch_pipeline):
    job_id = create_job(client)

    response = client.post(
        "/batch-evaluate",
        data={"job_id": job_id},
        files=[("files", ("ava.txt", b"Ava resume", "text/plain"))],
    )

    assert response.status_code == 401


def test_batch_evaluate_ranks_multiple_resumes_and_returns_specific_questions(client, mocked_batch_pipeline):
    job_id = create_job(client)
    token = "batch-test-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/batch-evaluate",
        data={"job_id": job_id},
        files=[
            ("files", ("ben.txt", b"Ben resume", "text/plain")),
            ("files", ("ava.txt", b"Ava resume", "text/plain")),
        ],
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    results = payload["results"]
    assert [result["candidate_name"] for result in results] == ["Ava", "Ben"]
    assert [result["match_score"] for result in results] == [88.0, 52.0]
    assert results[0]["matched_skills_count"] == 2
    assert results[1]["missing_skills_count"] == 2
    assert results[0]["detail"]["routing_decision"] == "auto_ranked"
    assert "Kubernetes" in results[0]["interview_questions"][0]
    assert results[1]["interview_questions"] is None
    assert results[0]["detail"]["interview_questions"] == results[0]["interview_questions"]
    assert results[1]["detail"]["interview_questions"] is None
    assert results[0]["detail"]["raw_resume_text"] == "Ava resume"
    assert results[1]["detail"]["raw_resume_text"] == "Ben resume"


def test_batch_evaluate_includes_time_and_cost_savings_summary(client, mocked_batch_pipeline):
    job_id = create_job(client)
    token = "batch-test-token"
    VALID_TOKENS.add(token)

    response = client.post(
        "/batch-evaluate",
        data={"job_id": job_id},
        files=[
            ("files", ("ben.txt", b"Ben resume", "text/plain")),
            ("files", ("ava.txt", b"Ava resume", "text/plain")),
        ],
        headers={"X-Recruiter-Token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert summary["candidates_screened"] == 2
    assert summary["avg_manual_review_minutes_assumption"] == AVG_MANUAL_REVIEW_MINUTES
    assert summary["avg_recruiter_hourly_cost_inr_assumption"] == AVG_RECRUITER_HOURLY_COST_INR

    raw_hours = (2 * AVG_MANUAL_REVIEW_MINUTES) / 60.0
    assert summary["estimated_time_saved_hours"] == round(raw_hours, 2)
    assert summary["estimated_cost_saved_inr"] == round(raw_hours * AVG_RECRUITER_HOURLY_COST_INR, 2)

    assert isinstance(summary["actual_processing_seconds"], (int, float))
    assert summary["actual_processing_seconds"] >= 0
