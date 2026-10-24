import React from 'react';
import { BarChart2, ArrowUpRight, ThumbsUp, Mail, ExternalLink, FileText, Download, Video } from 'lucide-react';
import { Campaign, KPISummary } from '../types';

interface ChannelROIComparisonProps {
  campaign: Campaign;
  kpi: KPISummary | null;
}

export const ChannelROIComparison: React.FC<ChannelROIComparisonProps> = ({
  campaign,
  kpi
}) => {
  const totalBudget = Number(campaign.budget) || 0;
  const channelMetrics = kpi?.channel_metrics || [];
  const allocationsByChannelId = new Map<number, number>();
  const rawAllocations: Array<{ channel_id: number; planned_amount?: number }> =
    (campaign as any).channel_allocations ||
    (campaign as any).campaign_channels ||
    [];
  for (const alloc of rawAllocations) {
    allocationsByChannelId.set(Number(alloc.channel_id), Number((alloc as any).planned_amount) || 0);
  }

  const hasRealKpi =
    channelMetrics.length > 0 &&
    channelMetrics.some(
      (ch) => Number(ch.cost) > 0 || Number(ch.revenue) > 0 || Number(ch.clicks) > 0 || Number(ch.views) > 0
    );

  const getChannelVisual = (nameOrCode: string) => {
    const key = (nameOrCode || '').toLowerCase();
    if (key.includes('facebook') || key.includes('meta')) {
      return { icon: ThumbsUp, color: 'text-blue-600 bg-blue-50 border-blue-200' };
    }
    if (key.includes('tiktok')) {
      return { icon: Video, color: 'text-rose-600 bg-rose-50 border-rose-200' };
    }
    if (key.includes('google')) {
      return { icon: ExternalLink, color: 'text-amber-600 bg-amber-50 border-amber-200' };
    }
    if (key.includes('email') || key.includes('zalo') || key.includes('crm')) {
      return { icon: Mail, color: 'text-purple-600 bg-purple-50 border-purple-200' };
    }
    return { icon: FileText, color: 'text-emerald-600 bg-emerald-50 border-emerald-200' };
  };

  return (
    <div className="space-y-6">
      {!hasRealKpi ? (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-8 text-center">
          <p className="text-sm font-semibold text-slate-700">Chưa có dữ liệu KPI thực tế theo từng kênh.</p>
          <p className="text-xs text-slate-500 mt-1">
            Khi chiến dịch ghi nhận chi phí, lượt nhấp hoặc doanh thu thực tế theo kênh, bảng đối chiếu ROI sẽ hiển thị tại đây.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-indigo-600" />
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Bảng So Sánh Hiệu Quả &amp; Ngân Sách Thực Tế Theo Kênh
              </h4>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-slate-500">
                Tổng ngân sách chiến dịch: <strong>{totalBudget.toLocaleString('vi-VN')} VNĐ</strong>
              </span>
              <button
                type="button"
                onClick={() => window.print()}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors flex items-center gap-1.5 no-print cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                <span>In / Lưu PDF</span>
              </button>
            </div>
          </div>

          <div
            className="overflow-x-auto"
            role="region"
            aria-label="Bảng so sánh ROI theo kênh tiếp thị"
            tabIndex={0}
          >
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-semibold text-[11px]">
                <tr>
                  <th className="py-3 px-4">Kênh tiếp thị</th>
                  <th className="py-3 px-4 text-right">Ngân sách phân bổ</th>
                  <th className="py-3 px-4 text-right">Đã chi (Spent)</th>
                  <th className="py-3 px-4 text-right">Lượt click (CTR)</th>
                  <th className="py-3 px-4 text-right">Đơn hàng</th>
                  <th className="py-3 px-4 text-right">Doanh thu thực tế</th>
                  <th className="py-3 px-4 text-right">ROAS / ROI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {channelMetrics.map((ch) => {
                  const visual = getChannelVisual(ch.channel_code || ch.channel_slug || ch.channel_name);
                  const Icon = visual.icon;
                  const allocated = allocationsByChannelId.get(Number(ch.channel_id)) || 0;
                  const cost = Number(ch.cost) || 0;
                  const revenue = Number(ch.revenue) || 0;
                  const clicks = Number(ch.clicks) || 0;
                  const conversions = Number(ch.conversions) || 0;
                  const ctr = ch.ctr_percent != null ? Number(ch.ctr_percent) : null;
                  const roi = cost > 0 ? Math.round(((revenue - cost) / cost) * 100) : null;
                  const roas = cost > 0 ? (revenue / cost).toFixed(2) : null;

                  return (
                    <tr key={ch.channel_id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-slate-800">
                        <div className="flex items-center gap-2">
                          <span className={`w-7 h-7 rounded-lg border flex items-center justify-center ${visual.color}`}>
                            <Icon className="w-3.5 h-3.5" />
                          </span>
                          <span>{ch.channel_name}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right font-medium text-slate-700 tabular-nums">
                        {allocated > 0 ? `${allocated.toLocaleString('vi-VN')} đ` : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-right font-medium text-slate-600 tabular-nums">
                        {cost.toLocaleString('vi-VN')} đ
                      </td>
                      <td className="py-3.5 px-4 text-right tabular-nums">
                        <span className="font-semibold text-slate-800">{clicks.toLocaleString('vi-VN')}</span>
                        <span className="block text-[10px] text-emerald-600 font-medium">
                          {ctr != null ? `CTR: ${ctr}%` : 'CTR: —'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-semibold text-slate-800 tabular-nums">
                        {conversions.toLocaleString('vi-VN')}
                      </td>
                      <td className="py-3.5 px-4 text-right font-bold text-slate-900 tabular-nums">
                        {revenue.toLocaleString('vi-VN')} đ
                      </td>
                      <td className="py-3.5 px-4 text-right tabular-nums">
                        {roi != null ? (
                          <div>
                            <span
                              className={`inline-flex items-center gap-0.5 font-bold ${
                                roi >= 100 ? 'text-emerald-600' : roi >= 0 ? 'text-indigo-600' : 'text-rose-600'
                              }`}
                            >
                              <ArrowUpRight className="w-3.5 h-3.5" />
                              {roi >= 0 ? `+${roi}%` : `${roi}%`}
                            </span>
                            {roas && (
                              <span className="block text-[10px] text-slate-500">ROAS {roas}x</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 font-medium">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
