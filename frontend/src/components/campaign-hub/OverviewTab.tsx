import React from 'react';
import { 
  Target, 
  FileText, 
  ArrowRight, 
  BarChart3, 
  DollarSign, 
  Save, 
  Edit3 
} from 'lucide-react';
import { Campaign, KPISummary, KpiProgress } from '../../types';
import { AdAccountsHub } from '../AdAccountsHub';

interface OverviewTabProps {
  campaign: Campaign | null;
  campaignKpi: KPISummary | null;
  kpiProgress?: KpiProgress | null;
  isEditingBrief: boolean;
  setIsEditingBrief: (val: boolean) => void;
  briefKeyMessage: string;
  setBriefKeyMessage: (val: string) => void;
  briefPrimaryCta: string;
  setBriefPrimaryCta: (val: string) => void;
  briefTargetKpiName: string;
  setBriefTargetKpiName: (val: string) => void;
  briefTargetKpiValue: number;
  setBriefTargetKpiValue: (val: number) => void;
  isSavingBrief: boolean;
  handleSaveBrief: () => void;
  channelAllocations: { channel_id: number; planned_amount: number; name: string }[];
  setChannelAllocations: React.Dispatch<React.SetStateAction<{ channel_id: number; planned_amount: number; name: string }[]>>;
  isEditingBudget: boolean;
  setIsEditingBudget: (val: boolean) => void;
  handleSaveBudgetAllocations: () => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  campaign,
  campaignKpi,
  kpiProgress,
  isEditingBrief,
  setIsEditingBrief,
  briefKeyMessage,
  setBriefKeyMessage,
  briefPrimaryCta,
  setBriefPrimaryCta,
  briefTargetKpiName,
  setBriefTargetKpiName,
  briefTargetKpiValue,
  setBriefTargetKpiValue,
  isSavingBrief,
  handleSaveBrief,
  channelAllocations,
  setChannelAllocations,
  isEditingBudget,
  setIsEditingBudget,
  handleSaveBudgetAllocations,
}) => {
  return (
    <div className="space-y-6">
      {/* Header Action Bar */}
      <div className="bg-white p-5 rounded-xl border border-[#E4E2DD] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-lg bg-[#F6F5F0] text-[#D95D39] border border-[#E4E2DD]">
              <Target className="w-5 h-5" />
            </span>
            <div>
              <h3 className="text-base font-extrabold text-[#121316]">Đề bài &amp; Mục tiêu vận hành chiến dịch</h3>
              <p className="text-xs text-[#3B3F46] mt-0.5">
                Thông điệp định hướng nội dung cốt lõi, lời kêu gọi hành động (CTA) và chỉ tiêu định lượng.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isEditingBrief ? (
            <>
              <button
                onClick={() => {
                  setIsEditingBrief(false);
                  setBriefKeyMessage(campaign?.key_message || '');
                  setBriefPrimaryCta(campaign?.primary_cta || '');
                  setBriefTargetKpiName(campaign?.target_kpi_name || '');
                  setBriefTargetKpiValue(campaign?.target_kpi_value || 0);
                }}
                className="px-3.5 py-1.5 rounded-lg border border-[#D0CEC7] text-xs font-semibold text-[#3B3F46] hover:bg-[#F6F5F0] transition-colors"
              >
                Hủy
              </button>
              <button
                onClick={handleSaveBrief}
                disabled={isSavingBrief}
                className="px-4 py-1.5 rounded-lg bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-60"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{isSavingBrief ? 'Đang lưu...' : 'Lưu thay đổi'}</span>
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditingBrief(true)}
              className="px-4 py-1.5 rounded-lg border border-[#D0CEC7] bg-[#F6F5F0] text-[#121316] hover:bg-[#EAE8E1] text-xs font-bold transition-colors flex items-center gap-1.5"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Chỉnh sửa đề bài</span>
            </button>
          )}
        </div>
      </div>

      {/* 2-Column Grid: Strategic Message & Quantified KPI Target */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Box 1: Core Message & CTA */}
        <div className="bg-white p-5 rounded-xl border border-[#E4E2DD] space-y-4">
          <div className="flex items-center justify-between border-b border-[#F0EFEA] pb-3">
            <span className="text-xs font-extrabold text-[#121316] uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#D95D39]" />
              Thông điệp cốt lõi &amp; Kêu gọi hành động
            </span>
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-[#F6F5F0] text-[#3B3F46] border border-[#E4E2DD]">
              Thông điệp thương hiệu
            </span>
          </div>

          <div>
            <label className="block text-xs font-bold text-[#3B3F46] mb-1.5">
              Thông điệp chủ đạo (Key Message)
            </label>
            {isEditingBrief ? (
              <textarea
                rows={3}
                value={briefKeyMessage}
                onChange={(e) => setBriefKeyMessage(e.target.value)}
                placeholder="Ví dụ: Giảm giá 30% cho 100 khách hàng đầu tiên đăng ký dùng thử phần mềm trong tháng 10..."
                className="w-full text-xs p-3 rounded-xl border border-[#D0CEC7] focus:outline-none focus:border-[#121316] text-[#121316]"
              />
            ) : (
              <div className="p-3.5 bg-[#F6F5F0] rounded-xl border border-[#E4E2DD] text-xs text-[#121316] leading-relaxed font-medium min-h-[72px] flex items-center">
                {campaign?.key_message || briefKeyMessage ? (
                  <span className="italic">&ldquo;{campaign?.key_message || briefKeyMessage}&rdquo;</span>
                ) : (
                  <span className="text-[#4E535C] italic">Chưa thiết lập thông điệp cốt lõi cho chiến dịch này. Nhấn &ldquo;Chỉnh sửa đề bài&rdquo; để bổ sung.</span>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-bold text-[#3B3F46] mb-1.5">
              Lời kêu gọi hành động chính (Primary CTA)
            </label>
            {isEditingBrief ? (
              <input
                type="text"
                value={briefPrimaryCta}
                onChange={(e) => setBriefPrimaryCta(e.target.value)}
                placeholder="Ví dụ: Đăng ký trải nghiệm ngay, Nhận ưu đãi 30%..."
                className="w-full text-xs p-2.5 rounded-xl border border-[#D0CEC7] focus:outline-none focus:border-[#121316] text-[#121316]"
              />
            ) : (
              <div className="flex flex-wrap items-center gap-3">
                <span className="px-3.5 py-1.5 rounded-lg bg-[#121316] text-white font-bold text-xs inline-flex items-center gap-1.5">
                  <span>{campaign?.primary_cta || briefPrimaryCta || 'Chưa thiết lập CTA'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </span>
                <span className="text-xs text-[#3B3F46]">CTA này được tự động gắn vào các mẫu bài quảng cáo.</span>
              </div>
            )}
          </div>
        </div>

        {/* Box 2: Quantified Target & Metrics */}
        <div className="bg-white p-5 rounded-xl border border-[#E4E2DD] space-y-4">
          <div className="flex items-center justify-between border-b border-[#F0EFEA] pb-3">
            <span className="text-xs font-extrabold text-[#121316] uppercase tracking-wider flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-[#15803D]" />
              Mục tiêu định lượng (KPI Target)
            </span>
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-[#F0FDF4] text-[#15803D] border border-[#BBF7D0]">
              Chỉ tiêu cam kết
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-[#3B3F46] mb-1.5">
                Tên chỉ tiêu KPI chính
              </label>
              {isEditingBrief ? (
                <input
                  type="text"
                  value={briefTargetKpiName}
                  onChange={(e) => setBriefTargetKpiName(e.target.value)}
                  placeholder="Ví dụ: Đơn hàng thành công"
                  className="w-full text-xs p-2.5 rounded-xl border border-[#D0CEC7] focus:outline-none focus:border-[#121316] text-[#121316]"
                />
              ) : (
                <div className="p-3 bg-[#F6F5F0] rounded-xl border border-[#E4E2DD] text-xs font-bold text-[#121316]">
                  {campaign?.target_kpi_name || briefTargetKpiName || 'Chưa đặt tên KPI'}
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold text-[#3B3F46] mb-1.5">
                Chỉ tiêu cam kết (Mục tiêu)
              </label>
              {isEditingBrief ? (
                <input
                  type="number"
                  value={briefTargetKpiValue || ''}
                  onChange={(e) => setBriefTargetKpiValue(Number(e.target.value))}
                  placeholder="1000"
                  className="w-full text-xs p-2.5 rounded-xl border border-[#D0CEC7] focus:outline-none focus:border-[#121316] text-[#121316] font-bold tabular-nums"
                />
              ) : (
                <div className="p-3 bg-[#F0FDF4] rounded-xl border border-[#BBF7D0] text-xs font-bold text-[#15803D] flex items-center justify-between">
                  <span className="text-base font-extrabold tabular-nums">
                    {(campaign?.target_kpi_value || briefTargetKpiValue || 0).toLocaleString('vi-VN')}
                  </span>
                  <span className="text-xs text-[#15803D] font-bold">Mục tiêu</span>
                </div>
              )}
            </div>
          </div>

          {/* KPI Performance summary */}
          <div className="p-3.5 bg-[#F6F5F0] rounded-xl border border-[#E4E2DD] space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#3B3F46] font-semibold">Tiến độ chuyển đổi thực tế:</span>
              <span className="font-extrabold text-[#121316] tabular-nums">
                {(campaignKpi?.total_conversions || 0).toLocaleString('vi-VN')} / {(campaign?.target_kpi_value || briefTargetKpiValue || 1).toLocaleString('vi-VN')}
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-[#E4E2DD] overflow-hidden">
              <div
                className="h-full rounded-full bg-[#15803D] transition-all duration-500"
                style={{
                  width: `${Math.min(
                    100,
                    Math.round(((campaignKpi?.total_conversions || 0) / ((campaign?.target_kpi_value || briefTargetKpiValue) || 1)) * 100)
                  )}%`
                }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-[#3B3F46]">
              <span>Tỷ lệ hoàn thành:</span>
              <span className="font-extrabold text-[#121316] tabular-nums">
                {Math.min(
                  100,
                  Math.round(((campaignKpi?.total_conversions || 0) / ((campaign?.target_kpi_value || briefTargetKpiValue) || 1)) * 100)
                )}%
              </span>
            </div>
          </div>

          {/* Đích KPI đã khai báo — target vs thực tế (GET /kpi-progress) */}
          {kpiProgress && kpiProgress.targets.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-[#3B3F46] uppercase tracking-wider">
                Chỉ tiêu KPI đã khai ({kpiProgress.measurable_count}/{kpiProgress.total_count} đo được)
                {kpiProgress.overall_achieved_pct !== null && (
                  <span className="ml-1.5 text-[#D95D39]">· Đạt TB {kpiProgress.overall_achieved_pct}%</span>
                )}
              </div>
              {kpiProgress.targets.map((t) => (
                <div key={t.target_id ?? t.metric_name} className="p-2.5 bg-white rounded-xl border border-[#E4E2DD] text-xs space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-[#121316]">{t.metric_name}</span>
                    {t.achieved_pct !== null ? (
                      <span className={`font-extrabold tabular-nums ${t.achieved_pct >= 100 ? 'text-[#15803D]' : t.achieved_pct >= 50 ? 'text-[#B45309]' : 'text-[#BE123C]'}`}>
                        {t.achieved_pct}%
                      </span>
                    ) : (
                      <span className="text-[#4E535C] font-semibold">Chưa đo được</span>
                    )}
                  </div>
                  <div className="flex justify-between text-xs text-[#3B3F46] tabular-nums">
                    <span>Mục tiêu: <b className="text-[#121316]">{t.target_value.toLocaleString('vi-VN')} {t.unit || ''}</b></span>
                    <span>Thực tế: <b className="text-[#121316]">{t.actual_value !== null ? t.actual_value.toLocaleString('vi-VN') : '—'} {t.actual_value !== null ? (t.unit || '') : ''}</b></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Section 3: Channel Budget Allocation */}
      <div className="bg-white p-5 rounded-xl border border-[#E4E2DD] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E4E2DD] pb-4">
          <div>
            <span className="text-xs font-bold text-[#121316] uppercase tracking-wider flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-[#B45309]" />
              Phân bổ ngân sách theo kênh & Đồng bộ hạn mức thẻ ngày
            </span>
            <p className="text-xs text-[#5A5E66] mt-0.5">
              Khi lưu phân bổ ngân sách kênh, hạn mức chi tiêu ngày (Spending Cap) của Tài khoản Quảng cáo đang gắn với chiến dịch sẽ tự động cập nhật tương ứng.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-[10px] text-[#5A5E66] uppercase font-bold block">Tổng ngân sách:</span>
              <span className="text-sm font-extrabold font-mono tabular-nums text-[#121316]">
                {campaign ? Number(campaign.budget).toLocaleString('vi-VN') : 0} ₫
              </span>
            </div>
            {isEditingBudget ? (
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setIsEditingBudget(false)}
                  className="px-3 py-1 rounded-lg border border-[#E4E2DD] text-xs font-semibold text-[#5A5E66] hover:bg-[#FAF9F5]"
                >
                  Hủy
                </button>
                <button
                  onClick={handleSaveBudgetAllocations}
                  className="px-3 py-1 rounded-lg bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-bold flex items-center gap-1"
                >
                  <Save className="w-3 h-3" />
                  <span>Lưu phân bổ</span>
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsEditingBudget(true)}
                className="px-3 py-1.5 rounded-lg border border-[#E4E2DD] bg-[#FAF9F5] text-[#121316] hover:bg-[#EFECE6] text-xs font-bold flex items-center gap-1"
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Chỉnh sửa kênh</span>
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {channelAllocations.map((ch) => {
            const totalBudget = campaign ? Number(campaign.budget) : 1;
            const pct = totalBudget > 0 ? Math.round((ch.planned_amount / totalBudget) * 100) : 0;
            return (
              <div key={ch.channel_id} className="p-3.5 bg-[#FAF9F5] rounded-xl border border-[#E4E2DD] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#121316]">{ch.name}</span>
                  <span className="text-[11px] font-bold font-mono tabular-nums text-[#B45309] bg-[#FFFBEB] border border-[#FDE68A] px-1.5 py-0.5 rounded">
                    {pct}%
                  </span>
                </div>

                {isEditingBudget ? (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      value={ch.planned_amount || ''}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setChannelAllocations(prev =>
                          prev.map(c => c.channel_id === ch.channel_id ? { ...c, planned_amount: val } : c)
                        );
                      }}
                      placeholder="0"
                      className="w-full text-xs p-2 rounded-lg border border-[#E4E2DD] focus:outline-none focus:ring-1 focus:ring-[#121316] font-bold font-mono tabular-nums text-[#121316]"
                    />
                    <span className="text-xs text-[#5A5E66]">₫</span>
                  </div>
                ) : (
                  <div className="text-sm font-extrabold font-mono tabular-nums text-[#121316]">
                    {ch.planned_amount.toLocaleString('vi-VN')} ₫
                  </div>
                )}

                <div className="w-full h-1.5 rounded-full bg-[#E4E2DD] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#D95D39] transition-all duration-300"
                    style={{ width: `${Math.min(100, pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section 4: Ad Accounts & POS Order Sync Hub */}
      <AdAccountsHub workspaceId={campaign?.workspace_id} />
    </div>
  );
};
