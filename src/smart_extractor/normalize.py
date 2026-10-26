"""Normalize text before comparing an extracted value to its label."""

import re
import unicodedata

# Typographic quotes -> plain ASCII, so curly and straight quotes compare equal.
_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def normalize_text(text: str) -> str:
    """Trim, collapse whitespace, ignore case, unify quote marks, tighten brackets."""
    text = unicodedata.normalize("NFC", text).translate(_QUOTES)
    text = re.sub(r"\s*([()\[\]])\s*", r"\1", text)  # OCR spacing: "( L )" == "(L)"
    return " ".join(text.casefold().split())
