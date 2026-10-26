"""Normalize text before comparing an extracted value to its label."""

import unicodedata

# Typographic quotes -> plain ASCII, so curly and straight quotes compare equal.
_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def normalize_text(text: str) -> str:
    """Trim, collapse whitespace, ignore case, unify quote marks."""
    text = unicodedata.normalize("NFC", text).translate(_QUOTES)
    return " ".join(text.casefold().split())
