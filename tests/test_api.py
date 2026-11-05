from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from smart_extractor.api import create_app
from smart_extractor.confidence import Signals
from smart_extractor.dataset import ManifestRow, load_manifest
from smart_extractor.review import connect, enqueue
from smart_extractor.run_eval import Extractor, empty_extractor, evaluate
from smart_extractor.schemas import Invoice, LineItem


def _invoice(vendor: str = "Acme") -> Invoice:
    return Invoice(
        invoice_number="INV-1",
        issue_date=date(2024, 3, 1),
        vendor_name=vendor,
        currency="USD",
        line_items=[LineItem(description="Apple", total=Decimal("1"))],
        total=Decimal("1"),
    )


def _client(tmp_path: Path) -> tuple[TestClient, int]:
    path = tmp_path / "q.sqlite"
    item = enqueue(connect(path), "doc-1", _invoice(), 0.4)
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads" / "doc-1.pdf").write_bytes(b"pdf")
    app = create_app(path, tmp_path / "uploads", dataset=tmp_path / "reviewed")
    return TestClient(app), item


def test_review_lists_pending_items(tmp_path: Path) -> None:
    client, item = _client(tmp_path)
    body = client.get("/review").json()
    assert [(r["id"], r["doc_id"]) for r in body] == [(item, "doc-1")]
    assert body[0]["extraction"]["vendor_name"] == "Acme"


def test_approving_removes_the_item(tmp_path: Path) -> None:
    client, item = _client(tmp_path)
    assert client.post(f"/review/{item}").json() == {"status": "approved"}
    assert client.get("/review").json() == []


def test_correcting_stores_the_new_version(tmp_path: Path) -> None:
    client, item = _client(tmp_path)
    corrected = _invoice("Fixed Ltd").model_dump(mode="json")
    assert client.post(f"/review/{item}", json=corrected).json() == {"status": "corrected"}
    row = connect(tmp_path / "q.sqlite").execute("SELECT corrected FROM review").fetchone()
    assert "Fixed Ltd" in row["corrected"]


def test_resolving_an_unknown_item_is_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.post("/review/999").status_code == 404


def test_a_bad_correction_is_rejected(tmp_path: Path) -> None:
    client, item = _client(tmp_path)
    assert client.post(f"/review/{item}", json={"vendor_name": "x"}).status_code == 422


def _extract_client(
    tmp_path: Path, signals: Signals | None, doc: Invoice | None = None
) -> TestClient:
    def build(recorded: dict[str, Signals]) -> Extractor:
        def extractor(path: Path, row: ManifestRow) -> Invoice | None:
            if signals is not None:
                recorded[row.id] = signals
            return doc if doc is not None else (_invoice() if signals else None)

        return extractor

    app = create_app(tmp_path / "q.sqlite", tmp_path / "uploads", build_extractor=build)
    return TestClient(app)


def _upload(client: TestClient, name: str = "inv.pdf", size: int = 10) -> Any:
    return client.post("/extract", params={"type": "invoice"}, files={"file": (name, b"x" * size)})


def test_confident_extraction_is_auto_approved(tmp_path: Path) -> None:
    client = _extract_client(tmp_path, Signals(0, 0, False, 0))
    body = _upload(client).json()
    assert body["status"] == "auto_approved"
    assert body["extraction"]["vendor_name"] == "Acme"
    assert client.get("/review").json() == []


def test_unsure_extraction_goes_to_the_review_queue(tmp_path: Path) -> None:
    client = _extract_client(tmp_path, Signals(1, 0, False, 0))
    body = _upload(client).json()
    assert body["status"] == "needs_review"
    assert [r["id"] for r in client.get("/review").json()] == [body["review_id"]]


def test_upload_is_stored_under_a_generated_name(tmp_path: Path) -> None:
    client = _extract_client(tmp_path, Signals(0, 0, False, 0))
    doc_id = _upload(client, name="../../evil.pdf").json()["doc_id"]
    assert [p.name for p in (tmp_path / "uploads").iterdir()] == [f"{doc_id}.pdf"]


def test_unsupported_oversized_and_unreadable_uploads_are_refused(tmp_path: Path) -> None:
    client = _extract_client(tmp_path, Signals(0, 0, False, 0))
    assert _upload(client, name="notes.txt").status_code == 400
    assert _upload(client, size=10_000_001).status_code == 413
    assert _upload(_extract_client(tmp_path, None)).status_code == 422


def test_approved_item_becomes_a_dev_label(tmp_path: Path) -> None:
    client, item = _client(tmp_path)
    client.post(f"/review/{item}")
    rows = load_manifest(tmp_path / "reviewed" / "manifest.csv")
    assert [(r.id, r.split, r.source, r.private) for r in rows] == [
        ("doc-1", "dev", "private", True)
    ]
    assert (tmp_path / "reviewed" / "doc-1.pdf").read_bytes() == b"pdf"
    # the new entry can be scored by the eval runner like any other dataset
    assert len(evaluate(tmp_path / "reviewed", "dev", empty_extractor)) == 1


def test_corrected_item_stores_the_humans_version_as_the_label(tmp_path: Path) -> None:
    client, item = _client(tmp_path)
    client.post(f"/review/{item}", json=_invoice("Fixed Ltd").model_dump(mode="json"))
    assert "Fixed Ltd" in (tmp_path / "reviewed" / "doc-1.json").read_text()


def test_item_without_its_upload_is_resolved_but_adds_no_label(tmp_path: Path) -> None:
    client, item = _client(tmp_path)
    (tmp_path / "uploads" / "doc-1.pdf").unlink()
    assert client.post(f"/review/{item}").status_code == 200
    assert not (tmp_path / "reviewed").exists()
