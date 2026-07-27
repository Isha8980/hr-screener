#!/usr/bin/env python3
"""Run the full HR screener pipeline over sample job and resume data."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.explain import generate_explanation
from app.fairness import run_fairness_check
from app.growth import suggest_growth_project
from app.jd_parser import parse_job_description
from app.matcher import match_candidate
from app.review_queue import route_candidate
from app.resume_parser import parse_resume


DATA_DIR = ROOT / "data"
SAMPLE_JOB_PATH = DATA_DIR / "sample_jobs" / "software_engineer.txt"
SAMPLE_RESUME_DIR = DATA_DIR / "sample_resumes"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    if not SAMPLE_JOB_PATH.exists():
        raise FileNotFoundError(f"Sample job file not found: {SAMPLE_JOB_PATH}")

    job = parse_job_description(_read_text(SAMPLE_JOB_PATH))
    resume_paths = sorted(SAMPLE_RESUME_DIR.glob("candidate_*.txt"))
    if not resume_paths:
        raise FileNotFoundError(f"No sample resumes found in {SAMPLE_RESUME_DIR}")

    print("HR Screener Demo")
    print("=" * 72)

    for resume_path in resume_paths[:3]:
        candidate = parse_resume(_read_text(resume_path))
        match_result = match_candidate(candidate, job)
        fairness_result = run_fairness_check(candidate, job)
        explanation_result = generate_explanation(match_result)
        routing_decision = route_candidate(match_result, fairness_result)

        growth_recommendation = None
        if routing_decision != "auto_ranked":
            try:
                growth_recommendation = suggest_growth_project(match_result, candidate)
            except (ValueError, RuntimeError):
                growth_recommendation = None

        print(f"Candidate: {candidate.name}")
        print(f"  Match score: {match_result.match_score}")
        print(f"  Explanation: {explanation_result.rationale_text}")
        print(f"  Fairness flag: {fairness_result.flagged}")
        print(f"  Routing: {routing_decision}")
        if growth_recommendation:
            print(f"  Growth: {growth_recommendation.suggested_project}")
        else:
            print("  Growth: n/a")
        print()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - demo script entrypoint
        print(f"Demo failed: {exc}")
        sys.exit(1)
