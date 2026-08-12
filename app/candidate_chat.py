"""
Stage 9: Candidate-Facing Chat -- Q&A over a single candidate's own evaluation.
"""

import os

from dotenv import load_dotenv

try:
    from openai import OpenAI, OpenAIError
except ModuleNotFoundError:  # pragma: no cover - exercised in environments without the dependency
    class OpenAIError(Exception):
        """Fallback OpenAI error type when the package is unavailable."""

    class OpenAI:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            raise RuntimeError("openai package is not installed")

load_dotenv()


def _format_candidate_context(evaluation: dict, candidate_name: str) -> str:
    """Render a single candidate's own evaluation data as a clean, readable
    summary (not raw JSON) for use as LLM context. Deliberately includes only
    this one candidate's data -- no other candidate is ever referenced."""
    match = evaluation.get("match_result") or {}
    growth = evaluation.get("growth_recommendation")
    ats = evaluation.get("resume_formatting_check") or {}

    matched_skills = match.get("matched_skills") or []
    missing_skills = match.get("missing_skills") or []

    lines = [
        f"Candidate: {candidate_name}",
        f"Match Score: {match.get('match_score', 'N/A')}",
        f"Confidence: {match.get('confidence', 'N/A')}",
        f"Matched Skills: {', '.join(matched_skills) if matched_skills else 'None'}",
        f"Missing Skills: {', '.join(missing_skills) if missing_skills else 'None'}",
        f"Experience Gap vs. Job Minimum (years): {match.get('experience_gap', 'N/A')}",
    ]

    if growth:
        lines.extend(
            [
                "",
                f"Suggested Growth Project: {growth.get('suggested_project', 'N/A')}",
                f"Resume Tip: {growth.get('resume_tip', 'N/A')}",
            ]
        )

    issues = ats.get("issues") or []
    suggestions = ats.get("suggestions") or []
    if issues or suggestions:
        lines.append("")
        lines.append("Resume Formatting Notes:")
        lines.extend(f"- Issue: {issue}" for issue in issues)
        lines.extend(f"- Suggestion: {suggestion}" for suggestion in suggestions)

    return "\n".join(lines)


def answer_candidate_question(evaluation: dict, candidate_name: str, question: str) -> str:
    """Answer a candidate's question about their own evaluation, grounded strictly
    in their own match data -- never referencing other candidates, never
    predicting or promising a hiring outcome, and never inventing facts.

    Args:
        evaluation: This candidate's own evaluation result dict (as returned by
            _run_evaluation: match_result, growth_recommendation,
            resume_formatting_check, etc.).
        candidate_name: The candidate's name.
        question: The candidate's free-text question.

    Returns:
        The model's plain-text answer.

    Raises:
        ValueError: If evaluation/question are empty, or OPENAI_API_KEY is not set.
        RuntimeError: If the OpenAI API call fails or returns no content.
    """
    if not evaluation:
        raise ValueError("No evaluation data available to answer questions about.")
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    context = _format_candidate_context(evaluation, candidate_name)
    system_prompt = (
        "Your name is Sage. You are a supportive, constructive career assistant helping a job "
        f"candidate understand their own screening results. Answer ONLY using {candidate_name}'s "
        "own evaluation data provided below.\n\n"
        "Strict rules:\n"
        "- Never discuss, mention, or compare this candidate to any other candidate. You have no "
        "information about anyone else's results and must never imply otherwise.\n"
        "- Never make hiring predictions, promises, or guesses about the outcome of this "
        "application (e.g. whether they will be hired, interviewed, or rejected). That decision "
        "belongs to the recruiting team, not you.\n"
        "- You SHOULD compare, filter, and reason over the evaluation data provided below to "
        "answer questions -- for example, whether their score or experience meets a number the "
        "candidate asks about. This is expected analysis of their own data, not fabrication. If "
        "the data shows they do not meet some threshold they ask about, say so directly and "
        "plainly rather than saying you don't have that information.\n"
        "- Do not infer, guess, estimate, or invent any fact (skill, score, reason, or detail) "
        "that is not explicitly present in the data below -- this is about not inventing facts, "
        "not about avoiding legitimate comparisons of the facts you do have.\n"
        '- Only respond exactly "I don\'t have that information." when the question asks about '
        "something genuinely absent from the data below (e.g. a detail never captured).\n\n"
        "Keep your tone warm, encouraging, and constructive, like supportive career coaching "
        "feedback -- similar in spirit to the growth recommendations this app already gives "
        "candidates.\n\n"
        f"{candidate_name}'s evaluation data:\n{context}"
    )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        answer = response.choices[0].message.content
        if not answer:
            raise ValueError("OpenAI API returned an empty response.")
        return answer.strip()
    except OpenAIError as oe:
        raise RuntimeError(f"OpenAI API error occurred while answering candidate question: {oe}") from oe
    except Exception as e:
        if isinstance(e, (RuntimeError, ValueError)):
            raise
        raise RuntimeError(f"An unexpected error occurred while answering candidate question: {e}") from e
