from app.resume_parser import parse_resume
from app.jd_parser import parse_job_description
from app.matcher import match_candidate
from app.growth import suggest_growth_project

with open("data/sample_jobs/software_engineer.txt") as f:
    job_text = f.read()
with open("data/sample_resumes/candidate_3.txt") as f:
    resume_text = f.read()

job = parse_job_description(job_text)
candidate = parse_resume(resume_text)
match_result = match_candidate(candidate, job)

print("Match score:", match_result.match_score)
print("Missing skills:", match_result.missing_skills)

recommendation = suggest_growth_project(match_result, candidate)
print(recommendation)