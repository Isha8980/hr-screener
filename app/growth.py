"""
Stage 6: Project / Career Recommendations.
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

from app.schemas import CandidateProfile, GrowthRecommendation, MatchResult

load_dotenv()


def suggest_growth_project(match_result: MatchResult, candidate: CandidateProfile) -> GrowthRecommendation | None:
    """Suggest one concrete project to help a candidate close a specific skill gap."""
    if match_result.match_score >= 90.0:
        return None

    missing_skills = match_result.missing_skills or []
    if not missing_skills:
        raise ValueError("No missing skills available for growth suggestions.")

    target_skill = missing_skills[0]
    existing_skills = candidate.skills or []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are an expert technical mentor. Suggest one specific, doable project that uses the "
        "candidate's existing skills to help them learn the target missing skill. Do not suggest "
        "a generic course. Return a concrete buildable project idea and a one-line resume tip."
    )
    user_payload = json.dumps(
        {
            "candidate_name": candidate.name,
            "existing_skills": existing_skills,
            "target_missing_skill": target_skill,
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
                response_format=GrowthRecommendation,
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
            return GrowthRecommendation.model_validate_json(content)
    except ValidationError as ve:
        raise RuntimeError(f"Failed to validate OpenAI response into GrowthRecommendation: {ve}") from ve
    except OpenAIError as oe:
        raise RuntimeError(f"OpenAI API error occurred while generating growth recommendation: {oe}") from oe
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"An unexpected error occurred while generating growth recommendation: {e}") from e


def recommend_growth_paths(candidate_data: dict, jd_data: dict) -> dict:
    """Provide growth and development recommendations to bridge candidate gaps."""
    return {"candidate_data": candidate_data, "jd_data": jd_data}
