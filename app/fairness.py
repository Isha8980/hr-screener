"""
Stage 3: Fairness / Bias Check.
"""

import re
from app.matcher import match_candidate
from app.schemas import CandidateProfile, JobRequirements, FairnessCheckResult

# Configurable threshold for flagging score disparity between raw and anonymized evaluations
BIAS_SCORE_DELTA_THRESHOLD = 5.0


def _mask_candidate_profile(candidate: CandidateProfile) -> CandidateProfile:
    """
    Create an anonymized copy of CandidateProfile by masking name and education institutions.
    """
    masked_name = "Candidate"

    # Replace university or college names in education with generic placeholder
    education_text = candidate.education or ""
    masked_education = re.sub(
        r"(?i)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:University|College|Institute|Academy|School))\b",
        "University A",
        education_text,
    )
    if masked_education == education_text and education_text:
        masked_education = "Degree (University A)"

    masked_raw_text = candidate.raw_resume_text or ""
    if candidate.name and candidate.name in masked_raw_text:
        masked_raw_text = masked_raw_text.replace(candidate.name, masked_name)

    return CandidateProfile(
        name=masked_name,
        skills=list(candidate.skills),
        experience_years=candidate.experience_years,
        education=masked_education,
        certifications=list(candidate.certifications),
        raw_resume_text=masked_raw_text,
    )


def run_fairness_check(
    candidate: CandidateProfile,
    job: JobRequirements,
    threshold: float = BIAS_SCORE_DELTA_THRESHOLD,
) -> FairnessCheckResult:
    """
    Evaluate candidate job fit against a masked version to detect potential demographic or institutional score bias.

    Args:
        candidate: Original CandidateProfile.
        job: Target JobRequirements.
        threshold: Delta score threshold above which a fairness issue is flagged.

    Returns:
        FairnessCheckResult: Detailed comparison between unmasked and masked match scores.
    """
    # 1. Match original candidate profile
    original_result = match_candidate(candidate, job)
    original_score = original_result.match_score

    # 2. Mask candidate PII & institutional indicators
    masked_candidate = _mask_candidate_profile(candidate)

    # 3. Match masked candidate profile
    masked_result = match_candidate(masked_candidate, job)
    masked_score = masked_result.match_score

    # 4. Calculate score delta
    score_delta = round(abs(original_score - masked_score), 2)

    # 5. Flag if delta exceeds threshold
    flagged = score_delta > threshold

    return FairnessCheckResult(
        candidate_name=candidate.name,
        original_score=original_score,
        masked_score=masked_score,
        score_delta=score_delta,
        flagged=flagged,
    )

