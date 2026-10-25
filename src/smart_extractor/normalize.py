"""Normalize text before comparing an extracted value to its label."""

import unicodedata

# Hebrew geresh/gershayim and typographic quotes -> plain ASCII, so ״ and " compare equal.
_QUOTES = str.maketrans({"׳": "'", "״": '"', "‘": "'", "’": "'", "“": '"', "”": '"'})


def normalize_text(text: str) -> str:
    """Trim, collapse whitespace, ignore case, drop Hebrew niqqud, unify quote marks."""
    text = unicodedata.normalize("NFC", text).translate(_QUOTES)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")  # niqqud are Mn marks
    return " ".join(text.casefold().split())
