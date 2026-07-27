from types import SimpleNamespace

from app.explain import generate_explanation
from app.schemas import ExplanationResult, MatchResult


def test_generate_explanation_mentions_input_skills(monkeypatch):
    match_result = MatchResult(
        candidate_name="Ava",
        matched_skills=["Python", "SQL"],
        missing_skills=["FastAPI"],
        experience_gap=1.0,
        match_score=82.0,
        confidence="medium",
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
            parsed = ExplanationResult(
                candidate_name=match_result.candidate_name,
                rationale_text="This candidate matches Python and SQL. Missing: FastAPI. Overall: strong fit.",
                matched_skills=match_result.matched_skills,
                missing_skills=match_result.missing_skills,
                confidence=match_result.confidence,
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))]
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.explain.OpenAI", DummyOpenAI)

    result = generate_explanation(match_result)

    assert isinstance(result, ExplanationResult)
    assert result.rationale_text.strip()
    assert "Python" in result.rationale_text or "FastAPI" in result.rationale_text
