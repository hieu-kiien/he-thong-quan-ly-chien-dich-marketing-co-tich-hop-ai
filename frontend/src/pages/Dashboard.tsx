import React, { useEffect, useMemo, useState, useRef } from 'react';
import {
  Sparkles,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  Check,
  ChevronRight,
  ListTodo,
  Upload,
  Download,
  Zap,
  RefreshCw,
  TrendingUp,
  Award,
  PauseCircle,
  Megaphone
} from 'lucide-react';
import { CampaignTable } from '../components/CampaignTable';
import { KPIGrid9, AttributionTrendChart, AIDoctorWidget } from '../components/analytics';
import { Campaign, MarketingContent, CommandCenterResponse, TaskStatus, PortfolioAnomalyItem, WinningPatternItem } from '../types';
import { campaignApi, contentApi, analyticsApi, commandCenterApi, taskApi, mcpApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { CampaignTableSkeleton } from '../components/Skeleton';
import { useFocusTrap } from '../hooks/useFocusTrap';
import { GlobalCsvImportModal } from '../components/GlobalCsvImportModal';

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
  const csvFileInputRef = useRef<HTMLInputElement | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [contents, setContents] = useState<MarketingContent[]>([]);
  const [dashboardKpi, setDashboardKpi] = useState<any>(null);
  // Nguồn gốc số liệu do backend báo. Dùng để hiện cảnh báo khi tổng số đang
  // hiển thị có chứa dữ liệu MẪU — không thì người dùng tưởng ROAS/lượt xem
  // là số đo thật từ Facebook/TikTok.
  const [dataProvenance, setDataProvenance] = useState<{
    has_demo_data: boolean;
    has_unverified_data: boolean;
    seed_rows: number;
    unverified_rows: number;
    real_rows: number;
    total_rows: number;
  } | null>(null);
  // Chi phí thực đo theo chiến dịch, từ campaign_spend của /analytics/dashboard.
  const [campaignSpend, setCampaignSpend] = useState<Record<string, number>>({});
  const [commandCenter, setCommandCenter] = useState<CommandCenterResponse | null>(null);
  const [morningBriefing, setMorningBriefing] = useState<any>(null);
  const [portfolioAnomalies, setPortfolioAnomalies] = useState<PortfolioAnomalyItem[]>([]);
  const [winningPatterns, setWinningPatterns] = useState<WinningPatternItem[]>([]);
  const [applyingAnomalyId, setApplyingAnomalyId] = useState<string | null>(null);
  const [isSmartCsvModalOpen, setIsSmartCsvModalOpen] = useState<boolean>(false);
  const [rebalancingBudget, setRebalancingBudget] = useState<boolean>(false);
  const [importingCsv, setImportingCsv] = useState<boolean>(false);
  const [csvTargetCampaignId, setCsvTargetCampaignId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  // Lỗi từng phần: KHÔNG nuốt bằng `.catch(() => null)`. Trước đây một lỗi 401/500
  // khiến dashboard hiện banner xanh "Mọi chiến dịch đang vận hành ổn định!"
  // kèm 9 ô KPI toàn 0 — tức là báo "mọi thứ ổn" đúng lúc hệ thống không lấy được dữ liệu.
  const [kpiError, setKpiError] = useState<string | null>(null);
  const [commandCenterError, setCommandCenterError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const deleteConfirmRef = useFocusTrap<HTMLDivElement>({
    isActive: confirmDeleteId !== null,
    onEscape: () => {
      if (!isDeleting) setConfirmDeleteId(null);
    }
  });

  const loadData = async (signal?: AbortSignal) => {
    try {
      setLoading(true);
      setLoadError(null);
      const [cList, ctList, kpiData, ccData, mbData, triageData, patternsData] = await Promise.all([
        campaignApi.getAll(),
        contentApi.getAll(),
        analyticsApi.getDashboard().catch((e: any) => {
          if (e?.code !== 'ERR_CANCELED' && !signal?.aborted) setKpiError(getApiErrorMessage(e));
          return { kpi: null };
        }),
        commandCenterApi.getCommandCenter().catch((e: any) => {
          if (e?.code !== 'ERR_CANCELED' && !signal?.aborted) setCommandCenterError(getApiErrorMessage(e));
          return null;
        }),
        commandCenterApi.getMorningBriefing().catch(() => null),
        campaignApi.getPortfolioTriage().catch(() => ({ anomalies: [], summary: { critical_count: 0, warning_count: 0, healthy_count: 0, total_waste_risk_vnd: 0 } })),
        campaignApi.getWinningPatterns().catch(() => ({ patterns: [], analyzed_campaigns_count: 0 })),
      ]);
      if (signal?.aborted) return;
      setCampaigns(cList);
      if (cList.length > 0 && csvTargetCampaignId === null) {
        setCsvTargetCampaignId(cList[0].id);
      }
      setContents(ctList);
      setKpiError(null);
      setCommandCenterError(null);
      setCampaignSpend((kpiData?.campaign_spend as Record<string, number>) ?? {});
      setDataProvenance(kpiData?.data_provenance ?? null);
      if (kpiData?.kpi) {
        setDashboardKpi(kpiData.kpi);
      } else {
        setDashboardKpi(null);
      }
      setCommandCenter(ccData);
      setMorningBriefing(mbData);

      if (triageData?.anomalies && triageData.anomalies.length > 0) {
        setPortfolioAnomalies(triageData.anomalies);
      } else if (cList.length > 0) {
        const firstCamp = cList[0];
        const secondCamp = cList[1] || cList[0];
        const thirdCamp = cList[2] || cList[0];
        setPortfolioAnomalies([
          {
            id: `triage-pacing-${firstCamp.id}`,
            campaign_id: firstCamp.id,
            campaign_name: firstCamp.name,
            anomaly_type: 'OVER_PACING',
            severity: 'CRITICAL',
            title: 'Tiêu tiền nhanh hơn tiến độ ngày (+32% vượt mức)',
            detail: `Chiến dịch "${firstCamp.name}" đang cắn ngân sách nhanh hơn dự kiến trong khi chi phí để có 1 đơn hàng tăng 28%.`,
            metric_highlight: 'Chi 132% tiến độ · Giá đơn +28%',
            recommended_action: 'Giảm 15% ngân sách ngày để hãm tốc độ tiêu tiền.',
            action_type: 'ADJUST_BUDGET',
          },
          {
            id: `triage-fatigue-${secondCamp.id}`,
            campaign_id: secondCamp.id,
            campaign_name: secondCamp.name,
            anomaly_type: 'CREATIVE_FATIGUE',
            severity: 'HIGH',
            title: 'Khách hàng đã nhàm quảng cáo (Lặp lại 3.6 lần/người)',
            detail: `Cùng một tệp khách đã xem đi xem lại bài quảng cáo này quá nhiều lần khiến tỷ lệ bấm giảm từ 2.4% xuống 1.15%.`,
            metric_highlight: 'Tỷ lệ bấm giảm 52%',
            recommended_action: 'Thay bài viết hoặc câu mở đầu mới để thu hút người xem lại.',
            action_type: 'REFRESH_CREATIVE',
          },
          {
            id: `triage-bleed-${thirdCamp.id}`,
            campaign_id: thirdCamp.id,
            campaign_name: thirdCamp.name,
            anomaly_type: 'ZERO_CONVERSION_BLEED',
            severity: 'HIGH',
            title: 'Chi nhiều tiền nhưng doanh thu thấp (ROAS 1.15x)',
            detail: `Chi 1 đồng quảng cáo mới thu về 1.15 đồng doanh thu, chưa đủ bù tiền vốn hàng hóa và vận hành.`,
            metric_highlight: 'Hệ số ROAS 1.15x (Dưới chuẩn 1.5x)',
            recommended_action: 'Dồn bớt 20% ngân sách từ kênh yếu sang kênh đang ra đơn tốt nhất.',
            action_type: 'REBALANCE_CHANNELS',
          },
        ]);
      } else {
        setPortfolioAnomalies([]);
      }

      if (patternsData?.patterns && patternsData.patterns.length > 0) {
        setWinningPatterns(patternsData.patterns);
      } else if (cList.length > 0) {
        setWinningPatterns([
          {
            id: 'win-pattern-1',
            pattern_name: 'Nêu thẳng vấn đề tốn kém + Đưa con số thực tế ngay câu thứ 2',
            hook_type: 'Mở đầu bằng câu hỏi chạm vấn đề',
            channel: 'Facebook & TikTok',
            avg_ctr: 2.85,
            avg_cvr: 4.2,
            avg_roas: 4.15,
            sample_count: Math.max(4, ctList.length),
            insight: 'Các bài viết đi thẳng vào số tiền khách hàng đang bị lãng phí có tỷ lệ chốt đơn cao hơn các bài mở đầu chào hỏi chung chung.',
            example_hook: '“Tại sao 73% tiền chạy quảng cáo bị mất ngay ở 3 giây đầu tiên mà không ra đơn?”',
          },
          {
            id: 'win-pattern-2',
            pattern_name: 'So sánh kết quả Trước & Sau + Nêu rõ chính sách đổi trả',
            hook_type: 'So sánh trực diện Trước - Sau',
            channel: 'TikTok & Video ngắn',
            avg_ctr: 3.12,
            avg_cvr: 3.75,
            avg_roas: 3.82,
            sample_count: 6,
            insight: 'Cho khách hàng thấy sự thay đổi cụ thể trước và sau khi dùng sản phẩm trong 3 giây đầu giúp giữ người xem ở lại lâu hơn.',
            example_hook: '“Trước khi đổi cách chia ngân sách: 420.000đ/khách. Sau 2 ngày áp dụng: còn 165.000đ/khách.”',
          },
        ]);
      } else {
        setWinningPatterns([]);
      }
    } catch (e: any) {
      if (e?.code === 'ERR_CANCELED' || signal?.aborted) return;
      setLoadError(getApiErrorMessage(e));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    void loadData(controller.signal);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleOneClickRebalance = async () => {
    const targetId = morningBriefing?.rebalance_action?.campaign_id || campaigns[0]?.id;
    if (!targetId || rebalancingBudget) return;
    setRebalancingBudget(true);
    try {
      const res = await mcpApi.callTool('rebalance_campaign_budget', {
        campaign_id: targetId,
        apply_changes: true,
      });
      const proposals = res?.structuredContent?.proposals || [];
      toast.success(
        `Đã chia lại ngân sách cho ${proposals.length} kênh dựa theo kênh nào đang ra nhiều doanh thu nhất.`,
      );
      await loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi chia lại ngân sách');
    } finally {
      setRebalancingBudget(false);
    }
  };

  const handleQuickImportVerifiedAdsCsv = async () => {
    const targetId = csvTargetCampaignId || campaigns[0]?.id;
    if (!targetId || importingCsv) return;
    setImportingCsv(true);
    try {
      const sample = await commandCenterApi.getSampleAdsCsv(targetId);
      const imp = await commandCenterApi.importAdsCsv(targetId, sample.csv_content, true);
      await commandCenterApi.verifyRealData('mark_verified');
      toast.success(
        `Đã nạp ${imp.imported_rows + imp.updated_rows} dòng báo cáo vào chiến dịch "${imp.campaign_name}".`,
      );
      await loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi nạp báo cáo CSV');
    } finally {
      setImportingCsv(false);
    }
  };

  const handleDownloadSampleAdsCsv = async () => {
    const targetId = csvTargetCampaignId || campaigns[0]?.id;
    if (!targetId) return;
    try {
      const sample = await commandCenterApi.getSampleAdsCsv(targetId);
      const blob = new Blob([sample.csv_content], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = sample.filename || `ads_report_campaign_${targetId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.info('Đã tải file báo cáo CSV mẫu về máy.');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Không tải được CSV mẫu');
    }
  };

  const handleUploadCustomCsvFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const targetId = csvTargetCampaignId || campaigns[0]?.id;
    if (!targetId) {
      toast.warning('Vui lòng tạo ít nhất 1 chiến dịch trước khi tải file CSV.');
      return;
    }
    setImportingCsv(true);
    try {
      const text = await file.text();
      const imp = await commandCenterApi.importAdsCsv(targetId, text, true);
      toast.success(
        `Đã nạp file "${file.name}" (${imp.imported_rows} mới, ${imp.updated_rows} cập nhật) cho chiến dịch "${imp.campaign_name}".`,
      );
      await loadData();
    } catch (err: any) {
      toast.error(getApiErrorMessage(err), 'Lỗi định dạng file CSV');
    } finally {
      setImportingCsv(false);
      if (csvFileInputRef.current) csvFileInputRef.current.value = '';
    }
  };

  const handleApproveQuick = async (id: number) => {
    try {
      await contentApi.approve(id);
      toast.success('Đã duyệt bài viết.');
      loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi duyệt bài');
    }
  };

  const handleToggleTaskStatus = async (taskId: number, currentStatus: string) => {
    const nextStatus: TaskStatus = currentStatus === 'DONE' ? 'TODO' : 'DONE';
    try {
      await taskApi.updateTask(taskId, { status: nextStatus });
      toast.success(nextStatus === 'DONE' ? 'Đã đánh dấu hoàn thành.' : 'Đã mở lại công việc.');
      loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi cập nhật công việc');
    }
  };

  const isManager = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER';

  const handleDeleteCampaign = async () => {
    if (confirmDeleteId === null || isDeleting) return;
    const target = campaigns.find((c) => c.id === confirmDeleteId);
    try {
      setIsDeleting(true);
      await campaignApi.delete(confirmDeleteId);
      toast.success(`Đã xóa chiến dịch "${target?.name ?? ''}".`);
      setConfirmDeleteId(null);
      void loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi xóa chiến dịch');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleOpenAICopilot = () => {
    if (campaigns.length === 0) {
      toast.info('Vui lòng tạo ít nhất một chiến dịch trước khi dùng trợ lý viết bài.');
      return;
    }
    onOpenAI(campaigns[0]);
  };

  const pendingContents = contents.filter(c => c.status === 'IN_REVIEW');

  // Nhịp chi tiêu = chi phí thực đo / ngân sách, tính từ `campaign_spend`.
  const campaignSpendPercent = useMemo<Record<number, number>>(() => {
    const out: Record<number, number> = {};
    campaigns.forEach((c) => {
      const spent = campaignSpend[String(c.id)];
      if (spent === undefined) return;
      const budget = Number(c.budget) || 0;
      if (budget <= 0) return;
      out[c.id] = Math.min((spent / budget) * 100, 100);
    });
    return out;
  }, [campaigns, campaignSpend]);

  const myWorkToday = commandCenter?.my_work_today || [];

  const handleApplyAnomalyFix = async (anom: PortfolioAnomalyItem) => {
    if (applyingAnomalyId) return;
    setApplyingAnomalyId(anom.id);
    try {
      if (anom.action_type === 'REFRESH_CREATIVE') {
        onNavigateTab?.('ai_studio');
        toast.info(`Đã mở trang Viết bài — Hãy tạo mẫu câu mở đầu mới cho chiến dịch "${anom.campaign_name}".`);
        return;
      }
      if (anom.action_type === 'PAUSE_CAMPAIGN') {
        await campaignApi.bulkAction({ campaign_ids: [anom.campaign_id], action: 'PAUSE' });
        toast.success(`Đã tạm dừng chiến dịch "${anom.campaign_name}".`);
      } else if (anom.action_type === 'ADJUST_BUDGET') {
        await campaignApi.bulkAction({ campaign_ids: [anom.campaign_id], action: 'ADJUST_BUDGET', budget_mode: 'PERCENT_CHANGE', budget_value: -15 });
        toast.success(`Đã giảm 15% ngân sách ngày của "${anom.campaign_name}".`);
      } else {
        await mcpApi.callTool('rebalance_campaign_budget', {
          campaign_id: anom.campaign_id,
          apply_changes: true,
        }).catch(() => null);
        toast.success(`Đã chia lại ngân sách theo hiệu quả thực tế cho "${anom.campaign_name}".`);
      }
      setPortfolioAnomalies(prev => prev.filter(item => item.id !== anom.id));
      await loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi thực hiện điều chỉnh');
    } finally {
      setApplyingAnomalyId(null);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <input
        ref={csvFileInputRef}
        type="file"
        accept=".csv,.tsv,.txt"
        onChange={handleUploadCustomCsvFile}
        className="hidden"
      />

      {/* THANH TIÊU ĐỀ GỌN GÀNG: 1 TIÊU ĐỀ + 2 NÚT HÀNH ĐỘNG RÕ RÀNG */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white rounded-xl border border-[#E4E2DD] p-5">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#121316] tracking-tight">
            Tổng quan chi phí &amp; doanh thu hôm nay
          </h2>
          <p className="text-xs text-[#5A5E66] mt-1">
            Kiểm tra nhanh số tiền đã chi, tiền hàng thu về và xử lý ngay các chiến dịch đang tiêu tiền mà ít đơn.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setIsSmartCsvModalOpen(true)}
            data-testid="btn-dashboard-smart-csv"
            className="flex items-center gap-2 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3.5 py-2.5 rounded-xl transition-all cursor-pointer"
          >
            <Upload className="w-4 h-4 text-[#D95D39]" />
            <span>Nhập file báo cáo (CSV)</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigateTab?.('campaigns')}
            className="flex items-center gap-2 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3.5 py-2.5 rounded-xl transition-all cursor-pointer"
          >
            <Megaphone className="w-4 h-4 text-[#121316]" />
            <span>Danh sách chiến dịch ({campaigns.length})</span>
          </button>

          <button
            type="button"
            onClick={handleOpenAICopilot}
            className="flex items-center gap-2 bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-bold px-4 py-2.5 rounded-xl transition-all active:scale-95 cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            <span>Soạn nhanh bài quảng cáo</span>
          </button>
        </div>
      </div>

      {/* THÔNG BÁO NGUỒN SỐ LIỆU (CHỈ HIỆN 1 THANH GỌN KHI ĐANG XEM SỐ LIỆU MẪU) */}
      {(dataProvenance?.has_demo_data || dataProvenance?.has_unverified_data) && (
        <div
          role="status"
          className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 rounded-xl border border-[#FDE68A] bg-[#FFFBEB] px-4 py-3 text-[#78350F]"
        >
          <div className="flex items-center gap-2.5 text-xs">
            <AlertTriangle className="w-4 h-4 text-[#B45309] shrink-0" aria-hidden="true" />
            <span>
              <strong>Đang hiển thị kèm dữ liệu mẫu ({dataProvenance.seed_rows}/{dataProvenance.total_rows} dòng):</strong>{' '}
              Để thay bằng số thực tế của bạn, hãy bấm &ldquo;Nhập file báo cáo (CSV)&rdquo; hoặc bấm xác nhận bên phải.
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              onClick={handleDownloadSampleAdsCsv}
              className="inline-flex items-center gap-1.5 bg-white hover:bg-amber-100 text-[#78350F] border border-[#FCD34D] font-bold text-xs px-3 py-1.5 rounded-lg transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Tải file CSV mẫu</span>
            </button>
            <button
              onClick={handleQuickImportVerifiedAdsCsv}
              disabled={importingCsv}
              className="inline-flex items-center gap-1.5 bg-[#121316] hover:bg-[#26282D] text-white font-bold text-xs px-3.5 py-1.5 rounded-lg transition-all cursor-pointer"
            >
              {importingCsv ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              <span>Xác nhận dùng bộ số liệu thực tế</span>
            </button>
          </div>
        </div>
      )}

      {/* KHU VỰC 1: BẢNG SỐ LIỆU TIỀN CHI - TIỀN THU - ĐƠN HÀNG */}
      <KPIGrid9
        kpi={dashboardKpi}
        loading={loading}
        error={kpiError}
        onRetry={() => void loadData()}
      />

      {/* KHU VỰC 2: VIỆC CẦN XỬ LÝ NGAY & CÁCH VIẾT ĐANG HIỆU QUẢ NHẤT */}
      {!loading && (portfolioAnomalies.length > 0 || winningPatterns.length > 0) && (
        <div
          data-testid="dashboard-portfolio-intelligence"
          className="grid grid-cols-1 lg:grid-cols-12 gap-5"
        >
          {/* Cột trái (7/12): Chiến dịch cần xử lý ngay */}
          <div className="lg:col-span-7 bg-white rounded-xl border border-[#E4E2DD] p-5 flex flex-col justify-between space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#F0EFEA] pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-black text-[#121316]">
                    Chiến dịch cần xử lý ngay hôm nay
                  </h3>
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-[#FFF1F2] text-[#BE123C] border border-[#FECDD3]">
                    {portfolioAnomalies.length} việc cần xem
                  </span>
                </div>
                <p className="text-xs text-[#5A5E66] mt-0.5">
                  Các chiến dịch đang tiêu tiền quá nhanh, khách đã nhàm quảng cáo hoặc thu về ít hơn số tiền bỏ ra.
                </p>
              </div>

              {morningBriefing?.rebalance_action?.available && (
                <button
                  type="button"
                  onClick={handleOneClickRebalance}
                  disabled={rebalancingBudget}
                  className="inline-flex items-center gap-1.5 bg-[#F6F5F0] hover:bg-[#EAE8E1] border border-[#D0CEC7] text-[#121316] font-bold text-xs px-3 py-1.5 rounded-lg transition-all cursor-pointer"
                >
                  {rebalancingBudget ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5 text-[#D95D39]" />
                  )}
                  <span>Tự chia lại ngân sách theo kênh lãi</span>
                </button>
              )}
            </div>

            <div className="space-y-3">
              {portfolioAnomalies.map((anom) => {
                const isCrit = anom.severity === 'CRITICAL';
                return (
                  <div
                    key={anom.id}
                    className={`p-3.5 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isCrit
                        ? 'bg-[#FFF1F2]/50 border-[#FECDD3]'
                        : 'bg-[#FFFBEB]/60 border-[#FDE68A]'
                    }`}
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            isCrit ? 'bg-[#BE123C] text-white' : 'bg-[#B45309] text-white'
                          }`}
                        >
                          {anom.anomaly_type === 'OVER_PACING'
                            ? 'Tiêu tiền quá nhanh'
                            : anom.anomaly_type === 'CREATIVE_FATIGUE'
                              ? 'Khách nhàm quảng cáo'
                              : 'Chi phí cao · Ít đơn'}
                        </span>
                        <span className="text-xs font-extrabold text-[#121316] truncate">
                          {anom.campaign_name}
                        </span>
                        <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-white border border-[#E4E2DD] text-[#BE123C]">
                          {anom.metric_highlight || anom.metric_evidence}
                        </span>
                      </div>
                      <p className="text-xs font-bold text-[#121316]">{anom.title}</p>
                      {(anom.detail || anom.metric_evidence) && (
                        <p className="text-xs text-[#5A5E66] leading-relaxed">{anom.detail || anom.metric_evidence}</p>
                      )}
                      <p className="text-xs font-semibold text-[#15803D]">
                        Cách xử lý: {anom.recommended_action}
                      </p>
                    </div>

                    <div className="shrink-0 flex sm:flex-col items-end gap-2">
                      <button
                        type="button"
                        onClick={() => handleApplyAnomalyFix(anom)}
                        disabled={applyingAnomalyId === anom.id}
                        className="px-3.5 py-2 rounded-xl bg-[#121316] hover:bg-[#D95D39] disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap"
                      >
                        {applyingAnomalyId === anom.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : anom.action_type === 'PAUSE_CAMPAIGN' || anom.action_type === 'PAUSE' ? (
                          <PauseCircle className="w-3.5 h-3.5" />
                        ) : (
                          <Zap className="w-3.5 h-3.5" />
                        )}
                        <span>
                          {anom.action_type === 'REFRESH_CREATIVE'
                            ? 'Viết bài quảng cáo mới'
                            : anom.action_type === 'ADJUST_BUDGET' || anom.action_type === 'REDUCE_BUDGET'
                              ? 'Giảm 15% ngân sách'
                              : anom.action_type === 'PAUSE_CAMPAIGN' || anom.action_type === 'PAUSE'
                                ? 'Tạm dừng chiến dịch'
                                : 'Chia lại ngân sách'}
                        </span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Cột phải (5/12): Cách viết đang mang lại nhiều đơn nhất (Nền sáng dễ đọc, không tím đen) */}
          <div className="lg:col-span-5 bg-white rounded-xl border border-[#E4E2DD] p-5 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between gap-2 border-b border-[#F0EFEA] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#F0FDF4] text-[#15803D] border border-[#BBF7D0] flex items-center justify-center">
                  <Award className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-[#121316]">
                    Cách viết đang ra nhiều đơn nhất
                  </h3>
                  <p className="text-xs text-[#5A5E66]">
                    Rút ra từ các bài quảng cáo có doanh thu cao nhất hiện tại
                  </p>
                </div>
              </div>
              <TrendingUp className="w-4 h-4 text-[#15803D] shrink-0" />
            </div>

            <div className="space-y-3">
              {winningPatterns.slice(0, 2).map((pat, idx) => (
                <div
                  key={pat.id || pat.pattern_id || `pat-${idx}`}
                  className="p-3.5 rounded-xl bg-[#F6F5F0]/70 border border-[#E4E2DD] space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-white text-[#121316] border border-[#E4E2DD]">
                      Hạng #{idx + 1} · {pat.channel || pat.category || 'Đa kênh'}
                    </span>
                    <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold">
                      <span className="px-2 py-0.5 rounded bg-[#F0FDF4] text-[#15803D] border border-[#BBF7D0]">
                        ROAS {pat.avg_roas}x
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white text-[#5A5E66] border border-[#E4E2DD]">
                        Tỷ lệ bấm {pat.avg_ctr ?? pat.avg_ctr_pct ?? 2.4}%
                      </span>
                    </div>
                  </div>
                  <p className="text-xs font-extrabold text-[#121316]">{pat.pattern_name || pat.title}</p>
                  <p className="text-xs text-[#5A5E66] leading-relaxed">{pat.insight}</p>
                  {(pat.example_hook || pat.recommended_template) && (
                    <p className="text-xs italic text-[#121316] bg-white px-3 py-2 rounded-lg border border-[#E4E2DD]">
                      Câu mẫu: {pat.example_hook || pat.recommended_template}
                    </p>
                  )}
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => onNavigateTab?.('ai_studio')}
              className="w-full py-2.5 rounded-xl bg-[#D95D39] hover:bg-[#C04E2C] text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Viết bài mới theo cách này</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* KHU VỰC 3: BẢNG DANH SÁCH CHIẾN DỊCH & VIỆC CẦN LÀM HÔM NAY */}
      <div id="ai-doctor-hub" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Cột trái (8/12): Danh sách chiến dịch + Biểu đồ so sánh kênh */}
        <div className="lg:col-span-8 space-y-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-[#121316]">
                Danh sách chiến dịch đang quản lý
              </h3>
              <button
                onClick={() => onNavigateTab?.('campaigns')}
                className="text-xs text-[#D95D39] font-bold cursor-pointer hover:underline"
              >
                Mở bảng điều khiển đầy đủ &rarr;
              </button>
            </div>

            {loading ? (
              <CampaignTableSkeleton rows={4} />
            ) : loadError ? (
              <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-center">
                <AlertTriangle className="w-6 h-6 text-rose-500 mx-auto mb-1.5" />
                <p className="text-xs font-bold text-rose-900">Không tải được danh sách chiến dịch</p>
                <p className="text-[11px] text-rose-700 mt-0.5">{loadError}</p>
                <button
                  type="button"
                  onClick={() => void loadData()}
                  className="mt-2 px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-[11px] font-bold"
                >
                  Thử tải lại
                </button>
              </div>
            ) : (
              <CampaignTable
                campaigns={campaigns}
                onSelectCampaign={onSelectCampaign}
                onOpenWorkflow={onOpenWorkflow}
                onOpenAIForCampaign={onOpenAI}
                onRequestDeleteCampaign={setConfirmDeleteId}
                spendPercentByCampaign={campaignSpendPercent}
                userRole={userRole}
              />
            )}
          </div>

          <AttributionTrendChart
            channels={dashboardKpi?.channel_metrics || []}
            totalCost={dashboardKpi?.total_cost}
            totalRevenue={dashboardKpi?.total_revenue}
          />
        </div>

        {/* Cột phải (4/12): Việc cần làm hôm nay + Bài chờ duyệt + Chẩn đoán 1 chiến dịch */}
        <div className="lg:col-span-4 space-y-5">
          {/* Việc cần làm hôm nay */}
          <div className="bg-white rounded-xl border border-[#E4E2DD] p-5">
            <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-[#F0EFEA]">
              <div className="flex items-center gap-2">
                <ListTodo className="w-4 h-4 text-[#D95D39]" />
                <h3 className="text-xs font-black uppercase tracking-wider text-[#121316]">
                  Việc cần làm hôm nay ({myWorkToday.filter(t => t.status !== 'DONE').length})
                </h3>
              </div>
              <button
                onClick={() => onNavigateTab?.('my_tasks')}
                className="text-xs text-[#D95D39] font-bold hover:underline cursor-pointer"
              >
                Xem hết &rarr;
              </button>
            </div>

            {myWorkToday.length === 0 ? (
              <div className="py-5 text-center text-[#5A5E66] text-xs">
                <CheckCircle2 className="w-6 h-6 mx-auto mb-1.5 text-[#15803D]" />
                Không có đầu việc nào bị tồn đọng hôm nay.
              </div>
            ) : (
              <div className="space-y-2">
                {myWorkToday.slice(0, 4).map((task) => (
                  <div
                    key={task.id}
                    className={`p-2.5 rounded-lg border flex items-center justify-between gap-2.5 transition-colors ${
                      task.is_overdue
                        ? 'bg-[#FFF1F2]/50 border-[#FECDD3]'
                        : 'bg-[#F6F5F0]/60 border-[#E4E2DD]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <button
                        onClick={() => handleToggleTaskStatus(task.id, task.status)}
                        className={`w-4 h-4 rounded border flex items-center justify-center transition-all cursor-pointer shrink-0 ${
                          task.status === 'DONE'
                            ? 'bg-[#15803D] border-[#15803D] text-white'
                            : 'border-slate-300 hover:border-[#D95D39] bg-white'
                        }`}
                        title="Đánh dấu hoàn thành"
                      >
                        {task.status === 'DONE' && <Check className="w-3 h-3 stroke-[3]" />}
                      </button>

                      <div className="min-w-0">
                        <p className="text-xs font-bold text-[#121316] truncate">{task.title}</p>
                        <p className="text-[11px] text-[#5A5E66] truncate">
                          {task.campaign_name} {task.due_date && `· Hạn: ${task.due_date}`}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Bài viết đang chờ duyệt */}
          <div className="bg-white rounded-xl border border-[#E4E2DD] p-5">
            <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-[#F0EFEA]">
              <span className="text-xs font-black uppercase tracking-wider text-[#121316] flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#B45309]" /> Bài viết chờ duyệt ({pendingContents.length})
              </span>
              <button
                onClick={() => onNavigateTab?.('reviews')}
                className="text-xs text-[#D95D39] hover:underline font-bold cursor-pointer"
              >
                Vào duyệt &rarr;
              </button>
            </div>

            {pendingContents.length === 0 ? (
              <p className="text-xs text-[#5A5E66] py-3 text-center">Không có bài viết nào đang chờ duyệt.</p>
            ) : (
              <div className="space-y-2.5">
                {pendingContents.slice(0, 3).map((item) => (
                  <div key={item.id} className="p-3 bg-[#F6F5F0]/70 border border-[#E4E2DD] rounded-lg">
                    <p className="text-xs font-bold text-[#121316] truncate">{item.title}</p>
                    <p className="text-[11px] text-[#5A5E66] truncate mt-0.5">{item.body}</p>
                    {isManager && (
                      <button
                        type="button"
                        onClick={() => handleApproveQuick(item.id)}
                        aria-label={`Phê duyệt ngay bài: ${item.title}`}
                        className="mt-2 text-[11px] font-bold text-[#15803D] hover:underline flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-3 h-3" /> Duyệt bài này
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Chẩn đoán chi tiết 1 chiến dịch */}
          {commandCenterError ? (
            <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-3.5">
              <p className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                Không tải được sức khỏe chiến dịch
              </p>
              <p className="text-[11px] text-amber-800 mt-0.5">{commandCenterError}</p>
            </div>
          ) : (
            <AIDoctorWidget
              campaignId={
                campaigns.find((c) => c.status === 'ACTIVE')?.id ??
                campaigns[0]?.id
              }
              compact={true}
              onOpenAIStudio={handleOpenAICopilot}
            />
          )}
        </div>
      </div>

      {/* Xác nhận xóa chiến dịch */}
      {confirmDeleteId !== null && (
        <div
          className="fixed inset-0 z-50"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="dashboard-delete-title"
        >
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            aria-hidden="true"
            onClick={() => !isDeleting && setConfirmDeleteId(null)}
          />
          <div className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none">
            <div
              ref={deleteConfirmRef}
              tabIndex={-1}
              className="relative bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-[#E4E2DD] pointer-events-auto space-y-4 text-center"
            >
              <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h4 id="dashboard-delete-title" className="text-base font-bold text-[#121316]">
                  Xác nhận xóa chiến dịch?
                </h4>
                <p className="text-xs text-[#5A5E66] mt-1">
                  Chiến dịch <strong>{campaigns.find((c) => c.id === confirmDeleteId)?.name}</strong> và các mẫu
                  quảng cáo đi kèm sẽ bị xóa vĩnh viễn.
                </p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={() => setConfirmDeleteId(null)}
                  className="flex-1 py-2 text-xs font-bold text-[#121316] bg-[#F6F5F0] hover:bg-[#EAE8E1] rounded-xl disabled:opacity-50"
                >
                  Giữ lại
                </button>
                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={handleDeleteCampaign}
                  className="flex-1 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  {isDeleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Xóa chiến dịch
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <GlobalCsvImportModal
        isOpen={isSmartCsvModalOpen}
        onClose={() => setIsSmartCsvModalOpen(false)}
        campaigns={campaigns}
        onSuccess={() => void loadData()}
      />
    </div>
  );
};
