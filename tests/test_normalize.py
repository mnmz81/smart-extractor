import pytest

from smart_extractor.normalize import normalize_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Acme   Ltd \n", "acme ltd"),
        ("ACME", "acme"),
        ("שָׁלוֹם", "שלום"),  # niqqud removed
        ("ג׳ינס", "ג'ינס"),  # geresh -> ASCII apostrophe
        ("it’s", "it's"),
        ("café", "café"),  # accented Latin letters are kept
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected
