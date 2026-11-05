"""Review queue in SQLite: low-confidence extractions wait here for a human to approve or fix."""

import sqlite3
from pathlib import Path

from smart_extractor.metrics import Document

_SCHEMA = """
CREATE TABLE IF NOT EXISTS review (
    id INTEGER PRIMARY KEY,
    doc_id TEXT NOT NULL,
    confidence REAL NOT NULL,
    extraction TEXT NOT NULL,  -- the model's answer as JSON
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'corrected')),
    corrected TEXT  -- the human's version as JSON, only when status = 'corrected'
)
"""


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def enqueue(conn: sqlite3.Connection, doc_id: str, doc: Document, confidence: float) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO review (doc_id, confidence, extraction) VALUES (?, ?, ?)",
            (doc_id, confidence, doc.model_dump_json()),
        )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def pending(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Least confident first: those need a human most."""
    return conn.execute(
        "SELECT * FROM review WHERE status = 'pending' ORDER BY confidence, id"
    ).fetchall()


def resolve(conn: sqlite3.Connection, review_id: int, corrected: Document | None = None) -> None:
    """Approve the extraction as it is, or store the human's corrected version."""
    status = "approved" if corrected is None else "corrected"
    with conn:
        changed = conn.execute(
            "UPDATE review SET status = ?, corrected = ? WHERE id = ? AND status = 'pending'",
            (status, None if corrected is None else corrected.model_dump_json(), review_id),
        ).rowcount
    if not changed:
        raise LookupError(f"no pending review item with id {review_id}")
