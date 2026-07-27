"""
Stage 4: Explainability Layer.
"""

import os
import json

from dotenv import load_dotenv
from pydantic import ValidationError

try:
    from openai import OpenAI, OpenAIError
except ModuleNotFoundError:  # pragma: no cover - exercised in environments without the dependency
    class OpenAIError(Exception):
        """Fallback OpenAI error type when the package is unavailable."""

    class OpenAI:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            raise RuntimeError("openai package is not installed")

from app.schemas import ExplanationResult, MatchResult

load_dotenv()


def generate_explanation(match_result: MatchResult) -> ExplanationResult:
    """Generate a short, plain-English explanation from match data without inventing facts."""
    if not isinstance(match_result, MatchResult):
        match_result = MatchResult.model_validate(match_result)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are an expert HR recruiting assistant. Write a short plain-English rationale "
        "based only on the provided match data. Keep it to 2-3 sentences and follow this style: "
        '"This candidate matches X of Y required skills. Missing: [skill]. Experience is '
        '[above/below/within] range. Overall: [brief verdict]." '
        "Do not invent missing skills, experience, or any other facts. Only summarize the input."
    )
    user_payload = json.dumps(
        {
            "candidate_name": match_result.candidate_name,
            "matched_skills": match_result.matched_skills,
            "missing_skills": match_result.missing_skills,
            "experience_gap": match_result.experience_gap,
            "match_score": match_result.match_score,
            "confidence": match_result.confidence,
        },
        indent=2,
    )

    try:
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_payload},
                ],
                response_format=ExplanationResult,
            )
            parsed_result = completion.choices[0].message.parsed
            if parsed_result is None:
                raise ValueError("OpenAI structured output returned None.")
            return parsed_result
        except AttributeError:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt + " Respond with valid JSON matching the schema."},
                    {"role": "user", "content": user_payload},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI API returned an empty response.")
            return ExplanationResult.model_validate_json(content)
    except ValidationError as ve:
        raise RuntimeError(f"Failed to validate OpenAI response into ExplanationResult: {ve}") from ve
    except OpenAIError as oe:
        raise RuntimeError(f"OpenAI API error occurred while generating explanation: {oe}") from oe
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"An unexpected error occurred while generating explanation: {e}") from e


def explain_match(match_result: dict, fairness_result: dict) -> dict:
    """Generate human-readable explanations for match scoring and decisions."""
    return {"match_result": match_result, "fairness_result": fairness_result}
