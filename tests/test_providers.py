from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from smart_extractor.pricing import cost_usd
from smart_extractor.providers import (
    AnthropicProvider,
    Attachment,
    SchemaFailure,
    Usage,
)


class Amount(BaseModel):
    total: float


def _client(parse: Any = None, create: Any = None) -> Any:
    return SimpleNamespace(messages=SimpleNamespace(parse=parse, create=create))


def _response(**extra: Any) -> Any:
    usage = SimpleNamespace(input_tokens=100, output_tokens=20)
    return SimpleNamespace(usage=usage, **extra)


def test_attachment_media_type_follows_the_file(tmp_path: Path) -> None:
    pdf, png = tmp_path / "a.pdf", tmp_path / "b.png"
    pdf.write_bytes(b"%PDF")
    png.write_bytes(b"\x89PNG")
    assert Attachment.from_file(pdf).media_type == "application/pdf"
    assert Attachment.from_file(png).media_type == "image/png"


def test_parse_counts_usage_and_returns_the_model() -> None:
    parsed = Amount(total=1.5)
    provider = AnthropicProvider(_client(parse=lambda **_: _response(parsed_output=parsed)))
    assert provider.parse("m", "p", Amount) == parsed
    assert provider.usage == Usage(calls=1, input_tokens=100, output_tokens=20)


def test_parse_sends_the_attachment_before_the_prompt() -> None:
    seen: dict[str, Any] = {}

    def parse(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _response(parsed_output=None)

    provider = AnthropicProvider(_client(parse=parse))
    assert provider.parse("m", "p", Amount, Attachment("application/pdf", b"x")) is None
    content = seen["messages"][0]["content"]
    assert content[0]["type"] == "document"
    assert content[1] == {"type": "text", "text": "p"}


def test_invalid_answer_becomes_schema_failure_with_readable_errors() -> None:
    def parse(**_: Any) -> Any:
        Amount.model_validate({"total": "unreadable"})

    with pytest.raises(SchemaFailure) as info:
        AnthropicProvider(_client(parse=parse)).parse("m", "p", Amount)
    assert info.value.errors[0].startswith("total:")


def test_complete_returns_the_text_block() -> None:
    reply = _response(content=[SimpleNamespace(type="text", text="hi")])
    provider = AnthropicProvider(_client(create=lambda **_: reply))
    assert provider.complete("m", "p") == "hi"
    assert provider.usage.calls == 1


def test_cost_uses_per_million_prices_and_is_none_for_unknown_models() -> None:
    usage = Usage(calls=1, input_tokens=1_000_000, output_tokens=2_000_000)
    assert cost_usd("claude-haiku-5-5", usage) == pytest.approx(0.10 + 2 * 0.50)
    assert cost_usd("some-new-model", usage) is None
