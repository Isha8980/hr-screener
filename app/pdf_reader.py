"""
PDF Reader module for extracting text from uploaded resume PDF files using pypdf.
"""

import io
from typing import Union, BinaryIO
from pypdf import PdfReader


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
        return extracted_text

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error extracting text from PDF: {e}") from e
