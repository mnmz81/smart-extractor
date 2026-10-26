"""LLM extractors: a naive 'return JSON' prompt and schema-constrained structured output."""

import base64
import json
from pathlib import Path
from typing import Any, Literal

import anthropic

from smart_extractor.config import get_settings
from smart_extractor.dataset import ManifestRow
from smart_extractor.ingest import extract_text, route
from smart_extractor.metrics import Document
from smart_extractor.retry import extract_with_retry
from smart_extractor.run_eval import Extractor
from smart_extractor.schemas import Invoice, Receipt

Mode = Literal["naive", "structured", "validated", "vision"]

DEFAULT_MODEL = "claude-haiku-5-5"
_MAX_TOKENS = 4096


def _model_for(row: ManifestRow) -> type[Invoice] | type[Receipt]:
    return Invoice if row.type == "invoice" else Receipt


def extract_naive(
    client: anthropic.Anthropic, model: str, text: str, row: ManifestRow
) -> Document | None:
    """Ask for JSON in plain words and parse whatever comes back; None if it does not validate."""
    prompt = f"Extract the data from this {row.type} and return it as JSON.\n\n{text}"
    response = client.messages.create(
        model=model, max_tokens=_MAX_TOKENS, messages=[{"role": "user", "content": prompt}]
    )
    reply = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return _model_for(row).model_validate(json.loads(reply))
    except ValueError:  # json.JSONDecodeError and pydantic.ValidationError both subclass it
        return None


def attachment_block(doc: Path) -> dict[str, Any]:
    """The file as a content block the model can read: a PDF document or an image."""
    media_type = "application/pdf" if doc.suffix == ".pdf" else f"image/{doc.suffix.lstrip('.')}"
    kind = "document" if doc.suffix == ".pdf" else "image"
    data = base64.standard_b64encode(doc.read_bytes()).decode()
    return {"type": kind, "source": {"type": "base64", "media_type": media_type, "data": data}}


def extract_structured(
    client: anthropic.Anthropic,
    model: str,
    text: str,
    row: ManifestRow,
    previous: Document | None = None,
    errors: list[str] | None = None,
    attachment: dict[str, Any] | None = None,
) -> Document | None:
    """Constrain the reply to the Pydantic schema; None if the model refuses or is cut off.

    With previous and errors, the prompt shows the earlier answer and the rules it broke.
    With attachment (see attachment_block), the model reads the page itself, not extracted text.
    """
    prompt = f"Extract the {row.type} data.\n\n{text}"
    if previous is not None and errors:
        broken = "\n".join(f"- {e}" for e in errors)
        prompt += (
            f"\n\nYour previous answer was:\n{previous.model_dump_json()}\n"
            f"It broke these rules:\n{broken}\nCheck the document again and fix the answer."
        )
    content: Any = [attachment, {"type": "text", "text": prompt}] if attachment else prompt
    response = client.messages.parse(
        model=model,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
        output_format=_model_for(row),
    )
    parsed = response.parsed_output
    return parsed if isinstance(parsed, Invoice | Receipt) else None


def make_extractor(mode: Mode, model: str = DEFAULT_MODEL) -> Extractor:
    """Build an Extractor for run_eval. Scans go to the model as images (naive stays text-only)."""
    key = get_settings().anthropic_api_key
    if key is None:
        raise SystemExit("ANTHROPIC_API_KEY is not set: add it to .env")
    client = anthropic.Anthropic(api_key=key.get_secret_value())

    def extractor(doc: Path, row: ManifestRow) -> Document | None:
        use_vision = mode == "vision" or route(doc) == "vision"
        if mode == "naive":
            return None if use_vision else extract_naive(client, model, extract_text(doc), row)
        page = attachment_block(doc) if use_vision else None
        text = "" if use_vision else extract_text(doc)

        def attempt(previous: Document | None, errors: list[str]) -> Document | None:
            return extract_structured(client, model, text, row, previous, errors, page)

        if mode == "structured" or mode == "vision":
            return attempt(None, [])
        return extract_with_retry(attempt).document

    return extractor
