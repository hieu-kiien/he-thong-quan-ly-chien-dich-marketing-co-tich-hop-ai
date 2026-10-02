const vndFormatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });
const vndFormatterCompact = new Intl.NumberFormat('vi-VN', { notation: 'compact', maximumFractionDigits: 1 });

/**
 * Số tiền trong hệ thống là VND. Trước đây UI gắn ký hiệu `$` và gọi
 * `toLocaleString()` không kèm locale, nên 15000000 hiện ra là "15,000,000 $".
 */
export const formatVND = (value: number | string | null | undefined): string => {
  const n = typeof value === 'string' ? Number(value) : value;
  if (n === null || n === undefined || Number.isNaN(n)) return '0';
  return `${vndFormatter.format(n)} ₫`;
};

export const formatVNDCompact = (value: number | string | null | undefined): string => {
  const n = typeof value === 'string' ? Number(value) : value;
  if (n === null || n === undefined || Number.isNaN(n)) return '0 ₫';
  return `${vndFormatterCompact.format(n)} ₫`;
};

/** Phần trăm có 1 chữ số thập phân; trả về chuỗi rỗng khi không có mẫu số. */
export const formatPercent = (
  numerator: number | null | undefined,
  denominator: number | null | undefined,
  digits = 2
): string => {
  const a = Number(numerator);
  const b = Number(denominator);
  if (!Number.isFinite(a) || !Number.isFinite(b) || b === 0) return '—';
  return `${((a / b) * 100).toFixed(digits)}%`;
};

export const formatNumber = (value: number | string | null | undefined): string => {
  const n = typeof value === 'string' ? Number(value) : value;
  if (n === null || n === undefined || Number.isNaN(n)) return '0';
  return vndFormatter.format(n);
};

export const formatRatio = (value: number | string | null | undefined, digits = 2): string => {
  const n = typeof value === 'string' ? Number(value) : value;
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  return n.toFixed(digits);
};

const dateFormatter = new Intl.DateTimeFormat('vi-VN');

/** Ngày theo địa phạm vi người dùng, không phụ thuộc locale của trình duyệt. */
export const formatDateVN = (value: string | Date | null | undefined): string => {
  if (!value) return '—';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return dateFormatter.format(d);
};

/** Ngày hôm nay theo giờ địa phương, định dạng YYYY-MM-DD. */
export const todayLocalISO = (): string => {
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${mm}-${dd}`;
};

/**
 * Cộng số ngày vào chuỗi YYYY-MM-DD mà không đi qua `new Date(string)`.
 * `new Date('2026-09-30')` được hiểu là UTC nửa đêm, nên ở múi giờ âm
 * `.toISOString().split('T')[0]` lùi về ngày hôm trước — tạo ra
 * `end_date < start_date` và backend trả 422 sau khi người dùng điền 4 bước.
 */
export const addDaysLocalISO = (isoDate: string, days: number): string => {
  const [y, m, d] = isoDate.split('-').map(Number);
  if (!y || !m || !d) return isoDate;
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + days);
  const mm = String(dt.getMonth() + 1).padStart(2, '0');
  const dd = String(dt.getDate()).padStart(2, '0');
  return `${dt.getFullYear()}-${mm}-${dd}`;
};