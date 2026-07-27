# hr-screener

An AI-powered candidate screening and recruitment platform built with Python 3.11, FastAPI, OpenAI, and Pydantic.

## Project Structure

```text
hr-screener/
  app/
    __init__.py
    jd_parser.py       # Stage 0: job description parsing
    resume_parser.py   # Stage 1: resume parsing
    matcher.py         # Stage 2: job-fit matching
    fairness.py        # Stage 3: fairness/bias check
    explain.py         # Stage 4: explainability layer
    review_queue.py    # Stage 5: human oversight logic
    growth.py          # Stage 6: project recommendations
    dashboard.py       # Stage 7: output/reporting
  data/
    sample_jobs/
    sample_resumes/
  tests/
  .env.example
  requirements.txt
  README.md
```

## Setup Instructions

### Prerequisites
- Python 3.11

### 1. Setting Up Virtual Environment

#### On macOS / Linux:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

#### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Installing Dependencies

Once your virtual environment is activated, install the required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables Configuration

Copy `.env.example` to create `.env`:

```bash
cp .env.example .env
```

Update `.env` with your API credentials:
```env
OPENAI_API_KEY=your_openai_api_key_here
HF_API_TOKEN=your_huggingface_api_token_here
```

Note: `.env` is included in `.gitignore` and should never be committed to version control.
