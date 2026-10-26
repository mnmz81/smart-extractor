"""Render a schema object to HTML (Jinja2) and HTML to PDF/PNG (headless Chromium)."""

from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape
from playwright.sync_api import sync_playwright

from smart_extractor.schemas import Invoice, Receipt
from smart_extractor.synthetic import Lang

_ENV = Environment(
    loader=PackageLoader("smart_extractor", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    undefined=StrictUndefined,
)

_LABELS: dict[Lang, dict[str, str]] = {
    "en": {
        "invoice": "Invoice", "vendor": "From", "customer": "Bill to", "issued": "Date",
        "due": "Due date", "description": "Description", "qty": "Qty",
        "unit_price": "Unit price", "amount": "Amount", "subtotal": "Subtotal",
        "tax": "Tax", "tip": "Tip", "total": "Total",
        "payment": "Payment", "cash": "Cash", "card": "Card",
    },
}  # fmt: skip


def render_invoice_html(inv: Invoice, lang: Lang) -> str:
    return _ENV.get_template("invoice.html.j2").render(inv=inv, lang=lang, t=_LABELS[lang])


def render_receipt_html(r: Receipt, lang: Lang) -> str:
    return _ENV.get_template("receipt.html.j2").render(r=r, lang=lang, t=_LABELS[lang])


def html_to_pdf(html: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=str(out), format="A4", print_background=True)
        browser.close()


def html_to_png(html: str, out: Path) -> None:
    """Page screenshot, used as the source for scanned variants."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123})  # A4 at 96 dpi
        page.set_content(html)
        page.screenshot(path=str(out))
        browser.close()
