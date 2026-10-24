import { useId } from 'react';
import { cn } from '@/lib/cn';
import { addDays, startOfMonth, todayKey } from '@/lib/format';

export interface DateRange {
  from?: string;
  to?: string;
}

export interface DateRangePickerProps {
  value: DateRange;
  onChange: (value: DateRange) => void;
  className?: string;
  /** Hiện các lựa chọn nhanh (7/30/90 ngày, tháng này). */
  presets?: boolean;
  label?: string;
}

const PRESETS: { key: string; label: string; range: () => DateRange }[] = [
  { key: '7', label: '7 ngày qua', range: () => ({ from: addDays(todayKey(), -6), to: todayKey() }) },
  { key: '30', label: '30 ngày qua', range: () => ({ from: addDays(todayKey(), -29), to: todayKey() }) },
  { key: '90', label: '90 ngày qua', range: () => ({ from: addDays(todayKey(), -89), to: todayKey() }) },
  { key: 'month', label: 'Tháng này', range: () => ({ from: startOfMonth(todayKey()), to: todayKey() }) },
];

/** Chọn khoảng ngày đơn giản bằng hai ô date gốc (YYYY-MM-DD) + lựa chọn nhanh. */
export function DateRangePicker({ value, onChange, className, presets = true, label = 'Khoảng thời gian' }: DateRangePickerProps) {
  const id = useId();
  const activePreset = PRESETS.find((p) => {
    const r = p.range();
    return r.from === value.from && r.to === value.to;
  })?.key;
  const inputCls =
    'h-9 rounded-md border border-border-strong bg-surface px-2 text-sm text-fg tabular focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent';
  return (
    <fieldset className={cn('flex flex-wrap items-center gap-2', className)}>
      <legend className="sr-only">{label}</legend>
      {presets && (
        <select
          aria-label="Chọn nhanh khoảng thời gian"
          value={activePreset ?? (value.from || value.to ? 'custom' : '')}
          onChange={(e) => {
            const p = PRESETS.find((x) => x.key === e.target.value);
            if (p) onChange(p.range());
            else if (e.target.value === '') onChange({});
          }}
          className={cn(inputCls, 'pr-7')}
        >
          <option value="">Mọi thời gian</option>
          {PRESETS.map((p) => (
            <option key={p.key} value={p.key}>
              {p.label}
            </option>
          ))}
          <option value="custom" disabled>
            Tuỳ chỉnh
          </option>
        </select>
      )}
      <label htmlFor={`${id}-from`} className="sr-only">
        Từ ngày
      </label>
      <input
        id={`${id}-from`}
        type="date"
        value={value.from ?? ''}
        max={value.to}
        onChange={(e) => onChange({ ...value, from: e.target.value || undefined })}
        className={inputCls}
      />
      <span className="text-fg-subtle" aria-hidden>
        –
      </span>
      <label htmlFor={`${id}-to`} className="sr-only">
        Đến ngày
      </label>
      <input
        id={`${id}-to`}
        type="date"
        value={value.to ?? ''}
        min={value.from}
        onChange={(e) => onChange({ ...value, to: e.target.value || undefined })}
        className={inputCls}
      />
    </fieldset>
  );
}
