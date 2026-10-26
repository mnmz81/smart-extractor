"""Read a PDF's text layer and route digital PDFs to the text path, scans to vision."""

from pathlib import Path
from typing import Literal

import pdfplumber

Route = Literal["text", "vision"]

_MIN_CHARS_PER_PAGE = 20  # a scan has an image and no text layer; a stray OCR stamp stays below


def extract_text(pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def route(pdf_path: Path) -> Route:
    """Digital PDFs have a text layer on every page; scans have little or none."""
    with pdfplumber.open(pdf_path) as pdf:
        counts = [len(page.chars) for page in pdf.pages]
    return "text" if counts and min(counts) >= _MIN_CHARS_PER_PAGE else "vision"
