from app.resume_parser import parse_resume
from app.jd_parser import parse_job_description
from app.matcher import match_candidate

with open("data/sample_jobs/citi_job.txt") as f:
    job_text = f.read()
with open("data/sample_resumes/isha_resume.txt") as f:
    resume_text = f.read()

job = parse_job_description(job_text)
candidate = parse_resume(resume_text)

print("=== JOB REQUIRED SKILLS (raw from parser) ===")
for s in job.required_skills:
    print(repr(s))

print("\n=== CANDIDATE SKILLS (raw from parser) ===")
for s in candidate.skills:
    print(repr(s))

result = match_candidate(candidate, job)
print("\n=== MATCH RESULT ===")
print("Score:", result.match_score)
print("Matched:", result.matched_skills)
print("Missing:", result.missing_skills)