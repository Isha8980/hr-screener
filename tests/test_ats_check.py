from app.ats_check import analyze_ats_readability


def test_analyze_ats_readability_reports_issues_and_suggestions():
    resume_text = "Name\nEmail\nPhone\n\nPython Developer\n\n- Built apps\n- Used tools"

    result = analyze_ats_readability(resume_text)

    assert 0 <= result["readability_score"] <= 100
    assert isinstance(result["issues"], list)
    assert isinstance(result["suggestions"], list)
    assert result["issues"]
    assert result["suggestions"]
