export type DocKind = 'invoice' | 'receipt';

export interface LineItem {
  description: string;
  quantity: string | number;
  unit_price: string | number | null;
  total: string | number;
}

export type Extraction = Record<string, unknown> & { line_items: LineItem[] };

export interface ExtractResult {
  doc_id: string;
  confidence: number;
  extraction: Extraction;
  status: 'auto_approved' | 'needs_review';
  review_id?: number;
}

export const MAX_BYTES = 10_000_000; // same limit as the API
export const ACCEPT = '.pdf,.png,.jpg,.jpeg';

async function check(res: Response): Promise<Response> {
  if (res.ok) return res;
  let detail = `${res.status}`;
  try {
    const body = await res.json();
    detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* the error body was not JSON: keep the status code */
  }
  throw new Error(detail);
}

export async function extract(file: File, kind: DocKind): Promise<ExtractResult> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`/api/extract?type=${kind}`, { method: 'POST', body: form });
  return (await check(res)).json();
}

/** No body approves the extraction as it is; a body is the corrected document. */
export async function resolve(reviewId: number, corrected?: Extraction): Promise<void> {
  const init: RequestInit = { method: 'POST' };
  if (corrected) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify(corrected);
  }
  await check(await fetch(`/api/review/${reviewId}`, init));
}

export interface ReviewItem {
  id: number;
  doc_id: string;
  confidence: number;
  extraction: Extraction;
}

export async function listReview(): Promise<ReviewItem[]> {
  return (await check(await fetch('/api/review'))).json();
}

/** The queue does not store the type, but only invoices have an invoice number. */
export function kindOf(e: Extraction): DocKind {
  return 'invoice_number' in e ? 'invoice' : 'receipt';
}

/** The name to show for a queued document: vendor or merchant, with the total. */
export function titleOf(e: Extraction): string {
  const name = e['vendor_name'] ?? e['merchant_name'] ?? '';
  return `${name || '—'} · ${e['total']} ${e['currency']}`;
}
