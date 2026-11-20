import {
  ChangeDetectionStrategy, Component, computed, input, linkedSignal, output, signal,
} from '@angular/core';
import { FormField, Input } from '@mushilu-san/ui/forms';
import { Badge, Button } from '@mushilu-san/ui/primitives';
import { Alert, Progress } from '@mushilu-san/ui/feedback';
import { DocKind, ExtractResult, Extraction, resolve } from './api';
import { FIELDS, Key, t } from './i18n';

const DECIMALS = ['subtotal', 'tax', 'tip', 'total'];
const NULLABLE = ['due_date', 'customer_name', 'merchant_name', 'purchased_at', 'payment_method',
  'subtotal', 'tax', 'tip'];

/** Form inputs give strings: blank optional fields go back to null, as the schema expects. */
export function toPayload(draft: Extraction): Extraction {
  const out: Extraction = structuredClone(draft);
  for (const key of NULLABLE) {
    if (key in out && out[key] === '') out[key] = null;
  }
  out.line_items = out.line_items.map((l) => ({ ...l, unit_price: l.unit_price === '' ? null : l.unit_price }));
  return out;
}

/** Inputs edit text: nulls become '' and numbers become strings, so a no-op compares equal. */
export function toStrings(e: Extraction): Extraction {
  const out: Extraction = { ...e };
  for (const key of Object.keys(out)) {
    if (key !== 'line_items') out[key] = String(out[key] ?? '');
  }
  out.line_items = e.line_items.map((l) => ({
    description: l.description,
    quantity: String(l.quantity),
    unit_price: l.unit_price === null ? '' : String(l.unit_price),
    total: String(l.total),
  }));
  return out;
}

@Component({
  selector: 'app-result',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Alert, Badge, Button, FormField, Input, Progress],
  templateUrl: './result.html',
  styleUrl: './result.css',
})
export class Result {
  readonly result = input.required<ExtractResult>();
  readonly kind = input.required<DocKind>();
  readonly reset = output<void>();

  protected readonly t = t;
  private readonly original = computed(() => toStrings(this.result().extraction));
  protected readonly draft = linkedSignal(() => this.original());
  protected readonly state = signal<'idle' | 'saving' | 'saved' | 'fixed'>('idle');
  protected readonly error = signal('');

  protected readonly fields = computed(() => FIELDS[this.kind()] as readonly Key[]);
  protected readonly reviewable = computed(() => this.result().review_id !== undefined);
  protected readonly percent = computed(() => Math.round(this.result().confidence * 100));
  protected readonly edited = computed(() => {
    return JSON.stringify(this.draft()) !== JSON.stringify(this.original());
  });

  protected value(key: string): string {
    return String(this.draft()[key] ?? '');
  }

  protected setField(key: string, value: string): void {
    this.draft.update((d) => ({ ...d, [key]: value }));
  }

  protected setLine(index: number, key: string, value: string): void {
    this.draft.update((d) => ({
      ...d,
      line_items: d.line_items.map((l, i) => (i === index ? { ...l, [key]: value } : l)),
    }));
  }

  protected isDecimal(key: string): boolean {
    return DECIMALS.includes(key);
  }

  protected async save(): Promise<void> {
    const id = this.result().review_id;
    if (id === undefined) return;
    this.state.set('saving');
    this.error.set('');
    try {
      await resolve(id, this.edited() ? toPayload(this.draft()) : undefined);
      this.state.set(this.edited() ? 'fixed' : 'saved');
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
      this.state.set('idle');
    }
  }
}
