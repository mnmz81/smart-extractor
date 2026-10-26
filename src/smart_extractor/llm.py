"""LLM extractors: a naive 'return JSON' prompt and schema-constrained structured output."""

import json
from pathlib import Path
from typing import Literal

import anthropic

from smart_extractor.config import get_settings
from smart_extractor.dataset import ManifestRow
from smart_extractor.ingest import extract_text, route
from smart_extractor.metrics import Document
from smart_extractor.run_eval import Extractor
from smart_extractor.schemas import Invoice, Receipt

Mode = Literal["naive", "structured"]

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


def extract_structured(
    client: anthropic.Anthropic, model: str, text: str, row: ManifestRow
) -> Document | None:
    """Constrain the reply to the Pydantic schema; None if the model refuses or is cut off."""
    response = client.messages.parse(
        model=model,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": f"Extract the {row.type} data.\n\n{text}"}],
        output_format=_model_for(row),
    )
    parsed = response.parsed_output
    return parsed if isinstance(parsed, Invoice | Receipt) else None


def make_extractor(mode: Mode, model: str = DEFAULT_MODEL) -> Extractor:
    """Build an Extractor for run_eval. Scans return None until the vision path exists."""
    key = get_settings().anthropic_api_key
    if key is None:
        raise SystemExit("ANTHROPIC_API_KEY is not set: add it to .env")
    client = anthropic.Anthropic(api_key=key.get_secret_value())
    extract = extract_naive if mode == "naive" else extract_structured

    def extractor(doc: Path, row: ManifestRow) -> Document | None:
        if route(doc) == "vision":
            return None  # shortcut: no vision path yet, scans score as missing until step 10
        return extract(client, model, extract_text(doc), row)

    return extractor
