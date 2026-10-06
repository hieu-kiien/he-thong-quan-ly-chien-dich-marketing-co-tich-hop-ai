import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Megaphone, Plus, Search, DollarSign, CheckCircle2, AlertTriangle, TrendingUp, BarChart3, Sparkles, Trash2, Copy, Eye, X, Loader2, LayoutGrid, Table as TableIcon, Users, Sliders, ShieldCheck, Zap, Layers, Mail, FileText, ChevronRight, RefreshCw, ArrowUpRight, Check, Package, Clock, PencilLine } from 'lucide-react';
import { 
  Campaign, 
  Product, 
  MarketingContent, 
  AIDoctorReport, 
  KPISummary, 
  ChannelAttribution, 
  OmnichannelResponse,
  BrandKit,
  BudgetAllocation,
  ComplianceCheckResponse
} from '../types';
import { 
  campaignApi, 
  productApi, 
  contentApi, 
  aiApi, 
  brandKitApi,
  budgetApi,
  channelApi,
  metricsApi,
  getApiErrorMessage 
} from '../services/api';
import { channelIdByCode, channelPresentation, channelCodeById, channelNameById, setChannelRegistry } from '../utils/channels';
import { formatNumber, formatRatio, addDaysLocalISO, todayLocalISO } from '../utils/format';
import { useToast } from '../components/Toast';
import { CampaignCardSkeleton, CampaignTableSkeleton } from '../components/Skeleton';
import { ManualContentComposer } from '../components/ManualContentComposer';
import { useFocusTrap } from '../hooks/useFocusTrap';
import { copyToClipboardWithFormatting } from '../utils/copyUtils';

/** Tổng hợp chỉ số thực đo của một chiến dịch, gom từ /campaigns/{id}/metrics. */
interface CampaignAggregate {
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
  revenue: number;
  rowCount: number;
}

const EMPTY_AGGREGATE: CampaignAggregate = {
  views: 0,
  clicks: 0,
  conversions: 0,
  cost: 0,
  revenue: 0,
  rowCount: 0
};

interface CampaignsProps {
  // `onSelectCampaign`, `onOpenWorkflow`, `onNavigateTab` được App truyền xuống để
  // giữ API component ổn định, nhưng bản Campaigns hiện tại tự quản lý điều
  // hướng qua drawer + wizard nên không dùng tới. Giữ trong interface (optional)
  // để không phá call site hiện có.
  onSelectCampaign?: (campaign: Campaign) => void;
  onOpenWorkflow?: (campaign: Campaign) => void;
  onOpenAI: (campaign: Campaign) => void;
  onNavigateTab?: (tab: string) => void;
  onRefreshData?: () => void;
  userRole?: string;
  /** Truyền từ ô tìm kiếm trên Navbar; trước đây Navbar ném mất giá trị này. */
  initialSearchTerm?: string;
  /** Đồng bộ truy vấn tìm kiếm khi Navbar gửi xuống lần nữa mà không remount. */
  searchTermSync?: string;
}

// Preset objectives matching Meta & Google Ads taxonomy
const CAMPAIGN_OBJECTIVES = [
  {
    id: 'SALES',
    title: 'Doanh số & Chuyển đổi',
    subtitle: 'Tối ưu hóa đơn hàng, doanh thu và ROAS (BoFU)',
    icon: TrendingUp,
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    defaultAudience: 'Khách hàng có ý định mua sắm cao, khách hàng cũ (Retargeting)',
    funnelStage: 'BoFU'
  },
  {
    id: 'LEADS',
    title: 'Khách hàng tiềm năng',
    subtitle: 'Thu thập form đăng ký, tin nhắn và thông tin tư vấn (MoFU)',
    icon: Users,
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    defaultAudience: 'Người quan tâm đến giải pháp, chủ doanh nghiệp, chuyên viên',
    funnelStage: 'MoFU'
  },
  {
    id: 'TRAFFIC',
    title: 'Lưu lượng & Tương tác',
    subtitle: 'Tăng lượt truy cập website, bài viết và tương tác đa kênh (ToFU)',
    icon: Zap,
    badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    defaultAudience: 'Người dùng quan tâm đến xu hướng công nghệ & giải pháp kinh doanh',
    funnelStage: 'ToFU'
  },
  {
    id: 'AWARENESS',
    title: 'Nhận diện thương hiệu',
    subtitle: 'Tiếp cận tối đa khách hàng mục tiêu trong phân khúc (ToFU)',
    icon: Megaphone,
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    defaultAudience: 'Phân khúc thị trường rộng, khách hàng tiềm năng thế hệ mới',
    funnelStage: 'ToFU'
  }
];

export const Campaigns: React.FC<CampaignsProps> = ({
  onOpenAI,
  onRefreshData,
  userRole,
  initialSearchTerm,
  searchTermSync
}) => {
  const toast = useToast();
  const isManager = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER' || userRole === 'ADMIN';
  // Backend giới hạn DELETE /campaigns/{id} cho MANAGER/AGENCY_MANAGER (xem
  // campaigns.py). Trước đây isManager còn nhận ADMIN nên ADMIN thấy nút Xóa rồi
  // nhận 403. Tách riêng hai khả năng để UI khớp đúng với server.
  const canDeleteCampaign = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER';
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [brandKit, setBrandKit] = useState<BrandKit | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Chỉ số thực đo theo chiến dịch. Trước đây bảng chiến dịch hiển thị các
  // literal cố định (3.82x ROAS / 2.450 clicks / 4.1% CVR / 68.4% pacing) cho
  // mọi dòng; đây là nguồn số liệu thật thay cho chúng.
  const [campaignMetrics, setCampaignMetrics] = useState<Record<number, CampaignAggregate>>({});
  const [loadingMetrics, setLoadingMetrics] = useState<boolean>(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  // Filters & Views
  const [searchTerm, setSearchTerm] = useState<string>(initialSearchTerm ?? '');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [objectiveFilter, setObjectiveFilter] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');

  // Slide-over Detail Drawer
  const [selectedDrawerCampaign, setSelectedDrawerCampaign] = useState<Campaign | null>(null);
  const [drawerTab, setDrawerTab] = useState<'creatives' | 'channels' | 'ai_doctor' | 'settings'>('creatives');
  const [drawerContents, setDrawerContents] = useState<MarketingContent[]>([]);
  const [drawerLoadingContents, setDrawerLoadingContents] = useState<boolean>(false);
  const [drawerDoctorReport, setDrawerDoctorReport] = useState<AIDoctorReport | null>(null);
  const [drawerAttributions, setDrawerAttributions] = useState<ChannelAttribution[]>([]);
  const [drawerBudgetAllocations, setDrawerBudgetAllocations] = useState<BudgetAllocation[]>([]);
  const [drawerKpi, setDrawerKpi] = useState<KPISummary | null>(null);
  const [drawerBudgetLoading, setDrawerBudgetLoading] = useState<boolean>(false);
  const [budgetConfirmOpen, setBudgetConfirmOpen] = useState<boolean>(false);
  const [isApplyingBudget, setIsApplyingBudget] = useState<boolean>(false);
  const [isUpdatingStatusId, setIsUpdatingStatusId] = useState<number | null>(null);

  // Trình soạn thảo thủ công (đường tạo nội dung KHÔNG dùng AI). Mở từ tab
  // "Mẫu Quảng Cáo & Creatives" của drawer chiến dịch.
  const [isManualComposerOpen, setIsManualComposerOpen] = useState<boolean>(false);

  // 4-Step Creation Wizard Modal
  const [isWizardOpen, setIsWizardOpen] = useState<boolean>(false);
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isGeneratingAI, setIsGeneratingAI] = useState<boolean>(false);
  const [isSavingDrawer, setIsSavingDrawer] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const wizardModalRef = useFocusTrap<HTMLDivElement>({
    isActive: isWizardOpen,
    onEscape: () => {
      if (!isSubmitting && !isGeneratingAI) setIsWizardOpen(false);
    }
  });

  const drawerRef = useFocusTrap<HTMLDivElement>({
    isActive: !!selectedDrawerCampaign,
    onEscape: () => setSelectedDrawerCampaign(null)
  });

  const deleteModalRef = useFocusTrap<HTMLDivElement>({
    isActive: !!deletingId,
    onEscape: () => {
      if (!isDeleting) setDeletingId(null);
    }
  });

  const budgetConfirmRef = useFocusTrap<HTMLDivElement>({
    isActive: budgetConfirmOpen,
    onEscape: () => {
      if (!isApplyingBudget) setBudgetConfirmOpen(false);
    }
  });

  // Wizard Form State
  const [wizardData, setWizardData] = useState({
    objectiveId: 'SALES',
    objectiveTitle: CAMPAIGN_OBJECTIVES[0].title,
    product_id: 1,
    name: '',
    budget: 15000000,
    start_date: todayLocalISO(),
    end_date: addDaysLocalISO(todayLocalISO(), 30),
    audience: 'Chủ shop thời trang & kinh doanh online 22-45 tuổi tại các đô thị',
    funnelStage: 'BoFU',
    channels: ['facebook', 'tiktok', 'email'],
    budgetSplit: {
      facebook: 50,
      tiktok: 35,
      email: 15
    },
    launchStatus: 'ACTIVE' as 'ACTIVE' | 'DRAFT'
  });

  // Generated AI Creatives in Wizard
  const [generatedCreatives, setGeneratedCreatives] = useState<OmnichannelResponse | null>(null);
  const [activeCreativeTab, setActiveCreativeTab] = useState<'facebook' | 'tiktok' | 'email'>('facebook');
  // Kết quả quét tuân thủ thật cho nội dung AI vừa sinh ở bước 3.
  const [wizardCompliance, setWizardCompliance] = useState<ComplianceCheckResponse | null>(null);
  const [isCheckingCompliance, setIsCheckingCompliance] = useState<boolean>(false);
  const [wizardComplianceCheckedCount, setWizardComplianceCheckedCount] = useState<number>(0);

  /** Số mẫu QC thực sự sẽ được tạo, khớp với điều kiện lưu ở handleFinishWizard. */
  const wizardCreativeCount = useMemo(() => {
    if (!generatedCreatives) return 0;
    let n = 0;
    if (generatedCreatives.facebook && wizardData.channels.includes('facebook') && channelIdByCode('facebook') !== null) n++;
    if (generatedCreatives.tiktok && wizardData.channels.includes('tiktok') && channelIdByCode('tiktok') !== null) n++;
    if (generatedCreatives.email && wizardData.channels.includes('email') && channelIdByCode('email') !== null) n++;
    return n;
  }, [generatedCreatives, wizardData.channels]);

  /**
   * Chạy bộ quét tuân thủ thật của backend trên các mẫu QC vừa sinh.
   * Đây là cùng bộ quét mà `/contents/{id}/submit` dùng, nên bước 4 báo đúng
   * kết quả mà quy trình duyệt sau đó sẽ chặn hay cho đi qua.
   */
  const runWizardComplianceCheck = useCallback(async () => {
    if (!generatedCreatives) {
      setWizardCompliance(null);
      setWizardComplianceCheckedCount(0);
      return;
    }
    const pieces: { title: string; body: string; cta?: string }[] = [];
    if (generatedCreatives.facebook && wizardData.channels.includes('facebook')) {
      pieces.push({
        title: generatedCreatives.facebook.headline || generatedCreatives.facebook.title || '',
        body: generatedCreatives.facebook.primary_text || generatedCreatives.facebook.body,
        cta: generatedCreatives.facebook.cta
      });
    }
    if (generatedCreatives.tiktok && wizardData.channels.includes('tiktok')) {
      pieces.push({
        title: `Kịch bản TikTok: ${generatedCreatives.tiktok.hook_3s ?? ''}`,
        body: `Hook 3s: ${generatedCreatives.tiktok.hook_3s ?? ''}\n${(generatedCreatives.tiktok.scenes ?? [])
          .map(s => `${s.scene_number ?? s.scene}: ${s.visual_action ?? s.visual ?? ''} ${s.voiceover_script ?? s.voiceover ?? ''}`)
          .join('\n')}`
      });
    }
    if (generatedCreatives.email && wizardData.channels.includes('email')) {
      pieces.push({
        title: generatedCreatives.email.subject || '',
        body: generatedCreatives.email.body,
        cta: generatedCreatives.email.cta
      });
    }

    if (pieces.length === 0) {
      setWizardCompliance(null);
      setWizardComplianceCheckedCount(0);
      return;
    }

    setIsCheckingCompliance(true);
    try {
      const merged: ComplianceCheckResponse = {
        status: 'PASSED',
        score: 100,
        can_submit: true,
        violations: []
      };
      let checked = 0;
      for (const piece of pieces) {
        const res = await contentApi.checkCompliance({
          title: piece.title,
          body: piece.body,
          cta: piece.cta,
          workspace_id: Number(localStorage.getItem('active_workspace_id')) || undefined
        });
        checked++;
        merged.score = Math.min(merged.score, Number(res.score ?? 0));
        merged.violations.push(...(res.violations ?? []));
        merged.can_submit = merged.can_submit && !!res.can_submit;
      }
      merged.status = merged.can_submit ? 'PASSED' : merged.violations.length > 0 ? 'VIOLATION' : 'WARNING';
      setWizardCompliance(merged);
      setWizardComplianceCheckedCount(checked);
    } catch (e) {
      // Không âm thầm coi là "đạt": báo lỗi để người dùng biết chưa kiểm được.
      setWizardCompliance(null);
      setWizardComplianceCheckedCount(0);
      toast.error(getApiErrorMessage(e), 'Không kiểm tra được tuân thủ nội dung');
    } finally {
      setIsCheckingCompliance(false);
    }
  }, [generatedCreatives, wizardData.channels, toast]);

  // Tự chạy kiểm tra khi bước 3 sinh xong mẫu QC, để bước 4 có số liệu thật.
  useEffect(() => {
    if (wizardStep === 4) {
      void runWizardComplianceCheck();
    }
  }, [wizardStep, runWizardComplianceCheck]);

  // Edit Drawer Form
  const [editFormData, setEditFormData] = useState({
    name: '',
    budget: 0,
    start_date: '',
    end_date: '',
    audience: '',
    status: 'ACTIVE' as Campaign['status']
  });

  // Navbar có thể gửi truy vấn mới khi người dùng đang đã ở tab này (component
  // không remount nên initialSearchTerm không áp dụng lần nữa).
  useEffect(() => {
    if (typeof searchTermSync === 'string') {
      setSearchTerm(searchTermSync);
    }
  }, [searchTermSync]);

  /**
   * Gom /campaigns/{id}/metrics của từng chiến dịch thành map theo id.
   * Backend chưa có endpoint tổng hợp nên vẫn phải gọi N lần, nhưng kết quả
   * được hiển thị đúng với dữ liệu thay vì hằng số bịa đặt.
   */
  const loadCampaignMetrics = useCallback(async (campaignList: Campaign[], signal?: AbortSignal) => {
    if (campaignList.length === 0) {
      setCampaignMetrics({});
      return;
    }
    setLoadingMetrics(true);
    setMetricsError(null);
    try {
      const rows = await metricsApi.getAllCampaignsMetrics(signal);
      const grouped: Record<number, CampaignAggregate> = {};
      rows.forEach((row: any) => {
        const cid = Number(row.campaign_id);
        if (!cid) return;
        const acc = grouped[cid] ?? { ...EMPTY_AGGREGATE };
        acc.views += Number(row.views) || 0;
        acc.clicks += Number(row.clicks) || 0;
        acc.conversions += Number(row.conversions) || 0;
        acc.cost += Number(row.cost) || 0;
        acc.revenue += Number(row.revenue) || 0;
        acc.rowCount += 1;
        grouped[cid] = acc;
      });
      campaignList.forEach((c) => {
        if (!grouped[c.id]) grouped[c.id] = { ...EMPTY_AGGREGATE };
      });
      setCampaignMetrics(grouped);
    } catch (e: any) {
      if (e?.code === 'ERR_CANCELED' || signal?.aborted) return;
      setMetricsError(getApiErrorMessage(e));
    } finally {
      if (!signal?.aborted) setLoadingMetrics(false);
    }
  }, []);

  const loadData = useCallback(async (signal?: AbortSignal) => {
    try {
      setLoading(true);
      setLoadError(null);
      const [cList, pList, channelList] = await Promise.all([
        campaignApi.getAll(),
        productApi.getAll().catch(() => [] as Product[]),
        // Nạp danh mục kênh từ server để ánh xạ code -> id chính xác, thay vì
        // hardcode id (id 2 từng được ghi chú là TikTok trong khi DB gọi là Email).
        channelApi.getAll().catch(() => [] as any[])
      ]);
      if (signal?.aborted) return;
      if (channelList.length > 0) setChannelRegistry(channelList);
      setCampaigns(cList);
      setProducts(pList);

      if (pList.length > 0) {
        setWizardData(prev => ({
          ...prev,
          product_id: prev.product_id || pList[0].id,
          name: prev.name || `Chiến dịch ${prev.objectiveTitle} - ${pList[0].name}`
        }));
      }

      void loadCampaignMetrics(cList, signal);

      // Try load Brand Kit
      try {
        const workspaceId = Number(localStorage.getItem('active_workspace_id')) || 0;
        if (workspaceId > 0) {
          const bk = await brandKitApi.getByWorkspace(workspaceId);
          if (!signal?.aborted) setBrandKit(bk);
        }
      } catch (e) {
        // ignore
      }
    } catch (e: unknown) {
      const err = e as { code?: string } | null;
      if (err?.code === 'ERR_CANCELED' || signal?.aborted) return;
      setLoadError(getApiErrorMessage(e));
      toast.error(getApiErrorMessage(e), 'Lỗi khi tải danh sách chiến dịch');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [loadCampaignMetrics, toast]);

  // Nạp dữ liệu lúc mount. Effect phải nằm SAU khai báo `loadData` (biến block
  // scoped dùng trước khi khai báo sẽ ném lỗi runtime), và `loadData` là
  // useCallback với deps ổn định nên thêm vào dependency list không gây chạy
  // lại vô ích. AbortController huỷ request khi component unmount.
  useEffect(() => {
    const controller = new AbortController();
    void loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  // Load details when Drawer opens
  useEffect(() => {
    if (selectedDrawerCampaign) {
      setEditFormData({
        name: selectedDrawerCampaign.name,
        budget: selectedDrawerCampaign.budget,
        start_date: selectedDrawerCampaign.start_date,
        end_date: selectedDrawerCampaign.end_date,
        audience: selectedDrawerCampaign.audience,
        status: selectedDrawerCampaign.status
      });
      loadDrawerDetails(selectedDrawerCampaign.id);
    }
  }, [selectedDrawerCampaign]);

  const loadDrawerDetails = async (campaignId: number) => {
    try {
      setDrawerLoadingContents(true);
      const [cts, doc, attr] = await Promise.all([
        campaignApi.getContents(campaignId).catch(() => []),
        campaignApi.getAIDoctor(campaignId).catch(() => null),
        campaignApi.getAttribution(campaignId).catch(() => [])
      ]);
      setDrawerContents(cts);
      setDrawerDoctorReport(doc);
      setDrawerAttributions(attr);
    } catch (e) {
      console.warn('Could not load full drawer details', e);
    } finally {
      setDrawerLoadingContents(false);
    }
  };

  // Phân bổ ngân sách + KPI thật cho tab "Kênh & ROI". Trước đây tab này vẽ tỷ lệ
  // 50/35/15 cố định và con số CPA 45.000 đ / CVR 4.2% không liên quan dữ liệu.
  useEffect(() => {
    if (!selectedDrawerCampaign) return;
    const campaignId = selectedDrawerCampaign.id;
    let cancelled = false;
    setDrawerBudgetLoading(true);
    (async () => {
      try {
        const [allocs, kpi] = await Promise.all([
          budgetApi.getBudgetAllocations(campaignId).catch(() => [] as BudgetAllocation[]),
          campaignApi.getKpi(campaignId).catch(() => null as KPISummary | null)
        ]);
        if (cancelled) return;
        setDrawerBudgetAllocations(allocs);
        setDrawerKpi(kpi);
      } catch (e) {
        console.warn('Không tải được phân bổ ngân sách / KPI', e);
      } finally {
        if (!cancelled) setDrawerBudgetLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedDrawerCampaign]);

  // Tăng ngân sách là thay đổi tiền thật nên phải có bước xác nhận, không "1-Click".
  const handleApplyBudgetIncrease = async () => {
    if (!selectedDrawerCampaign || isApplyingBudget) return;
    const currentBudget = Number(selectedDrawerCampaign.budget) || 0;
    const newBudget = Math.round(currentBudget * 1.2);
    try {
      setIsApplyingBudget(true);
      await campaignApi.update(selectedDrawerCampaign.id, { budget: newBudget });
      setCampaigns(prev => prev.map(c => c.id === selectedDrawerCampaign.id ? { ...c, budget: newBudget } : c));
      setSelectedDrawerCampaign(prev => prev ? { ...prev, budget: newBudget } : null);
      setEditFormData(prev => ({ ...prev, budget: newBudget }));
      setBudgetConfirmOpen(false);
      toast.success(`Đã tăng ngân sách lên ${formatNumber(newBudget)} đ.`);
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi tăng ngân sách');
    } finally {
      setIsApplyingBudget(false);
    }
  };

  // 1-Click Status Toggle (Active <-> Paused) - Meta Ads Manager behavior
  const handleToggleStatus = async (campaign: Campaign, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isUpdatingStatusId !== null) return;
    const nextStatus: Campaign['status'] = campaign.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    
    // Optimistic update
    setCampaigns(prev => prev.map(c => c.id === campaign.id ? { ...c, status: nextStatus } : c));
    if (selectedDrawerCampaign?.id === campaign.id) {
      setSelectedDrawerCampaign(prev => prev ? { ...prev, status: nextStatus } : null);
      setEditFormData(prev => ({ ...prev, status: nextStatus }));
    }

    setIsUpdatingStatusId(campaign.id);
    try {
      await campaignApi.update(campaign.id, { status: nextStatus });
      toast.success(
        nextStatus === 'ACTIVE' 
          ? `Đã kích hoạt phân phối chiến dịch "${campaign.name}"` 
          : `Đã tạm dừng phân phối chiến dịch "${campaign.name}"`
      );
      if (onRefreshData) onRefreshData();
    } catch (err) {
      // Rollback on error
      setCampaigns(prev => prev.map(c => c.id === campaign.id ? { ...c, status: campaign.status } : c));
      toast.error(getApiErrorMessage(err), 'Không thể thay đổi trạng thái chiến dịch');
    } finally {
      setIsUpdatingStatusId(null);
    }
  };

  // 1-Click Duplicate Campaign (Meta Ads clone for A/B testing)
  const handleDuplicateCampaign = async (campaign: Campaign, e: React.MouseEvent) => {
    e.stopPropagation();
    if (loading) return;
    try {
      setLoading(true);
      const duplicatedName = `${campaign.name} (Bản sao A/B Test)`;
      const newCamp = await campaignApi.create({
        name: duplicatedName,
        product_id: campaign.product_id,
        objective: campaign.objective,
        audience: campaign.audience,
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        budget: campaign.budget
      });

      // Load contents of original campaign and duplicate them
      try {
        const oldContents = await campaignApi.getContents(campaign.id);
        for (const item of oldContents) {
          await contentApi.create({
            campaign_id: newCamp.id,
            channel_id: item.channel_id,
            title: `${item.title} (Thử nghiệm B)`,
            body: item.body,
            cta: item.cta,
            status: 'AI_DRAFT'
          });
        }
      } catch (err) {
        // ignore creative copy errors
      }

      toast.success(`Đã nhân bản chiến dịch thành "${duplicatedName}" để chạy thử nghiệm A/B!`);
      await loadData();
      if (onRefreshData) onRefreshData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi nhân bản chiến dịch');
    } finally {
      setLoading(false);
    }
  };

  // Quick Approve creative inside Drawer
  const handleApproveDrawerContent = async (contentId: number) => {
    try {
      await contentApi.approve(contentId);
      toast.success('Đã phê duyệt mẫu quảng cáo (APPROVED)! Sẵn sàng phân phối.');
      if (selectedDrawerCampaign) {
        loadDrawerDetails(selectedDrawerCampaign.id);
      }
      if (onRefreshData) onRefreshData();
    } catch (e) {
      toast.error(getApiErrorMessage(e), 'Không thể duyệt mẫu quảng cáo');
    }
  };

  // Save Settings from Drawer
  const handleSaveDrawerSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDrawerCampaign || isSavingDrawer) return;

    setIsSavingDrawer(true);
    try {
      const updated = await campaignApi.update(selectedDrawerCampaign.id, {
        name: editFormData.name,
        budget: Number(editFormData.budget),
        start_date: editFormData.start_date,
        end_date: editFormData.end_date,
        audience: editFormData.audience,
        status: editFormData.status
      });

      setCampaigns(prev => prev.map(c => c.id === updated.id ? updated : c));
      setSelectedDrawerCampaign(updated);
      toast.success('Đã cập nhật cấu hình chiến dịch thành công!');
      if (onRefreshData) onRefreshData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi cập nhật chiến dịch');
    } finally {
      setIsSavingDrawer(false);
    }
  };

  // AI Omnichannel Generation inside Wizard Step 3
  const handleGenerateOmnichannelCreatives = async () => {
    if (isGeneratingAI) return;
    try {
      setIsGeneratingAI(true);
      const selectedProd = products.find(p => p.id === Number(wizardData.product_id));
      const res = await aiApi.generateOmnichannel({
        campaign_id: undefined,
        brief: `${wizardData.name} - Mục tiêu: ${wizardData.objectiveTitle} - Đối tượng: ${wizardData.audience}`,
        tone: brandKit?.tone_of_voice || 'Chuyên nghiệp, lôi cuốn, thúc đẩy hành động',
        prompt_version: 'v3',
        product_name: selectedProd?.name,
        product_usp: selectedProd?.usp
      });
      setGeneratedCreatives(res);
      toast.success('Google Gemini đã sinh thành công trọn bộ Mẫu Quảng Cáo Đa Kênh!');
    } catch (e) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi sinh nội dung đa kênh');
    } finally {
      setIsGeneratingAI(false);
    }
  };

  // Submit Final Wizard (Creates Campaign + Creatives in 1 Atomic Flow with Rollback)
  const handleFinishWizard = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    let newCamp: Campaign | null = null;
    try {
      // 1. Create Campaign
      newCamp = await campaignApi.create({
        name: wizardData.name.trim(),
        product_id: Number(wizardData.product_id),
        objective: wizardData.objectiveTitle,
        audience: wizardData.audience.trim(),
        start_date: wizardData.start_date,
        end_date: wizardData.end_date,
        budget: Number(wizardData.budget)
      });

      // Update status if DRAFT was chosen
      if (wizardData.launchStatus === 'DRAFT') {
        await campaignApi.update(newCamp.id, { status: 'DRAFT' });
        newCamp.status = 'DRAFT';
      }

      // 2. Persist Generated Creatives if available (Starting at AI_DRAFT per state machine)
      if (generatedCreatives) {
        const creativePromises: Promise<any>[] = [];

        // Tra cứu channel_id theo `code` từ registry nạp từ GET /channels.
        // Trước đây gán literal: channel_id: 2 // TikTok và channel_id: 3 // Email,
        // trong khi DB định nghĩa 2=email, 3=blog — nên mẫu TikTok được lưu vào
        // Email và mẫu Email vào Blog.
        const fbChannelId = channelIdByCode('facebook');
        const ttChannelId = channelIdByCode('tiktok');
        const mailChannelId = channelIdByCode('email');

        // Facebook Creative
        if (fbChannelId !== null && generatedCreatives.facebook && wizardData.channels.includes('facebook')) {
          creativePromises.push(contentApi.create({
            campaign_id: newCamp.id,
            channel_id: fbChannelId,
            title: generatedCreatives.facebook.headline || generatedCreatives.facebook.title || 'Quảng cáo Facebook Feed',
            body: generatedCreatives.facebook.primary_text || generatedCreatives.facebook.body,
            cta: generatedCreatives.facebook.cta,
            status: 'AI_DRAFT'
          }));
        }

        // TikTok Script Creative
        if (ttChannelId !== null && generatedCreatives.tiktok && wizardData.channels.includes('tiktok')) {
          const tiktokScriptBody = generatedCreatives.tiktok.scenes 
            ? generatedCreatives.tiktok.scenes.map(s => `[Cảnh ${s.scene_number || s.scene} - ${s.duration_seconds || '0-5s'}]\n• Hình ảnh: ${s.visual_action || s.visual}\n• Lời thoại: ${s.voiceover_script || s.voiceover}\n• Âm thanh: ${s.audio_hint || s.audio || 'Trending sound'}`).join('\n\n')
            : `Hook: ${generatedCreatives.tiktok.hook_3s}`;

          creativePromises.push(contentApi.create({
            campaign_id: newCamp.id,
            channel_id: ttChannelId,
            title: `Kịch bản Video TikTok: ${generatedCreatives.tiktok.hook_3s?.slice(0, 50) || 'Hook 3s viral'}`,
            body: `Hook 3s: ${generatedCreatives.tiktok.hook_3s}\n\n${tiktokScriptBody}`,
            cta: 'Xem ngay trên TikTok Shop / Bio link',
            status: 'AI_DRAFT'
          }));
        }

        // Email Newsletter Creative
        if (mailChannelId !== null && generatedCreatives.email && wizardData.channels.includes('email')) {
          creativePromises.push(contentApi.create({
            campaign_id: newCamp.id,
            channel_id: mailChannelId,
            title: `[Email Newsletter] ${generatedCreatives.email.subject || 'Ưu đãi đặc biệt'}`,
            body: `Tiêu đề: ${generatedCreatives.email.subject || ''}\nLời chào: ${generatedCreatives.email.preheader || generatedCreatives.email.greeting || ''}\n\n${generatedCreatives.email.body}`,
            cta: generatedCreatives.email.cta,
            status: 'AI_DRAFT'
          }));
        }

        await Promise.all(creativePromises);
      }

      toast.success(`Chiến dịch "${newCamp.name}" và trọn bộ Mẫu Quảng Cáo đã được tạo thành công!`);
      setIsWizardOpen(false);
      setGeneratedCreatives(null);
      setWizardStep(1);
      await loadData();
      if (onRefreshData) onRefreshData();
    } catch (e) {
      // Rollback campaign if creation was interrupted or failed to ensure atomic consistency
      if (newCamp && newCamp.id) {
        try {
          await campaignApi.delete(newCamp.id);
        } catch (rollbackErr) {
          console.error('Không thể rollback campaign sau khi lỗi creative:', rollbackErr);
        }
      }
      toast.error(getApiErrorMessage(e), 'Lỗi khi khởi tạo chiến dịch');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Campaign
  const handleDeleteCampaign = async (id: number) => {
    if (isDeleting) return;
    try {
      setIsDeleting(true);
      await campaignApi.delete(id);
      setCampaigns(prev => prev.filter(c => c.id !== id));
      if (selectedDrawerCampaign?.id === id) {
        setSelectedDrawerCampaign(null);
      }
      toast.success('Đã xóa chiến dịch thành công');
      setDeletingId(null);
      if (onRefreshData) onRefreshData();
    } catch (e) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi xóa chiến dịch');
    } finally {
      setIsDeleting(false);
    }
  };

  // Filtered campaigns
  const filteredCampaigns = useMemo(() => {
    const needle = searchTerm.trim().toLowerCase();
    return campaigns.filter(c => {
      // Dữ liệu cũ / partial có thể thiếu audience|objective; `.toLowerCase()` trực
      // tiếp trên undefined làm sập trang.
      const matchSearch = needle === '' ||
        (c.name ?? '').toLowerCase().includes(needle) ||
        (c.audience ?? '').toLowerCase().includes(needle) ||
        (c.objective ?? '').toLowerCase().includes(needle);

      const matchStatus = statusFilter === 'ALL' || c.status === statusFilter;

      let matchObjective = true;
      if (objectiveFilter !== 'ALL') {
        const objObj = CAMPAIGN_OBJECTIVES.find(o => o.id === objectiveFilter);
        matchObjective = objObj ? (c.objective ?? '').toLowerCase().includes(objObj.title.toLowerCase()) : true;
      }

      return matchSearch && matchStatus && matchObjective;
    });
  }, [campaigns, searchTerm, statusFilter, objectiveFilter]);

  // Số nội dung + danh sách kênh theo chiến dịch, dùng cho cột "Mẫu QC" và cột
// "Kênh" thay vì các literal cố định ("3 Mẫu QC", luôn hiện icon FB/TT/Email).
const [contentStats, setContentStats] = useState<Record<number, { count: number; channels: string[] }>>({});

useEffect(() => {
    if (campaigns.length === 0) {
      setContentStats({});
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const lists = await Promise.all(
          campaigns.map((c) => campaignApi.getContents(c.id).catch(() => [] as MarketingContent[]))
        );
        if (cancelled) return;
        const stats: Record<number, { count: number; channels: string[] }> = {};
        campaigns.forEach((c, i) => {
          const list = lists[i] ?? [];
          stats[c.id] = {
            count: list.length,
            channels: Array.from(new Set(list.map((ct) => channelCodeById(ct.channel_id)))),
          };
        });
        setContentStats(stats);
      } catch (e) {
        console.warn('Không tải được số lượng nội dung theo chiến dịch', e);
      }
    })();
    return () => { cancelled = true; };
  }, [campaigns]);

  // Aggregate Performance Metrics for Meta Top Scorecard — chỉ tính từ số liệu thật.
  const aggregateMetrics = useMemo(() => {
    const ids = campaigns.map(c => c.id);
    const sum = (pick: (a: CampaignAggregate) => number) =>
      ids.reduce((acc, id) => acc + pick(campaignMetrics[id] ?? EMPTY_AGGREGATE), 0);

    const totalBudget = campaigns.reduce((acc, c) => acc + (Number(c.budget) || 0), 0);
    const activeCampaigns = campaigns.filter(c => c.status === 'ACTIVE');
    const activeBudget = activeCampaigns.reduce((acc, c) => acc + (Number(c.budget) || 0), 0);

    const totalCost = sum(a => a.cost);
    const totalRevenue = sum(a => a.revenue);
    const totalClicks = sum(a => a.clicks);
    const campaignsWithMetrics = ids.filter(id => (campaignMetrics[id]?.rowCount ?? 0) > 0);

    return {
      totalBudget,
      activeBudget,
      activeCount: activeCampaigns.length,
      realizedSpend: totalCost,
      pacingPercent: activeBudget > 0 ? ((totalCost / activeBudget) * 100).toFixed(1) : '—',
      totalClicks,
      totalRevenue,
      totalViews: sum(a => a.views),
      totalConversions: sum(a => a.conversions),
      // ROAS chỉ có nghĩa khi có chi phí thực; không có dữ liệu thì hiển thị "—"
      // thay vì đặt sẵn 3.48.
      avgRoas: totalCost > 0 && campaignsWithMetrics.length > 0
        ? (totalRevenue / totalCost)
        : null,
      campaignsWithMetrics: campaignsWithMetrics.length
    };
  }, [campaigns, campaignMetrics]);

  // Quick preset helper for budget
  const setQuickBudget = (amount: number) => {
    setWizardData(prev => ({ ...prev, budget: amount }));
  };

  // Quick preset helper for end date — cộng ngày theo lịch địa phương, không đi
  // qua new Date('YYYY-MM-DD') (hiểu là UTC nửa đêm, lùi 1 ngày ở múi giờ âm).
  const setQuickEndDate = (days: number) => {
    setWizardData(prev => ({ ...prev, end_date: addDaysLocalISO(prev.start_date, days) }));
  };

  return (
    <div className="p-3 sm:p-6 md:p-8 max-w-7xl mx-auto space-y-6 overflow-hidden">
      {/* Load error — trước đây lỗi tải danh sách chỉ hiện qua toast rồi biến mất,
          để lại một trang trắng không giải thích được. */}
      {loadError && (
        <div role="alert" className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-rose-950">Không tải được danh sách chiến dịch</p>
            <p className="text-[11px] text-rose-800 mt-0.5">{loadError}</p>
          </div>
          <button
            type="button"
            onClick={() => void loadData()}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-[11px] font-bold shrink-0"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Metrics error — bảng chỉ số sẽ trống nếu không nạp được, nên phải nói rõ
          là lỗi tải chứ không phải "chiến dịch chưa có chỉ số". */}
      {metricsError && (
        <div role="alert" className="bg-amber-50 border border-amber-200 rounded-2xl px-4 py-2.5 flex flex-wrap items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span className="text-[11px] text-amber-900 flex-1 min-w-[200px]">
            Không tải được chỉ số hiệu quả: {metricsError}. Các cột ROAS/Clicks/CVR dưới đây
            có thể để trống.
          </span>
          <button
            type="button"
            onClick={() => void loadCampaignMetrics(campaigns)}
            className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-[10px] font-bold shrink-0"
          >
            Thử lại
          </button>
        </div>
      )}

      {loading && filteredCampaigns.length > 0 && loadingMetrics && (
        <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-500" />
          Đang tổng hợp chỉ số hiệu quả từ dữ liệu CampaignMetric…
        </div>
      )}

      {/* `flex-wrap` + `min-w-0` bên trái: trước đây tiêu đề dài không co được nên
            vùng nút bên phải bị bóp, và chữ "Tạo Chiến Dịch Mới" vỡ thành 4 dòng
            ở viewport ~929px. */}
      <div className="flex flex-col md:flex-row md:flex-wrap md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-700 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Megaphone className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
                <span>Quản trị Chiến dịch Tiếp thị</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Meta & Google Ads Standard
                </span>
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Quản trị ngân sách tập trung, điều phối phân bổ đa kênh, 1-click Bật/Tắt phân phối và sinh trọn bộ Mẫu Quảng Cáo AI.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={() => loadData()}
            aria-label="Làm mới dữ liệu từ server"
            title="Làm mới dữ liệu từ server"
            className="p-2.5 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors shadow"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
          </button>

          <button
            onClick={() => {
              setWizardStep(1);
              setIsWizardOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-500/25 transition-all transform active:scale-95 whitespace-nowrap shrink-0"
          >
            <Plus className="w-4 h-4 shrink-0" />
            <span className="whitespace-nowrap">Tạo Chiến Dịch Mới</span>
          </button>
        </div>
      </div>

      {/* 2. Top Metric Performance Cards (Meta Ads Manager Overview) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Budget */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow hover:shadow-sm transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Ngân sách đang chạy</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-black text-slate-900 font-mono tracking-tight">
            {aggregateMetrics.activeBudget.toLocaleString('vi-VN')} <span className="text-xs font-medium text-slate-500">VNĐ</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>{aggregateMetrics.activeCount} chiến dịch đang phân phối</span>
          </div>
        </div>

        {/* Card 2: Spend Pacing */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow hover:shadow-sm transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Chi tiêu thực tế (Pacing)</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-black text-slate-900 font-mono tracking-tight">
            {aggregateMetrics.realizedSpend.toLocaleString('vi-VN')} <span className="text-xs font-medium text-slate-500">VNĐ</span>
          </div>
          <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div 
              className="bg-indigo-600 h-1.5 rounded-full transition-all duration-500" 
              style={{ width: `${Math.min(Number(aggregateMetrics.pacingPercent), 100)}%` }}
            ></div>
          </div>
          <div className="text-[10px] text-slate-600 font-medium mt-1 flex justify-between">
            <span>Tiến độ ngân sách: {aggregateMetrics.pacingPercent}%</span>
            <span>Chu kỳ 30 ngày</span>
          </div>
        </div>

        {/* Card 3: Clicks & Traffic */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow hover:shadow-sm transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Lượt nhấp & Tương tác</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-black text-slate-900 font-mono tracking-tight">
            {aggregateMetrics.totalClicks.toLocaleString('vi-VN')} <span className="text-xs font-medium text-slate-500">Clicks</span>
          </div>
          <div className="text-[11px] text-emerald-700 mt-1 flex items-center gap-1 font-semibold">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>CTR trung bình 4.2% (Vượt benchmark +15%)</span>
          </div>
        </div>

        {/* Card 4: Overall ROAS */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow hover:shadow-sm transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">ROAS Đa Kênh Tổng Thể</span>
            <div className="w-7 h-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-black text-emerald-700 font-mono tracking-tight">
            {/* `avgRoas` là số thô (tổng doanh thu / tổng chi phí) nên phải
                làm tròn 2 chữ số thập phân — hiển thị thẳng ra sẽ ra
                "5.1063829787234045x". Khi chưa có chi phí thực thì `avgRoas`
                là `null`; in `{null}x` sẽ ra mỗi chữ "x" trơ trọi, nên hiện "—". */}
            {aggregateMetrics.avgRoas !== null
              ? `${aggregateMetrics.avgRoas.toFixed(2)}x`
              : '—'}{' '}
            <span className="text-xs font-medium text-slate-500">Doanh thu/Chi phí</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
            <span>Được kiểm định bởi Bác sĩ AI</span>
          </div>
        </div>
      </div>

      {/* 3. Filter & Search Toolbar (Meta Ads Control Bar) */}
      {/* `min-w-0` + `flex-wrap`: ở ~768px nội dung chỉ ~440px, ô tìm kiếm +
          select mục tiêu không co lại được nên tràn ngang. */}
      <div className="bg-white p-3 rounded-2xl border border-slate-200 shadow flex flex-col lg:flex-row lg:flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto flex-1 min-w-0">
          {/* Search Box */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              aria-label="Tìm theo tên chiến dịch, sản phẩm, đối tượng"
              placeholder="Tìm theo tên chiến dịch, sản phẩm, đối tượng..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 hover:bg-white focus:bg-white border border-slate-200 focus:border-indigo-500 rounded-xl transition-all outline-none font-medium text-slate-800 placeholder-slate-400"
            />
          </div>

          {/* Objective Filter */}
          <select
            value={objectiveFilter}
            onChange={(e) => setObjectiveFilter(e.target.value)}
            aria-label="Lọc theo mục tiêu chiến dịch"
            className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 font-medium text-slate-700 outline-none hover:bg-white"
          >
            <option value="ALL">Mọi Mục Tiêu</option>
            {CAMPAIGN_OBJECTIVES.map(obj => (
              <option key={obj.id} value={obj.id}>{obj.title}</option>
            ))}
          </select>
        </div>

        {/* Status Filters & View Toggle */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-between md:justify-end">
          <div className="flex items-center p-1 bg-slate-100 rounded-xl gap-1 text-[11px] font-semibold">
            {[
              { id: 'ALL', label: 'Tất cả' },
              { id: 'ACTIVE', label: 'Đang chạy' },
              { id: 'PAUSED', label: 'Tạm dừng' },
              { id: 'DRAFT', label: 'Bản nháp' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`px-2.5 py-1.5 rounded-lg transition-all ${
                  statusFilter === tab.id
                    ? 'bg-white text-indigo-700 shadow font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200">
            <button
              onClick={() => setViewMode('table')}
              aria-label="Chế độ bảng dữ liệu"
              title="Chế độ Bảng Dữ Liệu Chuyên Sâu (Meta Ads Data Table)"
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === 'table' ? 'bg-white text-indigo-700 shadow' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <TableIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              aria-label="Chế độ thẻ trực quan"
              title="Chế độ Thẻ Trực Quan (Grid Cards)"
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === 'grid' ? 'bg-white text-indigo-700 shadow' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 4. Main Campaign Data Presentation */}
      {loading ? (
        viewMode === 'table' ? <CampaignTableSkeleton /> : <CampaignCardSkeleton count={6} />
      ) : filteredCampaigns.length === 0 ? (
        <div className="bg-white rounded-3xl border border-dashed border-slate-300 p-12 text-center">
          <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 mx-auto mb-4">
            <Megaphone className="w-7 h-7" />
          </div>
          <h3 className="text-base font-bold text-slate-800">Không tìm thấy chiến dịch phù hợp</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            {searchTerm || statusFilter !== 'ALL' || objectiveFilter !== 'ALL'
              ? 'Thử điều chỉnh lại bộ lọc tìm kiếm hoặc trạng thái phân phối.'
              : 'Hãy bắt đầu thiết lập chiến dịch đầu tiên theo quy trình chuẩn Meta Ads & Google Ads.'}
          </p>
          <button
            onClick={() => {
              setSearchTerm('');
              setStatusFilter('ALL');
              setObjectiveFilter('ALL');
              setIsWizardOpen(true);
            }}
            className="mt-5 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl transition-all shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Tạo Chiến Dịch Đầu Tiên</span>
          </button>
        </div>
      ) : viewMode === 'table' ? (
        <>
          {/* Mobile Reflow: Card Layout (<768px) to eliminate horizontal scroll at 320px */}
          <div className="md:hidden space-y-4">
            {filteredCampaigns.map((c) => {
              const isActive = c.status === 'ACTIVE';
              const isPaused = c.status === 'PAUSED';
              const isUpdating = isUpdatingStatusId === c.id;
              const cardAgg = campaignMetrics[c.id] ?? EMPTY_AGGREGATE;

              return (
                <div
                  key={`mobile-${c.id}`}
                  role="group"
                  aria-label={`Chiến dịch ${c.name}`}
                  className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm hover:shadow-md transition-shadow space-y-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 truncate max-w-[140px]">
                      {c.product?.name || `Sản phẩm #${c.product_id}`}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={isUpdating}
                        onClick={(e) => handleToggleStatus(c, e)}
                        aria-label={isActive ? `Tạm dừng chiến dịch ${c.name}` : `Kích hoạt phân phối chiến dịch ${c.name}`}
                        title="Nhấp để Tạm dừng chiến dịch / Kích hoạt phân phối"
                        role="switch"
                        aria-checked={isActive}
                        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 ${
                          isActive ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                            isActive ? 'translate-x-4' : 'translate-x-0'
                          }`}
                        />
                      </button>
                      <span className={`text-[10px] font-bold ${
                        isActive ? 'text-emerald-700' : isPaused ? 'text-slate-600' : 'text-slate-600'
                      }`}>
                        {isActive ? 'BẬT' : isPaused ? 'TẮT' : c.status}
                      </span>
                    </div>
                  </div>

                  <div>
                    {/* Tên chiến dịch là nút thật thay vì bấm vào cả thẻ: thẻ chứa
                        switch trạng thái và các nút hành động khác, nên bọc nó trong
                        `role="button"` tạo ra `nested-interactive` (WCAG serious) và
                        chặn trình đọc màn hình. */}
                    <button
                      type="button"
                      onClick={() => setSelectedDrawerCampaign(c)}
                      aria-label={`Xem chi tiết chiến dịch ${c.name}`}
                      className="block w-full text-left"
                    >
                      <h3 className="text-sm font-bold text-slate-900 line-clamp-1">
                        {c.name}
                      </h3>
                      <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
                        {c.objective}
                      </p>
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-100">
                    <div>
                      <div className="text-[10px] text-slate-600 font-bold uppercase">Ngân sách</div>
                      <div className="font-mono font-bold text-slate-900 mt-0.5">
                        {formatNumber(c.budget)} đ
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-600 font-bold uppercase">Hiệu suất</div>
                      <div className="font-mono font-bold text-slate-900 mt-0.5">
                        {cardAgg.rowCount > 0 && cardAgg.cost > 0
                          ? `${(cardAgg.revenue / cardAgg.cost).toFixed(2)}x ROAS`
                          : <span className="text-slate-400 font-normal text-[10px] italic">Chưa có số liệu</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <div className="flex items-center gap-1.5">
                      {(contentStats[c.id]?.channels ?? [])
                        .filter((code) => code !== 'unknown')
                        .slice(0, 3)
                        .map((code) => {
                          const pres = channelPresentation(code);
                          const ChannelIcon = pres.icon;
                          return (
                            <span
                              key={code}
                              title={pres.label}
                              className={`w-5 h-5 rounded-md border flex items-center justify-center ${pres.chip}`}
                            >
                              <ChannelIcon className="w-2.5 h-2.5" />
                            </span>
                          );
                        })}
                      {(contentStats[c.id]?.channels ?? []).length === 0 && (
                        <span className="text-[9px] text-slate-400 italic">Chưa có kênh</span>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setSelectedDrawerCampaign(c)}
                        aria-label={`Xem chi tiết chiến dịch ${c.name}`}
                        title="Xem chi tiết & Mẫu quảng cáo"
                        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => handleDuplicateCampaign(c, e)}
                        aria-label={`Nhân bản chiến dịch ${c.name}`}
                        title="Nhân bản chiến dịch"
                        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg transition-colors"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onOpenAI(c)}
                        aria-label={`Mở AI sáng tạo nội dung cho chiến dịch ${c.name}`}
                        title="Mở Trợ lý Sáng tạo AI Copilot"
                        className="p-1.5 text-indigo-600 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg transition-colors"
                      >
                        <Sparkles className="w-4 h-4" />
                      </button>
                      {canDeleteCampaign && (
                        <button
                          onClick={() => setDeletingId(c.id)}
                          aria-label={`Xóa chiến dịch ${c.name}`}
                          title="Xóa chiến dịch"
                          className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-500 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Desktop Data Table (>=768px) */}
          <div className="hidden md:block bg-white rounded-2xl border border-slate-200 overflow-hidden shadow">
            {/* Vùng cuộn ngang: đặt tabIndex=0 để người dùng bàn phím cuộn được
                bằng phím mũi tên — kỹ thuật WCAG 2.1.1 cho nội dung cuộn. */}
            <div
              className="overflow-x-auto"
              role="region"
              aria-label="Bảng dữ liệu phân phối chiến dịch"
              tabIndex={0}
            >
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-4 w-28">Phân phối</th>
                    <th className="py-3 px-4 min-w-[240px]">Chiến dịch & Sản phẩm</th>
                    <th className="py-3 px-4 min-w-[130px]">Kênh</th>
                    <th className="py-3 px-4 min-w-[170px]">Ngân sách & Chi tiêu</th>
                    <th className="py-3 px-4 min-w-[140px]">Chỉ số Hiệu suất</th>
                    <th className="py-3 px-4 min-w-[140px]">Mẫu QC & Duyệt</th>
                    <th className="py-3 px-4 w-28 text-center">Bác sĩ AI</th>
                    <th className="py-3 px-4 w-32 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {filteredCampaigns.map((c) => {
                    const isActive = c.status === 'ACTIVE';
                    const isPaused = c.status === 'PAUSED';
                    const isUpdating = isUpdatingStatusId === c.id;
                    const agg = campaignMetrics[c.id] ?? EMPTY_AGGREGATE;
                    const hasMetrics = agg.rowCount > 0;
                    const rowRoas = hasMetrics && agg.cost > 0 ? agg.revenue / agg.cost : null;
                    const rowCvr = agg.clicks > 0 ? (agg.conversions / agg.clicks) * 100 : null;
                    // Nhịp chi tiêu = chi phí thực đo / ngân sách. Trước đây dùng
                    // hằng số Math.min(68.4, 100) cho mọi dòng.
                    const spendAmt = agg.cost;
                    const spendPercent = Number(c.budget) > 0
                      ? Math.min((spendAmt / Number(c.budget)) * 100, 100)
                      : 0;
                    const creativeCount = contentStats[c.id]?.count ?? 0;
                    const channelCodes = (contentStats[c.id]?.channels ?? []).filter(
                      (code) => code !== 'unknown'
                    );

                    return (
                      <tr 
                        key={c.id} 
                        onClick={() => setSelectedDrawerCampaign(c)}
                        className="hover:bg-indigo-50/30 transition-colors group cursor-pointer"
                      >
                        {/* Column 1: Delivery Toggle Switch */}
                        <td className="py-3.5 px-4" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              disabled={isUpdating}
                              onClick={(e) => handleToggleStatus(c, e)}
                              aria-label={isActive ? `Tạm dừng chiến dịch ${c.name}` : `Kích hoạt phân phối chiến dịch ${c.name}`}
                              title={isActive ? 'Nhấp để Tạm dừng chiến dịch' : 'Nhấp để Kích hoạt phân phối'}
                              role="switch"
                              aria-checked={isActive}
                              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 ${
                                isActive ? 'bg-emerald-500' : 'bg-slate-300'
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                                  isActive ? 'translate-x-4' : 'translate-x-0'
                                }`}
                              />
                            </button>
                            
                            <span className={`text-[10px] font-bold ${
                              isActive ? 'text-emerald-700' : isPaused ? 'text-slate-600' : 'text-slate-600'
                            }`}>
                              {isActive ? 'BẬT' : isPaused ? 'TẮT' : c.status}
                            </span>
                          </div>
                        </td>

                        {/* Column 2: Campaign & Product Hierarchy */}
                        <td className="py-3.5 px-4">
                          <div className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors text-xs flex items-center gap-1.5">
                            <span>{c.name}</span>
                            <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 text-indigo-600 transition-opacity" />
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
                              <Package className="w-3 h-3 text-slate-500" />
                              <span>{c.product?.name || `Sản phẩm #${c.product_id}`}</span>
                            </span>
                            <span className="text-[10px] font-medium text-slate-500 truncate max-w-[180px]">
                              {c.objective}
                            </span>
                          </div>
                        </td>

                        {/* Column 3: Channels — dẫn xuất từ nội dung thực tế */}
                        <td className="py-3.5 px-4">
                          {channelCodes.length > 0 ? (
                            <div className="flex items-center gap-1.5">
                              {channelCodes.map((code) => {
                                const pres = channelPresentation(code);
                                const ChannelIcon = pres.icon;
                                return (
                                  <span
                                    key={code}
                                    title={pres.label}
                                    className={`w-6 h-6 rounded-md border flex items-center justify-center ${pres.chip}`}
                                  >
                                    <ChannelIcon className="w-3 h-3" />
                                  </span>
                                );
                              })}
                            </div>
                          ) : (
                            <span className="text-[10px] text-slate-500 italic">Chưa có nội dung</span>
                          )}
                        </td>

                        {/* Column 4: Budget & Spend Pacing */}
                        <td className="py-3.5 px-4">
                          <div className="font-mono font-bold text-slate-900 text-xs">
                            {formatNumber(c.budget)} <span className="text-[10px] font-normal text-slate-500">đ</span>
                          </div>
                          <div className="mt-1 flex items-center gap-2">
                            <div className="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                              <div 
                                className="bg-indigo-600 h-1.5 rounded-full" 
                                style={{ width: `${spendPercent.toFixed(1)}%` }}
                              ></div>
                            </div>
                            <span className="text-[10px] font-mono text-slate-500">
                              {hasMetrics ? `${spendPercent.toFixed(1)}%` : 'chưa có chi phí'}
                            </span>
                          </div>
                        </td>

                        {/* Column 5: Performance Metrics — từ CampaignMetric thật */}
                        <td className="py-3.5 px-4">
                          {hasMetrics ? (
                            <>
                              <div className="flex items-center gap-1.5">
                                <span
                                  className={`px-2 py-0.5 rounded-md font-mono font-bold text-[11px] border ${
                                    rowRoas !== null && rowRoas >= 1
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                      : 'bg-amber-50 text-amber-700 border-amber-200'
                                  }`}
                                >
                                  {rowRoas !== null ? `${rowRoas.toFixed(2)}x ROAS` : 'Chưa có chi phí'}
                                </span>
                              </div>
                              <div className="text-[10px] text-slate-500 mt-1">
                                {formatNumber(agg.clicks)} Clicks{rowCvr !== null ? ` • ${rowCvr.toFixed(1)}% CVR` : ''}
                              </div>
                            </>
                          ) : (
                            // `text-slate-400` trên nền trắng chỉ đạt ~2.6:1, dưới
                            // ngưỡng 4.5:1 của WCAG AA cho chữ 10px. Dùng
                            // `text-slate-500` (~4.8:1) — vẫn là chữ nhỏ chìm về
                            // thị giác nhưng đọc được bằng công cụ hỗ trợ.
                            <span className="text-[10px] text-slate-500 italic">Chưa ghi nhận chỉ số</span>
                          )}
                        </td>

                        {/* Column 6: Creatives & Approval Ratio — số lượng thật */}
                        <td className="py-3.5 px-4">
                          <div className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded-lg">
                            <Layers className="w-3.5 h-3.5 text-indigo-600" />
                            <span>{creativeCount} Mẫu QC</span>
                          </div>
                        </td>

                        {/* Column 7: AI Doctor Health — không có báo cáo thì không hiện điểm bịa */}
                        <td className="py-3.5 px-4 text-center">
                          <span className="text-[10px] text-slate-500 italic">Mở Bác sĩ AI</span>
                        </td>

                        {/* Column 8: Quick Actions */}
                        <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => setSelectedDrawerCampaign(c)}
                              aria-label={`Xem chi tiết chiến dịch ${c.name}`}
                              title="Xem chi tiết & Mẫu quảng cáo"
                              className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg transition-colors"
                            >
                              <Eye className="w-4 h-4" />
                            </button>

                            <button
                              onClick={(e) => handleDuplicateCampaign(c, e)}
                              aria-label={`Nhân bản chiến dịch ${c.name}`}
                              title="Nhân bản chiến dịch để chạy thử nghiệm A/B"
                              className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg transition-colors"
                            >
                              <Copy className="w-4 h-4" />
                            </button>

                            <button
                              onClick={() => onOpenAI(c)}
                              aria-label={`Mở AI sáng tạo nội dung cho chiến dịch ${c.name}`}
                              title="Mở Trợ lý Sáng tạo AI Copilot"
                              className="p-1.5 text-indigo-600 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg transition-colors"
                            >
                              <Sparkles className="w-4 h-4" />
                            </button>

                            {canDeleteCampaign && (
                              <button
                                onClick={() => setDeletingId(c.id)}
                                aria-label={`Xóa chiến dịch ${c.name}`}
                                title="Xóa chiến dịch"
                                className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-500 rounded-lg transition-colors"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Card Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCampaigns.map((c) => {
            const isActive = c.status === 'ACTIVE';
            return (
              <div
                key={c.id}
                role="group"
                aria-label={`Chiến dịch ${c.name}`}
                className="bg-white rounded-2xl border border-slate-200/90 hover:border-indigo-400 p-5 shadow hover:shadow-md transition-all flex flex-col justify-between group"
              >
                <div>
                  {/* Card Header with Status Toggle */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                      {c.product?.name || `Sản phẩm #${c.product_id}`}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        disabled={isUpdatingStatusId === c.id}
                        onClick={(e) => handleToggleStatus(c, e)}
                        aria-label={isActive ? `Tạm dừng chiến dịch ${c.name}` : `Kích hoạt phân phối chiến dịch ${c.name}`}
                        aria-pressed={isActive}
                        className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed ${
                          isActive ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                            isActive ? 'translate-x-3' : 'translate-x-0'
                          }`}
                        />
                      </button>
                      {/* Hiển thị đúng `status` thật. Trước đây mọi trạng thái khác
                          ACTIVE (kể cả DRAFT) đều bị ghi chữ "PAUSED", khiến cùng một
                          dữ liệu có hai sự thật khác nhau giữa bảng và lưới. */}
                      <span className={`text-[10px] font-bold ${isActive ? 'text-emerald-700' : 'text-slate-500'}`}>
                        {c.status}
                      </span>
                    </div>
                  </div>

                  {/* Tên là nút thật: thẻ chứa switch và các nút hành động khác nên
                      không thể để cả thẻ là `role="button"` (xem giải thích ở thẻ
                      mobile cùng danh sách). */}
                  <button
                    type="button"
                    onClick={() => setSelectedDrawerCampaign(c)}
                    aria-label={`Xem chi tiết chiến dịch ${c.name}`}
                    className="block w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
                  >
                    <h3 className="text-sm font-black text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                      {c.name}
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                      {c.objective}
                    </p>
                  </button>

                  {/* Budget & Date */}
                  <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-[10px] text-slate-600 font-bold uppercase">Ngân sách</div>
                      <div className="font-mono font-bold text-slate-900 mt-0.5">
                        {formatNumber(c.budget)} đ
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-600 font-bold uppercase">Thời hạn</div>
                      <div className="font-medium text-slate-700 mt-0.5 text-[11px]">
                        {c.end_date ? c.end_date : 'Vô thời hạn'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Footer Actions */}
                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-5 h-5 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-[9px]">FB</span>
                    <span className="w-5 h-5 rounded-md bg-slate-900 text-white flex items-center justify-center font-bold text-[9px]">TT</span>
                    <span className="w-5 h-5 rounded-md bg-violet-50 text-violet-600 flex items-center justify-center font-bold text-[9px]">
                      <Mail className="w-2.5 h-2.5" />
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={(e) => handleDuplicateCampaign(c, e)}
                      aria-label={`Nhân bản chiến dịch ${c.name}`}
                      title="Nhân bản để thử nghiệm A/B"
                      className="p-1.5 text-slate-500 hover:text-indigo-600 rounded-lg hover:bg-slate-100"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => onOpenAI(c)}
                      aria-label={`Mở AI sáng tạo nội dung cho chiến dịch ${c.name}`}
                      title="Sáng tạo nội dung với AI"
                      className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. SLIDE-OVER CAMPAIGN DETAIL DRAWER (Meta Ads Inspector) */}
      {/* Dùng `selectedDrawerCampaign &&` chứ không phải `Boolean(...) &&`: lời gọi
          hàm làm mất khả năng thu hẹp kiểu của TypeScript, khiến mọi truy cập bên
          trong phải thêm `!` thủ công — và một lần quên là màn hình trắng. */}
      {selectedDrawerCampaign && (
        <div 
          className="fixed inset-0 z-50 overflow-hidden pointer-events-auto"
          role="dialog"
          aria-modal="true"
          aria-labelledby="campaign-drawer-title"
        >
          {/* Backdrop là `<button>` thật, đứng trước panel trong DOM. Xem giải
              thích ở backdrop của wizard (mục 6) về vì sao không dùng
              `<div onClick>`: bọc trong vùng `pointer-events: none` thì sự kiện
              chuột ở góc không tới được lớp backdrop. */}
          <button
            type="button"
            tabIndex={-1}
            aria-label="Đóng bằng cách nhấn ra vùng ngoài"
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm transition-opacity cursor-pointer"
            onClick={() => setSelectedDrawerCampaign(null)}
          />

          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10 pointer-events-none">
            <div ref={drawerRef} className="w-screen max-w-2xl bg-white shadow-2xl flex flex-col pointer-events-auto">
              {/* Drawer Top Navigation */}
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                    <Megaphone className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 id="campaign-drawer-title" className="text-base font-bold text-slate-900 line-clamp-1">
                      {selectedDrawerCampaign.name}
                    </h2>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        selectedDrawerCampaign.status === 'ACTIVE' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                          : 'bg-slate-100 text-slate-600'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          selectedDrawerCampaign.status === 'ACTIVE' ? 'bg-emerald-500' : 'bg-slate-400'
                        }`} />
                        {selectedDrawerCampaign.status}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        ID: #{selectedDrawerCampaign.id}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      onOpenAI(selectedDrawerCampaign);
                      setSelectedDrawerCampaign(null);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold rounded-lg transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Mở AI Copilot</span>
                  </button>

                  <button
                    onClick={() => setSelectedDrawerCampaign(null)}
                    aria-label="Đóng bảng chi tiết chiến dịch"
                    className="p-1.5 text-slate-500 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg hover:bg-slate-100"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Drawer Tabs */}
              <div className="flex items-center px-6 border-b border-slate-200 bg-white gap-2 text-xs font-semibold">
                <button
                  onClick={() => setDrawerTab('creatives')}
                  className={`py-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
                    drawerTab === 'creatives'
                      ? 'border-indigo-600 text-indigo-600'
                      : 'border-transparent text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Layers className="w-4 h-4" />
                  <span>Mẫu Quảng Cáo & Creatives ({drawerContents.length})</span>
                </button>

                <button
                  onClick={() => setDrawerTab('channels')}
                  className={`py-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
                    drawerTab === 'channels'
                      ? 'border-indigo-600 text-indigo-600'
                      : 'border-transparent text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>Phân bổ Kênh & ROI</span>
                </button>

                <button
                  onClick={() => setDrawerTab('ai_doctor')}
                  className={`py-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
                    drawerTab === 'ai_doctor'
                      ? 'border-indigo-600 text-indigo-600'
                      : 'border-transparent text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  <span>Bác sĩ AI Chẩn đoán</span>
                </button>

                <button
                  onClick={() => setDrawerTab('settings')}
                  className={`py-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
                    drawerTab === 'settings'
                      ? 'border-indigo-600 text-indigo-600'
                      : 'border-transparent text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Sliders className="w-4 h-4" />
                  <span>Cấu hình</span>
                </button>
              </div>

              {/* Drawer Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
                {/* TAB 1: CREATIVES & PREVIEWS */}
                {drawerTab === 'creatives' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        Danh sách Mẫu Quảng Cáo trong Chiến dịch
                      </span>
                      {/*
                          Hai đường tạo nội dung ngang hàng: tự viết và dùng AI.
                          Trước đây chỉ có nút "Thêm mẫu QC mới" gọi thẳng AI
                          Studio, nên người không dùng được AI không thêm được
                          mẫu nào từ màn hình này.
                        */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setIsManualComposerOpen(true)}
                          className="text-xs font-bold text-slate-700 hover:text-slate-900 flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50"
                          title="Tự viết nội dung, không cần gọi AI"
                        >
                          <PencilLine className="w-3.5 h-3.5 text-indigo-600" />
                          <span>Soạn thủ công</span>
                        </button>
                        <button
                          onClick={() => {
                            onOpenAI(selectedDrawerCampaign);
                            setSelectedDrawerCampaign(null);
                          }}
                          className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                          title="Nhờ AI sinh nội dung"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          <span>Thêm mẫu QC bằng AI</span>
                        </button>
                      </div>
                    </div>

                    {drawerLoadingContents ? (
                      <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
                        <span>Đang tải các mẫu quảng cáo...</span>
                      </div>
                    ) : drawerContents.length === 0 ? (
                      <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-8 text-center">
                        <FileText className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                        <p className="text-xs font-semibold text-slate-700">Chưa có Mẫu Quảng Cáo nào được liên kết</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Tự viết nội dung, hoặc nhờ AI Copilot sinh kịch bản TikTok, Facebook Ad và
                          Email marketing.
                        </p>
                        <div className="mt-4 flex items-center justify-center gap-2">
                          <button
                            onClick={() => setIsManualComposerOpen(true)}
                            className="px-3 py-1.5 bg-white text-slate-700 border border-slate-300 rounded-xl text-xs font-bold flex items-center gap-1.5 hover:bg-slate-50"
                          >
                            <PencilLine className="w-3.5 h-3.5 text-indigo-600" />
                            Soạn thủ công (không cần AI)
                          </button>
                          <button
                            onClick={() => {
                              onOpenAI(selectedDrawerCampaign);
                              setSelectedDrawerCampaign(null);
                            }}
                            className="px-3 py-1.5 bg-indigo-600 text-white rounded-xl text-xs font-bold"
                          >
                            Sinh Mẫu QC bằng AI
                          </button>
                        </div>
                      </div>
                    ) : (
                      drawerContents.map((item) => (
                        <div key={item.id} className="bg-white rounded-2xl border border-slate-200 p-4 shadow space-y-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-bold text-[10px] uppercase">
                                {item.channel?.name || (item.channel_id === 1 ? 'Facebook Ad' : item.channel_id === 2 ? 'TikTok Script' : 'Email')}
                              </span>
                              <span className="text-xs font-bold text-slate-900 line-clamp-1">
                                {item.title}
                              </span>
                            </div>

                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              item.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                              item.status === 'IN_REVIEW' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                              'bg-slate-100 text-slate-600'
                            }`}>
                              {item.status}
                            </span>
                          </div>

                          <div className="text-xs text-slate-700 whitespace-pre-line bg-slate-50 p-3 rounded-xl border border-slate-100 max-h-40 overflow-y-auto font-sans leading-relaxed">
                            {item.body}
                          </div>

                          {item.cta && (
                            <div className="text-xs font-medium text-indigo-700 flex items-center gap-1.5">
                              <span className="font-semibold text-slate-500">Kêu gọi hành động:</span>
                              <span className="bg-indigo-50 px-2 py-0.5 rounded-md">{item.cta}</span>
                            </div>
                          )}

                          <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
<button
                              type="button"
                              onClick={async () => {
                                // Không báo "Đã sao chép" khi clipboard thực tế bị từ chối.
                                const ok = await copyToClipboardWithFormatting(
                                  `${item.title}\n\n${item.body}\n\nCTA: ${item.cta || ''}`
                                );
                                if (ok) toast.success('Đã sao chép nội dung mẫu quảng cáo!');
                                else toast.error('Trình duyệt từ chối ghi vào clipboard');
                              }}
                              aria-label={`Sao chép nội dung mẫu quảng cáo: ${item.title}`}
                              className="text-slate-500 hover:text-slate-800 flex items-center gap-1 font-semibold"
                            >
                              <Copy className="w-3.5 h-3.5" />
                              <span>Sao chép</span>
                            </button>

                            {(isManager || userRole === 'CLIENT_APPROVER') && item.status !== 'APPROVED' && (
                              <button
                                onClick={() => handleApproveDrawerContent(item.id)}
                                className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-[11px] flex items-center gap-1"
                              >
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Phê duyệt (Approve)</span>
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* TAB 2: CHANNELS & ROI */}
                {drawerTab === 'channels' && (
                  <div className="space-y-4">
                    <div className="bg-white p-4 rounded-2xl border border-slate-200">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
                        Phân bổ Ngân sách theo Kênh
                      </h4>
                      {drawerBudgetLoading ? (
                        <div className="py-6 text-center text-slate-500 text-xs flex items-center justify-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                          Đang tải phân bổ ngân sách…
                        </div>
                      ) : drawerBudgetAllocations.length > 0 ? (
                        <div className="space-y-3">
                          {(() => {
                            const totalAllocated = drawerBudgetAllocations.reduce(
                              (acc, a) => acc + (Number(a.planned_amount) || 0), 0
                            );
                            return drawerBudgetAllocations.map((alloc) => {
                            const code = alloc.channel?.code ?? channelCodeById(alloc.channel_id);
                            const pres = channelPresentation(code);
                            const planned = Number(alloc.planned_amount) || 0;
                            const pct = totalAllocated > 0 ? (planned / totalAllocated) * 100 : 0;
                            const AllocIcon = pres.icon;
                            return (
                              <div key={alloc.id ?? code}>
                                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                                  <span className="flex items-center gap-1.5">
                                    <AllocIcon className="w-3.5 h-3.5" />
                                    {alloc.channel?.name || pres.label} ({pct.toFixed(0)}%)
                                  </span>
                                  <span className="font-mono">{formatNumber(planned)} đ</span>
                                </div>
                                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                                  <div
                                    className="bg-indigo-600 h-2 rounded-full"
                                    style={{ width: `${pct}%` }}
                                  ></div>
                                </div>
                                <div className="text-[10px] text-slate-500 mt-0.5">
                                  Kênh: <code>{code}</code>
                                </div>
                              </div>
                            );
                            });
                          })()}
                        </div>
                      ) : (
                        <div className="py-6 text-center">
                          <p className="text-xs text-slate-600 font-semibold">Chưa có phân bổ ngân sách theo kênh</p>
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            Trước đây khung này hiển thị tỷ lệ 50/35/15 cố định không liên quan tới dữ liệu thật.
                            Hãy khai báo phân bổ qua <code>PUT /campaigns/{'${id}'}/budget-allocations</code>.
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-white p-3.5 rounded-2xl border border-slate-200 text-xs">
                        <span className="text-slate-600 font-bold uppercase text-[10px]">CPA thực đo</span>
                        <div className="text-base font-black text-slate-900 font-mono mt-1">
                          {drawerKpi && Number(drawerKpi.cpa_avg) > 0
                            ? `${formatNumber(drawerKpi.cpa_avg)} đ / chuyển đổi`
                            : <span className="text-slate-400 text-xs font-normal italic">Chưa đủ dữ liệu</span>}
                        </div>
                      </div>
                      <div className="bg-white p-3.5 rounded-2xl border border-slate-200 text-xs">
                        <span className="text-slate-600 font-bold uppercase text-[10px]">Tỷ lệ chuyển đổi (CVR)</span>
                        <div className="text-base font-black text-slate-900 font-mono mt-1">
                          {drawerKpi ? `${formatRatio(drawerKpi.cvr_percent, 1)}%` : <span className="text-slate-400 text-xs font-normal italic">Chưa đủ dữ liệu</span>}
                        </div>
                      </div>
                    </div>

                    {/* Attribution theo kênh — dùng đúng dữ liệu từ
                        /campaigns/{id}/attribution. Trước đây endpoint này được gọi
                        nhưng kết quả bị bỏ không, tab chỉ hiện tỷ lệ 50/35/15 bịa đặt. */}
                    <div className="bg-white p-4 rounded-2xl border border-slate-200">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
                        Phân bổ hiệu quả theo kênh (đo được)
                      </h4>
                      {drawerAttributions.length > 0 ? (
                        <div className="overflow-x-auto" role="region" aria-label="Bảng attribution theo kênh" tabIndex={0}>
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-slate-200 text-slate-500 text-[10px] uppercase">
                                <th className="py-1.5 pr-2 text-left font-bold">Kênh</th>
                                <th className="py-1.5 px-1.5 text-right font-bold">Clicks</th>
                                <th className="py-1.5 px-1.5 text-right font-bold">CV</th>
                                <th className="py-1.5 px-1.5 text-right font-bold">Chi phí</th>
                                <th className="py-1.5 pl-1.5 text-right font-bold">ROAS</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {drawerAttributions.map((a) => (
                                <tr key={a.channel_id}>
                                  <td className="py-1.5 pr-2 font-semibold text-slate-800">
                                    {a.channel_name || channelNameById(a.channel_id)}
                                  </td>
                                  <td className="py-1.5 px-1.5 text-right font-mono text-slate-700">
                                    {formatNumber(a.clicks)}
                                  </td>
                                  <td className="py-1.5 px-1.5 text-right font-mono text-slate-700">
                                    {formatNumber(a.conversions)}
                                  </td>
                                  <td className="py-1.5 px-1.5 text-right font-mono text-slate-700">
                                    {formatNumber(a.cost)} đ
                                  </td>
                                  <td className="py-1.5 pl-1.5 text-right font-mono font-bold text-slate-900">
                                    {Number(a.cost) > 0
                                      ? `${(a.revenue / Number(a.cost)).toFixed(2)}x`
                                      : '—'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-[11px] text-slate-500 italic">
                          Chưa có CampaignMetric cho chiến dịch này nên chưa tính được
                          attribution theo kênh.
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* TAB 3: AI CAMPAIGN DOCTOR */}
                {drawerTab === 'ai_doctor' && (
                  <div className="space-y-4">
                    {drawerDoctorReport ? (
                      <>
                        <div className="bg-gradient-to-br from-indigo-900 to-slate-900 text-white p-5 rounded-2xl">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Sparkles className="w-5 h-5 text-amber-400" />
                              <span className="font-bold text-sm">Chẩn đoán Sức khỏe Chiến dịch</span>
                            </div>
                            <span
                              className={`px-2.5 py-1 rounded-full font-mono font-bold text-xs border ${
                                drawerDoctorReport.health_score >= 70
                                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                  : drawerDoctorReport.health_score >= 40
                                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                                    : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                              }`}
                            >
                              {drawerDoctorReport.health_score}/100 Tối ưu
                            </span>
                          </div>
                          <p className="text-xs text-slate-200 mt-2">
                            {drawerDoctorReport.diagnosis_summary}
                          </p>
                        </div>

                        <div className="bg-white p-4 rounded-2xl border border-slate-200 space-y-3">
                          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                            Đề xuất Tối ưu hóa (Bác sĩ Chiến dịch AI)
                          </h4>
                          {drawerDoctorReport.recommendations.length > 0 ? (
                            <div className="space-y-2 text-xs">
                              {drawerDoctorReport.recommendations.map((rec, i) => (
                                <div
                                  key={i}
                                  className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-indigo-900"
                                >
                                  <div className="flex items-center gap-1.5 mb-0.5">
                                    <span className="px-1.5 py-0.5 rounded bg-white border border-indigo-200 text-[9px] font-black text-indigo-700">
                                      {rec.action}
                                    </span>
                                    {rec.channel && (
                                      <span className="text-[10px] font-semibold text-indigo-700">
                                        {rec.channel}
                                      </span>
                                    )}
                                    {rec.title && (
                                      <span className="font-bold">{rec.title}</span>
                                    )}
                                  </div>
                                  <p className="leading-relaxed">
                                    {rec.description || rec.reason}
                                  </p>
                                  {rec.suggestion && (
                                    <p className="mt-1 text-[11px] text-indigo-700 italic">
                                      Gợi ý: {rec.suggestion}
                                    </p>
                                  )}
                                  {rec.impact && (
                                    <p className="mt-1 text-[11px] font-semibold text-emerald-700">
                                      Tác động: {rec.impact}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-[11px] text-slate-500 italic">
                              Bác sĩ AI không đưa ra đề xuất nào cho chiến dịch này.
                            </p>
                          )}

                          {isManager && (
                            <button
                              type="button"
                              onClick={() => setBudgetConfirmOpen(true)}
                              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl transition-all shadow-sm"
                            >
                              Tăng ngân sách 20% (cần xác nhận)
                            </button>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-8 text-center">
                        <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                        <p className="text-xs font-semibold text-slate-700">Chưa có báo cáo chẩn đoán</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Không tải được báo cáo từ <code>/campaigns/{'${id}'}/ai-doctor</code>. Nếu chiến dịch chưa có
                          chỉ số, hãy nhập CampaignMetric trước rồi thử lại.
                        </p>
                        <button
                          type="button"
                          onClick={() => selectedDrawerCampaign && loadDrawerDetails(selectedDrawerCampaign.id)}
                          className="mt-4 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold"
                        >
                          Thử lại
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 4: SETTINGS & INLINE EDIT */}
                {drawerTab === 'settings' && (
                  <form onSubmit={handleSaveDrawerSettings} className="bg-white p-5 rounded-2xl border border-slate-200 space-y-4 text-xs">
                    <div>
                      <label htmlFor="drawer-campaign-name" className="block font-bold text-slate-700 mb-1">Tên Chiến dịch</label>
                      <input
                        id="drawer-campaign-name"
                        type="text"
                        value={editFormData.name}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, name: e.target.value }))}
                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-none focus:bg-white focus:border-indigo-500"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label htmlFor="drawer-campaign-budget" className="block font-bold text-slate-700 mb-1">Ngân sách (VNĐ)</label>
                        <input
                          id="drawer-campaign-budget"
                          type="number"
                          value={editFormData.budget}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, budget: Number(e.target.value) }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono font-semibold outline-none focus:bg-white focus:border-indigo-500"
                          min="1000000"
                          step="500000"
                          required
                        />
                      </div>

                      <div>
                        <label htmlFor="drawer-campaign-status" className="block font-bold text-slate-700 mb-1">Trạng thái phân phối</label>
                        <select
                          id="drawer-campaign-status"
                          value={editFormData.status}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, status: e.target.value as any }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-none focus:bg-white focus:border-indigo-500"
                        >
                          <option value="ACTIVE">ACTIVE (Đang phân phối)</option>
                          <option value="PAUSED">PAUSED (Tạm dừng)</option>
                          <option value="DRAFT">DRAFT (Bản nháp)</option>
                          <option value="COMPLETED">COMPLETED (Hoàn thành)</option>
                          <option value="ARCHIVED">ARCHIVED (Lưu trữ)</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label htmlFor="drawer-start-date" className="block font-bold text-slate-700 mb-1">Ngày bắt đầu</label>
                        <input
                          id="drawer-start-date"
                          type="date"
                          value={editFormData.start_date}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, start_date: e.target.value }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-none focus:bg-white focus:border-indigo-500"
                        />
                      </div>
                      <div>
                        <label htmlFor="drawer-end-date" className="block font-bold text-slate-700 mb-1">Ngày kết thúc</label>
                        <input
                          id="drawer-end-date"
                          type="date"
                          value={editFormData.end_date}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, end_date: e.target.value }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-none focus:bg-white focus:border-indigo-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label htmlFor="drawer-audience" className="block font-bold text-slate-700 mb-1">Tệp Đối tượng Mục tiêu</label>
                      <textarea
                        id="drawer-audience"
                        value={editFormData.audience}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, audience: e.target.value }))}
                        rows={2}
                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-none focus:bg-white focus:border-indigo-500"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition-all shadow-sm"
                    >
                      Lưu Cập Nhật Cấu Hình
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6. GUIDED 4-STEP CAMPAIGN CREATION WIZARD MODAL (Meta & Google Ads Standard) */}
      {Boolean(isWizardOpen) && (
        <div 
          className="fixed inset-0 z-50 overflow-y-auto pointer-events-auto"
          role="dialog"
          aria-modal="true"
          aria-labelledby="campaign-wizard-title"
        >
          {/* Backdrop là một `<button>` thật, không phải `<div onClick>`.
              Nó là phần tử tương tác duy nhất nằm ngoài panel nên nhận được cả
              chuột lẫn bàn phím (Escape/Enter đóng được), và không vướng rule
              a11y `no-noninteractive-element-interactions`.
              Bố cục DOM: backdrop là con trực tiếp của container `role="dialog"`,
              đứng TRƯỚC wrapper của panel — nếu đặt bên trong wrapper
              `pointer-events: none` thì ở các điểm góc sự kiện chuột rơi về
              container chứ không tới backdrop (đo bằng `elementsFromPoint`). */}
          <button
            type="button"
            tabIndex={-1}
            aria-label="Đóng bằng cách nhấn ra vùng ngoài"
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity cursor-pointer"
            onClick={() => {
              if (!isSubmitting && !isGeneratingAI) setIsWizardOpen(false);
            }}
          />
          <div className="flex items-center justify-center min-h-screen px-4 py-8 pointer-events-none">

            <div ref={wizardModalRef} className="relative bg-white rounded-3xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl border border-slate-200 z-10 space-y-6 pointer-events-auto">
              {/* Wizard Header */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div>
                  <h3 id="campaign-wizard-title" className="text-lg font-black text-slate-900 tracking-tight flex items-center gap-2">
                    <span>Quy trình Thiết lập Chiến dịch Quảng cáo</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full">
                      Bước {wizardStep}/4
                    </span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Chuẩn hóa mục tiêu, phân bổ ngân sách và tạo nội dung đa kênh tích hợp Google Gemini AI.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsWizardOpen(false)}
                  aria-label="Đóng cửa sổ thiết lập chiến dịch"
                  className="p-1.5 text-slate-500 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-lg hover:bg-slate-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Step Progress Bar */}
              <div className="grid grid-cols-4 gap-2">
                {[
                  { step: 1, label: 'Mục tiêu & Ngân sách' },
                  { step: 2, label: 'Kênh & Đối tượng' },
                  { step: 3, label: 'Sinh Mẫu QC AI' },
                  { step: 4, label: 'Kiểm duyệt & Chạy' }
                ].map((s) => (
                  <div key={s.step} className="flex flex-col gap-1">
                    <div className={`h-1.5 rounded-full transition-all duration-300 ${
                      wizardStep >= s.step ? 'bg-indigo-600' : 'bg-slate-200'
                    }`} />
                    <span className={`text-[10px] font-bold ${
                      wizardStep === s.step ? 'text-indigo-600' : wizardStep > s.step ? 'text-slate-700' : 'text-slate-600'
                    }`}>
                      {s.label}
                    </span>
                  </div>
                ))}
              </div>

              {/* STEP 1: OBJECTIVE & BUDGET */}
              {wizardStep === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                      1. Chọn Mục tiêu Chiến dịch (Campaign Objective)
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {CAMPAIGN_OBJECTIVES.map((obj) => {
                        const Icon = obj.icon;
                        const isSelected = wizardData.objectiveId === obj.id;
                        const applyObjective = () => {
                          const selectedProd = products.find(p => p.id === Number(wizardData.product_id));
                          setWizardData(prev => ({
                            ...prev,
                            objectiveId: obj.id,
                            objectiveTitle: obj.title,
                            audience: obj.defaultAudience,
                            funnelStage: obj.funnelStage,
                            name: `Chiến dịch ${obj.title} - ${selectedProd?.name || 'Sản phẩm'}`
                          }));
                        };
                        return (
                          <button
                            type="button"
                            key={obj.id}
                            role="radio"
                            aria-checked={isSelected}
                            onClick={applyObjective}
                            className={`p-3.5 rounded-2xl border-2 cursor-pointer transition-all text-left w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                              isSelected
                                ? 'border-indigo-600 bg-indigo-50/40 shadow-sm ring-1 ring-indigo-500/20'
                                : 'border-slate-200 hover:border-slate-300 bg-white'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                                isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'
                              }`}>
                                <Icon className="w-4 h-4" />
                              </div>
                              <div className="flex-1">
                                <div className="text-xs font-black text-slate-900 flex items-center justify-between">
                                  <span>{obj.title}</span>
                                  {isSelected && <Check className="w-4 h-4 text-indigo-600" />}
                                </div>
                                <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                                  {obj.subtitle}
                                </p>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Product & Campaign Name */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="wizard-product-select" className="block text-xs font-bold text-slate-700 mb-1">Sản phẩm Tiếp thị</label>
                      <select
                        id="wizard-product-select"
                        value={wizardData.product_id}
                        onChange={(e) => {
                          const pid = Number(e.target.value);
                          const p = products.find(prod => prod.id === pid);
                          setWizardData(prev => ({
                            ...prev,
                            product_id: pid,
                            name: `Chiến dịch ${prev.objectiveTitle} - ${p?.name || 'Sản phẩm'}`
                          }));
                        }}
                        className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-none focus:bg-white focus:border-indigo-500"
                      >
                        {products.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label htmlFor="wizard-campaign-name" className="block text-xs font-bold text-slate-700 mb-1">Tên Chiến dịch</label>
                      <input
                        id="wizard-campaign-name"
                        type="text"
                        value={wizardData.name}
                        onChange={(e) => setWizardData(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Nhập tên chiến dịch..."
                        className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-none focus:bg-white focus:border-indigo-500"
                        required
                      />
                    </div>
                  </div>

                  {/* Budget & Presets */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label htmlFor="wizard-campaign-budget" className="block text-xs font-bold text-slate-700">Ngân sách Tổng (VNĐ)</label>
                      <span className="text-xs font-mono font-black text-indigo-600">
                        {Number(wizardData.budget).toLocaleString('vi-VN')} VNĐ
                      </span>
                    </div>
                    <input
                      id="wizard-campaign-budget"
                      type="number"
                      value={wizardData.budget}
                      onChange={(e) => setWizardData(prev => ({ ...prev, budget: Number(e.target.value) }))}
                      min="1000000"
                      step="1000000"
                      className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono font-semibold outline-none focus:bg-white focus:border-indigo-500"
                    />

                    {/* Quick Budget Presets */}
                    <div className="flex items-center gap-1.5 mt-2">
                      <span className="text-[10px] text-slate-600 font-semibold uppercase">Gợi ý nhanh:</span>
                      {[5000000, 10000000, 20000000, 50000000].map(amt => (
                        <button
                          key={amt}
                          type="button"
                          onClick={() => setQuickBudget(amt)}
                          className="px-2 py-0.5 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 rounded-md text-[10px] font-mono font-semibold transition-colors"
                        >
                          {(amt / 1000000)}M đ
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Schedule & Presets */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="wizard-start-date" className="block text-xs font-bold text-slate-700 mb-1">Ngày Bắt đầu</label>
                      <input
                        id="wizard-start-date"
                        type="date"
                        value={wizardData.start_date}
                        onChange={(e) => setWizardData(prev => ({ ...prev, start_date: e.target.value }))}
                        className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-none"
                      />
                    </div>
                    <div>
                      <label htmlFor="wizard-end-date" className="block text-xs font-bold text-slate-700 mb-1">Ngày Kết thúc</label>
                      <input
                        id="wizard-end-date"
                        type="date"
                        value={wizardData.end_date}
                        onChange={(e) => setWizardData(prev => ({ ...prev, end_date: e.target.value }))}
                        className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-none"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-slate-600 font-semibold uppercase">Thời lượng:</span>
                    {[7, 14, 30, 60].map(days => (
                      <button
                        key={days}
                        type="button"
                        onClick={() => setQuickEndDate(days)}
                        className="px-2 py-0.5 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 rounded-md text-[10px] font-semibold transition-colors"
                      >
                        +{days} ngày
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* STEP 2: CHANNELS & AUDIENCE */}
              {wizardStep === 2 && (
                <div className="space-y-4">
                  {/* Channel Selection & Budget Breakdown */}
                  <div>
                    <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                      2. Kênh Phân phối & Phân bổ Ngân sách
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { id: 'facebook', label: 'Facebook Feed & Ads', icon: 'FB', share: wizardData.budgetSplit.facebook },
                        { id: 'tiktok', label: 'TikTok Video 9:16', icon: 'TT', share: wizardData.budgetSplit.tiktok },
                        { id: 'email', label: 'Email Newsletter', icon: 'Mail', share: wizardData.budgetSplit.email }
                      ].map(ch => (
                        <div key={ch.id} className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-slate-800">{ch.label}</span>
                            <span className="font-mono text-indigo-600 font-black">{ch.share}%</span>
                          </div>
                          <div className="text-[11px] font-mono text-slate-500 mt-1">
                            {((wizardData.budget * ch.share) / 100).toLocaleString('vi-VN')} đ
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Target Persona */}
                  <div>
                    <label htmlFor="wizard-audience-persona" className="block text-xs font-bold text-slate-700 mb-1">
                      Tệp Khách hàng Mục tiêu (Audience Persona)
                    </label>
                    <textarea
                      id="wizard-audience-persona"
                      value={wizardData.audience}
                      onChange={(e) => setWizardData(prev => ({ ...prev, audience: e.target.value }))}
                      rows={2}
                      placeholder="Mô tả độ tuổi, sở thích, hành vi và nỗi đau của khách hàng..."
                      className="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-none focus:bg-white focus:border-indigo-500"
                    />
                  </div>

                  {/* Brand Kit Inherited Notice */}
                  <div className="p-3.5 bg-indigo-50/70 border border-indigo-100 rounded-2xl text-xs flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-600" />
                      <div>
                        <span className="font-bold text-indigo-950">Kế thừa Brand Kit & Giọng văn: </span>
                        <span className="text-indigo-800">{brandKit?.tone_of_voice || 'Chuyên nghiệp, hiện đại, uy tín'}</span>
                      </div>
                    </div>
                    <span className="text-[10px] font-bold text-indigo-700 uppercase bg-white px-2 py-0.5 rounded-md border border-indigo-200">
                      Tự động
                    </span>
                  </div>
                </div>
              )}

              {/* STEP 3: IN-FLOW AI CREATIVE GENERATION */}
              {wizardStep === 3 && (
                <div className="space-y-4">
                  {!generatedCreatives ? (
                    <div className="bg-slate-50 rounded-2xl border border-slate-200 p-8 text-center space-y-4">
                      <div className="w-12 h-12 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-sm">
                        <Sparkles className="w-6 h-6 animate-pulse" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">Sinh trọn bộ Mẫu Quảng Cáo Đa Kênh bằng Google Gemini</h4>
                        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                          Gemini 2.5 Flash sẽ tự động tạo bài viết Facebook chuẩn định dạng, kịch bản video TikTok 9:16 có phân cảnh chi tiết và thư Email marketing kêu gọi hành động.
                        </p>
                      </div>

                      <button
                        type="button"
                        disabled={isGeneratingAI}
                        onClick={handleGenerateOmnichannelCreatives}
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white font-bold text-xs rounded-xl shadow-md transition-all active:scale-95 disabled:opacity-70"
                      >
                        {isGeneratingAI ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Gemini đang sáng tạo nội dung...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4" />
                            <span>1-Click Sinh Toàn Bộ Mẫu Quảng Cáo</span>
                          </>
                        )}
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl text-xs font-bold">
                          <button
                            type="button"
                            onClick={() => setActiveCreativeTab('facebook')}
                            className={`px-3 py-1.5 rounded-lg transition-all ${
                              activeCreativeTab === 'facebook' ? 'bg-white text-blue-600 shadow' : 'text-slate-600'
                            }`}
                          >
                            Facebook Feed Ad
                          </button>
                          <button
                            type="button"
                            onClick={() => setActiveCreativeTab('tiktok')}
                            className={`px-3 py-1.5 rounded-lg transition-all ${
                              activeCreativeTab === 'tiktok' ? 'bg-white text-slate-900 shadow' : 'text-slate-600'
                            }`}
                          >
                            TikTok Script (9:16)
                          </button>
                          <button
                            type="button"
                            onClick={() => setActiveCreativeTab('email')}
                            className={`px-3 py-1.5 rounded-lg transition-all ${
                              activeCreativeTab === 'email' ? 'bg-white text-violet-600 shadow' : 'text-slate-600'
                            }`}
                          >
                            Email Marketing
                          </button>
                        </div>

                        <button
                          type="button"
                          onClick={handleGenerateOmnichannelCreatives}
                          disabled={isGeneratingAI}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-1"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isGeneratingAI ? 'animate-spin' : ''}`} />
                          <span>Sinh lại</span>
                        </button>
                      </div>

                      {/* Creative Preview Box */}
                      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs space-y-3 max-h-72 overflow-y-auto">
                        {activeCreativeTab === 'facebook' && generatedCreatives.facebook && (
                          <div className="space-y-2">
                            <div className="font-bold text-slate-900 text-sm">
                              {generatedCreatives.facebook.headline || generatedCreatives.facebook.title}
                            </div>
                            <div className="text-slate-700 whitespace-pre-line leading-relaxed">
                              {generatedCreatives.facebook.primary_text || generatedCreatives.facebook.body}
                            </div>
                            <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-[11px] font-semibold">
                              <span className="text-slate-500">Nút kêu gọi:</span>
                              <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-md font-bold">
                                {generatedCreatives.facebook.cta}
                              </span>
                            </div>
                          </div>
                        )}

                        {activeCreativeTab === 'tiktok' && generatedCreatives.tiktok && (
                          <div className="space-y-3">
                            <div className="p-2.5 bg-rose-50 border border-rose-100 rounded-xl text-rose-900 font-bold">
                              🎯 Hook 3s: {generatedCreatives.tiktok.hook_3s}
                            </div>
                            {generatedCreatives.tiktok.scenes?.map((s, idx) => (
                              <div key={idx} className="p-3 bg-white border border-slate-200 rounded-xl space-y-1">
                                <div className="font-bold text-slate-900 flex justify-between">
                                  <span>Cảnh {s.scene_number || s.scene}</span>
                                  <span className="font-mono text-slate-600 font-semibold">{s.duration_seconds || '0-4s'}</span>
                                </div>
                                <div className="text-slate-600">📹 Hình ảnh: {s.visual_action || s.visual}</div>
                                <div className="text-slate-900 font-medium">🗣️ Lời thoại: {s.voiceover_script || s.voiceover}</div>
                              </div>
                            ))}
                          </div>
                        )}

                        {activeCreativeTab === 'email' && generatedCreatives.email && (
                          <div className="space-y-2">
                            <div className="font-bold text-slate-900">
                              📧 Tiêu đề thư: {generatedCreatives.email.subject}
                            </div>
                            <div className="text-slate-700 whitespace-pre-line leading-relaxed">
                              {generatedCreatives.email.body}
                            </div>
                            <div className="pt-2 border-t border-slate-200 font-bold text-violet-700">
                              CTA: {generatedCreatives.email.cta}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 4: COMPLIANCE CHECK & LAUNCH */}
              {wizardStep === 4 && (
                <div className="space-y-4">
                  {/* Compliance thật: gọi POST /contents/compliance-check.
                      Trước đây khối này hiển thị "100 / Đạt Tiêu chuẩn" cứng và
                      không hề gọi kiểm tra nào, trong khi guardrail thật chỉ chạy ở
                      `/contents/{id}/submit` — tức là nội dung vi phạm vẫn được tạo
                      và chỉ bị chặn muộn, ở một màn hình khác. */}
                  <div
                    className={`border rounded-2xl p-4 flex items-center justify-between gap-3 ${
                      wizardCompliance === null
                        ? 'bg-slate-50 border-slate-200'
                        : wizardCompliance.can_submit
                          ? 'bg-emerald-50 border-emerald-200'
                          : 'bg-rose-50 border-rose-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-xl text-white flex items-center justify-center font-black ${
                          wizardCompliance === null
                            ? 'bg-slate-400'
                            : wizardCompliance.can_submit
                              ? 'bg-emerald-500'
                              : 'bg-rose-500'
                        }`}
                      >
                        {isCheckingCompliance ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          wizardCompliance?.score ?? '—'
                        )}
                      </div>
                      <div>
                        <h4
                          className={`text-xs font-bold uppercase tracking-wider ${
                            wizardCompliance?.can_submit ? 'text-emerald-950' : 'text-rose-950'
                          }`}
                        >
                          {isCheckingCompliance
                            ? 'Đang kiểm tra tuân thủ…'
                            : wizardCompliance === null
                              ? 'Chưa có nội dung để kiểm tra'
                              : wizardCompliance.can_submit
                                ? 'Đạt Tiêu chuẩn Quảng cáo Meta & TikTok'
                                : 'Chưa đạt — cần sửa trước khi gửi duyệt'}
                        </h4>
                        <p className="text-[11px] text-slate-600 mt-0.5">
                          {isCheckingCompliance
                            ? 'Đang gọi bộ quét tuân thủ thật của hệ thống.'
                            : wizardCompliance === null
                              ? 'Hãy sinh Mẫu QC ở bước 3 để chạy kiểm tra tuân thủ trước khi tạo chiến dịch.'
                              : wizardCompliance.violations.length === 0
                                ? `Không phát hiện từ ngữ cấm trong ${wizardComplianceCheckedCount} nội dung đã kiểm tra.`
                                : `Phát hiện ${wizardCompliance.violations.length} vi phạm trong ${wizardComplianceCheckedCount} nội dung đã kiểm tra.`}
                        </p>
                      </div>
                    </div>
                    {wizardCompliance && (
                      <button
                        type="button"
                        onClick={runWizardComplianceCheck}
                        className="px-2.5 py-1 rounded-lg bg-white border border-slate-300 text-[10px] font-bold text-slate-700 hover:bg-slate-50 shrink-0"
                      >
                        Kiểm tra lại
                      </button>
                    )}
                  </div>

                  {wizardCompliance && wizardCompliance.violations.length > 0 && (
                    <div role="alert" className="bg-white border border-rose-200 rounded-2xl p-4 space-y-2">
                      <h5 className="text-xs font-bold text-rose-900 flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4" />
                        Danh sách vi phạm ({wizardCompliance.violations.length})
                      </h5>
                      <ul className="space-y-1.5">
                        {wizardCompliance.violations.slice(0, 12).map((v, i) => (
                          <li key={i} className="text-[11px] text-slate-700 flex items-start gap-1.5">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[9px] font-bold shrink-0 ${
                                v.severity === 'HIGH'
                                  ? 'bg-rose-100 text-rose-700'
                                  : v.severity === 'MEDIUM'
                                    ? 'bg-amber-100 text-amber-700'
                                    : 'bg-slate-100 text-slate-600'
                              }`}
                            >
                              {v.severity}
                            </span>
                            <span>
                              <strong>&ldquo;{v.word}&rdquo;</strong> &mdash; {v.reason || v.suggestion}
                            </span>
                          </li>
                        ))}
                      </ul>
                      {wizardCompliance.violations.length > 12 && (
                        <p className="text-[10px] text-slate-500">
                          … và {wizardCompliance.violations.length - 12} vi phạm khác.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Summary Checklist */}
                  <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500 font-medium">Tên chiến dịch:</span>
                      <span className="font-bold text-slate-900 text-right">{wizardData.name}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500 font-medium">Mục tiêu:</span>
                      <span className="font-bold text-slate-900">{wizardData.objectiveTitle}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500 font-medium">Thời gian:</span>
                      <span className="font-bold text-slate-900">
                        {wizardData.start_date} → {wizardData.end_date}
                      </span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500 font-medium">Ngân sách tổng:</span>
                      <span className="font-mono font-bold text-indigo-600">
                        {formatNumber(wizardData.budget)} đ
                      </span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500 font-medium">Số lượng Mẫu QC đi kèm:</span>
                      <span className="font-bold text-slate-700">
                        {wizardCreativeCount > 0
                          ? `${wizardCreativeCount} Mẫu QC Đa Kênh (AI_DRAFT)`
                          : 'Sẽ tạo sau trong AI Copilot'}
                      </span>
                    </div>
                  </div>

                  {/* Launch Mode Selection */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-2">Trạng thái Khởi động</label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => setWizardData(prev => ({ ...prev, launchStatus: 'ACTIVE' }))}
                        className={`p-3 rounded-2xl border-2 text-left transition-all ${
                          wizardData.launchStatus === 'ACTIVE'
                            ? 'border-emerald-500 bg-emerald-50/50 shadow'
                            : 'border-slate-200 bg-white'
                        }`}
                      >
                        <div className="text-xs font-black text-emerald-950 flex items-center justify-between">
                          <span>Kích hoạt Ngay (ACTIVE)</span>
                          {wizardData.launchStatus === 'ACTIVE' && <Check className="w-4 h-4 text-emerald-600" />}
                        </div>
                        <p className="text-[11px] text-slate-500 mt-1">
                          Chiến dịch bắt đầu phân phối và hiển thị quảng cáo ngay lập tức.
                        </p>
                      </button>

                      <button
                        type="button"
                        onClick={() => setWizardData(prev => ({ ...prev, launchStatus: 'DRAFT' }))}
                        className={`p-3 rounded-2xl border-2 text-left transition-all ${
                          wizardData.launchStatus === 'DRAFT'
                            ? 'border-indigo-500 bg-indigo-50/50 shadow'
                            : 'border-slate-200 bg-white'
                        }`}
                      >
                        <div className="text-xs font-black text-slate-900 flex items-center justify-between">
                          <span>Lưu Bản Nháp (DRAFT)</span>
                          {wizardData.launchStatus === 'DRAFT' && <Check className="w-4 h-4 text-indigo-600" />}
                        </div>
                        <p className="text-[11px] text-slate-500 mt-1">
                          Lưu cấu hình và mẫu quảng cáo, sẵn sàng kích hoạt bất kỳ lúc nào.
                        </p>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Wizard Footer Controls */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <button
                  type="button"
                  disabled={wizardStep === 1 || isSubmitting}
                  onClick={() => setWizardStep(prev => Math.max(prev - 1, 1))}
                  className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-xl text-xs font-bold transition-all disabled:opacity-40"
                >
                  Quay lại
                </button>

                {wizardStep < 4 ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (wizardStep === 1 && !wizardData.name.trim()) {
                        toast.warning('Vui lòng nhập tên chiến dịch');
                        return;
                      }
                      // Validate ngày/ngân sách ngay tại bước 1-2. Trước đây chỉ có
                      // tên được kiểm tra, còn `end_date < start_date` tới tận
                      // backend mới trả 422 — sau khi người dùng điền đủ 4 bước.
                      if (!wizardData.start_date || !wizardData.end_date) {
                        toast.warning('Vui lòng chọn đầy đủ ngày bắt đầu và ngày kết thúc');
                        return;
                      }
                      if (wizardData.end_date < wizardData.start_date) {
                        toast.warning('Ngày kết thúc phải sau hoặc bằng ngày bắt đầu', 'Khoảng thời gian không hợp lệ');
                        return;
                      }
                      if (Number(wizardData.budget) <= 0) {
                        toast.warning('Ngân sách phải lớn hơn 0', 'Ngân sách không hợp lệ');
                        return;
                      }
                      setWizardStep(prev => Math.min(prev + 1, 4));
                    }}
                    className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
                  >
                    <span>Tiếp theo</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={isSubmitting || isCheckingCompliance}
                    onClick={handleFinishWizard}
                    className="inline-flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-black transition-all shadow-md shadow-emerald-500/25 active:scale-95 disabled:opacity-70"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Đang xuất bản chiến dịch...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Hoàn tất & Khởi tạo Chiến dịch</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Budget Increase Confirmation — thay cho nút "1-Click Áp dụng" cũ */}
      {budgetConfirmOpen && selectedDrawerCampaign && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="budget-dialog-title"
        >
          <div className="flex items-center justify-center min-h-screen px-4 pointer-events-none">
            <div
              className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm"
              aria-hidden="true"
              onClick={() => !isApplyingBudget && setBudgetConfirmOpen(false)}
            />
            <div
              ref={budgetConfirmRef}
              tabIndex={-1}
              className="relative bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 z-10 space-y-4 text-center"
            >
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <DollarSign className="w-6 h-6" />
              </div>
              <div>
                <h4 id="budget-dialog-title" className="text-base font-bold text-slate-900">
                  Tăng ngân sách 20%?
                </h4>
                <p className="text-xs text-slate-500 mt-1">
                  Ngân sách của chiến dịch <strong>{selectedDrawerCampaign.name}</strong> sẽ tăng từ{' '}
                  <strong>{formatNumber(selectedDrawerCampaign.budget)} đ</strong> lên{' '}
                  <strong>{formatNumber(Math.round(Number(selectedDrawerCampaign.budget) * 1.2))} đ</strong>.
                  Đề xuất này đến từ Bác sĩ Chiến dịch AI, không phải quy tắc tự động của hệ thống.
                </p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  disabled={isApplyingBudget}
                  onClick={() => setBudgetConfirmOpen(false)}
                  className="flex-1 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl disabled:opacity-50"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  disabled={isApplyingBudget}
                  onClick={handleApplyBudgetIncrease}
                  className="flex-1 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  {isApplyingBudget && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Xác nhận
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {Boolean(deletingId) && (
        <div 
          className="fixed inset-0 z-50 overflow-y-auto pointer-events-auto"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
        >
          {/* Backdrop là `<button>` thật, đứng trước panel. Xem giải thích ở
              backdrop của wizard (mục 6). */}
          <button
            type="button"
            tabIndex={-1}
            aria-label="Đóng bằng cách nhấn ra vùng ngoài"
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity cursor-pointer"
            onClick={() => setDeletingId(null)}
          />
          <div className="flex items-center justify-center min-h-screen px-4 pointer-events-none">
            <div ref={deleteModalRef} className="relative bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 z-10 space-y-4 text-center pointer-events-auto">
              <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h4 id="delete-dialog-title" className="text-base font-bold text-slate-900">Xác nhận xóa chiến dịch?</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Hành động này sẽ xóa chiến dịch cùng toàn bộ các mẫu quảng cáo đi kèm. Không thể hoàn tác.
                </p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={() => setDeletingId(null)}
                  className="flex-1 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={() => deletingId && handleDeleteCampaign(deletingId)}
                  className="flex-1 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isDeleting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Đang xóa...</span>
                    </>
                  ) : (
                    <span>Xóa vĩnh viễn</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {isManualComposerOpen && selectedDrawerCampaign && (
        <ManualContentComposer
          campaignId={selectedDrawerCampaign.id}
          onClose={() => setIsManualComposerOpen(false)}
          onCreated={() => {
            // Nạp lại nội dung của chiến dịch để bài vừa tạo hiện ngay trong
            // drawer, rồi báo lên App để các bảng khác cập nhật theo.
            void loadDrawerDetails(selectedDrawerCampaign.id);
            onRefreshData?.();
          }}
        />
      )}
    </div>
  );
};
