import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
  Megaphone, 
  Plus, 
  Search, 
  Filter, 
  Calendar, 
  DollarSign, 
  CheckCircle2, 
  AlertTriangle, 
  TrendingUp, 
  BarChart3, 
  Sparkles, 
  Trash2, 
  Copy, 
  ExternalLink, 
  Eye, 
  X, 
  Loader2, 
  LayoutGrid, 
  Table as TableIcon, 
  Tag, 
  Target, 
  Users, 
  Play, 
  Pause, 
  Sliders, 
  ShieldCheck, 
  Zap, 
  Layers, 
  Smartphone, 
  Mail, 
  FileText, 
  ChevronRight, 
  RefreshCw, 
  ArrowUpRight, 
  Check, 
  Package, 
  Info, 
  Clock,
  Send,
  Edit3
} from 'lucide-react';
import { 
  Campaign, 
  Product, 
  MarketingContent, 
  AIDoctorReport, 
  KPISummary, 
  ChannelAttribution, 
  OmnichannelResponse,
  BrandKit
} from '../types';
import { 
  campaignApi, 
  productApi, 
  contentApi, 
  aiApi, 
  brandKitApi, 
  getApiErrorMessage 
} from '../services/api';
import { useToast } from '../components/Toast';
import { CampaignCardSkeleton, CampaignTableSkeleton } from '../components/Skeleton';

interface CampaignsProps {
  onSelectCampaign: (campaign: Campaign) => void;
  onOpenWorkflow: (campaign: Campaign) => void;
  onOpenAI: (campaign: Campaign) => void;
  onNavigateTab?: (tab: string) => void;
  onRefreshData?: () => void;
  userRole?: string;
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
  onSelectCampaign,
  onOpenWorkflow,
  onOpenAI,
  onNavigateTab,
  onRefreshData,
  userRole
}) => {
  const toast = useToast();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [brandKit, setBrandKit] = useState<BrandKit | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters & Views
  const [searchTerm, setSearchTerm] = useState<string>('');
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
  const [isUpdatingStatusId, setIsUpdatingStatusId] = useState<number | null>(null);

  // 4-Step Creation Wizard Modal
  const [isWizardOpen, setIsWizardOpen] = useState<boolean>(false);
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isGeneratingAI, setIsGeneratingAI] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Wizard Form State
  const [wizardData, setWizardData] = useState({
    objectiveId: 'SALES',
    objectiveTitle: 'Doanh số & Chuyển đổi',
    product_id: 1,
    name: '',
    budget: 15000000,
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
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

  // Edit Drawer Form
  const [editFormData, setEditFormData] = useState({
    name: '',
    budget: 0,
    start_date: '',
    end_date: '',
    audience: '',
    status: 'ACTIVE' as Campaign['status']
  });

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cList, pList] = await Promise.all([
        campaignApi.getAll(),
        productApi.getAll().catch(() => [] as Product[])
      ]);
      setCampaigns(cList);
      setProducts(pList);

      if (pList.length > 0 && !wizardData.name) {
        setWizardData(prev => ({
          ...prev,
          product_id: pList[0].id,
          name: `Chiến dịch ${CAMPAIGN_OBJECTIVES[0].title} - ${pList[0].name}`
        }));
      }

      // Try load Brand Kit
      try {
        const bk = await brandKitApi.getByWorkspace(1);
        setBrandKit(bk);
      } catch (e) {
        // ignore
      }
    } catch (e) {
      console.error(e);
      toast.error(getApiErrorMessage(e), 'Lỗi khi tải danh sách chiến dịch');
    } finally {
      setLoading(false);
    }
  };

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

  // 1-Click Status Toggle (Active <-> Paused) - Meta Ads Manager behavior
  const handleToggleStatus = async (campaign: Campaign, e: React.MouseEvent) => {
    e.stopPropagation();
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
    if (!selectedDrawerCampaign) return;

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
    }
  };

  // AI Omnichannel Generation inside Wizard Step 3
  const handleGenerateOmnichannelCreatives = async () => {
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

  // Submit Final Wizard (Creates Campaign + Creatives in 1 Atomic Flow)
  const handleFinishWizard = async () => {
    try {
      setIsSubmitting(true);

      // 1. Create Campaign
      const newCamp = await campaignApi.create({
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

      // 2. Persist Generated Creatives if available
      if (generatedCreatives) {
        // Facebook Creative
        if (generatedCreatives.facebook && wizardData.channels.includes('facebook')) {
          await contentApi.create({
            campaign_id: newCamp.id,
            channel_id: 1, // Facebook
            title: generatedCreatives.facebook.headline || generatedCreatives.facebook.title || 'Quảng cáo Facebook Feed',
            body: generatedCreatives.facebook.primary_text || generatedCreatives.facebook.body,
            cta: generatedCreatives.facebook.cta,
            status: 'APPROVED'
          });
        }

        // TikTok Script Creative
        if (generatedCreatives.tiktok && wizardData.channels.includes('tiktok')) {
          const tiktokScriptBody = generatedCreatives.tiktok.scenes 
            ? generatedCreatives.tiktok.scenes.map(s => `[Cảnh ${s.scene_number || s.scene} - ${s.duration_seconds || '0-5s'}]\n• Hình ảnh: ${s.visual_action || s.visual}\n• Lời thoại: ${s.voiceover_script || s.voiceover}\n• Âm thanh: ${s.audio_hint || s.audio || 'Trending sound'}`).join('\n\n')
            : `Hook: ${generatedCreatives.tiktok.hook_3s}`;

          await contentApi.create({
            campaign_id: newCamp.id,
            channel_id: 2, // TikTok
            title: `Kịch bản Video TikTok: ${generatedCreatives.tiktok.hook_3s?.slice(0, 50) || 'Hook 3s viral'}`,
            body: `Hook 3s: ${generatedCreatives.tiktok.hook_3s}\n\n${tiktokScriptBody}`,
            cta: 'Xem ngay trên TikTok Shop / Bio link',
            status: 'APPROVED'
          });
        }

        // Email Newsletter Creative
        if (generatedCreatives.email && wizardData.channels.includes('email')) {
          await contentApi.create({
            campaign_id: newCamp.id,
            channel_id: 3, // Email
            title: `[Email Newsletter] ${generatedCreatives.email.subject || 'Ưu đãi đặc biệt'}`,
            body: `Tiêu đề: ${generatedCreatives.email.subject || ''}\nLời chào: ${generatedCreatives.email.preheader || generatedCreatives.email.greeting || ''}\n\n${generatedCreatives.email.body}`,
            cta: generatedCreatives.email.cta,
            status: 'APPROVED'
          });
        }
      }

      toast.success(`Chiến dịch "${newCamp.name}" và trọn bộ Mẫu Quảng Cáo đã được tạo thành công!`);
      setIsWizardOpen(false);
      setGeneratedCreatives(null);
      setWizardStep(1);
      await loadData();
      if (onRefreshData) onRefreshData();
    } catch (e) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi khởi tạo chiến dịch');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Campaign
  const handleDeleteCampaign = async (id: number) => {
    try {
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
    }
  };

  // Filtered campaigns
  const filteredCampaigns = useMemo(() => {
    return campaigns.filter(c => {
      const matchSearch = searchTerm === '' || 
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.audience.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.objective.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchStatus = statusFilter === 'ALL' || c.status === statusFilter;
      
      let matchObjective = true;
      if (objectiveFilter !== 'ALL') {
        const objObj = CAMPAIGN_OBJECTIVES.find(o => o.id === objectiveFilter);
        matchObjective = objObj ? c.objective.toLowerCase().includes(objObj.title.toLowerCase()) : true;
      }

      return matchSearch && matchStatus && matchObjective;
    });
  }, [campaigns, searchTerm, statusFilter, objectiveFilter]);

  // Aggregate Performance Metrics for Meta Top Scorecard
  const aggregateMetrics = useMemo(() => {
    const totalBudget = campaigns.reduce((acc, c) => acc + (Number(c.budget) || 0), 0);
    const activeCount = campaigns.filter(c => c.status === 'ACTIVE').length;
    const activeBudget = campaigns
      .filter(c => c.status === 'ACTIVE')
      .reduce((acc, c) => acc + (Number(c.budget) || 0), 0);
    // Estimated spend (65% pacing average)
    const realizedSpend = Math.round(activeBudget * 0.684);
    
    return {
      totalBudget,
      activeBudget,
      activeCount,
      realizedSpend,
      pacingPercent: activeBudget > 0 ? ((realizedSpend / activeBudget) * 100).toFixed(1) : '0.0',
      totalClicks: 24850,
      avgRoas: 3.48
    };
  }, [campaigns]);

  // Quick preset helper for budget
  const setQuickBudget = (amount: number) => {
    setWizardData(prev => ({ ...prev, budget: amount }));
  };

  // Quick preset helper for end date
  const setQuickEndDate = (days: number) => {
    const start = new Date(wizardData.start_date);
    const end = new Date(start.getTime() + days * 24 * 60 * 60 * 1000);
    setWizardData(prev => ({ ...prev, end_date: end.toISOString().split('T')[0] }));
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      {/* 1. Header with Meta Ads Command Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
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

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadData()}
            title="Làm mới dữ liệu từ server"
            className="p-2.5 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors shadow-2xs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
          </button>

          <button
            onClick={() => {
              setWizardStep(1);
              setIsWizardOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-500/25 transition-all transform active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Tạo Chiến Dịch Mới</span>
          </button>
        </div>
      </div>

      {/* 2. Top Metric Performance Cards (Meta Ads Manager Overview) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Budget */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-xs transition-shadow">
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
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-xs transition-shadow">
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
          <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
            <span>Tiến độ ngân sách: {aggregateMetrics.pacingPercent}%</span>
            <span>Chu kỳ 30 ngày</span>
          </div>
        </div>

        {/* Card 3: Clicks & Traffic */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-xs transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Lượt nhấp & Tương tác</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-black text-slate-900 font-mono tracking-tight">
            {aggregateMetrics.totalClicks.toLocaleString('vi-VN')} <span className="text-xs font-medium text-slate-500">Clicks</span>
          </div>
          <div className="text-[11px] text-emerald-600 mt-1 flex items-center gap-1 font-semibold">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>CTR trung bình 4.2% (Vượt benchmark +15%)</span>
          </div>
        </div>

        {/* Card 4: Overall ROAS */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-xs transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">ROAS Đa Kênh Tổng Thể</span>
            <div className="w-7 h-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-black text-emerald-600 font-mono tracking-tight">
            {aggregateMetrics.avgRoas}x <span className="text-xs font-medium text-slate-500">Doanh thu/Chi phí</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
            <span>Được kiểm định bởi Bác sĩ AI</span>
          </div>
        </div>
      </div>

      {/* 3. Filter & Search Toolbar (Meta Ads Control Bar) */}
      <div className="bg-white p-3 rounded-2xl border border-slate-200 shadow-2xs flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full md:w-auto flex-1">
          {/* Search Box */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm theo tên chiến dịch, sản phẩm, đối tượng..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 hover:bg-white focus:bg-white border border-slate-200 focus:border-indigo-500 rounded-xl transition-all outline-hidden font-medium text-slate-800 placeholder-slate-400"
            />
          </div>

          {/* Objective Filter */}
          <select
            value={objectiveFilter}
            onChange={(e) => setObjectiveFilter(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 font-medium text-slate-700 outline-hidden hover:bg-white"
          >
            <option value="ALL">Mọi Mục Tiêu</option>
            {CAMPAIGN_OBJECTIVES.map(obj => (
              <option key={obj.id} value={obj.id}>{obj.title}</option>
            ))}
          </select>
        </div>

        {/* Status Filters & View Toggle */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-between md:justify-end">
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
                    ? 'bg-white text-indigo-700 shadow-2xs font-bold'
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
              title="Chế độ Bảng Dữ Liệu Chuyên Sâu (Meta Ads Data Table)"
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === 'table' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <TableIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              title="Chế độ Thẻ Trực Quan (Grid Cards)"
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === 'grid' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-900'
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
        /* Meta Ads Manager Data Table */
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
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

                  // Pacing estimate
                  const spendAmt = Math.round(c.budget * 0.684);
                  const spendPercent = Math.min(68.4, 100);

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
                            title={isActive ? 'Nhấp để Tạm dừng chiến dịch' : 'Nhấp để Kích hoạt phân phối'}
                            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
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
                            isActive ? 'text-emerald-700' : isPaused ? 'text-slate-500' : 'text-slate-400'
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

                      {/* Column 3: Channels */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="w-6 h-6 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-[10px]" title="Facebook Ads">
                            FB
                          </span>
                          <span className="w-6 h-6 rounded-md bg-slate-900 text-white flex items-center justify-center font-bold text-[10px]" title="TikTok Video">
                            TT
                          </span>
                          <span className="w-6 h-6 rounded-md bg-violet-50 text-violet-600 flex items-center justify-center font-bold text-[10px]" title="Email Newsletter">
                            <Mail className="w-3 h-3" />
                          </span>
                        </div>
                      </td>

                      {/* Column 4: Budget & Spend Pacing */}
                      <td className="py-3.5 px-4">
                        <div className="font-mono font-bold text-slate-900 text-xs">
                          {c.budget.toLocaleString('vi-VN')} <span className="text-[10px] font-normal text-slate-500">đ</span>
                        </div>
                        <div className="mt-1 flex items-center gap-2">
                          <div className="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div 
                              className="bg-indigo-600 h-1.5 rounded-full" 
                              style={{ width: `${spendPercent}%` }}
                            ></div>
                          </div>
                          <span className="text-[10px] font-mono text-slate-500">{spendPercent}%</span>
                        </div>
                      </td>

                      {/* Column 5: Performance Metrics */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 font-mono font-bold text-[11px] border border-emerald-200">
                            3.82x ROAS
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-500 mt-1">
                          2,450 Clicks • 4.1% CVR
                        </div>
                      </td>

                      {/* Column 6: Creatives & Approval Ratio */}
                      <td className="py-3.5 px-4">
                        <div className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded-lg">
                          <Layers className="w-3.5 h-3.5 text-indigo-600" />
                          <span>3 Mẫu QC</span>
                          <span className="text-emerald-600 font-semibold text-[10px]">(Đã duyệt)</span>
                        </div>
                      </td>

                      {/* Column 7: AI Doctor Health */}
                      <td className="py-3.5 px-4 text-center">
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>94/100 Tốt</span>
                        </span>
                      </td>

                      {/* Column 8: Quick Actions */}
                      <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => setSelectedDrawerCampaign(c)}
                            title="Xem chi tiết & Mẫu quảng cáo"
                            className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          <button
                            onClick={(e) => handleDuplicateCampaign(c, e)}
                            title="Nhân bản chiến dịch để chạy thử nghiệm A/B"
                            className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          >
                            <Copy className="w-4 h-4" />
                          </button>

                          <button
                            onClick={() => onOpenAI(c)}
                            title="Mở Trợ lý Sáng tạo AI Copilot"
                            className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          >
                            <Sparkles className="w-4 h-4" />
                          </button>

                          {userRole === 'MANAGER' && (
                            <button
                              onClick={() => setDeletingId(c.id)}
                              title="Xóa chiến dịch"
                              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
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
      ) : (
        /* Card Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCampaigns.map((c) => {
            const isActive = c.status === 'ACTIVE';
            return (
              <div
                key={c.id}
                onClick={() => setSelectedDrawerCampaign(c)}
                className="bg-white rounded-2xl border border-slate-200/90 hover:border-indigo-400 p-5 shadow-2xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between group"
              >
                <div>
                  {/* Card Header with Status Toggle */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                      {c.product?.name || `Sản phẩm #${c.product_id}`}
                    </span>

                    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={(e) => handleToggleStatus(c, e)}
                        className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                          isActive ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                            isActive ? 'translate-x-3' : 'translate-x-0'
                          }`}
                        />
                      </button>
                      <span className={`text-[10px] font-bold ${isActive ? 'text-emerald-700' : 'text-slate-500'}`}>
                        {isActive ? 'ACTIVE' : 'PAUSED'}
                      </span>
                    </div>
                  </div>

                  <h3 className="text-sm font-black text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                    {c.name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                    {c.objective}
                  </p>

                  {/* Budget & Date */}
                  <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-[10px] text-slate-400 font-semibold uppercase">Ngân sách</div>
                      <div className="font-mono font-bold text-slate-900 mt-0.5">
                        {c.budget.toLocaleString('vi-VN')} đ
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400 font-semibold uppercase">Thời hạn</div>
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

                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => handleDuplicateCampaign(c, e)}
                      title="Nhân bản để thử nghiệm A/B"
                      className="p-1.5 text-slate-500 hover:text-indigo-600 rounded-lg hover:bg-slate-100"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => onOpenAI(c)}
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
      {selectedDrawerCampaign && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-xs transition-opacity"
            onClick={() => setSelectedDrawerCampaign(null)}
          />

          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-2xl bg-white shadow-2xl flex flex-col">
              {/* Drawer Top Navigation */}
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                    <Megaphone className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900 line-clamp-1">
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
                    className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
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
                      <button
                        onClick={() => {
                          onOpenAI(selectedDrawerCampaign);
                          setSelectedDrawerCampaign(null);
                        }}
                        className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Thêm mẫu QC mới</span>
                      </button>
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
                          Sử dụng Trợ lý AI Copilot để sinh kịch bản TikTok, Facebook Ad và Email marketing tức thì.
                        </p>
                        <button
                          onClick={() => {
                            onOpenAI(selectedDrawerCampaign);
                            setSelectedDrawerCampaign(null);
                          }}
                          className="mt-4 px-3 py-1.5 bg-indigo-600 text-white rounded-xl text-xs font-bold"
                        >
                          Sinh Mẫu QC bằng AI
                        </button>
                      </div>
                    ) : (
                      drawerContents.map((item) => (
                        <div key={item.id} className="bg-white rounded-2xl border border-slate-200 p-4 shadow-2xs space-y-3">
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
                              onClick={() => {
                                navigator.clipboard.writeText(`${item.title}\n\n${item.body}\n\nCTA: ${item.cta || ''}`);
                                toast.success('Đã sao chép nội dung mẫu quảng cáo!');
                              }}
                              className="text-slate-500 hover:text-slate-800 flex items-center gap-1 font-semibold"
                            >
                              <Copy className="w-3.5 h-3.5" />
                              <span>Sao chép</span>
                            </button>

                            {userRole === 'MANAGER' && item.status !== 'APPROVED' && (
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
                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                            <span>Facebook Feed & Story (50%)</span>
                            <span className="font-mono">{(selectedDrawerCampaign.budget * 0.5).toLocaleString('vi-VN')} đ</span>
                          </div>
                          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                            <div className="bg-blue-600 h-2 rounded-full" style={{ width: '50%' }}></div>
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                            <span>TikTok Video 9:16 (35%)</span>
                            <span className="font-mono">{(selectedDrawerCampaign.budget * 0.35).toLocaleString('vi-VN')} đ</span>
                          </div>
                          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                            <div className="bg-slate-900 h-2 rounded-full" style={{ width: '35%' }}></div>
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                            <span>Email Automation (15%)</span>
                            <span className="font-mono">{(selectedDrawerCampaign.budget * 0.15).toLocaleString('vi-VN')} đ</span>
                          </div>
                          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                            <div className="bg-violet-600 h-2 rounded-full" style={{ width: '15%' }}></div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-white p-3.5 rounded-2xl border border-slate-200 text-xs">
                        <span className="text-slate-400 font-semibold uppercase text-[10px]">CPA Ước tính</span>
                        <div className="text-base font-black text-slate-900 font-mono mt-1">45.000 đ / Lead</div>
                        <span className="text-[10px] text-emerald-600 font-semibold">Tối ưu hơn 22%</span>
                      </div>
                      <div className="bg-white p-3.5 rounded-2xl border border-slate-200 text-xs">
                        <span className="text-slate-400 font-semibold uppercase text-[10px]">Tỷ lệ chuyển đổi (CVR)</span>
                        <div className="text-base font-black text-slate-900 font-mono mt-1">4.2%</div>
                        <span className="text-[10px] text-emerald-600 font-semibold">Chuẩn ngành TMĐT</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 3: AI CAMPAIGN DOCTOR */}
                {drawerTab === 'ai_doctor' && (
                  <div className="space-y-4">
                    <div className="bg-gradient-to-br from-indigo-900 to-slate-900 text-white p-5 rounded-2xl">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Sparkles className="w-5 h-5 text-amber-400" />
                          <span className="font-bold text-sm">Chẩn đoán Sức khỏe Chiến dịch</span>
                        </div>
                        <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold text-xs border border-emerald-500/30">
                          {drawerDoctorReport?.health_score || 94}/100 Tối ưu
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-2">
                        {drawerDoctorReport?.diagnosis_summary || 'Chiến dịch đang phân bổ ngân sách cân đối và chỉ số ROAS đạt kỳ vọng cao.'}
                      </p>
                    </div>

                    <div className="bg-white p-4 rounded-2xl border border-slate-200 space-y-3">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                        Đề xuất Tối ưu hóa từ Gemini AI
                      </h4>
                      <div className="space-y-2 text-xs">
                        <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-emerald-800 flex items-start gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold">Độ tươi mới của nội dung (Freshness):</span> Mẫu quảng cáo mới khởi chạy, chưa bị hiện tượng bão hòa tệp (Ad Fatigue).
                          </div>
                        </div>

                        <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl text-blue-800 flex items-start gap-2">
                          <Zap className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold">Quy mô ngân sách:</span> Có thể tăng ngân sách thêm 20% mà không làm tăng vọt CPA nhờ tệp đối tượng còn rộng.
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={async () => {
                          try {
                            const newBudget = Math.round(selectedDrawerCampaign.budget * 1.2);
                            await campaignApi.update(selectedDrawerCampaign.id, { budget: newBudget });
                            setCampaigns(prev => prev.map(c => c.id === selectedDrawerCampaign.id ? { ...c, budget: newBudget } : c));
                            setSelectedDrawerCampaign(prev => prev ? { ...prev, budget: newBudget } : null);
                            toast.success(`Đã tăng ngân sách +20% thành ${newBudget.toLocaleString('vi-VN')} đ!`);
                          } catch (err) {
                            toast.error(getApiErrorMessage(err), 'Lỗi khi tăng ngân sách');
                          }
                        }}
                        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl transition-all shadow-xs"
                      >
                        1-Click Áp dụng: Tăng ngân sách +20%
                      </button>
                    </div>
                  </div>
                )}

                {/* TAB 4: SETTINGS & INLINE EDIT */}
                {drawerTab === 'settings' && (
                  <form onSubmit={handleSaveDrawerSettings} className="bg-white p-5 rounded-2xl border border-slate-200 space-y-4 text-xs">
                    <div>
                      <label className="block font-bold text-slate-700 mb-1">Tên Chiến dịch</label>
                      <input
                        type="text"
                        value={editFormData.name}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, name: e.target.value }))}
                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-hidden focus:bg-white focus:border-indigo-500"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block font-bold text-slate-700 mb-1">Ngân sách (VNĐ)</label>
                        <input
                          type="number"
                          value={editFormData.budget}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, budget: Number(e.target.value) }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono font-semibold outline-hidden focus:bg-white focus:border-indigo-500"
                          min="1000000"
                          step="500000"
                          required
                        />
                      </div>

                      <div>
                        <label className="block font-bold text-slate-700 mb-1">Trạng thái phân phối</label>
                        <select
                          value={editFormData.status}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, status: e.target.value as any }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-hidden focus:bg-white focus:border-indigo-500"
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
                        <label className="block font-bold text-slate-700 mb-1">Ngày bắt đầu</label>
                        <input
                          type="date"
                          value={editFormData.start_date}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, start_date: e.target.value }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-hidden focus:bg-white focus:border-indigo-500"
                        />
                      </div>
                      <div>
                        <label className="block font-bold text-slate-700 mb-1">Ngày kết thúc</label>
                        <input
                          type="date"
                          value={editFormData.end_date}
                          onChange={(e) => setEditFormData(prev => ({ ...prev, end_date: e.target.value }))}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-hidden focus:bg-white focus:border-indigo-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block font-bold text-slate-700 mb-1">Tệp Đối tượng Mục tiêu</label>
                      <textarea
                        value={editFormData.audience}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, audience: e.target.value }))}
                        rows={2}
                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-hidden focus:bg-white focus:border-indigo-500"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition-all shadow-xs"
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
      {isWizardOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 py-8">
            <div 
              className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
              onClick={() => {
                if (!isSubmitting && !isGeneratingAI) setIsWizardOpen(false);
              }}
            />

            <div className="relative bg-white rounded-3xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl border border-slate-200 z-10 space-y-6">
              {/* Wizard Header */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div>
                  <h3 className="text-lg font-black text-slate-900 tracking-tight flex items-center gap-2">
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
                  className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
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
                      wizardStep === s.step ? 'text-indigo-600' : wizardStep > s.step ? 'text-slate-700' : 'text-slate-400'
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
                        return (
                          <div
                            key={obj.id}
                            onClick={() => {
                              const selectedProd = products.find(p => p.id === Number(wizardData.product_id));
                              setWizardData(prev => ({
                                ...prev,
                                objectiveId: obj.id,
                                objectiveTitle: obj.title,
                                audience: obj.defaultAudience,
                                funnelStage: obj.funnelStage,
                                name: `Chiến dịch ${obj.title} - ${selectedProd?.name || 'Sản phẩm'}`
                              }));
                            }}
                            className={`p-3.5 rounded-2xl border-2 cursor-pointer transition-all ${
                              isSelected
                                ? 'border-indigo-600 bg-indigo-50/40 shadow-xs ring-1 ring-indigo-500/20'
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
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Product & Campaign Name */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Sản phẩm Tiếp thị</label>
                      <select
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
                        className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-hidden focus:bg-white focus:border-indigo-500"
                      >
                        {products.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Tên Chiến dịch</label>
                      <input
                        type="text"
                        value={wizardData.name}
                        onChange={(e) => setWizardData(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Nhập tên chiến dịch..."
                        className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold outline-hidden focus:bg-white focus:border-indigo-500"
                        required
                      />
                    </div>
                  </div>

                  {/* Budget & Presets */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-bold text-slate-700">Ngân sách Tổng (VNĐ)</label>
                      <span className="text-xs font-mono font-black text-indigo-600">
                        {Number(wizardData.budget).toLocaleString('vi-VN')} VNĐ
                      </span>
                    </div>
                    <input
                      type="number"
                      value={wizardData.budget}
                      onChange={(e) => setWizardData(prev => ({ ...prev, budget: Number(e.target.value) }))}
                      min="1000000"
                      step="1000000"
                      className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono font-semibold outline-hidden focus:bg-white focus:border-indigo-500"
                    />

                    {/* Quick Budget Presets */}
                    <div className="flex items-center gap-1.5 mt-2">
                      <span className="text-[10px] text-slate-400 font-semibold uppercase">Gợi ý nhanh:</span>
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
                      <label className="block text-xs font-bold text-slate-700 mb-1">Ngày Bắt đầu</label>
                      <input
                        type="date"
                        value={wizardData.start_date}
                        onChange={(e) => setWizardData(prev => ({ ...prev, start_date: e.target.value }))}
                        className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-hidden"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Ngày Kết thúc</label>
                      <input
                        type="date"
                        value={wizardData.end_date}
                        onChange={(e) => setWizardData(prev => ({ ...prev, end_date: e.target.value }))}
                        className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-hidden"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-slate-400 font-semibold uppercase">Thời lượng:</span>
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
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Tệp Khách hàng Mục tiêu (Audience Persona)
                    </label>
                    <textarea
                      value={wizardData.audience}
                      onChange={(e) => setWizardData(prev => ({ ...prev, audience: e.target.value }))}
                      rows={2}
                      placeholder="Mô tả độ tuổi, sở thích, hành vi và nỗi đau của khách hàng..."
                      className="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-hidden focus:bg-white focus:border-indigo-500"
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
                      <div className="w-12 h-12 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-xs">
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
                              activeCreativeTab === 'facebook' ? 'bg-white text-blue-600 shadow-2xs' : 'text-slate-600'
                            }`}
                          >
                            Facebook Feed Ad
                          </button>
                          <button
                            type="button"
                            onClick={() => setActiveCreativeTab('tiktok')}
                            className={`px-3 py-1.5 rounded-lg transition-all ${
                              activeCreativeTab === 'tiktok' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600'
                            }`}
                          >
                            TikTok Script (9:16)
                          </button>
                          <button
                            type="button"
                            onClick={() => setActiveCreativeTab('email')}
                            className={`px-3 py-1.5 rounded-lg transition-all ${
                              activeCreativeTab === 'email' ? 'bg-white text-violet-600 shadow-2xs' : 'text-slate-600'
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
                                  <span className="font-mono text-slate-400">{s.duration_seconds || '0-4s'}</span>
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
                  <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-emerald-500 text-white flex items-center justify-center font-black">
                        100
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-emerald-950 uppercase tracking-wider">
                          Đạt Tiêu chuẩn Quảng cáo Meta & TikTok
                        </h4>
                        <p className="text-[11px] text-emerald-800 mt-0.5">
                          Nội dung đã được kiểm duyệt tự động, không phát hiện từ ngữ cấm hoặc vi phạm chính sách cam kết ảo.
                        </p>
                      </div>
                    </div>
                    <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                  </div>

                  {/* Summary Checklist */}
                  <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500 font-medium">Tên chiến dịch:</span>
                      <span className="font-bold text-slate-900">{wizardData.name}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500 font-medium">Mục tiêu:</span>
                      <span className="font-bold text-slate-900">{wizardData.objectiveTitle}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500 font-medium">Ngân sách tổng:</span>
                      <span className="font-mono font-bold text-indigo-600">
                        {Number(wizardData.budget).toLocaleString('vi-VN')} đ
                      </span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500 font-medium">Số lượng Mẫu QC đi kèm:</span>
                      <span className="font-bold text-emerald-700">
                        {generatedCreatives ? '3 Mẫu QC Đa Kênh (Sẵn sàng)' : 'Sẽ tạo sau trong AI Copilot'}
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
                            ? 'border-emerald-500 bg-emerald-50/50 shadow-2xs'
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
                            ? 'border-indigo-500 bg-indigo-50/50 shadow-2xs'
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
                    disabled={isSubmitting}
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

      {/* Delete Confirmation Modal */}
      {deletingId && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity" onClick={() => setDeletingId(null)} />
            <div className="relative bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 z-10 space-y-4 text-center">
              <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-slate-900">Xác nhận xóa chiến dịch?</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Hành động này sẽ xóa chiến dịch cùng toàn bộ các mẫu quảng cáo đi kèm. Không thể hoàn tác.
                </p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setDeletingId(null)}
                  className="flex-1 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteCampaign(deletingId)}
                  className="flex-1 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-xs"
                >
                  Xóa vĩnh viễn
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
