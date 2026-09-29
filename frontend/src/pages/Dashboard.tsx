import React, { useEffect, useState } from 'react';
import { 
  Sparkles, 
  ArrowUpRight, 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  Plus, 
  AlertTriangle,
  AlertCircle,
  Check,
  Calendar,
  Layers,
  ChevronRight,
  ShieldAlert,
  Activity,
  ListTodo,
  ExternalLink
} from 'lucide-react';
import { MetricCard } from '../components/MetricCard';
import { CampaignTable } from '../components/CampaignTable';
import { KPIGrid9, AttributionTrendChart, AIDoctorWidget } from '../components/analytics';
import { 
  Campaign, 
  MarketingContent, 
  KPISummary,
  CommandCenterResponse,
  CommandCenterAttentionItem,
  CommandCenterMyWorkItem,
  CommandCenterCampaignHealth,
  TaskStatus
} from '../types';
import { campaignApi, contentApi, analyticsApi, commandCenterApi, taskApi, getApiErrorMessage } from '../services/api';
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
  const [commandCenter, setCommandCenter] = useState<CommandCenterResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cList, ctList, kpiData, ccData] = await Promise.all([
        campaignApi.getAll(),
        contentApi.getAll(),
        analyticsApi.getDashboard().catch(() => ({ kpi: null })),
        commandCenterApi.getCommandCenter().catch(() => null)
      ]);
      setCampaigns(cList);
      setContents(ctList);
      if (kpiData?.kpi) {
        setDashboardKpi(kpiData.kpi);
      }
      if (ccData) {
        setCommandCenter(ccData);
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

  const handleToggleTaskStatus = async (taskId: number, currentStatus: string) => {
    const nextStatus: TaskStatus = currentStatus === 'DONE' ? 'TODO' : 'DONE';
    try {
      await taskApi.updateTask(taskId, { status: nextStatus });
      toast.success(nextStatus === 'DONE' ? 'Đã hoàn thành tác vụ!' : 'Đã mở lại tác vụ!');
      loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi cập nhật tác vụ');
    }
  };

  const isManager = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER' || userRole === 'ADMIN';

  const handleDeleteCampaign = async (id: number) => {
    if (!isManager) {
      toast.warning('Chỉ Quản lý (Manager / Agency Manager) mới có quyền xóa chiến dịch');
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
  const attentionItems = commandCenter?.attention_items || [];
  const myWorkToday = commandCenter?.my_work_today || [];
  const campaignsHealth = commandCenter?.campaigns_health || [];
  const summaryCounts = commandCenter?.summary_counts;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black text-slate-900 tracking-tight">Command Center Điều Phối</h2>
            <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
              Vận hành thời gian thực
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Hệ thống quản lý và điều phối vận hành chiến dịch Marketing B2B: Việc cần chú ý, tác vụ hôm nay và sức khỏe chiến dịch.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateTab?.('my_tasks')}
            className="flex items-center gap-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-bold px-3.5 py-2.5 rounded-lg shadow-xs transition-all cursor-pointer"
          >
            <ListTodo className="w-4 h-4 text-indigo-600" />
            <span>Tác vụ của tôi ({summaryCounts?.total_my_tasks ?? 0})</span>
          </button>

          <button
            onClick={handleOpenAICopilot}
            className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-md shadow-indigo-500/20 transition-all active:scale-95 cursor-pointer"
          >
            <Sparkles className="w-4 h-4 animate-pulse" />
            <span>AI Copilot Điều Phối</span>
          </button>
        </div>
      </div>

      {/* SECTION 1: WHAT NEEDS ATTENTION (VIỆC CẦN CHÚ Ý) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Việc Cần Chú Ý Ngay (What Needs Attention)
            </h3>
            {attentionItems.length > 0 && (
              <span className="text-[11px] font-extrabold px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 border border-rose-300">
                {attentionItems.length} vấn đề
              </span>
            )}
          </div>
          {summaryCounts && summaryCounts.critical_issues > 0 && (
            <span className="text-xs text-rose-600 font-bold flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5" />
              {summaryCounts.critical_issues} rủi ro khẩn cấp
            </span>
          )}
        </div>

        {attentionItems.length === 0 ? (
          <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4 flex items-center gap-3 text-emerald-800 text-xs">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="font-bold">Mọi chiến dịch và tác vụ đang vận hành ổn định!</p>
              <p className="text-[11px] text-emerald-700">Không có tác vụ nào quá hạn, không có rủi ro vượt ngân sách hay cảnh báo deadline.</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {attentionItems.slice(0, 6).map((item) => {
              const isCritical = item.severity === 'CRITICAL';
              const isHigh = item.severity === 'HIGH';

              return (
                <div
                  key={item.id}
                  className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${
                    isCritical
                      ? 'bg-rose-50/70 border-rose-200 text-rose-950 hover:border-rose-300'
                      : isHigh
                      ? 'bg-amber-50/70 border-amber-200 text-amber-950 hover:border-amber-300'
                      : 'bg-indigo-50/60 border-indigo-200 text-indigo-950 hover:border-indigo-300'
                  }`}
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                        isCritical
                          ? 'bg-rose-200 text-rose-800'
                          : isHigh
                          ? 'bg-amber-200 text-amber-800'
                          : 'bg-indigo-200 text-indigo-800'
                      }`}>
                        {item.type === 'OVERDUE_TASK'
                          ? 'Tác vụ quá hạn'
                          : item.type === 'BUDGET_OVERRUN'
                          ? 'Cảnh báo ngân sách'
                          : item.type === 'PENDING_APPROVAL'
                          ? 'Chờ phê duyệt'
                          : 'Hạn chót chiến dịch'}
                      </span>
                      {item.due_date && (
                        <span className="text-[11px] font-semibold text-slate-500 flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> {item.due_date}
                        </span>
                      )}
                    </div>

                    <h4 className="text-xs font-bold leading-snug line-clamp-1">
                      {item.title}
                    </h4>
                    <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
                      {item.message}
                    </p>
                  </div>

                  <div className="pt-3 mt-2 border-t border-slate-200/60 flex items-center justify-between">
                    <span className="text-[10px] font-medium text-slate-500 truncate max-w-[150px]">
                      {item.campaign_name || 'Chiến dịch'}
                    </span>
                    <button
                      onClick={() => {
                        if (item.type === 'PENDING_APPROVAL') {
                          onNavigateTab?.('reviews');
                        } else if (item.campaign_id) {
                          const target = campaigns.find(c => c.id === item.campaign_id);
                          if (target) onSelectCampaign(target);
                          else onNavigateTab?.('campaigns');
                        } else {
                          onNavigateTab?.('my_tasks');
                        }
                      }}
                      className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer"
                    >
                      <span>Xử lý ngay</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: OPERATIONAL SPLIT GRID (MY WORK TODAY + ACTIVE CAMPAIGNS HEALTH) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (6/12): MY WORK TODAY */}
        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                  <ListTodo className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Tác Vụ Hôm Nay Của Tôi (My Work Today)</h3>
                  <p className="text-[11px] text-slate-500">Các đầu việc cần bạn hoàn thiện để chiến dịch không bị trễ tiến độ</p>
                </div>
              </div>
              <button
                onClick={() => onNavigateTab?.('my_tasks')}
                className="text-xs text-indigo-600 font-bold hover:underline cursor-pointer"
              >
                Xem tất cả &rarr;
              </button>
            </div>

            {myWorkToday.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500" />
                Bạn không có tác vụ nào đang tồn đọng. Hãy thư giãn hoặc nhận thêm việc mới!
              </div>
            ) : (
              <div className="space-y-2.5">
                {myWorkToday.slice(0, 5).map((task) => (
                  <div
                    key={task.id}
                    className={`p-3 rounded-lg border flex items-center justify-between gap-3 transition-colors ${
                      task.is_overdue
                        ? 'bg-rose-50/40 border-rose-200/80 hover:bg-rose-50/70'
                        : 'bg-slate-50/70 border-slate-200/60 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <button
                        onClick={() => handleToggleTaskStatus(task.id, task.status)}
                        className={`w-4 h-4 rounded border flex items-center justify-center transition-all cursor-pointer ${
                          task.status === 'DONE'
                            ? 'bg-emerald-600 border-emerald-600 text-white'
                            : 'border-slate-300 hover:border-indigo-500 bg-white'
                        }`}
                        title="Đánh dấu hoàn thành"
                      >
                        {task.status === 'DONE' && <Check className="w-3 h-3 stroke-[3]" />}
                      </button>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-bold text-slate-900 truncate">{task.title}</p>
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-200 text-slate-700">
                            {task.task_type}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 truncate mt-0.5">
                          {task.campaign_name} {task.due_date && `• Hạn: ${task.due_date}`}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        task.priority === 'URGENT'
                          ? 'bg-rose-100 text-rose-700'
                          : task.priority === 'HIGH'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}>
                        {task.priority}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-100 mt-4 flex items-center justify-between text-xs text-slate-500">
            <span>Còn {myWorkToday.filter(t => t.status !== 'DONE').length} việc cần giải quyết</span>
            <button
              onClick={() => onNavigateTab?.('my_tasks')}
              className="text-xs font-bold text-indigo-600 hover:text-indigo-800"
            >
              Mở trang Tác vụ
            </button>
          </div>
        </div>

        {/* Right Column (6/12): ACTIVE CAMPAIGNS HEALTH */}
        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                  <Activity className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Sức Khỏe Chiến Dịch (Campaign Health)</h3>
                  <p className="text-[11px] text-slate-500">Đánh giá theo luật tất định: Tác vụ quá hạn, tỷ lệ giải ngân và tiến độ</p>
                </div>
              </div>
              <button
                onClick={() => onNavigateTab?.('campaigns')}
                className="text-xs text-indigo-600 font-bold hover:underline cursor-pointer"
              >
                Xem tất cả &rarr;
              </button>
            </div>

            {campaignsHealth.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                Chưa có chiến dịch nào đang hoạt động. Hãy tạo chiến dịch mới!
              </div>
            ) : (
              <div className="space-y-3">
                {campaignsHealth.slice(0, 4).map((ch) => {
                  const isCritical = ch.health_status === 'CRITICAL';
                  const isAtRisk = ch.health_status === 'AT_RISK';

                  return (
                    <div key={ch.campaign_id} className="p-3 bg-slate-50/70 border border-slate-200/60 rounded-lg space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-xs font-bold text-slate-900 truncate">
                            {ch.campaign_name}
                          </span>
                          <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                            isCritical
                              ? 'bg-rose-100 text-rose-700 border border-rose-300'
                              : isAtRisk
                              ? 'bg-amber-100 text-amber-700 border border-amber-300'
                              : 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                          }`}>
                            {isCritical ? 'RỦI RO CAO' : isAtRisk ? 'CẦN LƯU Ý' : 'ỔN ĐỊNH'} ({ch.health_score}/100)
                          </span>
                        </div>

                        <button
                          onClick={() => {
                            const c = campaigns.find(x => x.id === ch.campaign_id);
                            if (c) onSelectCampaign(c);
                          }}
                          className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-0.5"
                        >
                          Chi tiết &rarr;
                        </button>
                      </div>

                      {/* Progress / Budget Stats */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[11px] text-slate-500">
                          <span>Ngân sách: ${ch.spent.toLocaleString()} / ${ch.budget.toLocaleString()}</span>
                          <span className="font-semibold">{ch.budget_utilization_pct}% đã chi</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all ${
                              ch.budget_utilization_pct > 100
                                ? 'bg-rose-600'
                                : ch.budget_utilization_pct > 90
                                ? 'bg-amber-500'
                                : 'bg-indigo-600'
                            }`}
                            style={{ width: `${Math.min(100, ch.budget_utilization_pct)}%` }}
                          />
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-0.5">
                        <span>Hoàn thành: {ch.completed_tasks}/{ch.total_tasks} tác vụ</span>
                        {ch.overdue_tasks > 0 && (
                          <span className="text-rose-600 font-bold">{ch.overdue_tasks} tác vụ quá hạn</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-100 mt-4 flex items-center justify-between text-xs text-slate-500">
            <span>{campaignsHealth.length} chiến dịch đang hoạt động</span>
            <button
              onClick={() => onNavigateTab?.('campaigns')}
              className="text-xs font-bold text-indigo-600 hover:text-indigo-800"
            >
              Quản lý Chiến dịch
            </button>
          </div>
        </div>

      </div>

      {/* SECTION 3: 9-KPI GRID (ANALYTICS BENTO TOP) */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
          Chỉ Số Hiệu Quả Chiến Dịch (Performance Metrics)
        </h3>
        <KPIGrid9 kpi={dashboardKpi} loading={loading} />
      </div>

      {/* SECTION 4: ANALYTICS & DOCTOR HUB */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (8/12 - 67%): Attribution Trend & Campaigns Table */}
        <div className="lg:col-span-8 space-y-6">
          <AttributionTrendChart
            channels={dashboardKpi?.channel_metrics || []}
            totalCost={dashboardKpi?.total_cost}
            totalRevenue={dashboardKpi?.total_revenue}
          />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Danh sách Chiến dịch</h3>
              <button 
                onClick={() => onNavigateTab?.('campaigns')}
                className="text-xs text-indigo-600 font-semibold cursor-pointer hover:underline"
              >
                Xem tất cả
              </button>
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

        {/* Right Column (4/12 - 33%): AI Strategic Insight & Doctor Hub */}
        <div className="lg:col-span-4 space-y-5">
          <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-violet-600" />
            <span>AI Doctor & Chẩn Đoán</span>
          </h3>

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
              <button 
                onClick={() => onNavigateTab?.('reviews')}
                className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer"
              >
                Vào duyệt &rarr;
              </button>
            </div>

            {pendingContents.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">Không có bài viết nào đang chờ duyệt</p>
            ) : (
              <div className="space-y-2.5">
                {pendingContents.slice(0, 3).map((item) => (
                  <div key={item.id} className="p-3 bg-slate-50 border border-slate-100 rounded-lg hover:border-slate-300 transition-colors">
                    <p className="text-xs font-bold text-slate-900 truncate">{item.title}</p>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">{item.body}</p>
                    {isManager && (
                      <button
                        onClick={() => handleApproveQuick(item.id)}
                        className="mt-2 text-[11px] font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
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
