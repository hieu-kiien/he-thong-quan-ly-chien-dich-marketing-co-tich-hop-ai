import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { Page } from '../types';
import { PAGE_SIZE_OPTIONS } from '../types';

/**
 * Bộ điều khiển phân trang dùng chung cho mọi màn hình danh sách.
 *
 * BA QUY TẮC ĐÃ THỰC THI Ở ĐÂY — cả ba đều là chỗ dễ sai:
 *
 * 1. **Không hiện khi danh sách rỗng.** Màn hình không có danh sách thì không
 *    được có bộ phân trang: một thanh "Trang 1/1" trên màn hình trống chỉ gây
 *    thắc mắc. Vì vậy `total === 0` -> trả `null`.
 *
 * 2. **Nút Trước/ Sau phải thực sự bị vô hiệu hóa.** Dựa vào `has_prev` /
 *    `has_next` từ server chứ không suy ra từ `page` bên client — nếu server
 *    báo `has_next=false` thì nút phải tắt, kể cả khi client nghĩ còn trang.
 *
 * 3. **Đổi kích thước trang phải về trang 1.** Ở trang 7 với `page_size=10`,
 *    đổi sang 50 sẽ ra một trang không tồn tại và danh sách trống. Đây là lỗi
 *    kinh điển của phân trang phía client.
 */
export interface PaginationProps {
  page: Page<unknown>;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  /** Nhãn đơn vị, ví dụ "chiến dịch". Rỗng thì không hiện. */
  itemLabel?: string;
  /** Ẩn bộ chọn kích thước trang khi màn hình quá hẹp (mobile). */
  showPageSize?: boolean;
  disabled?: boolean;
}

const PAGE_BUTTON_CLASS =
  'inline-flex h-9 min-w-9 items-center justify-center rounded-lg border px-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1';
const PAGE_BUTTON_ACTIVE = 'border-indigo-600 bg-indigo-600 text-white hover:bg-indigo-700';
const PAGE_BUTTON_IDLE =
  'border-slate-300 bg-white text-slate-700 hover:border-indigo-400 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400';

export const Pagination: React.FC<PaginationProps> = ({
  page,
  onPageChange,
  onPageSizeChange,
  itemLabel = '',
  showPageSize = true,
  disabled = false,
}) => {
  // Quy tắc 1: không có bản ghi thì không có bộ phân trang.
  if (!page || page.total === 0) return null;

  const totalPages = Math.max(page.total_pages, 1);
  const current = Math.min(Math.max(page.page, 1), totalPages);

  // Cửa sổ nút trang: luôn có trang đầu và trang cuối, quanh trang hiện tại.
  // Rút gọn thành "…" khi danh sách dài, vì dựng 40 nút sẽ vỡ layout hẹp.
  const pages: (number | 'gap')[] = [];
  const push = (n: number) => {
    if (!pages.includes(n)) pages.push(n);
  };
  push(1);
  for (let n = current - 1; n <= current + 1; n += 1) {
    if (n > 1 && n < totalPages) push(n);
  }
  push(totalPages);

  const withGaps: (number | 'gap')[] = [];
  pages.forEach((n, idx) => {
    if (idx > 0 && typeof n === 'number' && typeof pages[idx - 1] === 'number' && n - (pages[idx - 1] as number) > 1) {
      withGaps.push('gap');
    }
    withGaps.push(n);
  });

  const firstRow = page.total === 0 ? 0 : (current - 1) * page.page_size + 1;
  const lastRow = Math.min(current * page.page_size, page.total);

  return (
    <nav
      aria-label="Phân trang"
      data-testid="pagination"
      className="flex flex-col gap-3 border-t border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-600">
        <span data-testid="pagination-total">
          {`Hiển thị ${firstRow}-${lastRow} trên ${page.total} ${itemLabel || 'bản ghi'}`}
        </span>
        {showPageSize && (
          <label className="flex items-center gap-1.5">
            <span className="whitespace-nowrap">Số bản ghi / trang</span>
            <select
              aria-label="Số bản ghi mỗi trang"
              data-testid="pagination-page-size"
              value={page.page_size}
              disabled={disabled}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {PAGE_SIZE_OPTIONS.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          aria-label="Trang trước"
          data-testid="pagination-prev"
          onClick={() => onPageChange(current - 1)}
          disabled={disabled || !page.has_prev}
          className={`${PAGE_BUTTON_CLASS} ${PAGE_BUTTON_IDLE}`}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          <span className="ml-1 hidden sm:inline">Trước</span>
        </button>

        <div className="flex items-center gap-1" data-testid="pagination-pages">
          {withGaps.map((entry, idx) =>
            entry === 'gap' ? (
              <span key={`gap-${idx}`} className="px-1 text-sm text-slate-400" aria-hidden="true">
                …
              </span>
            ) : (
              <button
                key={entry}
                type="button"
                aria-label={`Trang ${entry}`}
                aria-current={entry === current ? 'page' : undefined}
                data-testid={`pagination-page-${entry}`}
                onClick={() => onPageChange(entry)}
                disabled={disabled}
                className={`${PAGE_BUTTON_CLASS} ${entry === current ? PAGE_BUTTON_ACTIVE : PAGE_BUTTON_IDLE}`}
              >
                {entry}
              </button>
            )
          )}
        </div>

        <button
          type="button"
          aria-label="Trang sau"
          data-testid="pagination-next"
          onClick={() => onPageChange(current + 1)}
          disabled={disabled || !page.has_next}
          className={`${PAGE_BUTTON_CLASS} ${PAGE_BUTTON_IDLE}`}
        >
          <span className="mr-1 hidden sm:inline">Sau</span>
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
};

export default Pagination;