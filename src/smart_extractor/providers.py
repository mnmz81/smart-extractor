"""LLM providers behind one small interface, so extractors do not care which model answers."""

import base64
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import anthropic
from pydantic import BaseModel, ValidationError

_MAX_TOKENS = 4096

count_lock = threading.Lock()  # guards the run-wide counters when documents run in parallel


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
        with count_lock:
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


def make_provider() -> Provider:
    """Build the Claude provider from .env; stops with a clear message if the key is missing."""
    from smart_extractor.config import get_settings  # imported here: config reads .env on use

    key = get_settings().anthropic_api_key
    if key is None:
        raise SystemExit("ANTHROPIC_API_KEY is not set: add it to .env")
    return AnthropicProvider(anthropic.Anthropic(api_key=key.get_secret_value(), max_retries=6))
