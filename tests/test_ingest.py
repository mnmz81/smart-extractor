from pathlib import Path

import pytest

from smart_extractor.ingest import extract_text, route

_SYNTHETIC = Path("data/synthetic")


@pytest.mark.skipif(not (_SYNTHETIC / "inv-0000.pdf").exists(), reason="dataset not generated")
def test_route_and_text_on_generated_docs() -> None:
    assert route(_SYNTHETIC / "inv-0000.pdf") == "text"
    assert "Invoice" in extract_text(_SYNTHETIC / "inv-0000.pdf")
    assert route(_SYNTHETIC / "inv-0004.pdf") == "vision"
