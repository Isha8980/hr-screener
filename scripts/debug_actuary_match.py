from app.matcher import match_candidate
from app.schemas import CandidateProfile, JobRequirements

raw_resume_text = "Summary: A part-qualified actuary with experience in the general insurance industry. Experience: Marsh McLennan - Actuarial Analyst. Built risk models. Developed a Monte Carlo simulations-based trade credit risk model in both R and Python. Technical Skills: Python, R, MS Excel, Advanced Excel, VBA, MS PowerPoint, MS Word, MetaRisk. Soft Skills: Teamwork, Time Management, Communication, Presentation skills, Report Writing, Leadership, Analytical Thinking. Milliman - Actuarial Intern. Developed a Generalised Linear Model-based tool using R, SAS, and VBA. Collected and analysed data of general insurance companies in Excel templates. Technical Skills: SAS, R, MS Excel, Advanced Excel, VBA. EY - Data Analytics Intern. Collected and processed large sets of data. Performed basic data manipulation and statistical analysis using Alteryx. Technical Skills: Alteryx, SQL, MS Excel. Education: University of Leeds - MSc in Data Science and Analytics. University of Delhi - B.A. Honours in Economics, coursework included Data Analysis and Statistical Methods for Economics. Projects: Customer Personality Analysis using Python and K-Means clustering. Technical Skills: Python, Tableau."

candidate = CandidateProfile(
    name="Test Actuary",
    skills=["Python", "R", "MS Excel", "Advanced Excel", "VBA", "MS PowerPoint",
            "MS Word", "MetaRisk", "SAS", "Alteryx", "SQL", "Tableau", "Overleaf"],
    experience_years=2.0,
    education="MSc in Data Science and Analytics from University of Leeds",
    certifications=[],
    raw_resume_text=raw_resume_text,
)

job = JobRequirements(
    title="MIS Analyst",
    required_skills=["Data Analysis", "Business Analysis", "Market Research", "Analytics"],
    preferred_skills=[],
    min_experience_years=2.0,
    max_experience_years=5.0,
    education_level="Bachelor's Degree",
    job_family="Analytics",
)

result = match_candidate(candidate, job)
print("Matched:", result.matched_skills)
print("Missing:", result.missing_skills)
print("Score:", result.match_score)
print("Soft skill evidence:", result.soft_skill_evidence)