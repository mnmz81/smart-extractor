import { ChangeDetectionStrategy, Component, output, signal } from '@angular/core';
import { ACCEPT } from './api';
import { t } from './i18n';

@Component({
  selector: 'app-dropzone',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="zone"
      [class.over]="over()"
      role="button"
      tabindex="0"
      [attr.aria-label]="t('dropTitle')"
      (click)="input.click()"
      (keydown.enter)="input.click()"
      (keydown.space)="$event.preventDefault(); input.click()"
      (dragover)="$event.preventDefault(); over.set(true)"
      (dragleave)="over.set(false)"
      (drop)="drop($event)"
    >
      <svg viewBox="0 0 24 24" width="40" height="40" fill="none" aria-hidden="true">
        <path d="M12 16V4m0 0L7 9m5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"
          stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <strong>{{ t('dropTitle') }}</strong>
      <span class="hint">{{ t('dropHint') }}</span>
      <input #input type="file" hidden [accept]="accept" (change)="pick($event)" />
    </div>
  `,
  styles: `
    .zone {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--mui-space-2);
      padding: var(--mui-space-12) var(--mui-space-6);
      border: 2px dashed var(--mui-color-border-strong);
      border-radius: var(--mui-radius-xl);
      background: var(--mui-color-surface);
      color: var(--mui-color-text);
      text-align: center;
      cursor: pointer;
      min-block-size: var(--mui-touch-target);
      transition: background var(--mui-duration-fast), border-color var(--mui-duration-fast);
    }
    .zone:hover, .zone.over {
      border-color: var(--mui-color-primary);
      background: var(--mui-color-primary-subtle);
    }
    .zone:focus-visible {
      outline: var(--mui-focus-ring-width) solid var(--mui-color-focus-ring);
      outline-offset: var(--mui-focus-ring-offset);
    }
    .hint { color: var(--mui-color-text-muted); font-size: var(--mui-font-size-sm); }
    @media (prefers-reduced-motion: reduce) { .zone { transition: none; } }
  `,
})
export class Dropzone {
  readonly picked = output<File>();
  protected readonly over = signal(false);
  protected readonly accept = ACCEPT;
  protected readonly t = t;

  protected drop(event: DragEvent): void {
    event.preventDefault();
    this.over.set(false);
    const file = event.dataTransfer?.files[0];
    if (file) this.picked.emit(file);
  }

  protected pick(event: Event): void {
    const el = event.target as HTMLInputElement;
    const file = el.files?.[0];
    el.value = ''; // so choosing the same file again still fires
    if (file) this.picked.emit(file);
  }
}
