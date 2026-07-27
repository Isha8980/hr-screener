from app.resume_parser import parse_resume
from app.jd_parser import parse_job_description
from app.matcher import match_candidate
from app.explain import generate_explanation

with open("data/sample_jobs/software_engineer.txt") as f:
    job_text = f.read()
with open("data/sample_resumes/candidate_1.txt") as f:
    resume_text = f.read()

job = parse_job_description(job_text)
candidate = parse_resume(resume_text)
match_result = match_candidate(candidate, job)

explanation = generate_explanation(match_result)
print(explanation)