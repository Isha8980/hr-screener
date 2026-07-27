from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.dashboard import app
from app.schemas import CandidateProfile, ExplanationResult, FairnessCheckResult, GrowthRecommendation, JobRequirements, MatchResult


def test_dashboard_accepts_uploaded_resume_file(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr("app.dashboard.parse_job_description", lambda text: JobRequirements(
        title="Backend Engineer",
        required_skills=["Python"],
        preferred_skills=[],
        min_experience_years=3.0,
        max_experience_years=6.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    ))
    monkeypatch.setattr("app.dashboard.parse_resume", lambda text: CandidateProfile(
        name="Ava",
        skills=["Python"],
        experience_years=4.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text=text,
    ))
    monkeypatch.setattr("app.dashboard.match_candidate", lambda candidate, job: MatchResult(
        candidate_name=candidate.name,
        matched_skills=["Python"],
        missing_skills=[],
        experience_gap=1.0,
        match_score=90.0,
        confidence="high",
    ))
    monkeypatch.setattr("app.dashboard.run_fairness_check", lambda candidate, job: FairnessCheckResult(
        candidate_name=candidate.name,
        original_score=90.0,
        masked_score=90.0,
        score_delta=0.0,
        flagged=False,
    ))
    monkeypatch.setattr("app.dashboard.generate_explanation", lambda match_result: ExplanationResult(
        candidate_name=match_result.candidate_name,
        rationale_text="Good fit.",
        matched_skills=match_result.matched_skills,
        missing_skills=match_result.missing_skills,
        confidence=match_result.confidence,
    ))
    monkeypatch.setattr("app.dashboard.route_candidate", lambda match_result, fairness_result: "auto_ranked")
    monkeypatch.setattr("app.dashboard.suggest_growth_project", lambda match_result, candidate: GrowthRecommendation(
        candidate_name=candidate.name,
        missing_skill="",
        suggested_project="",
        resume_tip="",
    ))

    with open("tests/test_dashboard.py", "rb") as fh:
        response = client.post(
            "/candidates/upload",
            files={"file": ("resume.txt", fh, "text/plain")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"]
