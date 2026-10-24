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

/** Thanh tab (role=tablist, phím mũi tên). Nội dung đặt trong <TabPanel>. */
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
    <div role="tablist" aria-label={label} className={cn('flex gap-1 overflow-x-auto border-b border-border', className)}>
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
              '-mb-px inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
              selected ? 'border-accent text-fg' : 'border-transparent text-fg-muted hover:text-fg',
            )}
          >
            {t.label}
            {t.count !== undefined && (
              <span className="rounded bg-subtle px-1.5 text-xs tabular text-fg-muted">{t.count}</span>
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
