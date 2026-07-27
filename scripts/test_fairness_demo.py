from app.resume_parser import parse_resume
from app.jd_parser import parse_job_description
from app.fairness import run_fairness_check

with open("data/sample_jobs/software_engineer.txt") as f:
    job_text = f.read()
with open("data/sample_resumes/candidate_1.txt") as f:
    resume_text = f.read()

job = parse_job_description(job_text)
candidate = parse_resume(resume_text)

result = run_fairness_check(candidate, job)
print(result)