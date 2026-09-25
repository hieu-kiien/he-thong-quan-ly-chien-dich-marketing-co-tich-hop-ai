import React, { useEffect, useState } from 'react';
import { 
  Sparkles, 
  ArrowUpRight, 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  Plus, 
  Eye, 
  MousePointer, 
  Target, 
  DollarSign 
} from 'lucide-react';
import { MetricCard } from '../components/MetricCard';
import { CampaignTable } from '../components/CampaignTable';
import { KPIGrid9, AttributionTrendChart, AIDoctorWidget } from '../components/analytics';
import { Campaign, MarketingContent, KPISummary } from '../types';
import { campaignApi, contentApi, analyticsApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { MetricCardSkeleton, CampaignTableSkeleton } from '../components/Skeleton';

interface DashboardProps {
  onSelectCampaign: (campaign: Campaign) => void;
  onOpenWorkflow: (campaign: Campaign) => void;
  onOpenAI: (campaign: Campaign) => void;
  onNavigateTab?: (tab: string) => void;
  userRole?: string;
}

export const Dashboard: React.FC<DashboardProps> = ({
  onSelectCampaign,
  onOpenWorkflow,
  onOpenAI,
  onNavigateTab,
  userRole
}) => {
  const toast = useToast();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [contents, setContents] = useState<MarketingContent[]>([]);
  const [dashboardKpi, setDashboardKpi] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cList, ctList, kpiData] = await Promise.all([
        campaignApi.getAll(),
        contentApi.getAll(),
        analyticsApi.getDashboard().catch(() => ({ kpi: null }))
      ]);
      setCampaigns(cList);
      setContents(ctList);
      if (kpiData?.kpi) {
        setDashboardKpi(kpiData.kpi);
      }
    } catch (e) {
      console.warn('Lỗi khi tải dữ liệu tổng quan:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveQuick = async (id: number) => {
    try {
      await contentApi.approve(id);
      toast.success('Đã phê duyệt nhanh bài viết!');
      loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi duyệt bài');
    }
  };

  const handleDeleteCampaign = async (id: number) => {
    if (userRole !== 'MANAGER') {
      toast.warning('Chỉ Quản lý (Manager) mới có quyền xóa chiến dịch');
      return;
    }

    if (!window.confirm('Bạn có chắc chắn muốn xóa chiến dịch này?')) return;

    try {
      await campaignApi.delete(id);
      toast.success('Đã xóa chiến dịch thành công!');
      loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi xóa chiến dịch');
    }
  };

  const handleOpenAICopilot = () => {
    if (campaigns.length === 0) {
      toast.info('Vui lòng tạo ít nhất một chiến dịch trước khi dùng AI Copilot');
      return;
    }
    onOpenAI(campaigns[0]);
  };

  const pendingContents = contents.filter(c => c.status === 'IN_REVIEW');

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">Tổng quan Chiến dịch</h2>
          <p className="text-xs text-slate-500 mt-1">Dữ liệu thời gian thực được đồng bộ từ CSDL SQLite và tích hợp AI Copilot.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleOpenAICopilot}
            className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-md shadow-indigo-500/20 transition-all active:scale-95"
          >
            <Sparkles className="w-4 h-4 animate-pulse" />
            <span>Sinh nội dung mới bằng AI</span>
          </button>
        </div>
      </div>

      {/* Value Process Roadmap: 4-Step Interactive Marketing Workflow */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-800/40 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        {/* Subtle Ambient Glow Effects */}
        <div className="absolute -top-20 -right-20 w-60 h-60 bg-indigo-500/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-violet-500/15 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-[11px] font-bold tracking-wide uppercase">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
                <span>Quy trình Marketing Tự động khép kín</span>
              </div>
              <h3 className="text-lg md:text-xl font-black tracking-tight text-white mt-2">
                Hệ thống MarketFlow AI giải quyết bài toán gì cho Doanh Nghiệp?
              </h3>
              <p className="text-xs text-slate-300 max-w-2xl mt-1 leading-relaxed">
                Tối ưu 80% thời gian tạo nội dung, giảm lãng phí ngân sách quảng cáo và đảm bảo chất lượng nhờ quy trình chuẩn 4 bước:
              </p>
            </div>

            <div className="flex items-center gap-2 self-start md:self-center shrink-0">
              {onNavigateTab && (
                <button
                  onClick={() => onNavigateTab('ai_studio')}
                  className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white text-xs font-bold shadow-md shadow-indigo-600/30 transition-all flex items-center gap-1.5 cursor-pointer active:scale-95"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Vào Xưởng AI Studio</span>
                </button>
              )}
            </div>
          </div>

          {/* 4 Steps Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
            {/* Step 1 */}
            <div className="bg-slate-800/60 border border-slate-700/60 hover:border-indigo-500/50 rounded-xl p-4 transition-all group">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/60">
                  Bước 1
                </span>
                <Target className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
              </div>
              <h4 className="font-bold text-sm text-white group-hover:text-indigo-200 transition-colors">
                Khởi tạo Chiến dịch
              </h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                Thiết lập mục tiêu, đối tượng người xem, định vị USP và phân bổ ngân sách.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-slate-800/60 border border-slate-700/60 hover:border-violet-500/50 rounded-xl p-4 transition-all group">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-violet-400 bg-violet-950/80 px-2 py-0.5 rounded border border-violet-800/60">
                  Bước 2
                </span>
                <Sparkles className="w-4 h-4 text-violet-400 group-hover:scale-110 transition-transform" />
              </div>
              <h4 className="font-bold text-sm text-white group-hover:text-violet-200 transition-colors">
                AI Viết Bài 1-Click
              </h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                OpenRouter AI tạo 5 góc ý tưởng + bài viết hoàn chỉnh (Tiêu đề, Body, CTA) chuẩn đa kênh.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-slate-800/60 border border-slate-700/60 hover:border-emerald-500/50 rounded-xl p-4 transition-all group">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60">
                  Bước 3
                </span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
              </div>
              <h4 className="font-bold text-sm text-white group-hover:text-emerald-200 transition-colors">
                Sếp Duyệt (Human Check)
              </h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                Hàng đợi kiểm duyệt (Review Queue) giúp Manager kiểm tra, sửa đổi và 1-click phê duyệt an toàn.
              </p>
            </div>

            {/* Step 4 */}
            <div className="bg-slate-800/60 border border-slate-700/60 hover:border-amber-500/50 rounded-xl p-4 transition-all group">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-800/60">
                  Bước 4
                </span>
                <TrendingUp className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
              </div>
              <h4 className="font-bold text-sm text-white group-hover:text-amber-200 transition-colors">
                Đo Lường Doanh Thu & ROI
              </h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                Theo dõi Views, CTR, Conversions thời gian thực. AI tự động đánh giá và gợi ý tối ưu hiệu quả.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Row 1: 9-KPI Grid (Bento Top) */}
      <KPIGrid9 kpi={dashboardKpi} loading={loading} />

      {/* Row 2: Bento Grid Layout (70% Table & Analytics + 30% AI Strategic Insight & Doctor) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (8/12 - 67%): Attribution Analytics & Scannable Campaign Table */}
        <div className="lg:col-span-8 space-y-6">
          {/* Multi-Channel Attribution Analytics Trend Chart */}
          <AttributionTrendChart
            channels={dashboardKpi?.channel_metrics || []}
            totalCost={dashboardKpi?.total_cost}
            totalRevenue={dashboardKpi?.total_revenue}
          />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Danh sách Chiến dịch</h3>
              <span className="text-xs text-indigo-600 font-semibold cursor-pointer hover:underline">Xem tất cả</span>
            </div>

            {loading ? (
              <CampaignTableSkeleton rows={4} />
            ) : (
              <CampaignTable
                campaigns={campaigns}
                onSelectCampaign={onSelectCampaign}
                onOpenWorkflow={onOpenWorkflow}
                onOpenAIForCampaign={onOpenAI}
                onDeleteCampaign={handleDeleteCampaign}
                userRole={userRole}
              />
            )}
          </div>
        </div>

        {/* Right Column (4/12 - 33%): Bento AI Strategic Insight & Doctor Hub */}
        <div className="lg:col-span-4 space-y-5">
          <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-violet-600" />
            <span>AI Doctor & Chiến Lược</span>
          </h3>

          {/* Actionable AI Doctor Widget (Compact Mode) */}
          <AIDoctorWidget
            campaignId={campaigns.length > 0 ? campaigns[0].id : undefined}
            compact={true}
            onOpenAIStudio={handleOpenAICopilot}
          />

          {/* Review Queue Snippet */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-amber-500" /> Hàng đợi duyệt ({pendingContents.length})
              </span>
              <span className="text-[11px] text-slate-400">Sếp duyệt</span>
            </div>

            {pendingContents.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 text-center">Không có bài viết nào đang chờ duyệt</p>
            ) : (
              <div className="space-y-2.5">
                {pendingContents.slice(0, 3).map((item) => (
                  <div key={item.id} className="p-3 bg-slate-50 border border-slate-100 rounded-lg hover:border-slate-300 transition-colors">
                    <p className="text-xs font-bold text-slate-900 truncate">{item.title}</p>
                    <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{item.body}</p>
                    {userRole === 'MANAGER' && (
                      <button
                        onClick={() => handleApproveQuick(item.id)}
                        className="mt-2 text-[11px] font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-3 h-3" /> Phê duyệt ngay
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
};
