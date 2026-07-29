from app.pdf_reader import extract_text_from_pdf
from app.resume_parser import parse_resume

pdf_paths = [
    "/Users/ishakhanna/Documents/Testing cv/sample ALP 1.pdf",
    "/Users/ishakhanna/Documents/Testing cv/sample ALP 2.pdf",
    "/Users/ishakhanna/Documents/Testing cv/sample ALP 3.pdf",
    "/Users/ishakhanna/Documents/Testing cv/sample ALP 4.pdf",
    "/Users/ishakhanna/Documents/Testing cv/sample ALP 5.pdf",
    "/Users/ishakhanna/Documents/Testing cv/Yashas Bansal Resume .pdf",
]

for path in pdf_paths:
    print("=" * 70)
    print("FILE:", path)
    try:
        raw_text = extract_text_from_pdf(path)
        print("Extracted text length:", len(raw_text))
        print("First 300 characters:")
        print(repr(raw_text[:300]))
    except Exception as e:
        print("EXTRACTION FAILED:", e)
        continue

    try:
        candidate = parse_resume(raw_text)
        print("\nParsed skills:", candidate.skills)
        print("Parsed raw_resume_text length:", len(candidate.raw_resume_text or ""))
    except Exception as e:
        print("PARSING FAILED:", e)