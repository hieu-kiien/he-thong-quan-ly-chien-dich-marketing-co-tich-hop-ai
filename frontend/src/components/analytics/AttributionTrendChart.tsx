import React, { useState } from 'react';
import { 
  TrendingUp, 
  Coins, 
  Award, 
  BarChart3, 
  Layers, 
  Calendar,
  Sparkles,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';
import { ChannelAttribution } from '../../types';
import { MOCK_CHANNEL_ATTRIBUTIONS } from '../../services/mockData';

interface AttributionTrendChartProps {
  channels?: ChannelAttribution[];
  totalCost?: number;
  totalRevenue?: number;
  className?: string;
}

export const AttributionTrendChart: React.FC<AttributionTrendChartProps> = ({
  channels = MOCK_CHANNEL_ATTRIBUTIONS,
  totalCost = 21500000,
  totalRevenue = 68900000,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState<'cost_revenue' | 'channel_attribution'>('cost_revenue');
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | 'all'>('7d');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Dữ liệu mô phỏng 7 ngày gần nhất theo tỷ lệ thực
  const trendDays = [
    { date: '20/09', cost: 2400000, revenue: 7800000 },
    { date: '21/09', cost: 2800000, revenue: 8900000 },
    { date: '22/09', cost: 3100000, revenue: 10200000 },
    { date: '23/09', cost: 2900000, revenue: 9500000 },
    { date: '24/09', cost: 3400000, revenue: 11200000 },
    { date: '25/09', cost: 3300000, revenue: 10800000 },
    { date: 'Hôm nay', cost: 3600000, revenue: 10500000 },
  ];

  const netProfit = totalRevenue - totalCost;
  const overallRoas = totalCost > 0 ? (totalRevenue / totalCost).toFixed(2) : '0.00';

  // Tính toán tọa độ SVG cho biểu đồ đường xu hướng
  const maxRevenue = Math.max(...trendDays.map(d => d.revenue)) * 1.15;
  const svgWidth = 600;
  const svgHeight = 220;
  const paddingX = 40;
  const paddingY = 25;
  const chartW = svgWidth - paddingX * 2;
  const chartH = svgHeight - paddingY * 2;

  const getCoordinates = (val: number, index: number) => {
    const x = paddingX + (index / (trendDays.length - 1)) * chartW;
    const y = svgHeight - paddingY - (val / maxRevenue) * chartH;
    return { x, y };
  };

  const revenuePoints = trendDays.map((d, i) => getCoordinates(d.revenue, i));
  const costPoints = trendDays.map((d, i) => getCoordinates(d.cost, i));

  const revenuePath = revenuePoints.reduce((acc, curr, i) => 
    i === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`, ''
  );
  const costPath = costPoints.reduce((acc, curr, i) => 
    i === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`, ''
  );

  const revenueArea = `${revenuePath} L ${revenuePoints[revenuePoints.length - 1].x} ${svgHeight - paddingY} L ${revenuePoints[0].x} ${svgHeight - paddingY} Z`;
  const costArea = `${costPath} L ${costPoints[costPoints.length - 1].x} ${svgHeight - paddingY} L ${costPoints[0].x} ${svgHeight - paddingY} Z`;

  return (
    <div className={`bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-xs ${className}`}>
      {/* Top Header: Controls & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100 dark:border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 animate-pulse"></span>
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Phân Tích Xu Hướng & Phân Bổ Đa Kênh
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Tương quan dòng tiền Doanh thu vs Chi phí và hiệu suất 3 kênh Facebook Ads, TikTok Video, Email
          </p>
        </div>

        {/* Tab Switcher & Range Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Tab Selector */}
          <div className="bg-slate-100 dark:bg-slate-800 p-1 rounded-xl flex items-center gap-1 text-xs">
            <button
              onClick={() => setActiveTab('cost_revenue')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 ${
                activeTab === 'cost_revenue'
                  ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Dòng Tiền Chi Phí & Doanh Thu</span>
            </button>
            <button
              onClick={() => setActiveTab('channel_attribution')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 ${
                activeTab === 'channel_attribution'
                  ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Phân Bổ 3 Kênh Tiếp Thị</span>
            </button>
          </div>

          {/* Range Filter */}
          <div className="hidden sm:flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl items-center gap-0.5 text-[11px] font-semibold">
            {(['7d', '30d', 'all'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  timeRange === r 
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs font-bold' 
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {r === '7d' ? '7 ngày' : r === '30d' ? '30 ngày' : 'Tất cả'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* TAB 1: BIỂU ĐỒ DÒNG TIỀN DOANH THU VS CHI PHÍ */}
      {activeTab === 'cost_revenue' && (
        <div className="pt-5 space-y-6">
          {/* Quick Stat Summary Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Tổng Chi Phí (Spend)</span>
              <div className="text-base font-black text-rose-600 dark:text-rose-400 mt-0.5">
                {totalCost.toLocaleString('vi-VN')} đ
              </div>
            </div>
            <div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Tổng Doanh Thu (Revenue)</span>
              <div className="text-base font-black text-emerald-600 dark:text-emerald-400 mt-0.5">
                {totalRevenue.toLocaleString('vi-VN')} đ
              </div>
            </div>
            <div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Lợi Nhuận Ròng (Profit)</span>
              <div className="text-base font-black text-indigo-600 dark:text-indigo-400 mt-0.5">
                +{netProfit.toLocaleString('vi-VN')} đ
              </div>
            </div>
            <div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Điểm Hoàn Vốn ROAS</span>
              <div className="text-base font-black text-slate-900 dark:text-white mt-0.5 flex items-center gap-1.5">
                <span>{overallRoas}x</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-emerald-100 text-emerald-800">Sinh Lời</span>
              </div>
            </div>
          </div>

          {/* SVG Trend Chart */}
          <div className="relative overflow-hidden w-full">
            <svg 
              viewBox={`0 0 ${svgWidth} ${svgHeight}`} 
              className="w-full h-56 select-none"
              preserveAspectRatio="xMidYMid meet"
            >
              <defs>
                <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10B981" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
                </linearGradient>
                <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F43F5E" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#F43F5E" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
                const y = paddingY + pct * chartH;
                return (
                  <line 
                    key={i} 
                    x1={paddingX} 
                    y1={y} 
                    x2={svgWidth - paddingX} 
                    y2={y} 
                    stroke="currentColor" 
                    className="text-slate-100 dark:text-slate-800" 
                    strokeDasharray="4 4" 
                  />
                );
              })}

              {/* Area Fills */}
              <path d={revenueArea} fill="url(#revenueGrad)" />
              <path d={costArea} fill="url(#costGrad)" />

              {/* Line Strokes */}
              <path 
                d={revenuePath} 
                fill="none" 
                stroke="#10B981" 
                strokeWidth="2.5" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
              />
              <path 
                d={costPath} 
                fill="none" 
                stroke="#F43F5E" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeDasharray="6 3"
              />

              {/* Interactive Data Points & Hover Targets */}
              {trendDays.map((d, i) => {
                const rPt = revenuePoints[i];
                const cPt = costPoints[i];
                const isHovered = hoveredIndex === i;

                return (
                  <g key={i}>
                    {/* Hover vertical line */}
                    {isHovered && (
                      <line 
                        x1={rPt.x} 
                        y1={paddingY} 
                        x2={rPt.x} 
                        y2={svgHeight - paddingY} 
                        stroke="#6366F1" 
                        strokeWidth="1.5" 
                        strokeDasharray="3 3" 
                      />
                    )}

                    {/* Revenue point */}
                    <circle 
                      cx={rPt.x} 
                      cy={rPt.y} 
                      r={isHovered ? 5 : 3.5} 
                      fill="#10B981" 
                      stroke="#ffffff" 
                      strokeWidth="2" 
                      className="transition-all"
                    />

                    {/* Cost point */}
                    <circle 
                      cx={cPt.x} 
                      cy={cPt.y} 
                      r={isHovered ? 4.5 : 3} 
                      fill="#F43F5E" 
                      stroke="#ffffff" 
                      strokeWidth="1.5" 
                      className="transition-all"
                    />

                    {/* Transparent Click Target */}
                    <rect 
                      x={rPt.x - 20} 
                      y={paddingY} 
                      width={40} 
                      height={chartH} 
                      fill="transparent" 
                      className="cursor-pointer"
                      onMouseEnter={() => setHoveredIndex(i)}
                      onMouseLeave={() => setHoveredIndex(null)}
                    />

                    {/* X-axis date labels */}
                    <text 
                      x={rPt.x} 
                      y={svgHeight - 6} 
                      textAnchor="middle" 
                      fontSize="10" 
                      fill="currentColor"
                      className="text-slate-400 dark:text-slate-500 font-semibold"
                    >
                      {d.date}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Interactive Tooltip Card */}
            {hoveredIndex !== null && (
              <div 
                className="absolute top-2 bg-slate-900 text-white text-xs p-3 rounded-xl shadow-xl pointer-events-none z-10 space-y-1 transition-all border border-slate-700"
                style={{ 
                  left: `${(hoveredIndex / (trendDays.length - 1)) * 75 + 10}%`,
                  transform: 'translateX(-50%)' 
                }}
              >
                <div className="font-bold text-slate-300 pb-1 border-b border-slate-700 flex items-center justify-between gap-4">
                  <span>Ngày {trendDays[hoveredIndex].date}</span>
                  <span className="text-[10px] text-emerald-400 font-mono">
                    ROAS: {(trendDays[hoveredIndex].revenue / trendDays[hoveredIndex].cost).toFixed(2)}x
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4 text-emerald-400">
                  <span>Doanh thu:</span>
                  <span className="font-bold">{trendDays[hoveredIndex].revenue.toLocaleString('vi-VN')} đ</span>
                </div>
                <div className="flex items-center justify-between gap-4 text-rose-400">
                  <span>Chi phí:</span>
                  <span className="font-bold">{trendDays[hoveredIndex].cost.toLocaleString('vi-VN')} đ</span>
                </div>
                <div className="flex items-center justify-between gap-4 text-indigo-300 pt-1 border-t border-slate-800 font-bold">
                  <span>Lãi ròng:</span>
                  <span>+{(trendDays[hoveredIndex].revenue - trendDays[hoveredIndex].cost).toLocaleString('vi-VN')} đ</span>
                </div>
              </div>
            )}
          </div>

          {/* Chart Legend */}
          <div className="flex items-center justify-center gap-6 text-xs font-semibold text-slate-600 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Đường Doanh Thu (Revenue)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-1.5 rounded-full bg-rose-500 border border-dashed"></span>
              <span>Đường Chi Phí Tiếp Thị (Spend)</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: PHÂN BỔ HIỆU QUẢ 3 KÊNH TIẾP THỊ (FACEBOOK, TIKTOK, EMAIL) */}
      {activeTab === 'channel_attribution' && (
        <div className="pt-5 space-y-6">
          
          {/* Stacked Share Distribution Bars */}
          <div className="space-y-4 bg-slate-50 dark:bg-slate-800/40 p-4.5 rounded-xl border border-slate-200/70 dark:border-slate-800">
            {/* Share of Revenue */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                <span className="flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Tỷ trọng Doanh Thu Đóng Góp (Share of Revenue)</span>
                </span>
                <span className="text-[11px] text-slate-500">TikTok dẫn đầu 51.1%</span>
              </div>
              <div className="h-4 w-full rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex shadow-inner">
                <div style={{ width: '42.7%' }} className="bg-blue-500 h-full" title="Facebook Ads: 42.7%"></div>
                <div style={{ width: '51.1%' }} className="bg-emerald-500 h-full" title="TikTok Video: 51.1%"></div>
                <div style={{ width: '6.2%' }} className="bg-purple-500 h-full" title="Email Marketing: 6.2%"></div>
              </div>
            </div>

            {/* Share of Cost */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                <span className="flex items-center gap-1.5">
                  <Coins className="w-3.5 h-3.5 text-rose-600" />
                  <span>Tỷ trọng Chi Phí Phân Bổ (Share of Cost)</span>
                </span>
                <span className="text-[11px] text-slate-500">Facebook 44.2% • TikTok 40.9% • Email 14.9%</span>
              </div>
              <div className="h-4 w-full rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex shadow-inner">
                <div style={{ width: '44.2%' }} className="bg-blue-400 h-full" title="Facebook Ads: 44.2%"></div>
                <div style={{ width: '40.9%' }} className="bg-emerald-400 h-full" title="TikTok Video: 40.9%"></div>
                <div style={{ width: '14.9%' }} className="bg-purple-400 h-full" title="Email Marketing: 14.9%"></div>
              </div>
            </div>
          </div>

          {/* Channel Attribution Breakdown Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {channels.map((ch) => {
              const isTikTok = ch.channel_slug?.includes('tiktok') || ch.channel_name.toLowerCase().includes('tiktok');
              const isFacebook = ch.channel_slug?.includes('facebook') || ch.channel_name.toLowerCase().includes('facebook');

              const badgeColor = isTikTok
                ? 'bg-amber-100 text-amber-800 border-amber-300'
                : isFacebook
                ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                : 'bg-rose-100 text-rose-800 border-rose-300';

              const badgeText = isTikTok
                ? '⭐ Ngôi Sao Sinh Lời'
                : isFacebook
                ? '🚀 Kênh Phủ Rộng'
                : '⚠️ Cần Tối Ưu Tiêu Đề';

              return (
                <div 
                  key={ch.channel_id} 
                  className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4.5 space-y-3.5 shadow-xs hover:shadow-md transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-sm text-slate-900 dark:text-white">{ch.channel_name}</h4>
                      <span className="text-[11px] text-slate-400">
                        {ch.views.toLocaleString('vi-VN')} views • {ch.clicks.toLocaleString('vi-VN')} clicks
                      </span>
                    </div>
                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${badgeColor}`}>
                      {badgeText}
                    </span>
                  </div>

                  {/* Financial Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800">
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-bold">Chi Phí</span>
                      <p className="font-bold text-slate-800 dark:text-slate-200">{ch.cost.toLocaleString('vi-VN')} đ</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-bold">Doanh Thu</span>
                      <p className="font-bold text-emerald-600 dark:text-emerald-400">{ch.revenue.toLocaleString('vi-VN')} đ</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-bold">ROAS Hoàn Vốn</span>
                      <p className="font-black text-indigo-600 text-sm">{ch.roas.toFixed(2)}x</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-bold">Tỷ Suất ROI</span>
                      <p className="font-bold text-slate-800 dark:text-slate-200">+{ch.roi_percent.toFixed(1)}%</p>
                    </div>
                  </div>

                  {/* Operational Metrics */}
                  <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-100 dark:border-slate-800">
                    <span>CTR: <strong className="text-slate-800 dark:text-slate-200">{ch.ctr_percent}%</strong></span>
                    <span>CPC: <strong className="text-slate-800 dark:text-slate-200">{Math.round(ch.cpc_avg).toLocaleString('vi-VN')} đ</strong></span>
                    <span>CVR: <strong className="text-slate-800 dark:text-slate-200">{ch.cvr_percent}%</strong></span>
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      )}
    </div>
  );
};
