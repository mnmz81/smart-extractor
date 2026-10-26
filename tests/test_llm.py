from types import SimpleNamespace
from typing import Any

from smart_extractor.dataset import ManifestRow
from smart_extractor.llm import extract_naive, extract_structured
from smart_extractor.schemas import Invoice

ROW = ManifestRow(
    id="inv-1", type="invoice", lang="en", source="synthetic", medium="digital",
    split="dev", private=False,
)  # fmt: skip
VALID = (
    '{"invoice_number": "INV-1", "issue_date": "2024-03-01", "vendor_name": "Acme",'
    ' "currency": "USD", "line_items": [{"description": "Apple", "total": "1"}], "total": "1"}'
)


class _FakeMessages:
    def __init__(self, reply: str, parsed: Any = None) -> None:
        self._reply, self._parsed = reply, parsed

    def create(self, **_: Any) -> Any:
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._reply)])

    def parse(self, **_: Any) -> Any:
        return SimpleNamespace(parsed_output=self._parsed)


def _client(reply: str = "", parsed: Any = None) -> Any:
    return SimpleNamespace(messages=_FakeMessages(reply, parsed))


def test_naive_parses_valid_json() -> None:
    result = extract_naive(_client(VALID), "m", "text", ROW)
    assert isinstance(result, Invoice)
    assert result.vendor_name == "Acme"


def test_naive_returns_none_on_prose_and_on_wrong_keys() -> None:
    assert extract_naive(_client("Sure! Here is the JSON: ..."), "m", "t", ROW) is None
    assert extract_naive(_client('{"vendor": "Acme"}'), "m", "t", ROW) is None


def test_structured_returns_parsed_model_or_none() -> None:
    parsed = Invoice.model_validate_json(VALID)
    assert extract_structured(_client(parsed=parsed), "m", "t", ROW) == parsed
    assert extract_structured(_client(parsed=None), "m", "t", ROW) is None


def test_structured_retry_prompt_contains_previous_answer_and_errors() -> None:
    captured: dict[str, Any] = {}
    parsed = Invoice.model_validate_json(VALID)

    def parse(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return SimpleNamespace(parsed_output=parsed)

    client = SimpleNamespace(messages=SimpleNamespace(parse=parse))
    extract_structured(client, "m", "text", ROW, previous=parsed, errors=["total is wrong"])  # type: ignore[arg-type]
    prompt = captured["messages"][0]["content"]
    assert "total is wrong" in prompt
    assert "INV-1" in prompt
