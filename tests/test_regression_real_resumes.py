"""
Regression tests pinning app.matcher.match_candidate() behavior against a curated
set of real-world resume/job pairs the team has manually verified during
development. These use hardcoded, already-known-correct structured
CandidateProfile / JobRequirements objects and call match_candidate() directly --
no OpenAI calls are made, so this file is fast and free to run.
"""

from app.matcher import match_candidate
from app.schemas import CandidateProfile, JobRequirements


def test_kartik_jain_analytics_background_partial_match():
    """Analytics-adjacent candidate: skills matched partly via structured skills,
    partly via raw resume text (e.g. "Analytics" inside "Data Analytics Intern")."""
    candidate = CandidateProfile(
        name="Kartik Jain",
        skills=[
            "Python", "R", "MS Excel", "Advanced Excel", "VBA", "MS PowerPoint",
            "MS Word", "MetaRisk", "SAS", "Alteryx", "SQL", "Tableau",
        ],
        experience_years=3.0,
        education="MSc in Data Science and Analytics, University of Leeds",
        certifications=[],
        raw_resume_text=(
            "Kartik Jain\n"
            "Leeds, England, UK\n"
            "Actuarial Analyst with nearly three years of experience in the general "
            "insurance industry.\n"
            "Performed data analysis for pricing and reserving models using Python, "
            "R, and VBA.\n"
            "Experience\n"
            "MarshMcLennan - Actuarial Analyst\n"
            "EY - Data Analytics Intern\n"
            "Education\n"
            "University of Leeds - MSc in Data Science and Analytics\n"
        ),
    )
    job = JobRequirements(
        title="MIS Analyst",
        required_skills=["Data Analysis", "Business Analysis", "Market Research", "Analytics"],
        preferred_skills=[],
        min_experience_years=5.0,
        max_experience_years=8.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Data Analysis", "Analytics"]
    assert result.missing_skills == ["Business Analysis", "Market Research"]
    assert 55.0 <= result.match_score <= 70.0


def test_marcus_vance_software_engineer_near_zero_match_against_analytics_job():
    """A software engineer's stack shouldn't spuriously match a data/business analysis job."""
    candidate = CandidateProfile(
        name="Marcus Vance",
        skills=["JavaScript", "TypeScript", "React", "Node.js", "PostgreSQL", "MongoDB", "Docker", "AWS"],
        experience_years=4.0,
        education="Bachelor's Degree in Computer Science",
        certifications=[],
        raw_resume_text=(
            "Marcus Vance\n"
            "Software Engineer with 4 years of experience building full-stack web "
            "applications using React, Node.js, and TypeScript.\n"
            "Deployed containerized services with Docker on AWS, backed by "
            "PostgreSQL and MongoDB.\n"
        ),
    )
    job = JobRequirements(
        title="MIS Analyst",
        required_skills=["Data Analysis", "Business Analysis", "Market Research", "Analytics"],
        preferred_skills=[],
        min_experience_years=5.0,
        max_experience_years=8.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert len(result.matched_skills) <= 1


def test_sarah_jenkins_marketing_near_zero_match_against_technical_data_job():
    """A marketing skill set shouldn't spuriously match a SQL/Python/BI data job."""
    candidate = CandidateProfile(
        name="Sarah Jenkins",
        skills=["Social Media Analytics", "SEO", "HubSpot", "Google Analytics 4", "Copywriting"],
        experience_years=3.0,
        education="Bachelor's Degree in Marketing",
        certifications=[],
        raw_resume_text=(
            "Sarah Jenkins\n"
            "Digital Marketing Specialist with expertise in SEO, content strategy, "
            "and copywriting.\n"
            "Managed social media campaigns and tracked performance using HubSpot "
            "and Google Analytics 4.\n"
        ),
    )
    job = JobRequirements(
        title="Data Analyst",
        required_skills=["Power BI", "SQL", "Python", "Snowflake"],
        preferred_skills=[],
        min_experience_years=2.0,
        max_experience_years=5.0,
        education_level="Bachelor's Degree",
        job_family="Data",
    )

    result = match_candidate(candidate, job)

    assert len(result.matched_skills) <= 1


def test_david_chen_data_analyst_matches_most_technical_requirements():
    """A genuine data analyst's skills should match nearly all of a technical data job's requirements."""
    candidate = CandidateProfile(
        name="David Chen",
        skills=["SQL", "Tableau", "Power BI", "Python", "Statistical Modeling"],
        experience_years=3.0,
        education="Bachelor's Degree in Statistics",
        certifications=[],
        raw_resume_text=(
            "David Chen\n"
            "Data Analyst with 3 years of experience building dashboards in Tableau "
            "and Power BI, writing SQL queries, and building statistical models in "
            "Python.\n"
        ),
    )
    job = JobRequirements(
        title="Data Analyst",
        required_skills=["Power BI", "SQL", "Python", "Snowflake"],
        preferred_skills=[],
        min_experience_years=2.0,
        max_experience_years=5.0,
        education_level="Bachelor's Degree",
        job_family="Data",
    )

    result = match_candidate(candidate, job)

    assert len(result.matched_skills) >= 3
    assert "SQL" in result.matched_skills
    assert "Python" in result.matched_skills
    assert "Power BI" in result.matched_skills
    assert "Snowflake" in result.missing_skills


def test_abbreviation_normalization_ms_excel_matches_advanced_microsoft_excel():
    """"MS Excel" (job requirement) should normalize to match "Advanced Microsoft Excel" (candidate skill)."""
    candidate = CandidateProfile(
        name="Priya Nair",
        skills=["Advanced Microsoft Excel"],
        experience_years=2.0,
        education="Bachelor's Degree",
        certifications=[],
        raw_resume_text="Priya Nair\nOffice Administrator skilled in Advanced Microsoft Excel.\n",
    )
    job = JobRequirements(
        title="Office Administrator",
        required_skills=["MS Excel"],
        preferred_skills=[],
        min_experience_years=0.0,
        education_level="Bachelor's Degree",
        job_family="Administration",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["MS Excel"]
    assert result.missing_skills == []


def test_experience_years_requirement_not_silently_matched():
    """A "5+ years of experience" requirement must land in missing_skills when the
    candidate falls short, not be silently treated as satisfied or dropped."""
    candidate = CandidateProfile(
        name="Jordan Lee",
        skills=["Python"],
        experience_years=2.0,
        education="Bachelor's Degree",
        certifications=[],
        raw_resume_text="Jordan Lee\nSoftware Developer with 2 years of experience in Python.\n",
    )
    job = JobRequirements(
        title="Senior Python Developer",
        required_skills=["Python", "5+ years of experience"],
        preferred_skills=[],
        min_experience_years=5.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    )

    result = match_candidate(candidate, job)

    assert "Python" in result.matched_skills
    assert len(result.missing_skills) == 1
    assert "5+ years" in result.missing_skills[0]
    assert "2 years" in result.missing_skills[0]
