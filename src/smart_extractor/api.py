"""HTTP API: extract a document, and let a human work through the review queue.

Run locally: scripts/uv.sh run uvicorn --factory smart_extractor.api:create_app
It spends API money per extraction and has no auth yet: keep it on localhost.
"""

import json
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, UploadFile

from smart_extractor.confidence import Signals, confidence
from smart_extractor.dataset import ManifestRow
from smart_extractor.flywheel import add_label, parse_document
from smart_extractor.providers import make_provider
from smart_extractor.review import connect, enqueue, get, pending, resolve
from smart_extractor.run_eval import Extractor
from smart_extractor.schemas import Invoice, Receipt

_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}
_MAX_BYTES = 10_000_000
_THRESHOLD = 0.98  # from the calibration curve: about half auto-approved at 94% accuracy

BuildExtractor = Callable[[dict[str, Signals]], Extractor]


def _claude_extractor(signals: dict[str, Signals]) -> Extractor:
    from smart_extractor.llm import make_extractor  # imported here: llm imports run_eval

    provider = make_provider()
    return make_extractor("validated", "claude-haiku-5-5", provider, signals=signals)


def create_app(
    queue_path: Path = Path("data/private/review.sqlite"),
    uploads: Path = Path("data/private/uploads"),
    dataset: Path = Path("data/private/reviewed"),
    threshold: float = _THRESHOLD,
    build_extractor: BuildExtractor = _claude_extractor,
) -> FastAPI:
    app = FastAPI(title="Smart Extractor")

    def queue() -> Iterator[sqlite3.Connection]:
        # one connection per request: endpoints run in a thread pool and sqlite3 objects
        # must not be shared across threads
        conn = connect(queue_path)
        try:
            yield conn
        finally:
            conn.close()

    Queue = Annotated[sqlite3.Connection, Depends(queue)]

    @app.post("/extract")
    def extract(
        file: UploadFile, type: Literal["invoice", "receipt"], conn: Queue
    ) -> dict[str, Any]:
        """Extract one document: auto-approved when confident, otherwise queued for review."""
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in _SUFFIXES:
            raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix!r}")
        data = file.file.read(_MAX_BYTES + 1)
        if len(data) > _MAX_BYTES:
            raise HTTPException(status_code=413, detail="file is larger than 10 MB")
        doc_id = uuid4().hex  # never the client's file name: it could escape the folder
        uploads.mkdir(parents=True, exist_ok=True)
        path = uploads / f"{doc_id}{suffix}"
        path.write_bytes(data)
        # shortcut: a manifest row built only to carry id and type, upgrade if the extractor
        # stops needing a dataset row
        row = ManifestRow(
            id=doc_id, type=type, lang="en", source="private", medium="digital",
            split="dev", private=True,
        )  # fmt: skip
        signals: dict[str, Signals] = {}
        doc = build_extractor(signals)(path, row)
        if doc is None:
            raise HTTPException(status_code=422, detail="the model gave no usable answer")
        score = confidence(signals[doc_id])
        result: dict[str, Any] = {
            "doc_id": doc_id,
            "confidence": score,
            "extraction": doc.model_dump(mode="json"),
        }
        if score >= threshold:
            return result | {"status": "auto_approved"}
        return result | {"status": "needs_review", "review_id": enqueue(conn, doc_id, doc, score)}

    @app.get("/review")
    def list_review(conn: Queue) -> list[dict[str, Any]]:
        return [
            {
                "id": r["id"],
                "doc_id": r["doc_id"],
                "confidence": r["confidence"],
                "extraction": json.loads(r["extraction"]),
            }
            for r in pending(conn)
        ]

    @app.post("/review/{review_id}")
    def resolve_review(
        review_id: int, conn: Queue, corrected: Invoice | Receipt | None = None
    ) -> dict[str, str]:
        """No body = approve the extraction as it is; a body = the corrected document."""
        item = get(conn, review_id)
        try:
            resolve(conn, review_id, corrected)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        assert item is not None  # resolve succeeded, so the item exists
        final = corrected or parse_document(item["extraction"])
        # shortcut: a failed label write after the resolve leaves a reviewed item with no
        # label, rare (disk errors); upgrade by writing the label before the status change
        upload = next(uploads.glob(f"{item['doc_id']}.*"), None)
        if upload is not None:  # without the document there is nothing to add to the dataset
            add_label(dataset, item["doc_id"], final, upload)
        return {"status": "approved" if corrected is None else "corrected"}

    return app
