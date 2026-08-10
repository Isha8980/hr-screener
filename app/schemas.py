"""
Pydantic data models for the hr-screener application.
"""

from typing import List, Literal, Optional, Set
from pydantic import BaseModel, Field


class JobRequirements(BaseModel):
    title: str = Field(..., description="Job title")
    required_skills: List[str] = Field(default_factory=list, description="List of required skills")
    preferred_skills: List[str] = Field(default_factory=list, description="List of preferred skills")
    min_experience_years: float = Field(0.0, ge=0, description="Minimum required years of experience")
    max_experience_years: Optional[float] = Field(None, ge=0, description="Maximum required years of experience")
    education_level: str = Field(..., description="Required education level")
    job_family: str = Field(..., description="Job family or department")


class CandidateProfile(BaseModel):
    name: str = Field(..., description="Candidate name")
    skills: List[str] = Field(default_factory=list, description="List of candidate skills")
    experience_years: float = Field(0.0, ge=0, description="Years of experience")
    education: str = Field(..., description="Candidate education background")
    certifications: List[str] = Field(default_factory=list, description="List of candidate certifications")
    raw_resume_text: str = Field("", description="Raw resume text")
    email: Optional[str] = Field(None, description="Candidate email address, if present in the resume")


class MatchResult(BaseModel):
    candidate_name: str = Field(..., description="Candidate name")
    matched_skills: List[str] = Field(default_factory=list, description="Matched skills")
    missing_skills: List[str] = Field(default_factory=list, description="Missing skills")
    experience_gap: float = Field(0.0, description="Difference in experience years")
    match_score: float = Field(..., ge=0.0, le=100.0, description="Match score between 0 and 100")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level: high, medium, or low")
    matched_via_resume_text: Set[str] = Field(
        default_factory=set,
        description="Concrete requirements matched from raw resume text rather than structured skills",
    )


class FairnessCheckResult(BaseModel):
    candidate_name: str = Field(..., description="Candidate name")
    original_score: float = Field(..., ge=0.0, le=100.0, description="Original match score")
    masked_score: float = Field(..., ge=0.0, le=100.0, description="Masked/anonymized match score")
    score_delta: float = Field(..., description="Score difference between original and masked")
    flagged: bool = Field(..., description="Whether fairness issue was flagged")


class ExplanationResult(BaseModel):
    candidate_name: str = Field(..., description="Candidate name")
    rationale_text: str = Field(..., description="Text rationale explaining match evaluation")
    matched_skills: List[str] = Field(default_factory=list, description="Matched skills")
    missing_skills: List[str] = Field(default_factory=list, description="Missing skills")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level")


class GrowthRecommendation(BaseModel):
    candidate_name: str = Field(..., description="Candidate name")
    missing_skill: str = Field(..., description="Missing skill targeted for growth")
    suggested_project: str = Field(..., description="Suggested project to acquire missing skill")
    resume_tip: str = Field(..., description="Tip for updating resume with new skill")


class InterviewQuestions(BaseModel):
    questions: List[str] = Field(
        ...,
        min_length=2,
        max_length=3,
        description="Candidate-specific interview questions targeting match gaps",
    )
