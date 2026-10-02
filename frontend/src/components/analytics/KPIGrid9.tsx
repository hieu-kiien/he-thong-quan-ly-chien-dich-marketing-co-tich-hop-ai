import React, { useId } from 'react';
import {
  Coins,
  TrendingUp,
  Award,
  Sparkles,
  Eye,
  MousePointer,
  Percent,
  Target,
  CreditCard,
  Info,
  AlertTriangle,
  Inbox
} from 'lucide-react';
import { KPISummary } from '../../types';
import { formatNumber } from '../../utils/format';

interface KPIGrid9Props {
  kpi?: KPISummary | null;
  loading?: boolean;
  /** Thông điệp lỗi tải dữ liệu. Không có trạng thái lỗi thì một API hỏng hiện ra
   *  y hệt một dashboard không có dữ liệu — tức 9 ô toàn 0/0 đ. */
  error?: string | null;
  onRetry?: () => void;
  className?: string;
}

interface CardShellProps {
  title: string;
  hint: string;
  icon: React.ReactNode;
  iconClass: string;
  value: React.ReactNode;
  valueClass?: string;
  footer: React.ReactNode;
}

const CardShell: React.FC<CardShellProps> = ({
  title, hint, icon, iconClass, value, footer
}) => {
  // `useId` sinh id ổn định và duy nhất theo thứ tự render, nên `sr-only` +
  // `aria-describedby` không đụng nhau giữa 9 thẻ (id viết tay dễ trùng khi
  // thẻ được render lại hoặc thêm/bớt).
  const hintId = useId();
  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm hover:shadow-md transition-all group">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <span>{title}</span>
          {/* Icon trang trí KHÔNG được mang `aria-label`: `<span>` mặc định có
              role "generic", mà ARIA cấm mọi thuộc tính aria-* trên role đó ->
              axe báo `aria-prohibited-attr` mức serious. Giải thích cho trình đọc
              màn hình đi qua `aria-describedby` trỏ tới phần tử `sr-only`; icon
              đánh dấu `aria-hidden` vì không mang thông tin riêng. */}
          <span
            className="group-hover:opacity-100 opacity-60 transition-opacity"
            title={hint}
            aria-describedby={hintId}
          >
            <Info className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
          </span>
          <span id={hintId} className="sr-only">{hint}</span>
        </span>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${iconClass}`}>
          {icon}
        </div>
      </div>
      {value}
      <div className="mt-3 flex items-center justify-between gap-2 text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
        {footer}
      </div>
    </div>
  );
};

/**
 * Lưới 9 KPI. Trước đây mỗi ô gắn một mức tăng/giảm so với kỳ trước viết cứng
 * (-4.2%, +18.5%, +14.8%, +12.3%, +22.4%, +9.4%, -8.1%) dù backend không cung cấp
 * hai mốc để so sánh. Người dùng nhận ra chi phí "giảm 4.2%" kể cả khi chi phí
 * đã tăng gấp mười. Ở đây phần delta chỉ hiện khi thật sự có dữ liệu so sánh.
 */
export const KPIGrid9: React.FC<KPIGrid9Props> = ({ kpi, loading = false, error, onRetry, className = '' }) => {
  if (loading) {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 ${className}`}>
        {Array.from({ length: 9 }).map((_, idx) => (
          <div key={idx} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm animate-pulse">
            <div className="flex items-center justify-between mb-3">
              <div className="h-3 w-28 bg-slate-200 rounded"></div>
              <div className="w-8 h-8 rounded-xl bg-slate-100"></div>
            </div>
            <div className="h-8 w-36 bg-slate-200 rounded mb-2"></div>
            <div className="h-3 w-48 bg-slate-100 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className={`rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center ${className}`}
      >
        <AlertTriangle className="w-7 h-7 text-rose-500 mx-auto mb-2" />
        <p className="text-sm font-bold text-rose-900">Không tải được chỉ số Dashboard</p>
        <p className="text-xs text-rose-700 mt-1 max-w-lg mx-auto">{error}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold"
          >
            Thử lại
          </button>
        )}
      </div>
    );
  }

  if (!kpi) {
    return (
      <div className={`rounded-2xl border border-slate-200 bg-white p-6 text-center ${className}`}>
        <Inbox className="w-7 h-7 text-slate-300 mx-auto mb-2" />
        <p className="text-sm font-bold text-slate-700">Chưa có dữ liệu chỉ số</p>
        <p className="text-xs text-slate-500 mt-1 max-w-lg mx-auto">
          Chưa nhập CampaignMetric nào trong phạm vi bạn được phép xem. Hãy tạo chiến dịch và nhập chỉ số,
          hoặc chạy <code>python backend/seed/seed_data.py</code> để nạp dữ liệu mẫu.
        </p>
      </div>
    );
  }

  const cost = Number(kpi.total_cost) || 0;
  const revenue = Number(kpi.total_revenue) || 0;
  const views = Number(kpi.total_views) || 0;
  const clicks = Number(kpi.total_clicks) || 0;
  const conversions = Number(kpi.total_conversions) || 0;
  const ctr = kpi.ctr_percent !== undefined ? kpi.ctr_percent : (views > 0 ? (clicks / views * 100) : 0);
  const cpc = kpi.cpc_avg !== undefined ? kpi.cpc_avg : (clicks > 0 ? (cost / clicks) : 0);
  const cvr = kpi.cvr_percent !== undefined ? kpi.cvr_percent : (clicks > 0 ? (conversions / clicks * 100) : 0);
  const roi = kpi.roi_percent !== undefined ? kpi.roi_percent : (cost > 0 ? ((revenue - cost) / cost * 100) : 0);
  const roas = kpi.roas !== undefined ? kpi.roas : (cost > 0 ? (revenue / cost) : 0);

  // Không có mốc kỳ trước trong API nên không được bịa delta.
  const noComparison = (
    // `text-slate-400` trên nền trắng ~2.6:1, dưới ngưỡng 4.5:1 của WCAG AA cho
    // chữ 10px. `text-slate-500` (~4.8:1) vẫn chìm về thị giác nhưng đạt chuẩn.
    <span className="text-slate-500 dark:text-slate-400 text-[10px] font-normal">
      chưa có dữ liệu kỳ so sánh
    </span>
  );

  const getRoasBadge = (val: number) => {
    if (val >= 3.0) {
      return {
        badge: 'bg-emerald-50 text-emerald-700 border-emerald-300',
        text: 'ROAS Xuất sắc (≥3.0x)',
        dot: 'bg-emerald-500'
      };
    }
    if (val >= 1.5) {
      return {
        badge: 'bg-amber-50 text-amber-700 border-amber-300',
        text: 'ROAS Đạt chuẩn (1.5x - 3.0x)',
        dot: 'bg-amber-500'
      };
    }
    return {
      badge: 'bg-rose-50 text-rose-700 border-rose-300',
      text: 'ROAS Cảnh báo (<1.5x)',
      dot: 'bg-rose-500'
    };
  };

  const roasBadgeInfo = getRoasBadge(roas);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 9-KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

        {/* CARD 1: Chi phí Tiếp thị (Total Spend) */}
        <CardShell
          title="Chi phí Tiếp thị"
          hint="Tổng chi phí quảng cáo và phân phối trên toàn bộ các kênh tiếp thị"
          icon={<Coins className="w-4 h-4" />}
          iconClass="bg-rose-50 text-rose-600"
          value={
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              {formatNumber(cost)} <span className="text-sm font-semibold text-slate-500">đ</span>
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">Tổng chi phí đã ghi nhận</span>
              {noComparison}
            </>
          }
        />

        {/* CARD 2: Doanh thu Tạo ra (Total Revenue) */}
        <CardShell
          title="Doanh thu Tạo ra"
          hint="Tổng doanh thu quy kết trực tiếp từ các đơn hàng và chuyển đổi"
          icon={<TrendingUp className="w-4 h-4" />}
          iconClass="bg-emerald-50 text-emerald-700"
          value={
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight text-emerald-700 dark:text-emerald-400">
              {formatNumber(revenue)} <span className="text-sm font-semibold text-slate-500">đ</span>
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">Giá trị đơn hàng quy kết</span>
              {noComparison}
            </>
          }
        />

        {/* CARD 3: Điểm hoàn vốn ROAS */}
        <CardShell
          title="Điểm hoàn vốn ROAS"
          hint="Return on Ad Spend = Doanh thu / Chi phí. Đo lường mức độ hoàn vốn quảng cáo"
          icon={<Award className="w-4 h-4" />}
          iconClass="bg-indigo-50 text-indigo-600"
          value={
            cost > 0 ? (
              <div className="flex items-baseline gap-2 flex-wrap">
                <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
                  {roas.toFixed(2)}<span className="text-lg font-bold text-indigo-600">x</span>
                </div>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold border ${roasBadgeInfo.badge}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${roasBadgeInfo.dot}`}></span>
                  <span>{roasBadgeInfo.text}</span>
                </span>
              </div>
            ) : (
              <div className="text-2xl font-black text-slate-400 dark:text-slate-500 tracking-tight">
                —
              </div>
            )
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">
                {cost > 0 ? 'Doanh thu / Chi phí quảng cáo' : 'Chưa có chi phí để tính ROAS'}
              </span>
              <span className="text-slate-600 dark:text-slate-300 font-semibold">Mục tiêu: ≥ 3.0x</span>
            </>
          }
        />

        {/* CARD 4: Tỷ suất sinh lời ROI */}
        <CardShell
          title="Tỷ suất lợi nhuận ROI"
          hint="Return on Investment = (Doanh thu - Chi phí) / Chi phí * 100%"
          icon={<Sparkles className="w-4 h-4" />}
          iconClass="bg-violet-50 text-violet-600"
          value={
            <div className="text-2xl font-black text-violet-600 dark:text-violet-400 tracking-tight">
              {cost > 0 ? `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%` : '—'}
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">Lợi nhuận ròng trên vốn tiếp thị</span>
              {noComparison}
            </>
          }
        />

        {/* CARD 5: Tổng Lượt xem (Total Views) */}
        <CardShell
          title="Tổng Lượt xem (Views)"
          hint="Số lượt hiển thị bài viết và phát video trên toàn bộ các kênh"
          icon={<Eye className="w-4 h-4" />}
          iconClass="bg-blue-50 text-blue-600"
          value={
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              {formatNumber(views)} <span className="text-sm font-semibold text-slate-500">lượt</span>
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">Tổng lượt hiển thị đã đo</span>
              {noComparison}
            </>
          }
        />

        {/* CARD 6: Tổng Lượt click (Total Clicks) */}
        <CardShell
          title="Tổng Lượt click"
          hint="Tổng số lượt nhấp vào đường link, nút bấm hoặc quảng cáo"
          icon={<MousePointer className="w-4 h-4" />}
          iconClass="bg-amber-50 text-amber-600"
          value={
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              {formatNumber(clicks)} <span className="text-sm font-semibold text-slate-500">click</span>
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">Lưu lượng truy cập đã đo</span>
              {noComparison}
            </>
          }
        />

        {/* CARD 7: Tỷ lệ Click CTR (%) */}
        <CardShell
          title="Tỷ lệ nhấp CTR (%)"
          hint="Click-Through Rate = Clicks / Views * 100%. Đo lường sức hấp dẫn của tiêu đề và hình ảnh"
          icon={<Percent className="w-4 h-4" />}
          iconClass="bg-teal-50 text-teal-600"
          value={
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              {views > 0 ? `${ctr.toFixed(2)}%` : '—'}
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">
                {views > 0 ? 'Clicks / Views' : 'Chưa có lượt xem để tính CTR'}
              </span>
              {noComparison}
            </>
          }
        />

        {/* CARD 8: Lượt chuyển đổi (Total Conversions) */}
        <CardShell
          title="Lượt chuyển đổi"
          hint="Số đơn hàng hoặc lượt điền form đăng ký thành công"
          icon={<Target className="w-4 h-4" />}
          iconClass="bg-purple-50 text-purple-600"
          value={
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              {formatNumber(conversions)} <span className="text-sm font-semibold text-slate-500">đơn</span>
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">
                {clicks > 0 ? `Tỷ lệ CVR: ${cvr.toFixed(2)}%` : 'Chưa có click để tính CVR'}
              </span>
              {noComparison}
            </>
          }
        />

        {/* CARD 9: Chi phí mỗi click (CPC) */}
        <CardShell
          title="Chi phí mỗi Click (CPC)"
          hint="Cost Per Click = Tổng chi phí / Lượt nhấp. Giá trị thấp phản ánh chi phí tối ưu"
          icon={<CreditCard className="w-4 h-4" />}
          iconClass="bg-cyan-50 text-cyan-600"
          value={
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              {clicks > 0 ? `${formatNumber(Math.round(cpc))} đ` : '—'}
            </div>
          }
          footer={
            <>
              <span className="text-slate-500 dark:text-slate-400">
                {clicks > 0 ? `Tổng chi phí / ${formatNumber(clicks)} click` : 'Chưa có click để tính CPC'}
              </span>
              {noComparison}
            </>
          }
        />

      </div>
    </div>
  );
};
