from types import SimpleNamespace
import json

from app.growth import generate_interview_questions, suggest_growth_project
from app.schemas import CandidateProfile, GrowthRecommendation, InterviewQuestions, MatchResult


def test_suggest_growth_project_returns_project_and_resume_tip(monkeypatch):
    match_result = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=70.0,
        confidence="medium",
    )
    candidate = CandidateProfile(
        name="Ava",
        skills=["Python", "SQL"],
        experience_years=4.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Backend engineer",
    )

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

        def parse(self, model, messages, response_format, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(parsed=GrowthRecommendation(
                    candidate_name=candidate.name,
                    missing_skill="FastAPI",
                    suggested_project="Build a small FastAPI service with SQLAlchemy and a CRUD API.",
                    resume_tip="Highlight the FastAPI service in your resume under backend projects.",
                )))]
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.growth.OpenAI", DummyOpenAI)

    result = suggest_growth_project(match_result, candidate)

    assert isinstance(result, GrowthRecommendation)
    assert result.suggested_project.strip()
    assert result.resume_tip.strip()


def test_suggest_growth_project_skips_excellent_fit(monkeypatch):
    match_result = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=92.0,
        confidence="high",
    )
    candidate = CandidateProfile(
        name="Ava",
        skills=["Python", "SQL"],
        experience_years=4.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Backend engineer",
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.growth.OpenAI", lambda *args, **kwargs: None)

    result = suggest_growth_project(match_result, candidate)

    assert result is None


def test_suggest_growth_project_generates_for_below_threshold(monkeypatch):
    match_result = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=75.0,
        confidence="high",
    )
    candidate = CandidateProfile(
        name="Ava",
        skills=["Python", "SQL"],
        experience_years=4.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Backend engineer",
    )

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

        def parse(self, model, messages, response_format, **kwargs):
            parsed = GrowthRecommendation(
                candidate_name=candidate.name,
                missing_skill="FastAPI",
                suggested_project="Build a FastAPI service using Python and SQL.",
                resume_tip="Highlight the FastAPI service on your resume.",
            )
            return type("Resp", (), {"choices": [type("Choice", (), {"message": type("Msg", (), {"parsed": parsed})()})()]})()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.growth.OpenAI", DummyOpenAI)

    result = suggest_growth_project(match_result, candidate)

    assert result is not None
    assert result.suggested_project


def test_generate_interview_questions_uses_each_candidates_match_data(monkeypatch):
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

        def parse(self, model, messages, response_format, **kwargs):
            payload = json.loads(messages[-1]["content"])
            missing_skill = payload["missing_skills"][0]
            parsed = InterviewQuestions(questions=[
                f"Describe your experience with {missing_skill}.",
                f"How would you close your gap in {missing_skill}?",
            ])
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.growth.OpenAI", DummyOpenAI)
    first_match = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=70.0,
        confidence="medium",
    )
    second_match = MatchResult(
        candidate_name="Ben",
        matched_skills=["SQL"],
        missing_skills=["Kubernetes"],
        experience_gap=2.0,
        match_score=55.0,
        confidence="low",
    )

    first_questions = generate_interview_questions(first_match)
    second_questions = generate_interview_questions(second_match)

    assert first_questions != second_questions
    assert "FastAPI" in first_questions[0]
    assert "Kubernetes" in second_questions[0]
