"""LLM extractors: a naive 'return JSON' prompt and schema-constrained structured output."""

import json
from pathlib import Path
from typing import Literal

from smart_extractor.dataset import ManifestRow
from smart_extractor.ingest import extract_text, route
from smart_extractor.metrics import Document
from smart_extractor.providers import Attachment, Provider, SchemaFailure
from smart_extractor.retry import RetryStats, extract_with_retry
from smart_extractor.run_eval import Extractor
from smart_extractor.schemas import Invoice, Receipt

Mode = Literal["naive", "structured", "validated", "vision"]


def _model_for(row: ManifestRow) -> type[Invoice] | type[Receipt]:
    return Invoice if row.type == "invoice" else Receipt


def extract_naive(provider: Provider, model: str, text: str, row: ManifestRow) -> Document | None:
    """Ask for JSON in plain words and parse whatever comes back; None if it does not validate."""
    prompt = f"Extract the data from this {row.type} and return it as JSON.\n\n{text}"
    reply = provider.complete(model, prompt)
    try:
        return _model_for(row).model_validate(json.loads(reply))
    except ValueError:  # json.JSONDecodeError and pydantic.ValidationError both subclass it
        return None


def parse_structured(
    provider: Provider,
    model: str,
    text: str,
    row: ManifestRow,
    previous: Document | None = None,
    errors: list[str] | None = None,
    attachment: Attachment | None = None,
) -> Document | None:
    """Constrain the reply to the schema. None if refused or cut off; SchemaFailure if invalid.

    With errors, the prompt lists what was wrong (and the earlier answer, if there was one).
    With attachment, the model reads the page itself, not extracted text.
    """
    prompt = (
        f"Extract the {row.type} data. Use null for optional values you cannot read; never guess "
        "them. The currency is required: infer it from symbols and context. Amounts are plain "
        "numbers: a dot or comma that groups thousands is not a decimal point (31.000 in IDR is "
        "31000)."
    )
    prompt += f"\n\n{text}"
    if errors:
        broken = "\n".join(f"- {e}" for e in errors)
        if previous is not None:
            prompt += f"\n\nYour previous answer was:\n{previous.model_dump_json()}"
        prompt += (
            f"\n\nThat answer has these problems:\n{broken}\nRead the document again and fix them."
        )
    return provider.parse(model, prompt, _model_for(row), attachment)


def extract_structured(
    provider: Provider,
    model: str,
    text: str,
    row: ManifestRow,
    attachment: Attachment | None = None,
) -> Document | None:
    """parse_structured, but an invalid answer is just None."""
    try:
        return parse_structured(provider, model, text, row, attachment=attachment)
    except SchemaFailure:
        return None


def make_extractor(
    mode: Mode, model: str, provider: Provider, stats: RetryStats | None = None
) -> Extractor:
    """Build an Extractor for run_eval. Scans go to the model as images (naive stays text-only)."""

    def extractor(doc: Path, row: ManifestRow) -> Document | None:
        use_vision = mode == "vision" or route(doc) == "vision"
        if mode == "naive":
            if use_vision:
                return None
            return extract_naive(provider, model, extract_text(doc), row)
        page = Attachment.from_file(doc) if use_vision else None
        text = "" if use_vision else extract_text(doc)
        if mode in ("structured", "vision"):
            return extract_structured(provider, model, text, row, page)

        def attempt(previous: Document | None, errors: list[str]) -> Document | None:
            return parse_structured(provider, model, text, row, previous, errors, page)

        result = extract_with_retry(attempt)
        if stats is not None:
            stats.add(result)
        return result.document

    return extractor
