"""Confidence in one extraction, from signals we can measure (not the model's own claim)."""

from dataclasses import dataclass

from smart_extractor.metrics import Document

# Penalties start from 1.0. The weights are a first guess: calibration on dev tunes them.
_RETRIED = 0.2  # needed at least one retry to pass the rules
_BROKEN = 0.5  # still breaks a rule or the schema after the last attempt
_VISION = 0.1  # read from an image, harder than extracted text
_MISSING = 0.2  # scaled by the share of fields that came back empty


@dataclass(frozen=True)
class Signals:
    retries: int
    errors: int  # problems left after the last attempt
    vision: bool
    missing: float  # share of top-level fields that are None, 0 to 1


def missing_share(doc: Document) -> float:
    values = doc.model_dump().values()
    return sum(v is None for v in values) / len(values)


def confidence(s: Signals) -> float:
    """1.0 = nothing suspicious, 0.0 = send to a human."""
    penalty = _MISSING * s.missing
    penalty += _RETRIED if s.retries else 0
    penalty += _BROKEN if s.errors else 0
    penalty += _VISION if s.vision else 0
    return max(0.0, 1.0 - penalty)
