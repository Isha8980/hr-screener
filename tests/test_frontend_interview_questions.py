import json
import shutil
import subprocess
from pathlib import Path

import pytest

INDEX_HTML = Path(__file__).resolve().parent.parent / "app" / "static" / "index.html"


def _extract_function(source: str, name: str) -> str:
    """Pull a top-level `function name(...) { ... }` block out of the page's script by brace-matching."""
    start = source.index(f"function {name}(")
    brace_start = source.index("{", start)
    depth = 0
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError(f"Could not find balanced body for function {name}")


@pytest.fixture(scope="module")
def render_batch_detail_js():
    source = INDEX_HTML.read_text(encoding="utf-8")
    return "\n".join(
        _extract_function(source, name)
        for name in ("escapeHtml", "batchScoreColor", "renderBatchDetail")
    )


def _render(render_batch_detail_js: str, item: dict) -> str:
    if not shutil.which("node"):
        pytest.skip("node is not available in this environment")

    script = f"""
{render_batch_detail_js}
const item = {json.dumps(item)};
process.stdout.write(renderBatchDetail(item, 0));
"""
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _base_item(interview_questions):
    return {
        "match_score": 80.0,
        "routing_decision": "auto_ranked",
        "interview_questions": interview_questions,
        "detail": {
            "match_result": {"matched_skills": ["Python"], "missing_skills": []},
            "resume_formatting_check": {"issues": [], "suggestions": [], "readability_score": 90},
            "explanation": {"rationale_text": "Good fit."},
            "growth_recommendation": None,
        },
    }


def test_interview_questions_section_hidden_when_list_is_empty(render_batch_detail_js):
    html = _render(render_batch_detail_js, _base_item([]))
    assert "Suggested Interview Questions" not in html


def test_interview_questions_section_hidden_when_list_is_null(render_batch_detail_js):
    html = _render(render_batch_detail_js, _base_item(None))
    assert "Suggested Interview Questions" not in html


def test_interview_questions_section_shown_when_questions_present(render_batch_detail_js):
    html = _render(render_batch_detail_js, _base_item(["What drew you to this role?"]))
    assert "Suggested Interview Questions" in html
    assert "What drew you to this role?" in html
    assert "<ol class=\"interview-question-list\">" in html
