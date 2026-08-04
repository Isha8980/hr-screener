# HR Screener

HR Screener is an AI-powered candidate screening tool built for recruiters and HR teams who need to evaluate applicants at volume without losing rigor or fairness along the way. It parses a job description and a candidate's resume, scores the fit with a deterministic (non-hallucinating) skill matcher, checks the result for demographic bias using a counterfactual test, and routes each candidate into a clear, explainable outcome — all through a simple web dashboard that supports both single-candidate screening and batch upload of an entire applicant pool.

## Live Demo

**[https://hr-screener.onrender.com](https://hr-screener.onrender.com)**

> This app is hosted on Render's free tier, so it spins down when idle. If it's been a while since the last visit, the first load may take **30–60 seconds** while the server wakes up — subsequent requests are fast.

## Key Features

- **AI-powered resume/job parsing** — extracts structured requirements and candidate profiles from unstructured job descriptions and resumes (PDF or plain text) using an LLM.
- **Deterministic skill matching with synonym normalization** — scores candidates against job requirements using explicit, auditable matching logic (not a black-box LLM judgment), with a curated synonym table so equivalent terms (e.g. "MS Excel" / "Advanced Excel", "Business Analysis" / "Business Analytics") are recognized without over-matching.
- **Counterfactual bias detection** — re-evaluates each candidate with demographic-signaling details masked and flags cases where the score shifts, surfacing potential bias for human review.
- **Plain-English explainability** — generates a human-readable rationale for every match score, so recruiters can see *why* a candidate scored the way they did.
- **4-tier candidate routing** — every candidate is automatically routed to one of **Auto-Ranked**, **Needs Review**, **Auto-Rejected**, or **Flagged for Bias**, keeping high-confidence decisions fast while routing ambiguous or sensitive cases to a human.
- **Personalized growth recommendations** — suggests a project and a resume tip tailored to each candidate's specific skill gaps.
- **ATS formatting checker** — flags resume formatting issues that could trip up applicant tracking systems, independent of skill content.
- **Batch screening with candidate ranking** — upload multiple resumes against one job posting and get back a ranked, sortable shortlist.
- **AI-generated interview questions** — automatically drafts candidate-specific interview questions for strong matches (match score ≥ 70), targeting their particular experience and gaps.

## Tech Stack

- **Backend:** Python, FastAPI
- **AI/LLM:** OpenAI API (GPT-4o-mini) for parsing, explanations, growth recommendations, and interview questions
- **Frontend:** HTML, CSS, JavaScript (no framework — served as static assets by FastAPI)
- **Testing:** pytest
- **Deployment:** Render

## How It Works

Each candidate flows through a deterministic pipeline:

```
Job/Resume Parsing → Skill Matching → Bias Check → Explanation → Routing → Growth Recommendations
```

1. **Parsing** — the job description and resume are each parsed by an LLM into structured data (required/preferred skills, experience, education, etc.).
2. **Skill Matching** — a rule-based matcher compares the candidate's structured profile against the job's requirements, using word-boundary and synonym-aware matching to produce a 0–100 match score, matched/missing skills, and a confidence level.
3. **Bias Check** — the same match is re-run against a version of the candidate's profile with identity-correlated details masked; a significant score delta gets flagged.
4. **Explanation** — an LLM turns the match result into a plain-English rationale.
5. **Routing** — based on score, confidence, and the bias check, the candidate is routed to Auto-Ranked, Needs Review, Auto-Rejected, or Flagged for Bias.
6. **Growth Recommendations** — for candidates with skill gaps, a tailored project suggestion and resume tip are generated.

## Testing

The project has **90+ automated tests** (pytest), covering every stage of the pipeline — parsing, matching, fairness, explainability, routing, growth recommendations, and the dashboard API — plus a dedicated **regression test suite validated against real, manually-verified resumes** to guard against unintended scoring changes as the matcher evolves.

Run the full suite with:

```bash
python -m pytest tests/
```

## Local Setup

### Prerequisites
- Python 3.11

### 1. Clone the repository

```bash
git clone <repository-url>
cd hr-screener
```

### 2. Create and activate a virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate   # On Windows: .\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=your_openai_api_key_here
RECRUITER_PASSWORD=your_recruiter_password_here
```

`.env` is excluded from version control and should never be committed.

### 5. Run the app

```bash
uvicorn app.dashboard:app --reload
```

The dashboard will be available at `http://127.0.0.1:8000`.

## Known Limitations

- **Synonym coverage is not exhaustive.** The deterministic matcher relies on a curated synonym/abbreviation table rather than semantic understanding, so it will not recognize every possible near-synonym term — only the pairs that have been explicitly added.
- **In-memory storage only.** Jobs, candidates, and the review queue are held in memory for the lifetime of the server process; there is no persistent database in the current scope, so all data is lost on restart.
