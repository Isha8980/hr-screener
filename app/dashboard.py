"""
Stage 7: Output / Reporting Dashboard API.
"""

import os
import secrets
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ats_check import analyze_ats_readability
from app.explain import generate_explanation
from app.fairness import run_fairness_check
from app.growth import generate_interview_questions, suggest_growth_project
from app.jd_parser import parse_job_description
from app.matcher import match_candidate
from app.pdf_reader import extract_text_from_pdf
from app.review_queue import log_override, route_candidate
from app.resume_parser import parse_resume
from app.schemas import CandidateProfile, JobRequirements

load_dotenv()

RECRUITER_PASSWORD = os.getenv("RECRUITER_PASSWORD")
if not RECRUITER_PASSWORD:
    RECRUITER_PASSWORD = "changeme"
    print("WARNING: RECRUITER_PASSWORD environment variable not set. Defaulting to 'changeme'.")

VALID_TOKENS: set[str] = set()

# Adjustable estimates used to compute the batch "Time & Cost Savings" summary.
# These are industry-typical assumptions, not measured facts about any
# particular recruiter or team -- adjust them if better local data is available.
AVG_MANUAL_REVIEW_MINUTES = 8
AVG_RECRUITER_HOURLY_COST_INR = 400

app = FastAPI(title="HR Screener Dashboard")

# In-memory storage for now; a real database would replace this later.
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
JOB_STORE: dict[str, dict[str, Any]] = {}
CANDIDATE_STORE: dict[str, dict[str, Any]] = {}
QUEUE_STORE: dict[str, dict[str, Any]] = {}


class JobTextRequest(BaseModel):
    text: str


class CandidateTextRequest(BaseModel):
    text: str


class EvaluationRequest(BaseModel):
    job_id: str
    candidate_id: str


class RecruiterLoginRequest(BaseModel):
    password: str


class OverrideRequest(BaseModel):
    candidate_name: str
    original_decision: str
    recruiter_decision: str
    reason: str


def _get_recruiter_token(x_recruiter_token: str | None, authorization: str | None) -> str | None:
    token = x_recruiter_token
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()
    return token


def _require_recruiter_token(x_recruiter_token: str | None, authorization: str | None) -> None:
    token = _get_recruiter_token(x_recruiter_token, authorization)
    if not token or token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid or missing recruiter token.")


async def _extract_resume_text(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    filename = file.filename.lower()
    if filename.endswith(".txt"):
        try:
            text = (await file.read()).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"'{file.filename}' is not valid UTF-8 text.") from exc
    elif filename.endswith(".pdf"):
        try:
            text = extract_text_from_pdf(await file.read())
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported.")

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")
    return text


def _run_evaluation(
    job: JobRequirements,
    candidate: CandidateProfile,
    candidate_id: str,
) -> tuple[dict[str, Any], Any]:
    """Run the evaluation pipeline shared by single and batch screening."""
    match_result = match_candidate(candidate, job)
    fairness_result = run_fairness_check(candidate, job)
    explanation_result = generate_explanation(match_result)
    routing_decision = route_candidate(match_result, fairness_result)

    growth_recommendation = None
    try:
        growth_recommendation = suggest_growth_project(match_result, candidate)
    except (ValueError, RuntimeError):
        growth_recommendation = None

    interview_questions = None
    if match_result.match_score >= 70:
        interview_questions = generate_interview_questions(match_result)

    result = {
        "match_result": match_result.model_dump(),
        "fairness_result": fairness_result.model_dump(),
        "explanation": explanation_result.model_dump(),
        "routing_decision": routing_decision,
        "growth_recommendation": growth_recommendation.model_dump() if growth_recommendation else None,
        "resume_formatting_check": analyze_ats_readability(candidate.raw_resume_text or ""),
        "interview_questions": interview_questions,
    }

    if routing_decision in {"needs_review", "flagged_for_bias", "auto_rejected"}:
        QUEUE_STORE[candidate_id] = {
            "candidate_id": candidate_id,
            "candidate_name": candidate.name,
            "status": routing_decision,
            "result": result,
        }

    return result, match_result


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs")
def create_job(payload: JobTextRequest) -> dict[str, Any]:
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")

    try:
        parsed_job = parse_job_description(payload.text)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = str(len(JOB_STORE) + 1)
    JOB_STORE[job_id] = {"job": parsed_job}
    return {"job_id": job_id, "job": parsed_job.model_dump()}


@app.post("/candidates")
def create_candidate(payload: CandidateTextRequest) -> dict[str, Any]:
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")

    try:
        parsed_candidate = parse_resume(payload.text)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    candidate_id = str(len(CANDIDATE_STORE) + 1)
    CANDIDATE_STORE[candidate_id] = {"candidate": parsed_candidate}
    return {"candidate_id": candidate_id, "candidate": parsed_candidate.model_dump()}


@app.post("/candidates/upload")
async def upload_candidate(file: UploadFile) -> dict[str, Any]:
    text = await _extract_resume_text(file)

    try:
        parsed_candidate = parse_resume(text)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    candidate_id = str(len(CANDIDATE_STORE) + 1)
    CANDIDATE_STORE[candidate_id] = {"candidate": parsed_candidate}
    return {"candidate_id": candidate_id, "candidate": parsed_candidate.model_dump()}


@app.post("/evaluate")
def evaluate_candidate(payload: EvaluationRequest) -> dict[str, Any]:
    job_record = JOB_STORE.get(payload.job_id)
    candidate_record = CANDIDATE_STORE.get(payload.candidate_id)

    if not job_record:
        raise HTTPException(status_code=404, detail=f"Job with id '{payload.job_id}' not found.")
    if not candidate_record:
        raise HTTPException(status_code=404, detail=f"Candidate with id '{payload.candidate_id}' not found.")

    job: JobRequirements = job_record["job"]
    candidate: CandidateProfile = candidate_record["candidate"]

    try:
        result, _ = _run_evaluation(job, candidate, payload.candidate_id)
        return result
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/batch-evaluate")
async def batch_evaluate(
    job_id: str = Form(...),
    files: list[UploadFile] = File(...),
    x_recruiter_token: str | None = Header(default=None, alias="X-Recruiter-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    _require_recruiter_token(x_recruiter_token, authorization)

    job_record = JOB_STORE.get(job_id)
    if not job_record:
        raise HTTPException(status_code=404, detail=f"Job with id '{job_id}' not found.")
    if not files:
        raise HTTPException(status_code=400, detail="At least one resume file is required.")

    job: JobRequirements = job_record["job"]
    batch_results: list[dict[str, Any]] = []
    batch_start_time = time.perf_counter()
    try:
        for file in files:
            text = await _extract_resume_text(file)
            candidate = parse_resume(text)
            candidate_id = str(len(CANDIDATE_STORE) + 1)
            CANDIDATE_STORE[candidate_id] = {"candidate": candidate}

            detail, match_result = _run_evaluation(job, candidate, candidate_id)
            batch_results.append(
                {
                    "candidate_name": candidate.name,
                    "match_score": match_result.match_score,
                    "routing_decision": detail["routing_decision"],
                    "matched_skills_count": len(match_result.matched_skills),
                    "missing_skills_count": len(match_result.missing_skills),
                    "interview_questions": detail["interview_questions"],
                    "detail": detail,
                }
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    actual_processing_seconds = time.perf_counter() - batch_start_time

    candidates_screened = len(batch_results)
    estimated_time_saved_hours = (candidates_screened * AVG_MANUAL_REVIEW_MINUTES) / 60.0
    estimated_cost_saved_inr = estimated_time_saved_hours * AVG_RECRUITER_HOURLY_COST_INR

    summary = {
        "candidates_screened": candidates_screened,
        "estimated_time_saved_hours": round(estimated_time_saved_hours, 2),
        "estimated_cost_saved_inr": round(estimated_cost_saved_inr, 2),
        "actual_processing_seconds": round(actual_processing_seconds, 2),
        "avg_manual_review_minutes_assumption": AVG_MANUAL_REVIEW_MINUTES,
        "avg_recruiter_hourly_cost_inr_assumption": AVG_RECRUITER_HOURLY_COST_INR,
    }

    return {
        "results": sorted(batch_results, key=lambda item: item["match_score"], reverse=True),
        "summary": summary,
    }


@app.post("/recruiter/login")
def recruiter_login(payload: RecruiterLoginRequest) -> dict[str, Any]:
    if payload.password != RECRUITER_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid recruiter password.")

    token = secrets.token_hex(16)
    VALID_TOKENS.add(token)
    return {"token": token, "status": "authenticated"}


@app.get("/queue")
def get_queue(
    x_recruiter_token: str | None = Header(default=None, alias="X-Recruiter-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> list[dict[str, Any]]:
    _require_recruiter_token(x_recruiter_token, authorization)

    return list(QUEUE_STORE.values())


@app.post("/override")
def override_candidate(payload: OverrideRequest) -> dict[str, Any]:
    log_override(
        candidate_name=payload.candidate_name,
        original_decision=payload.original_decision,
        recruiter_decision=payload.recruiter_decision,
        reason=payload.reason,
    )
    return {"status": "logged", "recruiter_decision": payload.recruiter_decision}


def get_dashboard_summary() -> dict:
    """Compile summary metrics and reports for HR dashboard display."""
    return {
        "job_count": len(JOB_STORE),
        "candidate_count": len(CANDIDATE_STORE),
        "queue_count": len(QUEUE_STORE),
    }
