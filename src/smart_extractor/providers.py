"""LLM providers behind one small interface, so extractors do not care which model answers."""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import anthropic
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

_MAX_TOKENS = 4096
_GEMINI_MAX_TOKENS = 8192  # thinking tokens count against the limit


@dataclass(frozen=True)
class Attachment:
    """A page the model reads directly: a PDF or an image file."""

    media_type: str
    data: bytes

    @classmethod
    def from_file(cls, path: Path) -> "Attachment":
        media_type = "application/pdf" if path.suffix == ".pdf" else f"image/{path.suffix[1:]}"
        return cls(media_type, path.read_bytes())


class SchemaFailure(Exception):
    """The model answered, but the answer does not fit the schema."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class Usage:
    """What a run sent and received, summed over all calls."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class Provider(Protocol):
    usage: Usage

    def complete(self, model: str, prompt: str) -> str:
        """Free-text answer to a prompt."""

    def parse[T: BaseModel](
        self, model: str, prompt: str, schema: type[T], attachment: Attachment | None = None
    ) -> T | None:
        """Schema-constrained answer: None if refused or cut off, SchemaFailure if invalid."""


def schema_errors(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]


class AnthropicProvider:
    def __init__(self, client: anthropic.Anthropic) -> None:
        self.client = client
        self.usage = Usage()

    def _count(self, usage: Any) -> None:
        self.usage.calls += 1
        self.usage.input_tokens += usage.input_tokens
        self.usage.output_tokens += usage.output_tokens

    def complete(self, model: str, prompt: str) -> str:
        response = self.client.messages.create(
            model=model, max_tokens=_MAX_TOKENS, messages=[{"role": "user", "content": prompt}]
        )
        self._count(response.usage)
        return next((b.text for b in response.content if b.type == "text"), "")

    def parse[T: BaseModel](
        self, model: str, prompt: str, schema: type[T], attachment: Attachment | None = None
    ) -> T | None:
        content: Any = prompt
        if attachment is not None:
            kind = "document" if attachment.media_type == "application/pdf" else "image"
            source = {
                "type": "base64",
                "media_type": attachment.media_type,
                "data": base64.standard_b64encode(attachment.data).decode(),
            }
            content = [{"type": kind, "source": source}, {"type": "text", "text": prompt}]
        try:
            response = self.client.messages.parse(
                model=model,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": content}],
                output_format=schema,
            )
        except ValidationError as exc:
            # shortcut: tokens of an invalid answer are billed but not counted, the SDK hides them
            raise SchemaFailure(schema_errors(exc)) from exc
        self._count(response.usage)
        parsed = response.parsed_output
        return parsed if isinstance(parsed, schema) else None


class GeminiProvider:
    """Gemini through google-genai: JSON-schema constrained output, validated here with Pydantic."""

    def __init__(self, client: genai.Client) -> None:
        self.client = client
        self.usage = Usage()

    def _count(self, response: Any) -> None:
        meta = response.usage_metadata
        self.usage.calls += 1
        if meta is not None:
            self.usage.input_tokens += meta.prompt_token_count or 0
            # thinking tokens are billed as output
            self.usage.output_tokens += (meta.candidates_token_count or 0) + (
                meta.thoughts_token_count or 0
            )

    def complete(self, model: str, prompt: str) -> str:
        config = types.GenerateContentConfig(max_output_tokens=_GEMINI_MAX_TOKENS)
        response = self.client.models.generate_content(model=model, contents=prompt, config=config)
        self._count(response)
        return response.text or ""

    def parse[T: BaseModel](
        self, model: str, prompt: str, schema: type[T], attachment: Attachment | None = None
    ) -> T | None:
        contents: list[Any] = [prompt]
        if attachment is not None:
            contents.insert(
                0, types.Part.from_bytes(data=attachment.data, mime_type=attachment.media_type)
            )
        config = types.GenerateContentConfig(
            max_output_tokens=_GEMINI_MAX_TOKENS,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
        )
        response = self.client.models.generate_content(
            model=model, contents=contents, config=config
        )
        self._count(response)
        if not response.text:  # blocked or empty
            return None
        try:
            return schema.model_validate_json(response.text)
        except ValidationError as exc:
            raise SchemaFailure(schema_errors(exc)) from exc


def make_provider(name: str) -> Provider:
    """Build a provider from the keys in .env; stops with a clear message if the key is missing."""
    from smart_extractor.config import get_settings  # imported here: config reads .env on use

    if name == "claude":
        key = get_settings().anthropic_api_key
        if key is None:
            raise SystemExit("ANTHROPIC_API_KEY is not set: add it to .env")
        return AnthropicProvider(anthropic.Anthropic(api_key=key.get_secret_value(), max_retries=6))
    if name == "gemini":
        google_key = get_settings().google_api_key
        if google_key is None:
            raise SystemExit("GOOGLE_API_KEY is not set: add it to .env")
        retries = types.HttpRetryOptions(attempts=6, initial_delay=2.0, max_delay=30.0)
        client = genai.Client(
            api_key=google_key.get_secret_value(),
            http_options=types.HttpOptions(retry_options=retries),  # 503 "high demand" spikes
        )
        return GeminiProvider(client)
    raise SystemExit(f"unknown provider: {name}")
