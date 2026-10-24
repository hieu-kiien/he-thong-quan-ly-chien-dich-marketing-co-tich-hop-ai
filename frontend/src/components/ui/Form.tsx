import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/cn';

const controlBase =
  'w-full rounded-md border bg-surface text-sm text-fg placeholder:text-fg-subtle transition-colors ' +
  'focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent ' +
  'disabled:cursor-not-allowed disabled:bg-subtle disabled:text-fg-muted';

const invalidCls = 'border-danger focus:ring-danger/30 focus:border-danger';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ invalid, className, ...rest }, ref) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(controlBase, 'h-9 px-3', invalid ? invalidCls : 'border-border-strong', className)}
      {...rest}
    />
  );
});

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, className, rows = 4, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn(controlBase, 'px-3 py-2 leading-6', invalid ? invalidCls : 'border-border-strong', className)}
      {...rest}
    />
  );
});

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  invalid?: boolean;
  options: SelectOption[];
  /** Dòng đầu trống (vd "Tất cả trạng thái"). */
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid, className, options, placeholder, ...rest },
  ref,
) {
  return (
    <div className={cn('relative', className)}>
      <select
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(controlBase, 'h-9 appearance-none pl-3 pr-8', invalid ? invalidCls : 'border-border-strong')}
        {...rest}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value} disabled={o.disabled}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle"
        aria-hidden
      />
    </div>
  );
});

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: ReactNode;
  description?: ReactNode;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, description, className, id, ...rest },
  ref,
) {
  const autoId = useId();
  const cid = id ?? autoId;
  return (
    <div className={cn('flex items-start gap-2.5', className)}>
      <input
        ref={ref}
        id={cid}
        type="checkbox"
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-border-strong text-accent accent-[rgb(var(--accent))] focus:ring-accent"
        {...rest}
      />
      <label htmlFor={cid} className="text-sm leading-5 text-fg">
        {label}
        {description && <span className="block text-xs text-fg-subtle">{description}</span>}
      </label>
    </div>
  );
});

export interface FieldControlProps {
  id: string;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
  invalid: boolean;
}

export interface FormFieldProps {
  label: ReactNode;
  /** Lỗi inline (vd từ `fields` của lỗi 422). */
  error?: string | null;
  hint?: ReactNode;
  required?: boolean;
  className?: string;
  /** Nhãn phụ bên phải (vd bộ đếm ký tự). */
  aside?: ReactNode;
  children: (control: FieldControlProps) => ReactNode;
}

/**
 * Nhãn + control + gợi ý + lỗi, nối id/aria tự động:
 * `<FormField label="Tên">{(p) => <Input {...p} value=... />}</FormField>`
 */
export function FormField({ label, error, hint, required, className, aside, children }: FormFieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errId = error ? `${id}-err` : undefined;
  const describedBy = [hintId, errId].filter(Boolean).join(' ') || undefined;
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="text-[0.8125rem] font-medium text-fg">
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden>
              *
            </span>
          )}
        </label>
        {aside && <span className="text-xs text-fg-subtle">{aside}</span>}
      </div>
      {children({ id, 'aria-invalid': !!error || undefined, 'aria-describedby': describedBy, invalid: !!error })}
      {hint && !error && (
        <p id={hintId} className="text-xs text-fg-subtle">
          {hint}
        </p>
      )}
      {error && (
        <p id={errId} className="text-xs text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
