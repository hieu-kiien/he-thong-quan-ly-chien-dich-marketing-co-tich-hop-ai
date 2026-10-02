import React from 'react';
import { 
  PieChart, 
  ArrowRight, 
} from 'lucide-react';
import { Campaign, KPISummary } from '../../types';
import { AIDoctorWidget } from '../analytics';

interface PerformanceTabProps {
  campaign: Campaign | null;
  campaignKpi: KPISummary | null;
  onOpenCopilot?: () => void;
  onOpenAttribution?: () => void;
}

export const PerformanceTab: React.FC<PerformanceTabProps> = ({
  campaign,
  campaignKpi,
  onOpenCopilot,
  onOpenAttribution,
}) => {
  if (!campaign) {
    return (
      <div className="p-10 text-center text-xs text-slate-500">
        Vui lòng chọn chiến dịch để xem báo cáo hiệu suất và Bác sĩ AI.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Current Live Campaign Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <span className="text-[11px] font-bold uppercase text-slate-400">Lượt hiển thị (Views)</span>
          <p className="text-xl font-black text-slate-900 mt-1">
            {campaignKpi?.total_views ? campaignKpi.total_views.toLocaleString('vi-VN') : '15,700'}
          </p>
          <span className="text-[10px] text-slate-400">Độ phủ toàn chiến dịch</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <span className="text-[11px] font-bold uppercase text-slate-400">Tương tác Click & CTR</span>
          <p className="text-xl font-black text-emerald-600 mt-1">
            {campaignKpi?.total_clicks ? campaignKpi.total_clicks.toLocaleString('vi-VN') : '1,260'} 
            <span className="text-xs text-slate-500 font-semibold ml-1">
              ({campaignKpi?.ctr_percent || 8.0}%)
            </span>
          </p>
          <span className="text-[10px] text-emerald-600 font-medium">CTR trung bình đạt chuẩn</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <span className="text-[11px] font-bold uppercase text-slate-400">Chi phí mỗi Click (CPC)</span>
          <p className="text-xl font-black text-slate-900 mt-1">
            {campaignKpi?.cpc_avg ? Math.round(campaignKpi.cpc_avg).toLocaleString('vi-VN') : '2,500'} đ
          </p>
          <span className="text-[10px] text-slate-400">Mức tối ưu trên kênh</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
          <span className="text-[11px] font-bold uppercase text-slate-400">Tỷ suất sinh lời (ROI)</span>
          <p className="text-xl font-black text-indigo-600 mt-1">
            +{campaignKpi?.roi_percent || 410}%
          </p>
          <span className="text-[10px] text-indigo-600 font-medium">Doanh thu / Chi phí</span>
        </div>
      </div>

      {/* Actionable AI Performance Doctor Widget */}
      <AIDoctorWidget
        campaignId={campaign.id}
        onOpenAIStudio={onOpenCopilot || (() => {})}
      />

      {/* Next Step Guidance: Stage 5 -> Stage 6 Closed Loop */}
      <div className="bg-gradient-to-r from-teal-50 via-emerald-50 to-indigo-50 border border-teal-200 p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="w-9 h-9 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-sm shadow-sm shrink-0 mt-0.5">
            5→6
          </span>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <span>Bước tiếp theo sau khi Bác sĩ AI chẩn đoán</span>
              <span className="bg-teal-100 text-teal-800 text-[10px] px-2 py-0.5 rounded-full font-bold">Closed-Loop</span>
            </h4>
            <p className="text-slate-600 text-xs mt-1 leading-relaxed">
              Dựa trên chẩn đoán của Bác sĩ AI, chuyển sang <strong>Giai đoạn 06: Đóng gói Tri thức & Tối ưu Phân bổ Ngân sách</strong> để thực hiện 1-Click Tối ưu ngân sách kênh và lưu góc bài chiến thắng vào Kho tri thức (Retrospective Vault).
            </p>
          </div>
        </div>
        {onOpenAttribution && (
          <button
            onClick={onOpenAttribution}
            className="px-5 py-2.5 bg-gradient-to-r from-teal-600 to-indigo-600 hover:from-teal-700 hover:to-indigo-700 text-white font-bold rounded-xl text-xs shadow-sm transition-all flex items-center justify-center gap-2 shrink-0 active:scale-95"
          >
            <PieChart className="w-4 h-4" />
            <span>Mở Phân bổ Ngân sách & Kho Tri thức</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
