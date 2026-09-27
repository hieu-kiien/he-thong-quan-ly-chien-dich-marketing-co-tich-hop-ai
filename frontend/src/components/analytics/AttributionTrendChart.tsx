import React, { useState, useEffect, useMemo } from 'react';
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
  CheckCircle2,
  Loader2,
  Inbox
} from 'lucide-react';
import { ChannelAttribution } from '../../types';
import { metricsApi, analyticsApi } from '../../services/api';

export interface DailyMetricPoint {
  date: string;
  cost: number;
  revenue: number;
}

export interface AttributionTrendChartProps {
  channels?: ChannelAttribution[];
  totalCost?: number;
  totalRevenue?: number;
  campaignId?: number;
  dailyMetrics?: DailyMetricPoint[];
  className?: string;
}

export const AttributionTrendChart: React.FC<AttributionTrendChartProps> = ({
  channels: propChannels,
  totalCost: propTotalCost,
  totalRevenue: propTotalRevenue,
  campaignId,
  dailyMetrics: propDailyMetrics,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState<'cost_revenue' | 'channel_attribution'>('cost_revenue');
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | 'all'>('7d');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Dynamic state for daily data and channels
  const [dynamicDailyMetrics, setDynamicDailyMetrics] = useState<DailyMetricPoint[]>([]);
  const [dynamicChannels, setDynamicChannels] = useState<ChannelAttribution[]>(propChannels || []);
  const [loading, setLoading] = useState<boolean>(!propDailyMetrics);

  useEffect(() => {
    if (propChannels && propChannels.length > 0) {
      setDynamicChannels(propChannels);
    }
  }, [propChannels]);

  useEffect(() => {
    if (propDailyMetrics && propDailyMetrics.length > 0) {
      setDynamicDailyMetrics(propDailyMetrics);
      setLoading(false);
      return;
    }

    let isMounted = true;
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        let rawMetrics: any[] = [];

        if (campaignId) {
          const [metricsData, attrData] = await Promise.all([
            metricsApi.getCampaignMetrics(campaignId).catch(() => []),
            (!propChannels || propChannels.length === 0)
              ? metricsApi.getCampaignAttribution(campaignId).catch(() => [])
              : Promise.resolve([])
          ]);
          rawMetrics = metricsData;
          if (isMounted && attrData && attrData.length > 0) {
            setDynamicChannels(attrData);
          }
        } else {
          // Global dashboard metrics overview
          const [allMetrics, dashboardData] = await Promise.all([
            metricsApi.getAllCampaignsMetrics().catch(() => []),
            (!propChannels || propChannels.length === 0)
              ? analyticsApi.getDashboard().catch(() => null)
              : Promise.resolve(null)
          ]);
          rawMetrics = allMetrics;
          if (isMounted && dashboardData?.channel_attributions && dashboardData.channel_attributions.length > 0) {
            setDynamicChannels(dashboardData.channel_attributions);
          }
        }

        if (!isMounted) return;

        if (rawMetrics && rawMetrics.length > 0) {
          // Aggregate by metric_date
          const dateMap = new Map<string, { cost: number; revenue: number }>();
          rawMetrics.forEach((m: any) => {
            const rawDate = m.metric_date || m.date || 'Hôm nay';
            const existing = dateMap.get(rawDate) || { cost: 0, revenue: 0 };
            existing.cost += Number(m.cost) || 0;
            existing.revenue += Number(m.revenue) || 0;
            dateMap.set(rawDate, existing);
          });

          // Sort chronologically
          const sortedDates = Array.from(dateMap.keys()).sort();
          const points: DailyMetricPoint[] = sortedDates.map((dStr) => {
            const item = dateMap.get(dStr)!;
            let formattedDate = dStr;
            if (dStr.includes('-')) {
              const parts = dStr.split('-');
              if (parts.length === 3) {
                formattedDate = `${parts[2]}/${parts[1]}`;
              }
            }
            return {
              date: formattedDate,
              cost: Math.round(item.cost),
              revenue: Math.round(item.revenue)
            };
          });

          setDynamicDailyMetrics(points);
        } else {
          setDynamicDailyMetrics([]);
        }
      } catch (err) {
        if (isMounted) setDynamicDailyMetrics([]);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchMetrics();
    return () => {
      isMounted = false;
    };
  }, [campaignId, propDailyMetrics]);

  // Filter trend days by selected time range
  const filteredTrendDays = useMemo(() => {
    if (dynamicDailyMetrics.length === 0) return [];
    if (timeRange === '7d') return dynamicDailyMetrics.slice(-7);
    if (timeRange === '30d') return dynamicDailyMetrics.slice(-30);
    return dynamicDailyMetrics;
  }, [dynamicDailyMetrics, timeRange]);

  const activeChannels = dynamicChannels.length > 0 ? dynamicChannels : (propChannels || []);

  // Aggregated totals
  const totalCost = propTotalCost !== undefined
    ? propTotalCost
    : filteredTrendDays.reduce((acc, d) => acc + d.cost, 0);

  const totalRevenue = propTotalRevenue !== undefined
    ? propTotalRevenue
    : filteredTrendDays.reduce((acc, d) => acc + d.revenue, 0);

  const netProfit = totalRevenue - totalCost;
  const overallRoas = totalCost > 0 ? (totalRevenue / totalCost).toFixed(2) : '0.00';

  // Coordinate calculations for SVG line graph
  const displayDays = useMemo(() => {
    if (filteredTrendDays.length === 0) return [];
    if (filteredTrendDays.length === 1) {
      return [
        { ...filteredTrendDays[0], date: 'Bắt đầu' },
        filteredTrendDays[0]
      ];
    }
    return filteredTrendDays;
  }, [filteredTrendDays]);

  const maxVal = useMemo(() => {
    if (displayDays.length === 0) return 1000000;
    const highest = Math.max(...displayDays.map(d => Math.max(d.revenue, d.cost)));
    return highest > 0 ? highest * 1.15 : 1000000;
  }, [displayDays]);

  const svgWidth = 600;
  const svgHeight = 220;
  const paddingX = 40;
  const paddingY = 25;
  const chartW = svgWidth - paddingX * 2;
  const chartH = svgHeight - paddingY * 2;

  const getCoordinates = (val: number, index: number) => {
    const divisor = displayDays.length > 1 ? displayDays.length - 1 : 1;
    const x = paddingX + (index / divisor) * chartW;
    const y = svgHeight - paddingY - (val / maxVal) * chartH;
    return { x, y };
  };

  const revenuePoints = displayDays.map((d, i) => getCoordinates(d.revenue, i));
  const costPoints = displayDays.map((d, i) => getCoordinates(d.cost, i));

  const revenuePath = revenuePoints.reduce((acc, curr, i) => 
    i === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`, ''
  );
  const costPath = costPoints.reduce((acc, curr, i) => 
    i === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`, ''
  );

  const revenueArea = revenuePoints.length > 0 
    ? `${revenuePath} L ${revenuePoints[revenuePoints.length - 1].x} ${svgHeight - paddingY} L ${revenuePoints[0].x} ${svgHeight - paddingY} Z`
    : '';
  const costArea = costPoints.length > 0 
    ? `${costPath} L ${costPoints[costPoints.length - 1].x} ${svgHeight - paddingY} L ${costPoints[0].x} ${svgHeight - paddingY} Z`
    : '';

  // Channel percentages dynamic calculation
  const totalChanRevenue = activeChannels.reduce((sum, ch) => sum + (ch.revenue || 0), 0);
  const totalChanCost = activeChannels.reduce((sum, ch) => sum + (ch.cost || 0), 0);

  const sortedChannels = [...activeChannels].sort((a, b) => (b.revenue || 0) - (a.revenue || 0));
  const leadChannel = sortedChannels[0];
  const leadRevenuePct = totalChanRevenue > 0 && leadChannel
    ? ((leadChannel.revenue / totalChanRevenue) * 100).toFixed(1)
    : '0.0';

  const channelColors = [
    { barRev: 'bg-blue-600', barCost: 'bg-blue-500' },
    { barRev: 'bg-emerald-600', barCost: 'bg-emerald-500' },
    { barRev: 'bg-purple-600', barCost: 'bg-purple-500' },
    { barRev: 'bg-amber-600', barCost: 'bg-amber-500' },
    { barRev: 'bg-rose-600', barCost: 'bg-rose-500' }
  ];

  return (
    <div className={`bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-xs ${className}`}>
      {/* Top Header: Controls & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100 dark:border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 animate-pulse" aria-hidden="true"></span>
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Phân Tích Xu Hướng & Phân Bổ Đa Kênh
            </h3>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Tương quan dòng tiền Doanh thu vs Chi phí và hiệu suất phân bổ đa kênh thời gian thực
          </p>
        </div>

        {/* Tab Switcher & Range Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Tab Selector */}
          <div className="bg-slate-100 dark:bg-slate-800 p-1 rounded-xl flex items-center gap-1 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('cost_revenue')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 ${
                activeTab === 'cost_revenue'
                  ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Dòng Tiền Chi Phí & Doanh Thu</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('channel_attribution')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 ${
                activeTab === 'channel_attribution'
                  ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Phân Bổ Kênh Tiếp Thị</span>
            </button>
          </div>

          {/* Range Filter */}
          <div className="hidden sm:flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl items-center gap-0.5 text-[11px] font-semibold">
            {(['7d', '30d', 'all'] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setTimeRange(r)}
                className={`px-2.5 py-1 rounded-lg transition-all focus:outline-hidden focus:ring-2 focus:ring-indigo-500 ${
                  timeRange === r 
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs font-bold' 
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                {r === '7d' ? '7 ngày' : r === '30d' ? '30 ngày' : 'Tất cả'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="py-16 text-center flex flex-col items-center justify-center gap-3 text-slate-600 dark:text-slate-400">
          <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
          <p className="text-xs font-semibold">Đang tổng hợp dữ liệu phân bổ từ máy chủ...</p>
        </div>
      ) : activeTab === 'cost_revenue' ? (
        /* TAB 1: BIỂU ĐỒ DÒNG TIỀN DOANH THU VS CHI PHÍ */
        <div className="pt-5 space-y-6">
          {/* Quick Stat Summary Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <div>
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Tổng Chi Phí (Spend)</span>
              <div className="text-base font-black text-rose-700 dark:text-rose-400 mt-0.5">
                {totalCost.toLocaleString('vi-VN')} đ
              </div>
            </div>
            <div>
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Tổng Doanh Thu (Revenue)</span>
              <div className="text-base font-black text-emerald-700 dark:text-emerald-400 mt-0.5">
                {totalRevenue.toLocaleString('vi-VN')} đ
              </div>
            </div>
            <div>
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Lợi Nhuận Ròng (Profit)</span>
              <div className="text-base font-black text-indigo-700 dark:text-indigo-400 mt-0.5">
                {netProfit >= 0 ? `+${netProfit.toLocaleString('vi-VN')}` : `${netProfit.toLocaleString('vi-VN')}`} đ
              </div>
            </div>
            <div>
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Điểm Hoàn Vốn ROAS</span>
              <div className="text-base font-black text-slate-900 dark:text-white mt-0.5 flex items-center gap-1.5">
                <span>{overallRoas}x</span>
                {Number(overallRoas) >= 1 ? (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-emerald-100 text-emerald-800">Sinh Lời</span>
                ) : (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-rose-100 text-rose-800">Cần Tối Ưu</span>
                )}
              </div>
            </div>
          </div>

          {/* SVG Trend Chart or Empty State */}
          {displayDays.length === 0 ? (
            <div className="py-12 px-4 text-center space-y-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-dashed border-slate-200 dark:border-slate-700">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto">
                <BarChart3 className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                  Chưa có Dữ liệu Xu hướng Dòng tiền
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                  Hệ thống chưa ghi nhận chỉ số hiệu suất hàng ngày cho chiến dịch. Khi chiến dịch bắt đầu phân phối và ghi nhận chi phí/doanh thu, biểu đồ đường sẽ tự động cập nhật.
                </p>
              </div>
            </div>
          ) : (
            <div className="relative overflow-hidden w-full">
              <svg 
                viewBox={`0 0 ${svgWidth} ${svgHeight}`} 
                className="w-full h-56 select-none"
                preserveAspectRatio="xMidYMid meet"
                role="img"
                aria-label="Biểu đồ phân tích dòng tiền doanh thu và chi phí tiếp thị theo thời gian"
              >
                <defs>
                  <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#047857" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#047857" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#BE123C" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#BE123C" stopOpacity="0.0" />
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
                  stroke="#047857" 
                  strokeWidth="2.5" 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                />
                <path 
                  d={costPath} 
                  fill="none" 
                  stroke="#BE123C" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeDasharray="6 3"
                />

                {/* Interactive Data Points & Hover Targets */}
                {displayDays.map((d, i) => {
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
                          stroke="#4338CA" 
                          strokeWidth="1.5" 
                          strokeDasharray="3 3" 
                        />
                      )}

                      {/* Revenue point */}
                      <circle 
                        cx={rPt.x} 
                        cy={rPt.y} 
                        r={isHovered ? 5 : 3.5} 
                        fill="#047857" 
                        stroke="#ffffff" 
                        strokeWidth="2" 
                        className="transition-all"
                      />

                      {/* Cost point */}
                      <circle 
                        cx={cPt.x} 
                        cy={cPt.y} 
                        r={isHovered ? 4.5 : 3} 
                        fill="#BE123C" 
                        stroke="#ffffff" 
                        strokeWidth="1.5" 
                        className="transition-all"
                      />

                      {/* Interactive Focusable Target */}
                      <rect 
                        x={rPt.x - 20} 
                        y={paddingY} 
                        width={40} 
                        height={chartH} 
                        fill="transparent" 
                        className="cursor-pointer focus:outline-hidden"
                        tabIndex={0}
                        aria-label={`Ngày ${d.date}: Doanh thu ${d.revenue.toLocaleString('vi-VN')} đ, Chi phí ${d.cost.toLocaleString('vi-VN')} đ`}
                        onMouseEnter={() => setHoveredIndex(i)}
                        onMouseLeave={() => setHoveredIndex(null)}
                        onFocus={() => setHoveredIndex(i)}
                        onBlur={() => setHoveredIndex(null)}
                      />

                      {/* X-axis date labels */}
                      <text 
                        x={rPt.x} 
                        y={svgHeight - 6} 
                        textAnchor="middle" 
                        fontSize="10" 
                        fill="currentColor"
                        className="text-slate-600 dark:text-slate-400 font-semibold"
                      >
                        {d.date}
                      </text>
                    </g>
                  );
                })}
              </svg>

              {/* Interactive Tooltip Card */}
              {hoveredIndex !== null && displayDays[hoveredIndex] && (
                <div 
                  role="tooltip"
                  className="absolute top-2 bg-slate-900 text-white text-xs p-3 rounded-xl shadow-xl pointer-events-none z-10 space-y-1 transition-all border border-slate-700"
                  style={{ 
                    left: `${(hoveredIndex / (displayDays.length - 1 || 1)) * 75 + 10}%`,
                    transform: 'translateX(-50%)' 
                  }}
                >
                  <div className="font-bold text-slate-300 pb-1 border-b border-slate-700 flex items-center justify-between gap-4">
                    <span>Ngày {displayDays[hoveredIndex].date}</span>
                    <span className="text-[10px] text-emerald-400 font-mono font-bold">
                      ROAS: {displayDays[hoveredIndex].cost > 0 
                        ? (displayDays[hoveredIndex].revenue / displayDays[hoveredIndex].cost).toFixed(2) 
                        : '0.00'}x
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-emerald-400 font-medium">
                    <span>Doanh thu:</span>
                    <span className="font-bold">{displayDays[hoveredIndex].revenue.toLocaleString('vi-VN')} đ</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-rose-400 font-medium">
                    <span>Chi phí:</span>
                    <span className="font-bold">{displayDays[hoveredIndex].cost.toLocaleString('vi-VN')} đ</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-indigo-300 pt-1 border-t border-slate-800 font-bold">
                    <span>Lãi ròng:</span>
                    <span>
                      {displayDays[hoveredIndex].revenue - displayDays[hoveredIndex].cost >= 0 ? '+' : ''}
                      {(displayDays[hoveredIndex].revenue - displayDays[hoveredIndex].cost).toLocaleString('vi-VN')} đ
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Chart Legend */}
          <div className="flex items-center justify-center gap-6 text-xs font-semibold text-slate-700 dark:text-slate-300 pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-1.5 rounded-full bg-emerald-700" aria-hidden="true"></span>
              <span>Đường Doanh Thu (Revenue)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-1.5 rounded-full bg-rose-700 border border-dashed" aria-hidden="true"></span>
              <span>Đường Chi Phí Tiếp Thị (Spend)</span>
            </div>
          </div>
        </div>
      ) : (
        /* TAB 2: PHÂN BỔ HIỆU QUẢ CÁC KÊNH TIẾP THỊ */
        <div className="pt-5 space-y-6">
          {activeChannels.length === 0 ? (
            <div className="py-12 px-4 text-center space-y-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-dashed border-slate-200 dark:border-slate-700">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto">
                <Layers className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                  Chưa có Dữ liệu Kênh Phân bổ
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                  Hệ thống chưa ghi nhận số liệu phân rã theo kênh (Facebook, TikTok, Email) cho chiến dịch.
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Stacked Share Distribution Bars */}
              <div className="space-y-4 bg-slate-50 dark:bg-slate-800/40 p-4.5 rounded-xl border border-slate-200/70 dark:border-slate-800">
                {/* Share of Revenue */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <TrendingUp className="w-3.5 h-3.5 text-emerald-700" />
                      <span>Tỷ trọng Doanh Thu Đóng Góp (Share of Revenue)</span>
                    </span>
                    <span className="text-[11px] text-slate-600 dark:text-slate-400">
                      {leadChannel ? `${leadChannel.channel_name} dẫn đầu ${leadRevenuePct}%` : 'Đang đồng bộ...'}
                    </span>
                  </div>
                  <div className="h-4 w-full rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex shadow-inner">
                    {activeChannels.map((ch, idx) => {
                      const pct = totalChanRevenue > 0 ? (ch.revenue / totalChanRevenue) * 100 : 0;
                      if (pct <= 0) return null;
                      const col = channelColors[idx % channelColors.length].barRev;
                      return (
                        <div 
                          key={ch.channel_id || idx} 
                          style={{ width: `${pct}%` }} 
                          className={`${col} h-full transition-all duration-300`} 
                          title={`${ch.channel_name}: ${pct.toFixed(1)}% (${ch.revenue.toLocaleString('vi-VN')} đ)`}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Share of Cost */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <Coins className="w-3.5 h-3.5 text-rose-700" />
                      <span>Tỷ trọng Chi Phí Phân Bổ (Share of Cost)</span>
                    </span>
                    <span className="text-[11px] text-slate-600 dark:text-slate-400 truncate max-w-xs sm:max-w-md">
                      {activeChannels.map(ch => {
                        const pct = totalChanCost > 0 ? ((ch.cost / totalChanCost) * 100).toFixed(1) : '0.0';
                        return `${ch.channel_name} ${pct}%`;
                      }).join(' • ')}
                    </span>
                  </div>
                  <div className="h-4 w-full rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex shadow-inner">
                    {activeChannels.map((ch, idx) => {
                      const pct = totalChanCost > 0 ? (ch.cost / totalChanCost) * 100 : 0;
                      if (pct <= 0) return null;
                      const col = channelColors[idx % channelColors.length].barCost;
                      return (
                        <div 
                          key={ch.channel_id || idx} 
                          style={{ width: `${pct}%` }} 
                          className={`${col} h-full transition-all duration-300`} 
                          title={`${ch.channel_name}: ${pct.toFixed(1)}% (${ch.cost.toLocaleString('vi-VN')} đ)`}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Channel Attribution Breakdown Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {activeChannels.map((ch) => {
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
                          <span className="text-[11px] text-slate-600 dark:text-slate-400">
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
                          <span className="text-[10px] text-slate-600 dark:text-slate-400 uppercase font-bold">Chi Phí</span>
                          <p className="font-bold text-slate-900 dark:text-slate-200">{ch.cost.toLocaleString('vi-VN')} đ</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-600 dark:text-slate-400 uppercase font-bold">Doanh Thu</span>
                          <p className="font-bold text-emerald-700 dark:text-emerald-400">{ch.revenue.toLocaleString('vi-VN')} đ</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-600 dark:text-slate-400 uppercase font-bold">ROAS Hoàn Vốn</span>
                          <p className="font-black text-indigo-700 dark:text-indigo-400 text-sm">{ch.roas.toFixed(2)}x</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-600 dark:text-slate-400 uppercase font-bold">Tỷ Suất ROI</span>
                          <p className="font-bold text-slate-900 dark:text-slate-200">+{ch.roi_percent.toFixed(1)}%</p>
                        </div>
                      </div>

                      {/* Operational Metrics */}
                      <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 pt-1 border-t border-slate-100 dark:border-slate-800">
                        <span>CTR: <strong className="text-slate-900 dark:text-slate-200">{ch.ctr_percent}%</strong></span>
                        <span>CPC: <strong className="text-slate-900 dark:text-slate-200">{Math.round(ch.cpc_avg).toLocaleString('vi-VN')} đ</strong></span>
                        <span>CVR: <strong className="text-slate-900 dark:text-slate-200">{ch.cvr_percent}%</strong></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
