from typing import Any

from pydantic import BaseModel

from smart_extractor.dataset import ManifestRow
from smart_extractor.llm import extract_naive, extract_structured, parse_structured
from smart_extractor.providers import Attachment, SchemaFailure, Usage
from smart_extractor.schemas import Invoice

ROW = ManifestRow(
    id="inv-1", type="invoice", lang="en", source="synthetic", medium="digital",
    split="dev", private=False,
)  # fmt: skip
VALID = (
    '{"invoice_number": "INV-1", "issue_date": "2024-03-01", "vendor_name": "Acme",'
    ' "currency": "USD", "line_items": [{"description": "Apple", "total": "1"}], "total": "1"}'
)


class FakeProvider:
    """Records what it was asked and answers from a script."""

    def __init__(self, reply: str = "", parsed: Any = None, fail: list[str] | None = None) -> None:
        self.usage = Usage()
        self.reply, self.parsed, self.fail = reply, parsed, fail
        self.prompts: list[str] = []
        self.attachments: list[Attachment | None] = []

    def complete(self, model: str, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply

    def parse[T: BaseModel](
        self, model: str, prompt: str, schema: type[T], attachment: Attachment | None = None
    ) -> T | None:
        self.prompts.append(prompt)
        self.attachments.append(attachment)
        if self.fail:
            raise SchemaFailure(self.fail)
        return self.parsed  # type: ignore[no-any-return]


def test_naive_parses_valid_json() -> None:
    result = extract_naive(FakeProvider(reply=VALID), "m", "text", ROW)
    assert isinstance(result, Invoice)
    assert result.vendor_name == "Acme"


def test_naive_returns_none_on_prose_and_on_wrong_keys() -> None:
    assert extract_naive(FakeProvider(reply="Sure! Here is the JSON"), "m", "t", ROW) is None
    assert extract_naive(FakeProvider(reply='{"vendor": "Acme"}'), "m", "t", ROW) is None


def test_structured_returns_parsed_model_or_none() -> None:
    parsed = Invoice.model_validate_json(VALID)
    assert extract_structured(FakeProvider(parsed=parsed), "m", "t", ROW) == parsed
    assert extract_structured(FakeProvider(parsed=None), "m", "t", ROW) is None


def test_structured_returns_none_when_the_answer_breaks_the_schema() -> None:
    assert extract_structured(FakeProvider(fail=["total: not a number"]), "m", "t", ROW) is None


def test_prompt_tells_the_model_to_use_null() -> None:
    provider = FakeProvider(parsed=None)
    extract_structured(provider, "m", "text", ROW)
    assert "null" in provider.prompts[0]


def test_retry_prompt_contains_previous_answer_and_errors() -> None:
    provider = FakeProvider(parsed=Invoice.model_validate_json(VALID))
    parse_structured(provider, "m", "text", ROW, provider.parsed, ["total is wrong"])
    assert "total is wrong" in provider.prompts[0]
    assert "INV-1" in provider.prompts[0]


def test_schema_errors_without_a_previous_answer_still_reach_the_prompt() -> None:
    provider = FakeProvider(parsed=None)
    parse_structured(provider, "m", "text", ROW, None, ["total: not a number"])
    assert "total: not a number" in provider.prompts[0]
    assert "previous answer" not in provider.prompts[0]


def test_attachment_is_passed_to_the_provider() -> None:
    provider = FakeProvider(parsed=None)
    page = Attachment("application/pdf", b"%PDF")
    extract_structured(provider, "m", "", ROW, page)
    assert provider.attachments == [page]
