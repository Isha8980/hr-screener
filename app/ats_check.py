"""Resume formatting checks for basic ATS-friendly readability.

This module uses the phrase "Resume Formatting Check" rather than "ATS score"
for user-facing output because ATS parsing quality is not standardized across
systems and the heuristic here is meant to flag common parsing risks.
"""

import re
from typing import Dict, List


def analyze_ats_readability(resume_text: str) -> dict:
    """Return a simple readability-style assessment for resume formatting issues."""
    if not resume_text or not resume_text.strip():
        return {
            "readability_score": 0,
            "issues": ["Resume text is empty."],
            "suggestions": ["Paste a completed resume so the formatting check can analyze it."],
        }

    text = resume_text.strip()
    issues: List[str] = []
    suggestions: List[str] = []

    section_headers = ["experience", "education", "skills"]
    found_headers = [header for header in section_headers if re.search(rf"\b{header}\b", text, re.IGNORECASE)]
    if len(found_headers) < 3:
        issues.append("The resume does not clearly show Experience, Education, and Skills sections.")
        suggestions.append("Add clear section headers such as Experience, Education, and Skills.")

    bullet_like = re.findall(r"^\s*[-•*]\s+", text, flags=re.MULTILINE)
    if not bullet_like:
        issues.append("The resume uses very few or no bullet points.")
        suggestions.append("Use simple bullet points for work experience and achievements.")

    unusual_bullets = re.findall(r"^[^\w\s]*[\u2022\u25E6\u25AA\u25CF\u2023]\s*", text, flags=re.MULTILINE)
    if unusual_bullets:
        issues.append("The resume contains unusual bullet characters that may confuse simple parsers.")
        suggestions.append("Use standard hyphen or bullet formatting for lists.")

    if re.search(r"\|", text) or re.search(r"\t", text):
        issues.append("The resume appears to use table-like or tabular formatting.")
        suggestions.append("Avoid tables and tab separators; use plain section headings and bullet points instead.")

    contact_patterns = [
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        r"\b\d{3}[-. ]?\d{3}[-. ]?\d{4}\b",
    ]
    if not any(re.search(pattern, text, re.IGNORECASE) for pattern in contact_patterns):
        issues.append("Contact information such as email or phone number is missing.")
        suggestions.append("Add a clear email address and phone number near the top of the resume.")

    word_count = len(re.findall(r"\b\w+\b", text))
    if word_count < 120:
        issues.append("The resume is quite short for a typical professional summary.")
        suggestions.append("Expand the resume with a few more bullet points and role details.")

    score = 100
    score -= len(issues) * 12
    score = max(0, min(100, score))

    return {
        "readability_score": score,
        "issues": issues,
        "suggestions": suggestions,
    }
