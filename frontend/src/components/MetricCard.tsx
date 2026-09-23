import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtext: string;
  trend?: number; // Ví dụ: +12.5%
  trendLabel?: string;
  sparklineColor?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtext,
  trend = 12.5,
  trendLabel = 'so với tháng trước',
  sparklineColor = '#22C55E'
}) => {
  const isPositive = trend >= 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:shadow-md transition-shadow relative overflow-hidden flex flex-col justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">{title}</p>
        <div className="flex items-baseline gap-2">
          <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight">{value}</h3>
          {trend !== undefined && (
            <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-md flex items-center gap-0.5 ${
              isPositive 
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60' 
                : 'bg-rose-50 text-rose-700 border border-rose-200/60'
            }`}>
              {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {isPositive ? `+${trend}%` : `${trend}%`}
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-end justify-between">
        <p className="text-xs text-slate-400 font-medium">{subtext} • {trendLabel}</p>
        {/* Mini SVG Sparkline */}
        <div className="w-20 h-7 shrink-0">
          <svg viewBox="0 0 100 35" className="w-full h-full overflow-visible">
            <path
              d="M0,28 Q15,5 30,20 T60,10 T85,18 T100,5"
              fill="none"
              stroke={sparklineColor}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};
