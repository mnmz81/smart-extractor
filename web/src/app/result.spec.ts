import { describe, expect, it } from 'vitest';
import { Extraction } from './api';
import { toPayload, toStrings } from './result';

const receipt = (): Extraction => ({
  currency: 'ILS',
  merchant_name: null,
  tip: null,
  total: '22.90',
  line_items: [
    { description: 'חלב', quantity: 2, unit_price: null, total: '13.00' },
  ],
});

describe('form conversion', () => {
  it('shows nulls as blanks and numbers as text', () => {
    const s = toStrings(receipt());
    expect(s['merchant_name']).toBe('');
    expect(s.line_items[0]).toEqual({
      description: 'חלב', quantity: '2', unit_price: '', total: '13.00',
    });
  });

  it('a no-op round trip changes nothing', () => {
    const s = toStrings(receipt());
    expect(JSON.stringify(toStrings(s))).toBe(JSON.stringify(s));
  });

  it('sends blank optional fields back as null', () => {
    const p = toPayload(toStrings(receipt()));
    expect(p['merchant_name']).toBeNull();
    expect(p['tip']).toBeNull();
    expect(p['currency']).toBe('ILS');
    expect(p.line_items[0].unit_price).toBeNull();
  });
});
