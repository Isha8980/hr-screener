from app.jd_parser import parse_job_description

with open("data/sample_jobs/software_engineer.txt") as f:
    text = f.read()

result = parse_job_description(text)
print(result)