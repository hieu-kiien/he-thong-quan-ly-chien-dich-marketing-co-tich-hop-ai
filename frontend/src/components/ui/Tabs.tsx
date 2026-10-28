import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

export interface TabItem<K extends string> {
  key: K;
  label: ReactNode;
  count?: number;
}

export interface TabsProps<K extends string> {
  items: TabItem<K>[];
  value: K;
  onChange: (key: K) => void;
  className?: string;
  /** Nhãn cho trình đọc màn hình. */
  label?: string;
}

/** Thanh tab dạng Segmented Pill hiện đại (không dùng overflow-x-auto để tránh sinh thanh trượt thừa). */
export function Tabs<K extends string>({ items, value, onChange, className, label }: TabsProps<K>) {
  const baseId = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKey = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = -1;
    if (e.key === 'ArrowRight') next = (index + 1) % items.length;
    if (e.key === 'ArrowLeft') next = (index - 1 + items.length) % items.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = items.length - 1;
    if (next >= 0) {
      e.preventDefault();
      onChange(items[next].key);
      refs.current[next]?.focus();
    }
  };

  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn(
        'inline-flex flex-wrap items-center gap-1 rounded-xl border border-border bg-subtle/90 p-1 shadow-2xs',
        className,
      )}
    >
      {items.map((t, i) => {
        const selected = t.key === value;
        return (
          <button
            key={t.key}
            ref={(el) => (refs.current[i] = el)}
            role="tab"
            type="button"
            id={`${baseId}-${t.key}`}
            aria-selected={selected}
            aria-controls={tabPanelId(t.key)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.key)}
            onKeyDown={(e) => onKey(e, i)}
            className={cn(
              'inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-2 text-xs font-semibold transition-all focus:outline-none',
              selected
                ? 'bg-accent text-accent-fg shadow-xs'
                : 'text-fg-muted hover:bg-surface/80 hover:text-fg',
            )}
          >
            {t.label}
            {t.count !== undefined && (
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.5 text-[11px] font-semibold tabular-nums',
                  selected ? 'bg-white/20 text-white' : 'bg-surface text-fg-muted',
                )}
              >
                {t.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export const tabPanelId = (key: string) => `tabpanel-${key}`;

export function TabPanel({ tabKey, children, className }: { tabKey: string; children: ReactNode; className?: string }) {
  return (
    <div role="tabpanel" id={tabPanelId(tabKey)} className={className}>
      {children}
    </div>
  );
}
