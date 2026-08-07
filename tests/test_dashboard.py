from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dashboard import app
from app.schemas import CandidateProfile, FairnessCheckResult, GrowthRecommendation, JobRequirements, MatchResult, ExplanationResult


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_routes_with_mocked_openai(monkeypatch, client):
    monkeypatch.setenv("RECRUITER_PASSWORD", "test-password-123")
    monkeypatch.setattr("app.dashboard.RECRUITER_PASSWORD", "test-password-123")

    class DummyOpenAI:
        def __init__(self, api_key):
            self.api_key = api_key

        @property
        def beta(self):
            return self

        @property
        def chat(self):
            return self

        @property
        def completions(self):
            return self

        def parse(self, model, messages, response_format):
            if response_format is JobRequirements:
                parsed = JobRequirements(
                    title="Backend Engineer",
                    required_skills=["Python", "FastAPI"],
                    preferred_skills=["Docker"],
                    min_experience_years=3.0,
                    max_experience_years=6.0,
                    education_level="Bachelor's Degree",
                    job_family="Engineering",
                )
            elif response_format is CandidateProfile:
                parsed = CandidateProfile(
                    name="Ava",
                    skills=["Python", "SQL"],
                    experience_years=4.0,
                    education="Bachelor of Science",
                    certifications=[],
                    raw_resume_text="Backend engineer resume",
                )
            elif response_format is ExplanationResult:
                parsed = ExplanationResult(
                    candidate_name="Ava",
                    rationale_text="This candidate matches Python. Missing: FastAPI. Overall: moderate fit.",
                    matched_skills=["Python"],
                    missing_skills=["FastAPI"],
                    confidence="medium",
                )
            elif response_format is GrowthRecommendation:
                parsed = GrowthRecommendation(
                    candidate_name="Ava",
                    missing_skill="FastAPI",
                    suggested_project="Build a FastAPI service with SQLAlchemy and PostgreSQL.",
                    resume_tip="Highlight the FastAPI project under backend development.",
                )
            else:
                parsed = None
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.dashboard.parse_job_description", lambda text: JobRequirements(
        title="Backend Engineer",
        required_skills=["Python", "FastAPI"],
        preferred_skills=["Docker"],
        min_experience_years=3.0,
        max_experience_years=6.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    ))
    monkeypatch.setattr("app.dashboard.parse_resume", lambda text: CandidateProfile(
        name="Ava",
        skills=["Python", "SQL"],
        experience_years=4.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Backend engineer resume",
    ))
    monkeypatch.setattr("app.dashboard.match_candidate", lambda candidate, job: MatchResult(
        candidate_name=candidate.name,
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=70.0,
        confidence="medium",
    ))
    monkeypatch.setattr("app.dashboard.run_fairness_check", lambda candidate, job: FairnessCheckResult(
        candidate_name=candidate.name,
        original_score=70.0,
        masked_score=70.0,
        score_delta=0.0,
        flagged=False,
    ))
    monkeypatch.setattr("app.dashboard.generate_explanation", lambda match_result: ExplanationResult(
        candidate_name=match_result.candidate_name,
        rationale_text="This candidate matches Python. Missing: FastAPI. Overall: moderate fit.",
        matched_skills=match_result.matched_skills,
        missing_skills=match_result.missing_skills,
        confidence=match_result.confidence,
    ))
    monkeypatch.setattr("app.dashboard.route_candidate", lambda match_result, fairness_result: "needs_review")
    monkeypatch.setattr("app.dashboard.suggest_growth_project", lambda match_result, candidate: GrowthRecommendation(
        candidate_name=candidate.name,
        missing_skill="FastAPI",
        suggested_project="Build a FastAPI service with SQLAlchemy and PostgreSQL.",
        resume_tip="Highlight the FastAPI project under backend development.",
    ))
    monkeypatch.setattr(
        "app.dashboard.generate_interview_questions",
        lambda match_result: ["How have you applied FastAPI in a production project?"],
    )
    monkeypatch.setattr("app.dashboard.log_override", lambda **kwargs: None)

    create_job_response = client.post("/jobs", json={"text": "Backend Engineer job"})
    assert create_job_response.status_code == 200
    job_id = create_job_response.json()["job_id"]

    create_candidate_response = client.post("/candidates", json={"text": "Ava resume"})
    assert create_candidate_response.status_code == 200
    candidate_id = create_candidate_response.json()["candidate_id"]

    evaluate_response = client.post("/evaluate", json={"job_id": job_id, "candidate_id": candidate_id})
    assert evaluate_response.status_code == 200
    assert evaluate_response.json()["routing_decision"] == "needs_review"
    assert evaluate_response.json()["growth_recommendation"]["suggested_project"]
    assert evaluate_response.json()["raw_resume_text"] == "Backend engineer resume"

    login_response = client.post("/recruiter/login", json={"password": "test-password-123"})
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    queue_response = client.get("/queue", headers={"X-Recruiter-Token": token})
    assert queue_response.status_code == 200
    assert queue_response.json()

    override_response = client.post(
        "/override",
        json={
            "candidate_name": "Ava",
            "original_decision": "needs_review",
            "recruiter_decision": "auto_ranked",
            "reason": "Strong experience",
        },
    )
    assert override_response.status_code == 200
    assert override_response.json()["status"] == "logged"


def test_queue_returns_401_without_valid_token(client):
    res_no_token = client.get("/queue")
    assert res_no_token.status_code == 401

    res_bad_token = client.get("/queue", headers={"X-Recruiter-Token": "invalid-token"})
    assert res_bad_token.status_code == 401


def test_recruiter_login_and_queue_access(monkeypatch, client):
    monkeypatch.setenv("RECRUITER_PASSWORD", "test-password-123")
    monkeypatch.setattr("app.dashboard.RECRUITER_PASSWORD", "test-password-123")

    res_invalid_pwd = client.post("/recruiter/login", json={"password": "wrong-password"})
    assert res_invalid_pwd.status_code == 401

    res_valid_pwd = client.post("/recruiter/login", json={"password": "test-password-123"})
    assert res_valid_pwd.status_code == 200
    token = res_valid_pwd.json()["token"]
    assert token

    res_queue = client.get("/queue", headers={"X-Recruiter-Token": token})
    assert res_queue.status_code == 200
    assert isinstance(res_queue.json(), list)
