"""
Stage 0: Job Description Parsing.
"""

import os
import re
from typing import Set
import urllib.request
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.schemas import JobRequirements

load_dotenv()

# Allow-list for URL fetching
# Note: LinkedIn (linkedin.com) is intentionally excluded because:
# 1. LinkedIn's Terms of Service strictly prohibit automated scraping and data extraction without express written permission.
# 2. LinkedIn uses authentication walls, anti-bot mechanisms, and IP rate limits that block unauthenticated web scraping.
# 3. Scraping profiles or job posts from LinkedIn poses legal, privacy, and compliance risks.
ALLOWED_DOMAINS: Set[str] = {
    "careers.company.com",
    "jobs.lever.co",
    "boards.greenhouse.io",
    "workday.com",
    "jobs.ashbyhq.com",
    "mycompany.com",
}


def parse_job_description(text: str) -> JobRequirements:
    """
    Parse raw job description text into a structured JobRequirements model using OpenAI API.

    Args:
        text: Unstructured raw job description text.

    Returns:
        JobRequirements: Validated Pydantic model containing job metadata.

    Raises:
        ValueError: If input text is empty or invalid.
        RuntimeError: If OpenAI API call fails or returns invalid structured output.
    """
    if not text or not text.strip():
        raise ValueError("Job description text cannot be empty.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are an expert HR recruitment assistant. "
        "Your task is to parse the provided job description text and extract structured information "
        "matching the exact required fields: title, required_skills, preferred_skills, "
        "min_experience_years, max_experience_years, education_level, and job_family."
    )

    try:
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format=JobRequirements,
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
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI API returned an empty response.")
            return JobRequirements.model_validate_json(content)

    except ValidationError as ve:
        raise RuntimeError(f"Failed to validate OpenAI response into JobRequirements: {ve}") from ve
    except OpenAIError as oe:
        raise RuntimeError(f"OpenAI API error occurred while parsing job description: {oe}") from oe
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"An unexpected error occurred while parsing job description: {e}") from e


def fetch_and_parse_job_from_url(url: str) -> JobRequirements:
    """
    Fetch job description HTML from an allowed career page domain, clean it, and parse it.

    Args:
        url: URL of the job posting.

    Returns:
        JobRequirements: Parsed job requirements model.

    Raises:
        ValueError: If domain is disallowed (including LinkedIn) or URL fetching/parsing fails.
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()

    # Expressly check for LinkedIn
    if "linkedin.com" in domain:
        raise ValueError(
            "Scraping LinkedIn URLs is strictly prohibited due to LinkedIn Terms of Service, "
            "bot-detection mechanisms, and privacy/compliance policies. "
            "Please paste the raw job description text directly."
        )

    # Check against allow-list
    if not any(domain == allowed or domain.endswith("." + allowed) for allowed in ALLOWED_DOMAINS):
        raise ValueError(
            f"Domain '{domain}' is not in the allowed list of career domains. "
            f"Allowed domains: {', '.join(sorted(ALLOWED_DOMAINS))}"
        )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) hr-screener/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode("utf-8", errors="ignore")

        # Basic HTML stripping
        text = re.sub(r"<script.*?>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            raise ValueError(f"Failed to extract text content from URL: {url}")

        return parse_job_description(text)

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to fetch job description from URL '{url}': {e}") from e

