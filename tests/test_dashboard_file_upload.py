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


def test_resume_file_endpoint_serves_uploaded_pdf_for_evaluated_candidate(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr("app.dashboard.extract_text_from_pdf", lambda data: "Ava Python resume text")
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
    monkeypatch.setattr("app.dashboard.suggest_growth_project", lambda match_result, candidate: None)
    monkeypatch.setattr("app.dashboard.generate_interview_questions", lambda match_result: ["Tell me about a Python project."])

    job_response = client.post("/jobs", json={"text": "Backend Engineer job"})
    assert job_response.status_code == 200
    job_id = job_response.json()["job_id"]

    pdf_bytes = b"%PDF-1.4 fake pdf content for testing\n%%EOF"
    upload_response = client.post(
        "/candidates/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 200
    candidate_id = upload_response.json()["candidate_id"]

    evaluate_response = client.post("/evaluate", json={"job_id": job_id, "candidate_id": candidate_id})
    assert evaluate_response.status_code == 200
    assert evaluate_response.json()["candidate_id"] == candidate_id
    assert evaluate_response.json()["has_resume_file"] is True

    file_response = client.get(f"/resume-file/{candidate_id}")
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "application/pdf"
    assert file_response.content == pdf_bytes


def test_resume_file_endpoint_returns_404_for_unknown_candidate():
    client = TestClient(app)
    response = client.get("/resume-file/does-not-exist")
    assert response.status_code == 404
