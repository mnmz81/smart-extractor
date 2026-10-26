"""Re-ask the model with what went wrong until the document passes or retries run out."""

from collections.abc import Callable
from dataclasses import dataclass

from smart_extractor.metrics import Document
from smart_extractor.providers import SchemaFailure
from smart_extractor.rules import check_document

Attempt = Callable[[Document | None, list[str]], Document | None]


@dataclass
class RetryResult:
    document: Document | None
    retries: int  # extra model calls beyond the first
    errors: list[str]  # problems the returned document (or the last answer) still has


def extract_with_retry(attempt: Attempt, max_retries: int = 2) -> RetryResult:
    """attempt(previous, errors) extracts once; the first call gets (None, []).

    An attempt may raise SchemaFailure: its errors go into the next try like a broken rule.
    """
    best: Document | None = None  # last answer that fit the schema
    errors: list[str] = []
    retries = 0
    while True:
        try:
            document = attempt(best, errors)
        except SchemaFailure as failure:
            errors = failure.errors
        else:
            if document is None:  # refused or cut off: retrying the same request will not help
                break
            best, errors = document, check_document(document)
        if not errors or retries == max_retries:
            break
        retries += 1
    return RetryResult(best, retries, errors)


@dataclass
class RetryStats:
    """Retry behavior summed over a run."""

    documents: int = 0
    retried: int = 0  # documents that needed at least one retry
    retries: int = 0  # extra model calls in total
    unresolved: int = 0  # documents still breaking a rule or the schema at the end

    def add(self, result: RetryResult) -> None:
        self.documents += 1
        self.retried += result.retries > 0
        self.retries += result.retries
        self.unresolved += bool(result.errors)
