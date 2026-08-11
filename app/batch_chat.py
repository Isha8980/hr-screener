"""
Stage 8: Recruiter Batch Chat -- Q&A over a completed batch screening run.
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


def _format_batch_context(results: list[dict], job_title: str) -> str:
    """Render batch screening results as a clean, readable per-candidate summary
    (not raw JSON) for use as LLM context."""
    lines = [f"Job: {job_title}", f"Total candidates screened: {len(results)}", ""]
    for index, item in enumerate(results, start=1):
        detail = item.get("detail") or {}
        match = detail.get("match_result") or {}
        matched_skills = match.get("matched_skills") or []
        missing_skills = match.get("missing_skills") or []
        lines.extend(
            [
                f"{index}. {item.get('candidate_name', 'Unknown')}",
                f"   Match Score: {item.get('match_score', 'N/A')}",
                f"   Routing Decision: {item.get('routing_decision', 'N/A')}",
                f"   Experience Gap vs. Job Minimum (years): {match.get('experience_gap', 'N/A')}",
                f"   Matched Skills: {', '.join(matched_skills) if matched_skills else 'None'}",
                f"   Missing Skills: {', '.join(missing_skills) if missing_skills else 'None'}",
                "",
            ]
        )
    return "\n".join(lines)


def answer_batch_question(results: list[dict], job_title: str, question: str) -> str:
    """Answer a recruiter's question about a batch of candidates, grounded strictly
    in the provided results -- never inferring or inventing facts not present.

    Args:
        results: The batch-evaluate results list (candidate_name, match_score,
            routing_decision, detail.match_result, etc.).
        job_title: The job title the batch was screened against.
        question: The recruiter's free-text question.

    Returns:
        The model's plain-text answer.

    Raises:
        ValueError: If results/question are empty, or OPENAI_API_KEY is not set.
        RuntimeError: If the OpenAI API call fails or returns no content.
    """
    if not results:
        raise ValueError("No batch results available to answer questions about.")
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    context = _format_batch_context(results, job_title)
    system_prompt = (
        "You are a recruiter's assistant answering questions about one specific batch of "
        "candidate screening results. Answer ONLY using the candidate data provided below. "
        "Do not use outside knowledge, and do not infer, guess, estimate, or invent any fact "
        "(skill, score, name, experience, or decision) that is not explicitly present in the "
        'data. If the answer cannot be determined from the data provided, respond exactly: '
        '"I don\'t have that information." Keep answers concise and reference specific '
        "candidate names when relevant.\n\n"
        f"Candidate data:\n{context}"
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
        raise RuntimeError(f"OpenAI API error occurred while answering batch question: {oe}") from oe
    except Exception as e:
        if isinstance(e, (RuntimeError, ValueError)):
            raise
        raise RuntimeError(f"An unexpected error occurred while answering batch question: {e}") from e
