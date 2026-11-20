import { afterEach, describe, expect, it, vi } from 'vitest';
import { extract, resolve } from './api';

const reply = (status: number, body: unknown) =>
  vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }));

afterEach(() => vi.unstubAllGlobals());

describe('api', () => {
  it('posts the file with the document type', async () => {
    const f = reply(200, { doc_id: 'x' });
    vi.stubGlobal('fetch', f);
    await extract(new File(['a'], 'a.pdf'), 'receipt');
    expect(f.mock.calls[0][0]).toBe('/api/extract?type=receipt');
    expect(f.mock.calls[0][1].body).toBeInstanceOf(FormData);
  });

  it('approves with no body and corrects with a JSON body', async () => {
    const f = reply(200, {});
    vi.stubGlobal('fetch', f);
    await resolve(3);
    expect(f.mock.calls[0][1].body).toBeUndefined();
    await resolve(3, { line_items: [] });
    expect(f.mock.calls[1][1].body).toBe('{"line_items":[]}');
  });

  it('surfaces the server error text', async () => {
    vi.stubGlobal('fetch', reply(413, { detail: 'file is larger than 10 MB' }));
    await expect(extract(new File(['a'], 'a.pdf'), 'invoice')).rejects.toThrow('larger than 10 MB');
  });
});

describe('queue helpers', () => {
  it('tells invoices from receipts and names the document', async () => {
    const { kindOf, titleOf } = await import('./api');
    expect(kindOf({ invoice_number: 'A1', line_items: [] })).toBe('invoice');
    expect(kindOf({ merchant_name: 'x', line_items: [] })).toBe('receipt');
    expect(titleOf({ merchant_name: 'סופר', total: '9.90', currency: 'ILS', line_items: [] })).toBe(
      'סופר · 9.90 ILS',
    );
  });
});
