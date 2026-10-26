# Smart Extractor

Extract schema-validated JSON from invoices and receipts using LLMs.

## Status

The evaluation foundation is in place; the extractors are next.

- Pydantic schemas: `Invoice`, `Receipt`, `LineItem`
- Eval set: a seeded synthetic generator (digital and degraded "scanned" PDFs, English),
  public receipts from CORD, and a private set of real documents that never leaves the machine
- Manifest with a fixed dev/test split (`data/*/manifest.csv`)
- Planned: metrics, baseline, Claude and Gemini extractors, retry on validation errors,
  confidence scoring and a review queue, FastAPI service, Docker and CI

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```sh
scripts/uv.sh sync
scripts/uv.sh run playwright install chromium   # used to render the synthetic documents
cp .env.example .env                            # API keys go here, never in code
```

## Usage

```sh
scripts/generate_dataset.sh --n 40              # synthetic PDFs + labels -> data/synthetic/
scripts/fetch_public.sh --n 10                  # CORD samples + draft labels -> data/public/
scripts/label_doc.sh cord-0000                  # finish a draft label by hand, validate, add to manifest
scripts/uv.sh run pytest                        # tests
```

## Data

- `data/synthetic/`: generated, reproducible from a seed.
- `data/public/`: downloaded from [CORD v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2)
  (CC BY 4.0, see [NOTICE](NOTICE)). Not stored in the repository.
- `data/private/`: real documents, gitignored. Only aggregate scores are ever published.
