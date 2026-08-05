"""
Stage 2: Job-Fit Matching.
"""

import re

from app.schemas import CandidateProfile, JobRequirements, MatchResult


_SKILL_ABBREVIATIONS = {
    "ms": "microsoft",
    "ppt": "powerpoint",
}

# Curated groups of professional/resume terms that are practically always
# interchangeable but share no matching substring, so word-boundary matching
# alone would otherwise miss them. Every term in a group normalizes to the
# group's first (canonical) term. Keep additions unambiguous.
#
# Deliberately excluded: bare "bi", "ba", "bs", and bare "word". These are
# short enough to collide with ordinary English text or unrelated
# abbreviations (e.g. "one-word summary", a company/department named "BA"),
# so they are never word-boundary matched on their own -- only the fuller,
# unambiguous forms below are.
_SKILL_SYNONYM_GROUPS = [
    # Degree / education level
    ["postgraduate degree", "msc", "mba", "masters", "master's degree", "graduate degree"],
    ["bachelor's degree", "bachelors", "undergraduate degree", "b.tech", "btech"],
    ["phd", "doctorate", "doctoral degree"],
    # Analytics / business terms
    ["business analysis", "business analytics"],
    ["data analysis", "data analytics"],
    ["financial analysis", "financial analytics"],
    ["market research", "market analysis"],
    ["business intelligence"],
    # Soft skill phrasing
    ["communication skills", "communication", "interpersonal skills", "verbal and written communication"],
    ["analytical skills", "analytical thinking", "analytical ability"],
    ["problem-solving skills", "problem solving", "problem-solving ability"],
    ["stakeholder management", "stakeholder engagement", "client management"],
    ["project management", "project coordination"],
    ["team player", "teamwork", "collaboration", "cross-functional collaboration"],
    ["attention to detail", "detail-oriented"],
    ["time management", "organizational skills", "planning and organizing"],
    ["presentation skills", "public speaking"],
    ["leadership", "leadership skills", "team leadership"],
    # Common tool/tech abbreviations (in addition to the MS/PPT table above)
    ["excel", "microsoft excel", "ms excel", "advanced excel"],
    ["powerpoint", "ms powerpoint", "ppt"],
    ["ms word", "microsoft word"],
]

_SKILL_SYNONYMS = {term: group[0] for group in _SKILL_SYNONYM_GROUPS for term in group}


def _normalize_skill(skill: str) -> str:
    """Normalize casing and a conservative set of unambiguous skill abbreviations
    and term synonyms."""
    normalized = skill.strip().lower()
    for abbreviation, expanded in _SKILL_ABBREVIATIONS.items():
        normalized = re.sub(rf"\b{re.escape(abbreviation)}\b", expanded, normalized)
    for synonym, canonical in _SKILL_SYNONYMS.items():
        normalized = re.sub(rf"\b{re.escape(synonym)}\b", canonical, normalized)
    return normalized


def _contains_whole_phrase(needle: str, haystack: str) -> bool:
    """Match a complete word or phrase, including terms ending in punctuation such as C++."""
    pattern = rf"(?<!\w){re.escape(needle)}(?!\w)"
    return re.search(pattern, haystack) is not None


def _skill_matches(skill_item: str, candidate_skills: set[str]) -> bool:
    """Return True for exact skills or contextual matches of multi-word candidate skills.

    Handles compound skill requirements separated by commas, 'or', or slashes.
    """
    parts = re.split(r",|\bor\b|/", skill_item, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [skill_item]

    for part in parts:
        normalized_part = _normalize_skill(part)
        for candidate_skill in candidate_skills:
            if normalized_part == candidate_skill:
                return True
            if _contains_whole_phrase(candidate_skill, normalized_part):
                return True
            if _contains_whole_phrase(normalized_part, candidate_skill):
                return True
    return False


def _requirement_matches_resume_text(requirement: str, resume_text: str) -> bool:
    """Match requirement alternatives as whole phrases in raw resume text."""
    parts = re.split(r",|\bor\b|/", requirement, flags=re.IGNORECASE)
    parts = [part.strip() for part in parts if part.strip()] or [requirement]
    normalized_resume = _normalize_skill(resume_text)
    if not normalized_resume:
        return False
    return any(
        _contains_whole_phrase(_normalize_skill(part), normalized_resume)
        or _contains_whole_phrase(normalized_resume, _normalize_skill(part))
        for part in parts
    )


def _experience_requirement(requirement: str) -> tuple[float, str] | None:
    """Extract the minimum years from an explicit experience requirement."""
    patterns = (
        r"\b(?:at\s+least|minimum(?:\s+of)?)\s+(\d+(?:\.\d+)?)\s+years?\b",
        r"\b(\d+(?:\.\d+)?)\s*\+\s*years?\b",
        r"\b(\d+(?:\.\d+)?)\s*[-–—]\s*\d+(?:\.\d+)?\s+years?\b",
        r"\b(\d+(?:\.\d+)?)\s+years?(?:\s+of)?\s+experience\b",
    )
    for pattern in patterns:
        match = re.search(pattern, requirement, flags=re.IGNORECASE)
        if match:
            return float(match.group(1)), match.group(0)
    return None


def _match_requirements(
    requirements: list[str],
    candidate_skills: set[str],
    candidate_experience: float,
    resume_text: str,
) -> tuple[list[str], list[str], set[str]]:
    """Deterministically match experience, structured skills, then raw resume text."""
    matched = []
    missing = []
    matched_via_resume_text = set()
    for requirement in requirements:
        experience_requirement = _experience_requirement(requirement)
        if experience_requirement is not None:
            minimum_years, phrase = experience_requirement
            if candidate_experience >= minimum_years:
                matched.append(requirement)
            else:
                missing.append(
                    f"Requires {phrase}, candidate has {candidate_experience:g} years"
                )
        elif _skill_matches(requirement, candidate_skills):
            matched.append(requirement)
        elif _requirement_matches_resume_text(requirement, resume_text):
            matched.append(requirement)
            matched_via_resume_text.add(requirement)
        else:
            missing.append(requirement)
    return matched, missing, matched_via_resume_text


def match_candidate(candidate: CandidateProfile, job: JobRequirements) -> MatchResult:
    """
    Evaluate job-fit match between a candidate profile and job requirements.

    Args:
        candidate: Structured candidate profile.
        job: Structured job requirements.

    Returns:
        MatchResult: Match score, skill gaps, experience gap, and confidence rating.
    """
    # 1. Normalize candidate skills for comparison
    candidate_skills_raw = candidate.skills or []
    # 2. Compare skills against required and preferred skills
    required_skills = job.required_skills or []
    preferred_skills = job.preferred_skills or []
    candidate_skills_set = set()
    for s in candidate_skills_raw:
        norm = _normalize_skill(s)
        if norm:
            candidate_skills_set.add(norm)
        parts = re.split(r",|\bor\b|/", s, flags=re.IGNORECASE)
        for p in parts:
            p_norm = _normalize_skill(p)
            if p_norm:
                candidate_skills_set.add(p_norm)

    cand_exp = candidate.experience_years or 0.0
    (
        matched_required,
        missing_required,
        required_resume_matches,
    ) = _match_requirements(
        required_skills, candidate_skills_set, cand_exp, candidate.raw_resume_text or ""
    )
    (
        matched_preferred,
        missing_preferred,
        preferred_resume_matches,
    ) = _match_requirements(
        preferred_skills, candidate_skills_set, cand_exp, candidate.raw_resume_text or ""
    )

    matched_skills = matched_required + matched_preferred
    missing_skills = missing_required + missing_preferred
    matched_via_resume_text = required_resume_matches | preferred_resume_matches

    # 3. Calculate experience gap (candidate exp minus min required exp)
    min_exp = job.min_experience_years or 0.0
    experience_gap = round(cand_exp - min_exp, 2)

    # 4. Calculate weighted match score (0 - 100)
    # Required skills weight: 55%
    if required_skills:
        req_score = (len(matched_required) / len(required_skills)) * 100.0
    else:
        req_score = 100.0

    # Preferred skills weight: 20%
    if preferred_skills:
        pref_score = (len(matched_preferred) / len(preferred_skills)) * 100.0
    else:
        pref_score = 100.0

    # Experience weight: 25%
    if min_exp > 0:
        if cand_exp >= min_exp:
            exp_score = 100.0
        else:
            exp_score = (cand_exp / min_exp) * 100.0
    else:
        exp_score = 100.0

    total_score = (req_score * 0.55) + (pref_score * 0.20) + (exp_score * 0.25)
    match_score = round(max(0.0, min(100.0, total_score)), 2)

    # 5. Determine confidence level
    is_missing_key_sections = (
        not candidate.skills
        or not candidate.raw_resume_text
        or candidate.education in ["", "Not specified", "None"]
    )

    if match_score >= 70.0:
        confidence = "high"
    elif match_score >= 40.0:
        confidence = "medium"
    else:
        confidence = "low"

    if is_missing_key_sections and confidence != "low":
        confidence = "low"

    return MatchResult(
        candidate_name=candidate.name,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        experience_gap=experience_gap,
        match_score=match_score,
        confidence=confidence,
        matched_via_resume_text=matched_via_resume_text,
    )
