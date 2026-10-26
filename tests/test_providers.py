from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from smart_extractor.pricing import cost_usd
from smart_extractor.providers import (
    AnthropicProvider,
    Attachment,
    GeminiProvider,
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


def _gemini_response(text: str | None) -> Any:
    meta = SimpleNamespace(
        prompt_token_count=100, candidates_token_count=20, thoughts_token_count=30
    )
    return SimpleNamespace(text=text, usage_metadata=meta)


def _gemini(response: Any, seen: dict[str, Any] | None = None) -> GeminiProvider:
    def generate_content(**kwargs: Any) -> Any:
        if seen is not None:
            seen.update(kwargs)
        return response

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    return GeminiProvider(client)  # type: ignore[arg-type]


def test_gemini_parses_json_and_counts_thinking_as_output() -> None:
    provider = _gemini(_gemini_response('{"total": 2.5}'))
    assert provider.parse("m", "p", Amount) == Amount(total=2.5)
    assert provider.usage == Usage(calls=1, input_tokens=100, output_tokens=50)


def test_gemini_sends_page_first_and_asks_for_the_json_schema() -> None:
    seen: dict[str, Any] = {}
    _gemini(_gemini_response('{"total": 1}'), seen).parse(
        "m", "p", Amount, Attachment("application/pdf", b"%PDF")
    )
    assert seen["contents"][1] == "p"
    assert seen["contents"][0].inline_data.mime_type == "application/pdf"
    assert seen["config"].response_mime_type == "application/json"
    assert seen["config"].response_json_schema["properties"]["total"]


def test_gemini_empty_answer_is_none_and_bad_json_is_schema_failure() -> None:
    assert _gemini(_gemini_response(None)).parse("m", "p", Amount) is None
    with pytest.raises(SchemaFailure):
        _gemini(_gemini_response('{"total": "unreadable"}')).parse("m", "p", Amount)


def test_gemini_complete_returns_text() -> None:
    assert _gemini(_gemini_response("hi")).complete("m", "p") == "hi"
