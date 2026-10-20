from pathlib import Path

import pytest

from smart_extractor.render import html_to_pdf, render_invoice_html
from smart_extractor.synthetic import Lang, make_invoice


@pytest.mark.parametrize("lang", ["en", "he"])
def test_html_contains_label_values(lang: Lang) -> None:
    inv = make_invoice(1, lang)
    html = render_invoice_html(inv, lang)
    assert inv.invoice_number in html
    assert str(inv.total) in html
    assert f'dir="{"rtl" if lang == "he" else "ltr"}"' in html


def test_html_escapes_markup() -> None:
    inv = make_invoice(1).model_copy(update={"vendor_name": "<script>x</script>"})
    assert "<script>" not in render_invoice_html(inv, "en")


def test_pdf_is_written(tmp_path: Path) -> None:
    out = tmp_path / "inv.pdf"
    html_to_pdf(render_invoice_html(make_invoice(1, "he"), "he"), out)
    assert out.read_bytes().startswith(b"%PDF")
