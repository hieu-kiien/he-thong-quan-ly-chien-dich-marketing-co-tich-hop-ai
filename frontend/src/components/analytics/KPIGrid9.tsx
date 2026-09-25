import React from 'react';
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
  ArrowUpRight,
  ArrowDownRight,
  Info
} from 'lucide-react';
import { KPISummary } from '../../types';

interface KPIGrid9Props {
  kpi?: KPISummary | null;
  loading?: boolean;
  className?: string;
}

export const KPIGrid9: React.FC<KPIGrid9Props> = ({ kpi, loading = false, className = '' }) => {
  if (loading) {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4.5 ${className}`}>
        {Array.from({ length: 9 }).map((_, idx) => (
          <div key={idx} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs animate-pulse">
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

  const cost = kpi?.total_cost || 0;
  const revenue = kpi?.total_revenue || 0;
  const views = kpi?.total_views || 0;
  const clicks = kpi?.total_clicks || 0;
  const conversions = kpi?.total_conversions || 0;
  const ctr = kpi?.ctr_percent !== undefined ? kpi.ctr_percent : (views > 0 ? (clicks / views * 100) : 0);
  const cpc = kpi?.cpc_avg !== undefined ? kpi.cpc_avg : (clicks > 0 ? (cost / clicks) : 0);
  const cvr = kpi?.cvr_percent !== undefined ? kpi.cvr_percent : (clicks > 0 ? (conversions / clicks * 100) : 0);
  const roi = kpi?.roi_percent !== undefined ? kpi.roi_percent : (cost > 0 ? ((revenue - cost) / cost * 100) : 0);
  const roas = kpi?.roas !== undefined ? kpi.roas : (cost > 0 ? (revenue / cost) : 0);

  // Phân cấp màu cho ROAS
  const getRoasBadge = (val: number) => {
    if (val >= 3.0) {
      return {
        badge: 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800',
        text: 'ROAS Xuất sắc (≥3.0x)',
        dot: 'bg-emerald-500'
      };
    }
    if (val >= 1.5) {
      return {
        badge: 'bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
        text: 'ROAS Đạt chuẩn (1.5x - 3.0x)',
        dot: 'bg-amber-500'
      };
    }
    return {
      badge: 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800',
      text: 'ROAS Cảnh báo (<1.5x)',
      dot: 'bg-rose-500'
    };
  };

  const roasBadgeInfo = getRoasBadge(roas);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 9-KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4.5">
        
        {/* CARD 1: Chi phí Tiếp thị (Total Spend) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Chi phí Tiếp thị</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Tổng chi phí quảng cáo và phân phối trên toàn bộ các kênh tiếp thị">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-600 flex items-center justify-center shrink-0">
              <Coins className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            {cost.toLocaleString('vi-VN')} <span className="text-sm font-semibold text-slate-500">đ</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Toàn bộ 3 kênh quảng cáo</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowDownRight className="w-3.5 h-3.5" />
              <span>-4.2%</span>
            </span>
          </div>
        </div>

        {/* CARD 2: Doanh thu Tạo ra (Total Revenue) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Doanh thu Tạo ra</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Tổng doanh thu quy kết trực tiếp từ các đơn hàng và chuyển đổi">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 flex items-center justify-center shrink-0">
              <TrendingUp className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight text-emerald-600 dark:text-emerald-400">
            {revenue.toLocaleString('vi-VN')} <span className="text-sm font-semibold text-slate-500">đ</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Giá trị đơn hàng quy kết</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>+18.5%</span>
            </span>
          </div>
        </div>

        {/* CARD 3: Điểm hoàn vốn ROAS */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Điểm hoàn vốn ROAS</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Return on Ad Spend = Doanh thu / Chi phí. Đo lường mức độ hoàn vốn quảng cáo">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 flex items-center justify-center shrink-0">
              <Award className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              {roas.toFixed(2)}<span className="text-lg font-bold text-indigo-600">x</span>
            </div>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold border ${roasBadgeInfo.badge}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${roasBadgeInfo.dot}`}></span>
              <span>{roasBadgeInfo.text}</span>
            </span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Doanh thu / Chi phí quảng cáo</span>
            <span className="text-slate-600 dark:text-slate-300 font-semibold">Mục tiêu: ≥ 3.0x</span>
          </div>
        </div>

        {/* CARD 4: Tỷ suất sinh lời ROI */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Tỷ suất lợi nhuận ROI</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Return on Investment = (Doanh thu - Chi phí) / Chi phí * 100%">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-violet-50 dark:bg-violet-950/40 text-violet-600 flex items-center justify-center shrink-0">
              <Sparkles className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-violet-600 dark:text-violet-400 tracking-tight">
            {roi >= 0 ? `+${roi.toFixed(1)}%` : `${roi.toFixed(1)}%`}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Lợi nhuận ròng trên vốn tiếp thị</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>+35.1%</span>
            </span>
          </div>
        </div>

        {/* CARD 5: Tổng Lượt xem (Total Views) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Tổng Lượt xem (Views)</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Số lượt hiển thị bài viết và phát video trên toàn bộ các kênh">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 flex items-center justify-center shrink-0">
              <Eye className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            {views.toLocaleString('vi-VN')} <span className="text-sm font-semibold text-slate-500">lượt</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Độ phủ Facebook, TikTok, Email</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>+14.8%</span>
            </span>
          </div>
        </div>

        {/* CARD 6: Tổng Lượt click (Total Clicks) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Tổng Lượt click</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Tổng số lượt nhấp vào đường link, nút bấm hoặc quảng cáo">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-950/40 text-amber-600 flex items-center justify-center shrink-0">
              <MousePointer className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            {clicks.toLocaleString('vi-VN')} <span className="text-sm font-semibold text-slate-500">click</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Lưu lượng truy cập thực tế</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>+12.3%</span>
            </span>
          </div>
        </div>

        {/* CARD 7: Tỷ lệ Click CTR (%) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Tỷ lệ nhấp CTR (%)</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Click-Through Rate = Clicks / Views * 100%. Đo lường sức hấp dẫn của tiêu đề và hình ảnh">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-teal-50 dark:bg-teal-950/40 text-teal-600 flex items-center justify-center shrink-0">
              <Percent className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            {ctr.toFixed(2)}%
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Chuẩn ngành TMĐT: 2.5%</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>+22.4%</span>
            </span>
          </div>
        </div>

        {/* CARD 8: Lượt chuyển đổi (Total Conversions) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Lượt chuyển đổi</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Số đơn hàng hoặc lượt điền form đăng ký thành công">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-600 flex items-center justify-center shrink-0">
              <Target className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            {conversions.toLocaleString('vi-VN')} <span className="text-sm font-semibold text-slate-500">đơn</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">Tỷ lệ CVR: {cvr.toFixed(2)}%</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>+9.4%</span>
            </span>
          </div>
        </div>

        {/* CARD 9: Chi phí mỗi click (CPC) & CVR */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Chi phí mỗi Click (CPC)</span>
              <span className="group-hover:opacity-100 opacity-60 transition-opacity" title="Cost Per Click = Tổng chi phí / Lượt nhấp. Giá trị thấp phản ánh chi phí tối ưu">
                <Info className="w-3.5 h-3.5 text-slate-400" />
              </span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-cyan-50 dark:bg-cyan-950/40 text-cyan-600 flex items-center justify-center shrink-0">
              <CreditCard className="w-4.5 h-4.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            {Math.round(cpc).toLocaleString('vi-VN')} <span className="text-sm font-semibold text-slate-500">đ</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
            <span className="text-slate-500 dark:text-slate-400">CVR trung bình: {cvr.toFixed(2)}%</span>
            <span className="font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowDownRight className="w-3.5 h-3.5" />
              <span>-8.1% (Tối ưu)</span>
            </span>
          </div>
        </div>

      </div>
    </div>
  );
};
