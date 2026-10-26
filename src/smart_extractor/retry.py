"""Re-ask the model with the broken business rules until the document passes or retries run out."""

from collections.abc import Callable
from dataclasses import dataclass

from smart_extractor.metrics import Document
from smart_extractor.rules import check_document

Attempt = Callable[[Document | None, list[str]], Document | None]


@dataclass
class RetryResult:
    document: Document | None
    retries: int  # extra model calls beyond the first
    errors: list[str]  # rules the returned document still breaks


def extract_with_retry(attempt: Attempt, max_retries: int = 2) -> RetryResult:
    """attempt(previous, errors) extracts once; the first call gets (None, [])."""
    document = attempt(None, [])
    retries = 0
    while document is not None:
        errors = check_document(document)
        if not errors or retries == max_retries:
            return RetryResult(document, retries, errors)
        retried = attempt(document, errors)
        retries += 1
        if retried is None:  # keep the last real answer rather than lose it
            return RetryResult(document, retries, errors)
        document = retried
    return RetryResult(None, retries, [])
