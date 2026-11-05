# Smart Extractor

Extract schema-validated JSON from invoices and receipts with Claude, and route the
uncertain results to a human instead of trusting every answer.

Pipeline: PDF or image → text or vision path → structured output checked against a Pydantic
schema → business rules (totals add up, dates make sense) → retry with the errors fed back →
confidence score → auto-approve, or review queue → corrections become new labeled data.

## Results

Measured on a held-out eval set: synthetic invoices and receipts (including degraded scans)
plus public receipts from CORD. Dev is 40 documents, test is 10 and was run once per setup.
The set is small, so read the differences as direction, not precision.

**Test split, `validated` extractor** (rules + retry):

| model | fully correct | field accuracy | cost / doc | retry rate | s / doc |
|---|---|---|---|---|---|
| Haiku 5.5 | 8/10 | 86.8% | $0.0008 | 20% | 6.83 |
| Sonnet 5.5 | 8/10 | 94.4% | $0.0100 | 0% | 5.47 |

**Dev split, `structured` extractor:** Haiku 24/40 documents (85.1% of fields, $0.0005/doc),
Sonnet 29/40 (90.3%, $0.0093/doc). Sonnet is more accurate and about 18x the cost, so Haiku is
the default.

**Concurrency.** Running 4 documents at once (`--concurrency 4`, the default) cut the wall time
per document from 4.21 s to 1.23 s (about 3.4x) on 40 documents, with no rate-limit errors.

**Confidence.** The score comes from signals we can measure (retried, rules still broken,
read from an image, share of empty fields), not from asking the model how sure it is.
On the hard synthetic dev set (about 32 documents, 56% fully correct overall):

| auto-approved | accuracy of auto-approved |
|---|---|
| 34% | 100% |
| 50% | 94% |
| 69% | 82% |
| 100% | 56% |

Auto-approving only the top half of documents gives 94% accuracy; the rest go to a person.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```sh
scripts/uv.sh sync
scripts/uv.sh run playwright install chromium   # used to render the synthetic documents
cp .env.example .env                            # put ANTHROPIC_API_KEY here, never in code
```

## Usage

```sh
scripts/generate_dataset.sh --n 40              # synthetic PDFs + labels -> data/synthetic/
scripts/fetch_public.sh --n 10                  # CORD samples + draft labels -> data/public/
scripts/run_eval.sh --data data/synthetic/hard --extractor validated   # paid: one call per document
scripts/calibrate.sh --data data/synthetic/hard # confidence vs. accuracy curve (paid)
scripts/uv.sh run pytest                        # tests, no API calls
```

Extractors: `baseline` (extracts nothing, the floor), `naive` (plain "return JSON" prompt),
`structured` (schema-constrained output), `validated` (structured + business rules + retry),
`vision` (the model reads the page image).

### API

```sh
scripts/uv.sh run uvicorn --factory smart_extractor.api:create_app
```

- `POST /extract?type=invoice|receipt`: upload a file. At confidence 0.98 or higher the result
  returns as `auto_approved`; otherwise it is queued and returns `needs_review`.
- `GET /review`: pending items, least confident first.
- `POST /review/{id}`: no body approves; a body is the corrected document. Reviewed documents are
  added to a private dev-split dataset, so the eval set grows from real corrections.

There is no authentication and every extraction costs API money: keep it on localhost.

### Docker

```sh
docker build -t smart-extractor .
docker run --rm -p 127.0.0.1:8000:8000 --env-file .env \
  -v "$PWD/data/private:/app/data/private" smart-extractor
```

The key is passed at run time and is never part of the image.

## Batch processing

The eval runner uses `asyncio` with a semaphore to cap documents in flight. For large offline
jobs the Anthropic Message Batches API is a better fit: it costs 50% less but returns results
later, so it suits backfills and not the live `POST /extract` path.

## Data

- `data/synthetic/`: generated, reproducible from a seed.
- `data/public/`: downloaded from [CORD v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2)
  (CC BY 4.0, see [NOTICE](NOTICE)). Not stored in the repository.
- `data/private/`: real documents and uploads, gitignored. Only aggregate scores are published.

## Contributing

Enable the secret-blocking pre-commit hook once per clone:

```bash
git config core.hooksPath .githooks
```
