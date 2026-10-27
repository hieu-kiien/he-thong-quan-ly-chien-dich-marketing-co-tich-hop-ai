/**
 * Định dạng hiển thị (vi-VN, Asia/Ho_Chi_Minh).
 * Giá trị null/undefined luôn hiển thị "—" (không tự suy diễn số liệu).
 */

export const TZ = 'Asia/Ho_Chi_Minh';
export const EMPTY = '—';

type Num = number | null | undefined;

const intFmt = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });
const compactFmt = new Intl.NumberFormat('vi-VN', { notation: 'compact', maximumFractionDigits: 1 });

/** 1250000 → "1.250.000 ₫" */
export function formatMoney(value: Num): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return `${intFmt.format(Math.round(value))} ₫`;
}

export function formatNumber(value: Num): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return intFmt.format(value);
}

export function formatCompact(value: Num): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return compactFmt.format(value);
}

/**
 * Tỷ lệ dạng phân số (0.0234) → "2,34%". Backend trả ctr/cvr là phân số.
 * `budget_used_pct`/`used_pct` có thể là phần trăm — dùng formatPct cho trường hợp đó.
 */
export function formatRate(value: Num, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return `${(value * 100).toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
}

/** Giá trị đã là phần trăm (45.2) → "45,2%". */
export function formatPct(value: Num, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return `${value.toLocaleString('vi-VN', { minimumFractionDigits: 0, maximumFractionDigits: digits })}%`;
}

/** "2026-10-24" → "24/10/2026" (không đổi múi giờ: ngày thuần). */
export function formatDate(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (m && value.length === 10) return `${m[3]}/${m[2]}/${m[1]}`;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return EMPTY;
  return new Intl.DateTimeFormat('vi-VN', { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric' }).format(d);
}

/** ISO có timezone → "24/10/2026 19:30" theo giờ Việt Nam. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return EMPTY;
  const p = zonedParts(d);
  return `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}`;
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return EMPTY;
  const p = zonedParts(d);
  return `${p.hour}:${p.minute}`;
}

/** "5 phút trước", "hôm qua"... cho thông báo. */
export function formatRelative(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const d = new Date(value);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'vừa xong';
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} ngày trước`;
  return formatDateTime(value);
}

interface ZonedParts {
  year: string;
  month: string;
  day: string;
  hour: string;
  minute: string;
}

const partsFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: TZ,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

export function zonedParts(d: Date): ZonedParts {
  const out: Record<string, string> = {};
  for (const part of partsFmt.formatToParts(d)) out[part.type] = part.value;
  return { year: out.year, month: out.month, day: out.day, hour: out.hour, minute: out.minute };
}

/** Ngày (YYYY-MM-DD) của một thời điểm theo giờ Việt Nam. */
export function zonedDateKey(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value;
  const p = zonedParts(d);
  return `${p.year}-${p.month}-${p.day}`;
}

/** Hôm nay theo giờ Việt Nam, dạng YYYY-MM-DD. */
export function todayKey(): string {
  return zonedDateKey(new Date());
}

/** Giá trị cho <input type="datetime-local"> từ ISO, theo giờ Việt Nam. */
export function toDateTimeLocal(value: string | null | undefined): string {
  if (!value) return '';
  const p = zonedParts(new Date(value));
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

/** "2026-10-24T19:30" (giờ Việt Nam) → "2026-10-24T19:30:00+07:00". */
export function fromDateTimeLocal(value: string): string {
  return `${value.length === 16 ? `${value}:00` : value}+07:00`;
}

// ---------------------------------------------------------------- Date math on YYYY-MM-DD

export function parseDateKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

/** Ngày (YYYY-MM-DD) theo thành phần NGÀY ĐỊA PHƯƠNG của Date (cho ô lịch dựng bằng new Date(y, m, d)). */
export function localDateKey(d: Date): string {
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export function dateKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function addDays(key: string, days: number): string {
  const d = parseDateKey(key);
  d.setUTCDate(d.getUTCDate() + days);
  return dateKey(d);
}

export function addMonths(key: string, months: number): string {
  const d = parseDateKey(key);
  d.setUTCDate(1);
  d.setUTCMonth(d.getUTCMonth() + months);
  return dateKey(d);
}

/** Thứ trong tuần, Thứ Hai = 0 ... Chủ nhật = 6. */
export function weekdayMon0(key: string): number {
  return (parseDateKey(key).getUTCDay() + 6) % 7;
}

export function startOfWeek(key: string): string {
  return addDays(key, -weekdayMon0(key));
}

export function startOfMonth(key: string): string {
  return `${key.slice(0, 7)}-01`;
}

export function endOfMonth(key: string): string {
  return addDays(addMonths(startOfMonth(key), 1), -1);
}

export function daysBetween(a: string, b: string): number {
  return Math.round((parseDateKey(b).getTime() - parseDateKey(a).getTime()) / 86400000);
}

export const WEEKDAY_SHORT = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];

export function monthLabel(key: string): string {
  const d = parseDateKey(key);
  return `Tháng ${d.getUTCMonth() + 1}/${d.getUTCFullYear()}`;
}

/** Nhãn kỳ cho biểu đồ theo granularity. */
export function formatPeriod(period: string, granularity: 'day' | 'week' | 'month'): string {
  if (granularity === 'month') {
    const m = /^(\d{4})-(\d{2})/.exec(period);
    return m ? `${m[2]}/${m[1]}` : period;
  }
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(period);
  if (!m) return period;
  return granularity === 'week' ? `Tuần ${m[3]}/${m[2]}` : `${m[3]}/${m[2]}`;
}
