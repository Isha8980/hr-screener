"""
PDF Reader module for extracting text from uploaded resume PDF files using pypdf.
"""

import io
import re
from typing import Union, BinaryIO
from pypdf import PdfReader

_LOWER_TO_UPPER_BOUNDARY = re.compile(r"(?<=[a-z])(?=[A-Z])")
_MERGED_TOKEN_MIN_LENGTH = 15
_MERGED_TOKEN_MIN_BOUNDARIES = 2


def _despace_merged_words(text: str) -> str:
    """Insert spaces at lowercase-to-uppercase transitions within long tokens that
    look like multiple words pypdf ran together (e.g. "DataAnalyticsIntern").

    Short/legitimate camelCase terms (e.g. "JavaScript", "PowerBI") only have a
    single such transition and are left untouched by the min-boundaries check.
    """

    def _fix_token(match: re.Match) -> str:
        token = match.group(0)
        if len(token) < _MERGED_TOKEN_MIN_LENGTH:
            return token
        if len(_LOWER_TO_UPPER_BOUNDARY.findall(token)) < _MERGED_TOKEN_MIN_BOUNDARIES:
            return token
        return _LOWER_TO_UPPER_BOUNDARY.sub(" ", token)

    return re.sub(r"\S+", lambda m: _fix_token(m), text)


def extract_text_from_pdf(pdf_source: Union[str, bytes, BinaryIO]) -> str:
    """
    Extract raw text from a PDF file path, bytes, or file-like object using pypdf.

    Args:
        pdf_source: File path (str), raw bytes (bytes), or file-like object.

    Returns:
        str: Extracted text from all pages in the PDF.

    Raises:
        ValueError: If pdf_source is empty or invalid.
        RuntimeError: If text extraction encounters an error.
    """
    if pdf_source is None:
        raise ValueError("PDF source cannot be None.")

    try:
        if isinstance(pdf_source, bytes):
            if not pdf_source:
                raise ValueError("PDF bytes cannot be empty.")
            stream = io.BytesIO(pdf_source)
            reader = PdfReader(stream)
        elif isinstance(pdf_source, str):
            if not pdf_source.strip():
                raise ValueError("PDF file path cannot be empty.")
            reader = PdfReader(pdf_source)
        else:
            reader = PdfReader(pdf_source)

        text_pages = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_pages.append(extracted)

        extracted_text = "\n".join(text_pages).strip()
        return _despace_merged_words(extracted_text)

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error extracting text from PDF: {e}") from e
