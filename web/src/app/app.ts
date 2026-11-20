import { ChangeDetectionStrategy, Component, effect, signal } from '@angular/core';
import { Alert } from '@mushilu-san/ui/feedback';
import { ToggleGroup, ToggleGroupItem } from '@mushilu-san/ui/forms';
import { Button, Spinner } from '@mushilu-san/ui/primitives';
import {
  DocKind, ExtractResult, MAX_BYTES, ReviewItem, extract, kindOf, listReview, titleOf,
} from './api';
import { Dropzone } from './dropzone';
import { lang, t } from './i18n';
import { Result } from './result';

const TYPES = ['application/pdf', 'image/png', 'image/jpeg'];

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Alert, Button, Dropzone, Result, Spinner, ToggleGroup, ToggleGroupItem],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly t = t;
  protected readonly kind = signal<DocKind>('invoice');
  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected readonly result = signal<ExtractResult | null>(null);
  protected readonly queue = signal<ReviewItem[]>([]);
  protected readonly kindOf = kindOf;
  protected readonly titleOf = titleOf;

  constructor() {
    void this.refreshQueue();
    effect(() => {
      document.documentElement.lang = lang();
      document.documentElement.dir = lang() === 'he' ? 'rtl' : 'ltr';
      document.title = t('title');
    });
  }

  protected toggleLang(): void {
    lang.update((l) => (l === 'he' ? 'en' : 'he'));
  }

  protected setKind(value: string): void {
    this.kind.set(value === 'receipt' ? 'receipt' : 'invoice');
  }

  protected async run(file: File): Promise<void> {
    this.error.set('');
    if (!TYPES.includes(file.type)) return this.error.set(t('badType'));
    if (file.size > MAX_BYTES) return this.error.set(t('tooBig'));
    this.loading.set(true);
    try {
      this.result.set(await extract(file, this.kind()));
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.loading.set(false);
    }
  }

  protected clear(): void {
    this.result.set(null);
    this.error.set('');
    void this.refreshQueue();
  }

  protected open(item: ReviewItem): void {
    this.result.set({
      doc_id: item.doc_id,
      confidence: item.confidence,
      extraction: item.extraction,
      status: 'needs_review',
      review_id: item.id,
    });
  }

  private async refreshQueue(): Promise<void> {
    try {
      this.queue.set(await listReview());
    } catch {
      this.queue.set([]); // the queue is a convenience: a failure must not block uploads
    }
  }
}
