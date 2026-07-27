"""
Stage 5: Human Oversight Logic.
"""

import json
from pathlib import Path
from typing import Any

from app.schemas import FairnessCheckResult, MatchResult

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def route_candidate(match_result: MatchResult, fairness_result: FairnessCheckResult) -> str:
    """Route a candidate to auto-ranking, review, or bias review based on confidence and fairness."""
    if fairness_result.flagged:
        return "flagged_for_bias"
    if match_result.confidence == "high":
        return "auto_ranked"
    return "needs_review"


def log_override(candidate_name: str, original_decision: str, recruiter_decision: str, reason: str) -> None:
    """Append an override decision to a local JSON log file.

    In production this should be replaced with a real database-backed audit trail.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DATA_DIR / "override_log.json"

    entries: list[dict[str, Any]] = []
    if log_path.exists():
        try:
            entries = json.loads(log_path.read_text())
        except json.JSONDecodeError:
            entries = []

    entries.append(
        {
            "candidate_name": candidate_name,
            "original_decision": original_decision,
            "recruiter_decision": recruiter_decision,
            "reason": reason,
        }
    )
    log_path.write_text(json.dumps(entries, indent=2))


def process_review_queue(candidate_id: str, status: str, comments: str = "") -> dict:
    """Manage human reviewer feedback and oversight queue."""
    return {"candidate_id": candidate_id, "status": status, "comments": comments}
