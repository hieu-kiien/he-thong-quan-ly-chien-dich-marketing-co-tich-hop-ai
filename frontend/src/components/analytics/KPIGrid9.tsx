import React, { useId } from 'react';
import {
  Coins,
  TrendingUp,
  Award,
  Target,
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

interface PrimaryCardProps {
  title: string;
  hint: string;
  icon: React.ReactNode;
  value: React.ReactNode;
  subtext: React.ReactNode;
  highlightBorder?: boolean;
}

const PrimaryCard: React.FC<PrimaryCardProps> = ({
  title,
  hint,
  icon,
  value,
  subtext,
  highlightBorder = false,
}) => {
  // `useId` sinh id ổn định và duy nhất theo thứ tự render, nên `sr-only` +
  // `aria-describedby` không đụng nhau giữa các thẻ.
  const hintId = useId();
  return (
    <div
      className={`bg-white rounded-xl border p-4 transition-all group ${
        highlightBorder ? 'border-[#D95D39]/50 shadow-sm' : 'border-[#E4E2DD]'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold text-[#5A5E66] flex items-center gap-1.5">
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
        <div className="w-7 h-7 rounded-lg bg-[#F6F5F0] text-[#121316] flex items-center justify-center shrink-0 border border-[#E4E2DD]">
          {icon}
        </div>
      </div>
      {value}
      <div className="mt-2 pt-2 border-t border-[#F0EFEA] text-[11px] text-[#5A5E66] flex items-center justify-between gap-2">
        {subtext}
      </div>
    </div>
  );
};

/**
 * Lưới 9 KPI được phân tầng rõ ràng theo chuẩn Anti-AI Taste:
 * - Hàng 1 (4 chỉ số quyết định sống còn): Tiền đã chi, Doanh thu thu về, Hệ số lời/lỗ (ROAS), Số đơn hàng.
 * - Hàng 2 (5 chỉ số phễu phụ trên 1 thanh gọn): Lãi ròng (ROI), Lượt xem, Lượt bấm, Tỷ lệ bấm (CTR), Giá mỗi lượt bấm (CPC).
 */
export const KPIGrid9: React.FC<KPIGrid9Props> = ({ kpi, loading = false, error, onRetry, className = '' }) => {
  if (loading) {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 ${className}`}>
        {Array.from({ length: 4 }).map((_, idx) => (
          <div key={idx} className="bg-white rounded-xl border border-[#E4E2DD] p-4 animate-pulse">
            <div className="flex items-center justify-between mb-3">
              <div className="h-3 w-28 bg-slate-200 rounded"></div>
              <div className="w-7 h-7 rounded-lg bg-slate-100"></div>
            </div>
            <div className="h-7 w-32 bg-slate-200 rounded mb-2"></div>
            <div className="h-3 w-40 bg-slate-100 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className={`rounded-xl border border-rose-200 bg-rose-50 p-5 text-center ${className}`}
      >
        <AlertTriangle className="w-6 h-6 text-rose-600 mx-auto mb-2" />
        <p className="text-sm font-bold text-rose-950">Không tải được bảng số liệu</p>
        <p className="text-xs text-rose-800 mt-1 max-w-lg mx-auto">{error}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold"
          >
            Thử tải lại
          </button>
        )}
      </div>
    );
  }

  if (!kpi) {
    return (
      <div className={`rounded-xl border border-[#E4E2DD] bg-white p-6 text-center ${className}`}>
        <Inbox className="w-6 h-6 text-slate-400 mx-auto mb-2" />
        <p className="text-sm font-bold text-[#121316]">Chưa có số liệu quảng cáo</p>
        <p className="text-xs text-[#5A5E66] mt-1 max-w-lg mx-auto">
          Bạn có thể bấm nút &ldquo;Nhập file báo cáo (CSV)&rdquo; ở góc trên để tải số liệu từ Facebook, TikTok hoặc Shopee vào hệ thống.
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

  const getRoasBadge = (val: number) => {
    if (val >= 3.0) {
      return {
        badge: 'bg-[#F0FDF4] text-[#15803D] border-[#BBF7D0]',
        text: 'Đang lãi tốt (≥ 3.0x)',
        dot: 'bg-[#15803D]'
      };
    }
    if (val >= 1.5) {
      return {
        badge: 'bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]',
        text: 'Hòa vốn / Lãi nhẹ',
        dot: 'bg-[#B45309]'
      };
    }
    return {
      badge: 'bg-[#FFF1F2] text-[#BE123C] border-[#FECDD3]',
      text: 'Đang lỗ (< 1.5x)',
      dot: 'bg-[#BE123C]'
    };
  };

  const roasBadgeInfo = getRoasBadge(roas);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* TẦNG 1: 4 CON SỐ QUAN TRỌNG NHẤT (TIỀN CHI, TIỀN THU, LỜI/LỖ, ĐƠN HÀNG) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <PrimaryCard
          title="Tiền quảng cáo đã chi"
          hint="Tổng số tiền đã tiêu trên toàn bộ các kênh quảng cáo"
          icon={<Coins className="w-4 h-4" />}
          value={
            <div className="text-2xl font-black text-[#121316] font-mono tabular-nums tracking-tight">
              {formatNumber(cost)} <span className="text-xs font-semibold text-[#5A5E66]">đ</span>
            </div>
          }
          subtext={<span>Tổng chi phí thực tế đã ghi nhận</span>}
        />

        <PrimaryCard
          title="Doanh thu mang về"
          hint="Tổng số tiền bán hàng thu được từ các chiến dịch quảng cáo"
          icon={<TrendingUp className="w-4 h-4 text-[#15803D]" />}
          value={
            <div className="text-2xl font-black text-[#15803D] font-mono tabular-nums tracking-tight">
              {formatNumber(revenue)} <span className="text-xs font-semibold text-[#5A5E66]">đ</span>
            </div>
          }
          subtext={<span>Tổng giá trị đơn hàng từ quảng cáo</span>}
        />

        <PrimaryCard
          title="Hệ số thu hồi vốn (ROAS)"
          hint="Lấy Doanh thu chia cho Chi phí. Ví dụ 3.5x nghĩa là chi 1 đồng quảng cáo thu về 3.5 đồng doanh thu."
          icon={<Award className="w-4 h-4 text-[#D95D39]" />}
          highlightBorder={true}
          value={
            cost > 0 ? (
              <div className="flex items-baseline gap-2 flex-wrap">
                <div className="text-2xl font-black text-[#121316] font-mono tabular-nums tracking-tight">
                  {roas.toFixed(2)}<span className="text-base font-bold text-[#D95D39]">x</span>
                </div>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold border ${roasBadgeInfo.badge}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${roasBadgeInfo.dot}`}></span>
                  <span>{roasBadgeInfo.text}</span>
                </span>
              </div>
            ) : (
              <div className="text-2xl font-black text-slate-400 font-mono tracking-tight">—</div>
            )
          }
          subtext={
            <span>
              {cost > 0
                ? `Chi 1 đồng thu về ${roas.toFixed(2)} đồng (Chuẩn ≥ 3.0x)`
                : 'Chưa có chi phí để tính hệ số'}
            </span>
          }
        />

        <PrimaryCard
          title="Tổng đơn hàng / Chuyển đổi"
          hint="Số đơn đặt hàng hoặc khách để lại thông tin mua hàng thành công"
          icon={<Target className="w-4 h-4" />}
          value={
            <div className="text-2xl font-black text-[#121316] font-mono tabular-nums tracking-tight">
              {formatNumber(conversions)} <span className="text-xs font-semibold text-[#5A5E66]">đơn</span>
            </div>
          }
          subtext={
            <span>
              {clicks > 0
                ? `Cứ 100 người bấm thì có ${cvr.toFixed(1)} người mua (CVR ${cvr.toFixed(2)}%)`
                : 'Chưa có lượt bấm để tính tỷ lệ chốt'}
            </span>
          }
        />
      </div>

      {/* TẦNG 2: 5 CHỈ SỐ PHỄU PHỤ (GỌN TRÊN 1 THANH NGANG ĐỂ KHÔNG RỐI MẮT) */}
      <div className="bg-white rounded-xl border border-[#E4E2DD] px-4 py-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 divide-y sm:divide-y-0 sm:divide-x divide-[#F0EFEA]">
        <div className="pt-2 sm:pt-0 sm:px-3 first:pl-0 first:pt-0">
          <div className="text-[11px] font-semibold text-[#5A5E66]">Tỷ suất lãi ròng (ROI)</div>
          <div className="text-sm font-black font-mono tabular-nums text-[#121316] mt-0.5">
            {cost > 0 ? `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%` : '—'}
          </div>
          <div className="text-[10px] text-[#8A8F98]">(Doanh thu - Chi phí) / Chi phí</div>
        </div>

        <div className="pt-2 sm:pt-0 sm:px-3">
          <div className="text-[11px] font-semibold text-[#5A5E66]">Lượt hiển thị (Views)</div>
          <div className="text-sm font-black font-mono tabular-nums text-[#121316] mt-0.5">
            {formatNumber(views)} <span className="text-[11px] font-normal text-[#5A5E66]">lượt</span>
          </div>
          <div className="text-[10px] text-[#8A8F98]">Số lần khách nhìn thấy quảng cáo</div>
        </div>

        <div className="pt-2 sm:pt-0 sm:px-3">
          <div className="text-[11px] font-semibold text-[#5A5E66]">Lượt bấm vào xem (Clicks)</div>
          <div className="text-sm font-black font-mono tabular-nums text-[#121316] mt-0.5">
            {formatNumber(clicks)} <span className="text-[11px] font-normal text-[#5A5E66]">click</span>
          </div>
          <div className="text-[10px] text-[#8A8F98]">Số người bấm vào bài quảng cáo</div>
        </div>

        <div className="pt-2 sm:pt-0 sm:px-3">
          <div className="text-[11px] font-semibold text-[#5A5E66]">Tỷ lệ người bấm (CTR)</div>
          <div className="text-sm font-black font-mono tabular-nums text-[#121316] mt-0.5">
            {views > 0 ? `${ctr.toFixed(2)}%` : '—'}
          </div>
          <div className="text-[10px] text-[#8A8F98]">100 người thấy có {views > 0 ? ctr.toFixed(1) : 0} người bấm</div>
        </div>

        <div className="pt-2 sm:pt-0 sm:px-3">
          <div className="text-[11px] font-semibold text-[#5A5E66]">Giá mỗi lượt bấm (CPC)</div>
          <div className="text-sm font-black font-mono tabular-nums text-[#121316] mt-0.5">
            {clicks > 0 ? `${formatNumber(Math.round(cpc))} đ` : '—'}
          </div>
          <div className="text-[10px] text-[#8A8F98]">Chi phí trung bình cho 1 người bấm</div>
        </div>
      </div>
    </div>
  );
};
