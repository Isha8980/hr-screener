"""
Unit tests for app/matcher.py
"""

import pytest
from app.matcher import _skill_matches, match_candidate
from app.schemas import CandidateProfile, JobRequirements


@pytest.fixture
def target_job():
    return JobRequirements(
        title="Senior Backend Engineer",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        preferred_skills=["Kubernetes", "Redis", "AWS"],
        min_experience_years=5.0,
        max_experience_years=8.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    )


def test_match_candidate_strong_match(target_job):
    strong_candidate = CandidateProfile(
        name="Alice Senior",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS"],
        experience_years=6.0,
        education="Bachelor of Science in Computer Science, Tech Univ",
        certifications=["AWS Certified Developer"],
        raw_resume_text="Senior Developer with 6 years experience building Python backend services...",
    )

    result = match_candidate(strong_candidate, target_job)

    assert result.candidate_name == "Alice Senior"
    assert result.match_score >= 85.0
    assert result.confidence == "high"
    assert result.experience_gap == 1.0  # 6.0 - 5.0
    assert "Python" in result.matched_skills
    assert "FastAPI" in result.matched_skills
    assert "Redis" in result.missing_skills


def test_match_candidate_partial_match(target_job):
    partial_candidate = CandidateProfile(
        name="Bob Mid",
        skills=["Python", "PostgreSQL", "Git"],
        experience_years=3.0,
        education="Bachelor of Science in Information Technology",
        certifications=[],
        raw_resume_text="Mid-level developer with 3 years experience...",
    )

    result = match_candidate(partial_candidate, target_job)

    assert result.candidate_name == "Bob Mid"
    assert 40.0 <= result.match_score <= 75.0
    assert result.experience_gap == -2.0  # 3.0 - 5.0
    assert "Python" in result.matched_skills
    assert "FastAPI" in result.missing_skills
    assert "Docker" in result.missing_skills


def test_match_candidate_poor_match(target_job):
    poor_candidate = CandidateProfile(
        name="Charlie Junior",
        skills=["HTML", "CSS", "Photoshop"],
        experience_years=0.5,
        education="Diploma in Web Design",
        certifications=[],
        raw_resume_text="Junior Web Designer with 6 months experience...",
    )

    result = match_candidate(poor_candidate, target_job)

    assert result.candidate_name == "Charlie Junior"
    assert result.match_score < 30.0
    assert result.experience_gap == -4.5  # 0.5 - 5.0
    assert len(result.matched_skills) == 0
    assert "Python" in result.missing_skills
    assert "FastAPI" in result.missing_skills


def test_match_candidate_low_confidence_missing_sections(target_job):
    incomplete_candidate = CandidateProfile(
        name="Dana Anonymous",
        skills=[],
        experience_years=0.0,
        education="Not specified",
        certifications=[],
        raw_resume_text="",
    )

    result = match_candidate(incomplete_candidate, target_job)

    assert result.candidate_name == "Dana Anonymous"
    assert result.confidence == "low"


def test_match_candidate_low_score_gets_low_confidence_even_with_many_skills(target_job):
    weak_candidate = CandidateProfile(
        name="Frank Weak",
        skills=["Python", "JavaScript", "HTML", "CSS", "Photoshop", "Figma", "Git"],
        experience_years=1.0,
        education="Bachelor of Science in Computer Science",
        certifications=[],
        raw_resume_text="Candidate with many listed skills but weak fit",
    )

    result = match_candidate(weak_candidate, target_job)

    assert result.match_score < 40.0
    assert result.confidence == "low"


def test_match_candidate_high_score_gets_high_confidence(target_job):
    strong_candidate = CandidateProfile(
        name="Grace Strong",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS", "Redis"],
        experience_years=6.0,
        education="Bachelor of Science in Computer Science",
        certifications=["AWS Certified Developer"],
        raw_resume_text="Strong candidate with excellent fit",
    )

    result = match_candidate(strong_candidate, target_job)

    assert result.match_score >= 70.0
    assert result.confidence == "high"


def test_match_candidate_matches_compound_skill_option():
    candidate = CandidateProfile(
        name="Eve",
        skills=["FastAPI"],
        experience_years=5.0,
        education="Bachelor of Science in Software Engineering",
        certifications=[],
        raw_resume_text="Backend engineer with 5 years experience",
    )
    job = JobRequirements(
        title="Backend Engineer",
        required_skills=["FastAPI or Django"],
        preferred_skills=[],
        min_experience_years=3.0,
        max_experience_years=6.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    )

    result = match_candidate(candidate, job)

    assert "FastAPI or Django" in result.matched_skills
    assert "FastAPI or Django" not in result.missing_skills


def test_match_candidate_matches_comma_separated_compound_skill():
    candidate = CandidateProfile(
        name="Data Analyst",
        skills=["SQL"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Data analyst skilled in SQL databases",
    )
    job = JobRequirements(
        title="Business Intelligence Analyst",
        required_skills=["Tableau, VBA Macros, SQL"],
        preferred_skills=[],
        min_experience_years=2.0,
        max_experience_years=5.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert "Tableau, VBA Macros, SQL" in result.matched_skills
    assert "Tableau, VBA Macros, SQL" not in result.missing_skills


def test_match_candidate_flags_unmet_experience_requirement_as_missing():
    candidate = CandidateProfile(
        name="Junior Engineer",
        skills=["5+ years of experience"],
        experience_years=2.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Engineer with two years of experience",
    )
    job = JobRequirements(
        title="Senior Engineer",
        required_skills=["5+ years of experience"],
        preferred_skills=[],
        education_level="Bachelor's Degree",
        job_family="Engineering",
    )

    result = match_candidate(candidate, job)

    assert "5+ years of experience" not in result.matched_skills
    assert "Requires 5+ years, candidate has 2 years" in result.missing_skills


def test_concrete_technical_skills_do_not_match_unlisted_soft_skill_requirements():
    candidate = CandidateProfile(
        name="Technical Analyst",
        skills=["SQL", "Tableau", "Python"],
        experience_years=4.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="SQL, Tableau, and Python analyst",
    )
    job = JobRequirements(
        title="Operations Analyst",
        required_skills=["Confidentiality", "Cross-functional collaboration"],
        preferred_skills=[],
        min_experience_years=3.0,
        education_level="Bachelor's Degree",
        job_family="Operations",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == []
    assert result.missing_skills == ["Confidentiality", "Cross-functional collaboration"]


def test_compound_skill_and_experience_requirements_still_match():
    candidate = CandidateProfile(
        name="Backend Engineer",
        skills=["FastAPI"],
        experience_years=5.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="FastAPI engineer with five years of experience",
    )
    job = JobRequirements(
        title="Backend Engineer",
        required_skills=["FastAPI or Django", "3+ years of experience"],
        preferred_skills=[],
        min_experience_years=3.0,
        education_level="Bachelor's Degree",
        job_family="Engineering",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["FastAPI or Django", "3+ years of experience"]
    assert result.missing_skills == []
    assert result.experience_gap == 2.0


def test_more_specific_data_analysis_skill_matches_generic_requirement():
    candidate = CandidateProfile(
        name="Data Analyst",
        skills=["Exploratory Data Analysis (EDA)"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Skills: Exploratory Data Analysis (EDA)",
    )
    job = JobRequirements(
        title="Data Analyst",
        required_skills=["Data Analysis"],
        preferred_skills=[],
        min_experience_years=2.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Data Analysis"]
    assert result.missing_skills == []


def test_more_specific_excel_skill_matches_generic_requirement():
    candidate = CandidateProfile(
        name="Reporting Analyst",
        skills=["Advanced Microsoft Excel"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Skills: Advanced Microsoft Excel",
    )
    job = JobRequirements(
        title="Reporting Analyst",
        required_skills=["Excel"],
        preferred_skills=[],
        min_experience_years=2.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Excel"]
    assert result.missing_skills == []


def test_ms_excel_requirement_matches_advanced_microsoft_excel_skill():
    candidate = CandidateProfile(
        name="Reporting Analyst",
        skills=["Advanced Microsoft Excel"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Reporting analyst",
    )
    job = JobRequirements(
        title="Reporting Analyst",
        required_skills=["MS Excel"],
        preferred_skills=[],
        min_experience_years=2.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["MS Excel"]
    assert result.missing_skills == []
    assert result.matched_via_resume_text == set()


def test_short_generic_skill_does_not_match_unrelated_word_fragment():
    assert not _skill_matches(
        "Documentation of operational procedures",
        {"data"},
    )


def test_concrete_requirements_fall_back_to_raw_resume_text():
    candidate = CandidateProfile(
        name="Graduate Analyst",
        skills=["Python", "SQL"],
        experience_years=2.0,
        education="Master of Science",
        certifications=[],
        raw_resume_text=(
            "Education: MSc in Data Science and Analytics\n"
            "Relevant Coursework: Data Analysis\n"
        ),
    )
    job = JobRequirements(
        title="Data Analyst",
        required_skills=["Data Analysis", "Analytics"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Master's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Data Analysis", "Analytics"]
    assert result.missing_skills == []
    assert result.matched_via_resume_text == {"Data Analysis", "Analytics"}


def test_resume_text_fallback_preserves_word_boundaries():
    candidate = CandidateProfile(
        name="Operations Specialist",
        skills=[],
        experience_years=2.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Maintained database systems and documentation for operational procedures.",
    )
    job = JobRequirements(
        title="Operations Specialist",
        required_skills=["data"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Operations",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == []
    assert result.missing_skills == ["data"]
    assert result.matched_via_resume_text == set()


def test_single_word_requirement_is_caught_by_strict_first_pass():
    candidate = CandidateProfile(
        name="Support Specialist",
        skills=["Communication"],
        experience_years=2.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Skills:\nCommunication",
    )
    job = JobRequirements(
        title="Support Specialist",
        required_skills=["Communication"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Support",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Communication"]
    assert result.missing_skills == []
    assert result.matched_via_resume_text == set()


def test_business_analytics_skill_matches_business_analysis_requirement():
    candidate = CandidateProfile(
        name="Priya Nair",
        skills=["Business Analytics"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Business analyst with a background in Business Analytics.",
    )
    job = JobRequirements(
        title="Business Analyst",
        required_skills=["Business Analysis"],
        preferred_skills=[],
        min_experience_years=2.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Business Analysis"]
    assert result.missing_skills == []


def test_data_analytics_skill_matches_data_analysis_requirement():
    candidate = CandidateProfile(
        name="Reporting Analyst",
        skills=["Data Analytics"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Reporting analyst experienced in Data Analytics.",
    )
    job = JobRequirements(
        title="Reporting Analyst",
        required_skills=["Data Analysis"],
        preferred_skills=[],
        min_experience_years=2.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Data Analysis"]
    assert result.missing_skills == []


def test_msc_in_resume_text_matches_postgraduate_degree_requirement():
    candidate = CandidateProfile(
        name="Kartik Jain",
        skills=["Python"],
        experience_years=3.0,
        education="MSc in Business Analytics, University of Leeds",
        certifications=[],
        raw_resume_text="Candidate holds an MSc in Business Analytics from a top university.",
    )
    job = JobRequirements(
        title="Business Analyst",
        required_skills=["Postgraduate degree"],
        preferred_skills=[],
        min_experience_years=2.0,
        education_level="Postgraduate Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Postgraduate degree"]
    assert result.missing_skills == []


@pytest.mark.parametrize(
    ("candidate_skill", "job_requirement"),
    [
        ("Bachelors", "Bachelor's Degree"),
        ("Doctorate", "PhD"),
        ("Financial Analytics", "Financial Analysis"),
        ("Market Analysis", "Market Research"),
        ("Interpersonal Skills", "Communication Skills"),
        ("Analytical Thinking", "Analytical Skills"),
        ("Problem Solving", "Problem-Solving Skills"),
        ("Client Management", "Stakeholder Management"),
        ("Project Coordination", "Project Management"),
        ("Teamwork", "Cross-functional Collaboration"),
        ("Detail-Oriented", "Attention to Detail"),
        ("Organizational Skills", "Time Management"),
        ("Public Speaking", "Presentation Skills"),
        ("Team Leadership", "Leadership"),
        ("MS PowerPoint", "PPT"),
        ("MS Word", "Word"),
    ],
)
def test_expanded_synonym_groups_match_across_terms(candidate_skill, job_requirement):
    """One representative pair per newly-added synonym group (the degree,
    analytics/business, soft-skill, and tool-abbreviation groups not already
    covered by earlier tests)."""
    candidate = CandidateProfile(
        name="Candidate",
        skills=[candidate_skill],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text=f"Experienced professional skilled in {candidate_skill}.",
    )
    job = JobRequirements(
        title="Generalist Role",
        required_skills=[job_requirement],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="General",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == [job_requirement]
    assert result.missing_skills == []


def test_expanded_synonym_groups_do_not_cause_false_positive_matches():
    """A candidate with none of the newly-added synonym vocabulary must not get
    spurious matches against a job requiring many of those canonical terms."""
    candidate = CandidateProfile(
        name="Warehouse Associate",
        skills=["Forklift Operation", "Inventory Counting", "Shipping Logistics"],
        experience_years=2.0,
        education="High School Diploma",
        certifications=[],
        raw_resume_text=(
            "Warehouse associate experienced in forklift operation, inventory "
            "counting, and shipping logistics."
        ),
    )
    job = JobRequirements(
        title="Business Analyst",
        required_skills=[
            "Bachelor's Degree",
            "PhD",
            "Financial Analysis",
            "Market Research",
            "Business Intelligence",
            "Communication Skills",
            "Analytical Skills",
            "Problem-Solving Skills",
            "Stakeholder Management",
            "Project Management",
            "Leadership",
            "Excel",
            "PowerPoint",
            "Word",
        ],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == []
    assert len(result.missing_skills) == len(job.required_skills)


def test_stray_word_in_resume_text_does_not_match_ms_word_requirement():
    """A resume that merely uses the ordinary English word "word" must not
    satisfy an "MS Word" requirement now that bare "word" is no longer
    word-boundary matched."""
    candidate = CandidateProfile(
        name="Content Writer",
        skills=["Copywriting", "SEO"],
        experience_years=2.0,
        education="Bachelor's Degree",
        certifications=[],
        raw_resume_text="Wrote a one-word summary for each campaign to keep messaging tight.",
    )
    job = JobRequirements(
        title="Office Administrator",
        required_skills=["MS Word"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Administration",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == []
    assert result.missing_skills == ["MS Word"]


def test_unrelated_ba_abbreviation_does_not_match_bachelors_degree_requirement():
    """A resume that uses "BA" as an unrelated abbreviation (e.g. a department
    name) must not satisfy a "Bachelor's degree" requirement now that bare
    "ba"/"bs" are no longer word-boundary matched."""
    candidate = CandidateProfile(
        name="Client Onboarding Specialist",
        skills=["Client Onboarding", "CRM Administration"],
        experience_years=3.0,
        education="High School Diploma",
        certifications=[],
        raw_resume_text="Worked in the BA department handling client onboarding and CRM administration.",
    )
    job = JobRequirements(
        title="Office Administrator",
        required_skills=["Bachelor's degree"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Administration",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == []
    assert result.missing_skills == ["Bachelor's degree"]


@pytest.mark.parametrize(
    ("candidate_skill", "job_requirement"),
    [
        ("Microsoft Word", "MS Word"),
        ("Bachelors", "Bachelor's Degree"),
        ("Business Intelligence", "Business Intelligence"),
    ],
)
def test_safer_multi_word_synonym_forms_still_match(candidate_skill, job_requirement):
    """The retained fuller, unambiguous forms must still match correctly after
    removing the risky bare "bi"/"ba"/"bs"/"word" entries."""
    candidate = CandidateProfile(
        name="Candidate",
        skills=[candidate_skill],
        experience_years=3.0,
        education="Bachelor's Degree",
        certifications=[],
        raw_resume_text=f"Experienced professional skilled in {candidate_skill}.",
    )
    job = JobRequirements(
        title="Generalist Role",
        required_skills=[job_requirement],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="General",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == [job_requirement]
    assert result.missing_skills == []


def test_synonym_table_does_not_cause_false_positive_business_analysis_match():
    """A candidate with no analytics/business-analysis background must not match
    "Business Analysis" just because the synonym table exists."""
    candidate = CandidateProfile(
        name="Graphic Designer",
        skills=["Graphic Design", "Photoshop", "Illustrator"],
        experience_years=3.0,
        education="Bachelor of Fine Arts",
        certifications=[],
        raw_resume_text="Graphic designer skilled in Photoshop and Illustrator.",
    )
    job = JobRequirements(
        title="Business Analyst",
        required_skills=["Business Analysis"],
        preferred_skills=[],
        min_experience_years=2.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == []
    assert result.missing_skills == ["Business Analysis"]


def test_british_spelling_data_visualisation_matches_american_requirement():
    candidate = CandidateProfile(
        name="Priya Nair",
        skills=["Data Visualisation"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Experienced in Data Visualisation using Power BI and Tableau.",
    )
    job = JobRequirements(
        title="Data Analyst",
        required_skills=["Data Visualization"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Analytics",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Data Visualization"]
    assert result.missing_skills == []


def test_british_spelling_organisation_skill_matches_american_organization_requirement():
    candidate = CandidateProfile(
        name="James Whitfield",
        skills=["Organisation"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Strong Organisation skills developed across cross-functional projects.",
    )
    job = JobRequirements(
        title="Operations Coordinator",
        required_skills=["Organization"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Operations",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Organization"]
    assert result.missing_skills == []


def test_british_spelling_normalization_does_not_collide_unrelated_words():
    """"Tour Management" and "Tor Network Security" are genuinely different,
    unrelated skills that both happen to end in an "-our"/"or"-adjacent
    pattern; the length-gated spelling normalization must not collapse them
    into a false match (e.g. "tour" -> "tor")."""
    candidate = CandidateProfile(
        name="Concert Producer",
        skills=["Tour Management", "Logistics Planning"],
        experience_years=4.0,
        education="Bachelor of Arts",
        certifications=[],
        raw_resume_text="Managed multi-city tour management and logistics planning for live events.",
    )
    job = JobRequirements(
        title="Security Engineer",
        required_skills=["Tor Network Security"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Security",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == []
    assert result.missing_skills == ["Tor Network Security"]


def test_structured_thinking_skill_matches_analytical_skills_requirement():
    candidate = CandidateProfile(
        name="Riya Desai",
        skills=["Structured Thinking"],
        experience_years=3.0,
        education="Bachelor of Science",
        certifications=[],
        raw_resume_text="Consultant known for Structured Thinking in framing ambiguous business problems.",
    )
    job = JobRequirements(
        title="Business Consultant",
        required_skills=["Analytical Skills"],
        preferred_skills=[],
        min_experience_years=1.0,
        education_level="Bachelor's Degree",
        job_family="Consulting",
    )

    result = match_candidate(candidate, job)

    assert result.matched_skills == ["Analytical Skills"]
    assert result.missing_skills == []
