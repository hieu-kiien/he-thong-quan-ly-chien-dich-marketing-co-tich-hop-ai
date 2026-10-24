import { forwardRef, useEffect, useState } from 'react';
import { cn } from '@/lib/cn';
import { Input, type InputProps } from './Form';

const fmt = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });

export interface MoneyInputProps extends Omit<InputProps, 'value' | 'onChange' | 'type'> {
  value: number | null;
  onChange: (value: number | null) => void;
}

/** Ô nhập tiền VND: hiển thị "1.250.000", giá trị là số nguyên (hoặc null khi để trống). */
export const MoneyInput = forwardRef<HTMLInputElement, MoneyInputProps>(function MoneyInput(
  { value, onChange, className, ...rest },
  ref,
) {
  const [text, setText] = useState(value === null || value === undefined ? '' : fmt.format(value));

  useEffect(() => {
    const parsed = text.replace(/\D/g, '');
    const current = parsed === '' ? null : Number(parsed);
    if (current !== value) setText(value === null || value === undefined ? '' : fmt.format(value));
    // Chỉ đồng bộ khi giá trị từ ngoài thay đổi.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <div className={cn('relative', className)}>
      <Input
        ref={ref}
        inputMode="numeric"
        autoComplete="off"
        value={text}
        onChange={(e) => {
          const digits = e.target.value.replace(/\D/g, '').slice(0, 15);
          const num = digits === '' ? null : Number(digits);
          setText(num === null ? '' : fmt.format(num));
          onChange(num);
        }}
        className="pr-8 tabular"
        {...rest}
      />
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-fg-subtle" aria-hidden>
        ₫
      </span>
    </div>
  );
});
