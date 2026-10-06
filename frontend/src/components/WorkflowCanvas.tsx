import React, { useState, useEffect } from 'react';
import { Play, Sparkles, ShieldCheck, BarChart3, ArrowRight, CheckCircle2, XCircle, ZoomIn, ZoomOut, Calendar, Target, Users, Layers, FileText, Check, Copy, Stethoscope, RefreshCw, ThumbsUp, MessageSquare, Share2, Mail, Video, ExternalLink, Eye, CalendarCheck, ShieldAlert, Wand2, X, PieChart, ListTodo } from 'lucide-react';
import { Campaign, MarketingContent, KPISummary, AIIdeaItem, AIDraftResponse, ContentComplianceCheck, Task, TaskStatus, TaskPriority, TaskType } from '../types';
import { campaignApi, contentApi, aiApi, scheduleApi, taskApi, budgetApi, evaluateMarketingCompliance, getApiErrorMessage } from '../services/api';
import { useToast } from './Toast';
import { copyToClipboardWithFormatting } from '../utils/copyUtils';
import { 
  OverviewTab, 
  TasksTab, 
  ContentTab, 
  CalendarTab, 
  BudgetTab, 
  PerformanceTab 
} from './campaign-hub';

interface WorkflowCanvasProps {
  campaign: Campaign | null;
  contents: MarketingContent[];
  campaigns?: Campaign[];
  onSelectCampaign?: (c: Campaign | null) => void;
  /** Mở trợ lý AI Copilot. Canvas đã có tab Copilot riêng nên prop này không bắt
   *  buộc dùng; giữ optional để không phá call site. */
  onOpenAI?: (campaign: Campaign) => void;
  onApproveContent?: (id: number) => void;
  onSubmitForReview?: (id: number) => void;
  userRole?: string;
  onRefreshData?: () => void;
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  campaign,
  contents,
  campaigns = [],
  onSelectCampaign,
  onApproveContent,
  onSubmitForReview,
  userRole,
  onRefreshData
}) => {
  const toast = useToast();
  const isApprover = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER' || userRole === 'CLIENT_APPROVER' || userRole === 'ADMIN';

  // Top Tabs: 'brief' | 'tasks' | 'pipeline' | 'calendar' | 'attribution' | 'copilot' | 'doctor' | 'lifecycle'
  const [activeTab, setActiveTab] = useState<'brief' | 'tasks' | 'pipeline' | 'calendar' | 'attribution' | 'copilot' | 'doctor' | 'lifecycle'>('brief');

  // KPI & Doctor states
  const [campaignKpi, setCampaignKpi] = useState<KPISummary | null>(null);
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  // Operational Brief & Tasks states
  const [campaignTasks, setCampaignTasks] = useState<Task[]>([]);
  const [loadingTasks, setLoadingTasks] = useState<boolean>(false);
  const [isEditingBrief, setIsEditingBrief] = useState<boolean>(false);
  const [briefKeyMessage, setBriefKeyMessage] = useState<string>('');
  const [briefPrimaryCta, setBriefPrimaryCta] = useState<string>('');
  const [briefTargetKpiName, setBriefTargetKpiName] = useState<string>('');
  const [briefTargetKpiValue, setBriefTargetKpiValue] = useState<number>(0);
  const [isSavingBrief, setIsSavingBrief] = useState<boolean>(false);

  // Budget allocations edit state
  const [isEditingBudget, setIsEditingBudget] = useState<boolean>(false);
  const [channelAllocations, setChannelAllocations] = useState<{ channel_id: number; planned_amount: number; name: string }[]>([
    { channel_id: 1, name: 'Facebook Ads', planned_amount: 0 },
    { channel_id: 2, name: 'Email Marketing', planned_amount: 0 },
    { channel_id: 3, name: 'SEO & Blog Content', planned_amount: 0 },
    { channel_id: 4, name: 'Google Search Ads', planned_amount: 0 },
    { channel_id: 5, name: 'TikTok Video Ads', planned_amount: 0 },
  ]);

  // New task form inside Campaign
  const [newTaskTitle, setNewTaskTitle] = useState<string>('');
  const [newTaskType, setNewTaskType] = useState<TaskType>('CONTENT');
  const [newTaskPriority, setNewTaskPriority] = useState<TaskPriority>('MEDIUM');
  const [newTaskDueDate, setNewTaskDueDate] = useState<string>('');
  const [isCreatingTask, setIsCreatingTask] = useState<boolean>(false);

  // Lifecycle node zoom & active node
  const [activeNode, setActiveNode] = useState<string>('ai_gen');
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // In-Hub AI Copilot states
  const [channel, setChannel] = useState<'facebook' | 'tiktok' | 'email' | 'google_ads'>('facebook');
  const [framework, setFramework] = useState<'AIDA' | 'PAS' | 'FAB'>('AIDA');
  const [tone, setTone] = useState<string>('Chuyên nghiệp, tin cậy, truyền cảm hứng');
  const [generatingIdeas, setGeneratingIdeas] = useState<boolean>(false);
  const [ideas, setIdeas] = useState<AIIdeaItem[]>([]);
  const [selectedIdea, setSelectedIdea] = useState<string>('');
  const [generatingDraft, setGeneratingDraft] = useState<boolean>(false);
  const [generatedDraft, setGeneratedDraft] = useState<AIDraftResponse | null>(null);
  const [savingAction, setSavingAction] = useState<boolean>(false);
  const [copiedDraft, setCopiedDraft] = useState<boolean>(false);

  // AI Compliance State
  const [complianceResult, setComplianceResult] = useState<ContentComplianceCheck | null>(null);
  const [checkingCompliance, setCheckingCompliance] = useState<boolean>(false);

  // Scheduling Modal State
  const [scheduleModalContent, setScheduleModalContent] = useState<MarketingContent | null>(null);
  const [scheduledDate, setScheduledDate] = useState<string>('2026-09-25');
  const [scheduledTime, setScheduledTime] = useState<string>('19:30');
  const [schedulingAction, setSchedulingAction] = useState<boolean>(false);

  // Rejection Modal State
  const [rejectModalContent, setRejectModalContent] = useState<MarketingContent | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('Cần chỉnh sửa lại giọng văn cho phù hợp hơn với chính sách thương hiệu.');
  const [rejectingAction, setRejectingAction] = useState<boolean>(false);

  const loadCampaignExtraData = (campId: number) => {
    setLoadingTasks(true);
    taskApi.getCampaignTasks(campId)
      .then(res => setCampaignTasks(res))
      .catch(() => setCampaignTasks([]))
      .finally(() => setLoadingTasks(false));

    // Phân bổ ngân sách được nạp để đổ vào `channelAllocations` (dùng bởi
    // OverviewTab cho phần sửa ngân sách theo kênh). Trước đây còn giữ thêm
    // state `budgetAllocations` riêng nhưng không component nào đọc tới nó —
    // dữ liệu bị tải rồi vứt, tức là 1 request thừa mỗi lần đổi chiến dịch.
    budgetApi.getBudgetAllocations(campId)
      .then(res => {
        if (res.length > 0) {
          setChannelAllocations(prev => prev.map(ch => {
            const found = res.find(a => a.channel_id === ch.channel_id);
            return found ? { ...ch, planned_amount: Number(found.planned_amount) } : ch;
          }));
        }
      })
      .catch(() => undefined);
  };

  useEffect(() => {
    if (campaign?.id) {
      campaignApi.getKpi(campaign.id)
        .then(res => setCampaignKpi(res))
        .catch(() => setCampaignKpi(null));

      setBriefKeyMessage(campaign.key_message || '');
      setBriefPrimaryCta(campaign.primary_cta || '');
      setBriefTargetKpiName(campaign.target_kpi_name || '');
      setBriefTargetKpiValue(campaign.target_kpi_value || 0);

      loadCampaignExtraData(campaign.id);
    }
    // Chỉ nạp lại khi ĐỔI chiến dịch. Đưa 4 trường brief vào deps sẽ khiến effect
    // chạy lại mỗi lần người dùng gõ trong ô brief (vì App truyền campaign object
    // mới sau mỗi lần refetch), xoá mất nội dung đang soạn — đúng lỗi "gõ mất
    // chữ" mà danh sách deps rộng gây ra.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaign?.id]);

  const handleSaveBrief = async () => {
    if (!campaign) return;
    try {
      setIsSavingBrief(true);
      await campaignApi.update(campaign.id, {
        key_message: briefKeyMessage.trim() || undefined,
        primary_cta: briefPrimaryCta.trim() || undefined,
        target_kpi_name: briefTargetKpiName.trim() || undefined,
        target_kpi_value: briefTargetKpiValue || undefined
      });
      toast.success('Đã cập nhật thông điệp và mục tiêu chiến dịch!');
      setIsEditingBrief(false);
      if (onRefreshData) onRefreshData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi lưu thông điệp chiến dịch');
    } finally {
      setIsSavingBrief(false);
    }
  };

  const handleSaveBudgetAllocations = async () => {
    if (!campaign) return;
    try {
      const dataToSave = channelAllocations
        .filter(c => c.planned_amount > 0)
        .map(c => ({ channel_id: c.channel_id, planned_amount: c.planned_amount }));
      // Đồng bộ lại state cục bộ từ phản hồi của server: trước đây dùng phản hồi
      // để cập nhật `budgetAllocations` (một state không ai đọc) nên biểu mẫu vẫn
      // giữ số người dùng gõ dù server đã trả về giá trị chuẩn hoá khác.
      const saved = await budgetApi.updateBudgetAllocations(campaign.id, dataToSave);
      if (saved.length > 0) {
        setChannelAllocations(prev =>
          prev.map(ch => {
            const found = saved.find(a => a.channel_id === ch.channel_id);
            return found ? { ...ch, planned_amount: Number(found.planned_amount) } : ch;
          })
        );
      }
      setIsEditingBudget(false);
      toast.success('Đã cập nhật phân bổ ngân sách các kênh!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi lưu phân bổ ngân sách');
    }
  };

  const handleCreateCampaignTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campaign || !newTaskTitle.trim()) return;
    try {
      setIsCreatingTask(true);
      const created = await taskApi.createTask(campaign.id, {
        title: newTaskTitle.trim(),
        task_type: newTaskType,
        priority: newTaskPriority,
        due_date: newTaskDueDate || undefined,
        status: 'TODO'
      });
      setCampaignTasks(prev => [created, ...prev]);
      toast.success('Đã tạo tác vụ cho chiến dịch!');
      setNewTaskTitle('');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi tạo tác vụ');
    } finally {
      setIsCreatingTask(false);
    }
  };

  const handleUpdateCampaignTaskStatus = async (taskId: number, nextStatus: TaskStatus) => {
    try {
      const updated = await taskApi.updateTask(taskId, { status: nextStatus });
      setCampaignTasks(prev => prev.map(t => t.id === taskId ? updated : t));
      toast.success(`Đã cập nhật trạng thái tác vụ: ${nextStatus}`);
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi cập nhật tác vụ');
    }
  };

  const handleDeleteCampaignTask = async (taskId: number) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa tác vụ này?')) return;
    try {
      await taskApi.deleteTask(taskId);
      setCampaignTasks(prev => prev.filter(t => t.id !== taskId));
      toast.success('Đã xóa tác vụ thành công!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi xóa tác vụ');
    }
  };


  if (!campaign) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/80 p-16 text-center text-slate-500 shadow-sm">
        <Layers className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="text-base font-bold text-slate-800">Chưa chọn chiến dịch tiếp thị</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
          Vui lòng chọn một chiến dịch từ danh sách phía trên để mở Trung tâm Điều phối Chiến dịch (Campaign Operations Hub).
        </p>
      </div>
    );
  }

  // Filter contents for this campaign
  const campaignContents = contents.filter(c => c.campaign_id === campaign.id);
  const draftContents = campaignContents.filter(c => c.status === 'DRAFT' || c.status === 'AI_DRAFT');
  const inReviewContents = campaignContents.filter(c => c.status === 'IN_REVIEW');
  const approvedContents = campaignContents.filter(c => c.status === 'APPROVED');
  const rejectedContents = campaignContents.filter(c => c.status === 'REJECTED');
  const publishedContents = campaignContents.filter(c => c.status === 'PUBLISHED');

  // Submit for Review
  const handleSubmitContent = async (id: number) => {
    try {
      setSubmittingId(id);
      await contentApi.submitForReview(id);
      toast.success('Đã đưa bài viết vào Hàng đợi kiểm duyệt (IN_REVIEW)');
      if (onSubmitForReview) onSubmitForReview(id);
      if (onRefreshData) onRefreshData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gửi duyệt nội dung');
    } finally {
      setSubmittingId(null);
    }
  };

  // Approve Content
  const handleApproveContentItem = async (id: number) => {
    try {
      setApprovingId(id);
      if (onApproveContent) {
        await onApproveContent(id);
      } else {
        await contentApi.approve(id);
        toast.success('Đã phê duyệt bài viết thành công (APPROVED)!');
      }
      if (onRefreshData) onRefreshData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi phê duyệt');
    } finally {
      setApprovingId(null);
    }
  };

  // Reject Content
  const handleRejectConfirm = async () => {
    if (!rejectModalContent) return;
    if (rejectReason.trim().length < 3) {
      toast.warning("Vui lòng nhập lý do từ chối cụ thể (tối thiểu 3 ký tự)!");
      return;
    }
    try {
      setRejectingAction(true);
      await contentApi.reject(rejectModalContent.id, rejectReason.trim());
      toast.warning('Đã từ chối bài viết và gửi yêu cầu chỉnh sửa cho Marketer');
      setRejectModalContent(null);
      if (onRefreshData) onRefreshData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi từ chối bài viết');
    } finally {
      setRejectingAction(false);
    }
  };

  // Schedule Content Confirmation
  const handleScheduleConfirm = async () => {
    if (!scheduleModalContent) return;
    try {
      setSchedulingAction(true);
      const scheduledAt = `${scheduledDate} ${scheduledTime}`;
      await scheduleApi.create(scheduleModalContent.id, scheduledAt);
      toast.success(`Đã lập lịch xuất bản thành công vào lúc ${scheduledTime} ngày ${scheduledDate}!`);
      setScheduleModalContent(null);
      if (onRefreshData) onRefreshData();
      setActiveTab('calendar');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi lập lịch xuất bản');
    } finally {
      setSchedulingAction(false);
    }
  };

  // AI Copilot Generate Ideas
  const handleGenerateIdeas = async () => {
    try {
      setGeneratingIdeas(true);
      const res = await aiApi.generateIdeas(campaign.id, channel, 'v3', {
        tone: `${tone} (${framework} framework)`
      });
      setIdeas(res.ideas || []);
      if (res.ideas && res.ideas.length > 0) {
        setSelectedIdea(res.ideas[0].headline);
      }
      toast.success(`Đã sinh ${res.ideas?.length || 0} ý tưởng góc nhìn sáng tạo!`);
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi sinh ý tưởng AI');
    } finally {
      setGeneratingIdeas(false);
    }
  };

  // AI Copilot Generate Draft
  const handleGenerateDraft = async () => {
    if (!selectedIdea.trim()) {
      toast.warning('Vui lòng chọn hoặc nhập một góc tiếp cận trước khi viết bài.');
      return;
    }
    try {
      setGeneratingDraft(true);
      setComplianceResult(null);
      const res = await aiApi.generateDraft(campaign.id, selectedIdea, channel, 'v3');
      setGeneratedDraft(res);
      toast.success('AI Copilot đã hoàn thành bản thảo đa kênh!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi sinh bản thảo AI');
    } finally {
      setGeneratingDraft(false);
    }
  };

  // Run AI Compliance Check
  const handleCheckCompliance = () => {
    if (!generatedDraft) return;
    setCheckingCompliance(true);
    setTimeout(() => {
      const result = evaluateMarketingCompliance(generatedDraft.title, generatedDraft.body, generatedDraft.cta);
      setComplianceResult(result);
      setCheckingCompliance(false);
      if (result.status === 'PASSED') {
        toast.success(`Đạt chuẩn tuân thủ chính sách quảng cáo! (${result.score}/100 điểm)`);
      } else if (result.status === 'WARNING') {
        toast.warning(`Phát hiện một số từ ngữ nhạy cảm (${result.score}/100 điểm)`);
      } else {
        toast.error(`Cảnh báo vi phạm chính sách quảng cáo! (${result.score}/100 điểm)`);
      }
    }, 400);
  };

  // Fix compliance automatically
  const handleAutoFixCompliance = () => {
    if (!generatedDraft || !complianceResult) return;
    let fixedBody = generatedDraft.body;
    for (const item of complianceResult.flagged_items) {
      if (item.phrase && item.phrase !== '(Thiếu Call To Action)') {
        const regex = new RegExp(item.phrase, 'gi');
        fixedBody = fixedBody.replace(regex, item.suggestion.replace(/^thay bằng /i, '').replace(/["']/g, ''));
      }
    }
    setGeneratedDraft(prev => prev ? ({ ...prev, body: fixedBody, cta: prev.cta || 'Đăng ký tư vấn ngay' }) : null);
    setComplianceResult(null);
    toast.success('Đã tự động thay thế các từ ngữ rủi ro bằng ngôn từ an toàn chuẩn quảng cáo!');
  };

  // Save AI Draft into Campaign
  const handleSaveToCampaign = async (autoSubmit: boolean) => {
    if (!generatedDraft) return;
    try {
      setSavingAction(true);
      const channelIdMap: Record<string, number> = {
        facebook: 1,
        email: 2,
        blog: 3,
        google_ads: 4,
        tiktok: 1
      };
      const channelId = channelIdMap[channel] || 1;

      const newContent = await contentApi.create({
        campaign_id: campaign.id,
        channel_id: channelId,
        title: generatedDraft.title || selectedIdea,
        body: generatedDraft.body,
        cta: generatedDraft.cta,
        status: 'AI_DRAFT'
      });

      if (autoSubmit) {
        await contentApi.submitForReview(newContent.id);
        toast.success('Đã lưu bài viết vào Chiến dịch & Đưa vào Hàng đợi chờ Sếp duyệt (HITL)!');
      } else {
        toast.success('Đã lưu bài viết vào mục Bản nháp (AI_DRAFT) của Chiến dịch!');
      }

      if (onRefreshData) onRefreshData();
      setActiveTab('pipeline');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi lưu bài viết vào chiến dịch');
    } finally {
      setSavingAction(false);
    }
  };

  // Copy text helper
  const handleCopyText = (text: string) => {
    // Không báo "Đã sao chép" khi clipboard thực tế bị từ chối (HTTP, quyền bị chặn).
    void copyToClipboardWithFormatting(text).then((ok) => {
      if (!ok) {
        toast.error('Trình duyệt từ chối ghi vào clipboard');
        return;
      }
      setCopiedDraft(true);
      setTimeout(() => setCopiedDraft(false), 2000);
      toast.info('Đã sao chép nội dung vào Clipboard!');
    });
  };

  // Handle Marketer asking AI to fix rejected draft
  const handleAskAIToFixRejection = (item: MarketingContent) => {
    setSelectedIdea(`Hiệu chỉnh lại bài viết: "${item.title}" để khắc phục các góp ý phản hồi từ Quản lý.`);
    setActiveTab('copilot');
    toast.info('Đã tải bài viết bị từ chối vào AI Copilot. Bấm "Viết nội dung hoàn chỉnh" để AI sửa lại.');
  };

  // Helpers for channel badges
  const getChannelBadge = (chId: number) => {
    switch (chId) {
      case 1:
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">Facebook</span>;
      case 2:
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">Email</span>;
      case 3:
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">Blog SEO</span>;
      case 4:
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">Google Ads</span>;
      default:
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-200">Social</span>;
    }
  };

  const spentAmount = campaignKpi?.total_cost || 0;
  const budgetAmount = Number(campaign.budget) || 1;
  const spendPercent = Math.min(Math.round((spentAmount / budgetAmount) * 100), 100);

  return (
    <div className="space-y-6">
      {/* 1. CAMPAIGN HEADER & OPERATIONAL CONTEXT BANNER */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                campaign.status === 'ACTIVE' 
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : campaign.status === 'PLANNED'
                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                  : 'bg-slate-100 text-slate-700 border border-slate-200'
              }`}>
                {campaign.status}
              </span>
              <h2 className="text-xl font-black text-slate-900 tracking-tight">{campaign.name}</h2>
              <span className="text-xs text-slate-400">• ID: #{campaign.id}</span>
            </div>

            <p className="text-xs text-slate-600 line-clamp-1">
              <span className="font-semibold text-slate-700">Mục tiêu:</span> {campaign.objective}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
              <div className="flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-indigo-500" />
                <span>Khách hàng mục tiêu: <strong className="text-slate-700">{campaign.audience}</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-indigo-500" />
                <span>Thời hạn: <strong className="text-slate-700">{campaign.start_date} → {campaign.end_date}</strong></span>
              </div>
            </div>
          </div>

          {/* Budget Health Meter */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-4 min-w-[280px] shrink-0">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-500 font-medium">Ngân sách đã chi:</span>
              <span className="font-bold text-slate-900">
                {spentAmount.toLocaleString('vi-VN')} đ / {budgetAmount.toLocaleString('vi-VN')} đ
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
              <div 
                className={`h-2 rounded-full transition-all duration-500 ${
                  spendPercent > 90 ? 'bg-rose-500' : spendPercent > 70 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${spendPercent}%` }}
              ></div>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1.5">
              <span>Tiến độ tiêu ngân sách</span>
              <span className="font-semibold text-slate-700">{spendPercent}%</span>
            </div>
          </div>
        </div>

        {/* ENTERPRISE CLOSED-LOOP MARKETING STEPPER GUIDE */}
        <div className="bg-slate-900 text-white p-4 border-t border-slate-800">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span className="text-[11px] font-black uppercase tracking-wider text-emerald-300">
                Chu Trình Vận Hành Tiếp Thị Khép Kín (Closed-Loop Enterprise Lifecycle)
              </span>
              <span className="text-[11px] text-slate-400 hidden sm:inline">• Chuẩn HubSpot, Meta & Salesforce</span>
            </div>
            <span className="text-[11px] text-slate-400">
              Bấm vào từng bước để điều phối chiến dịch theo chuẩn nghiệp vụ
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {[
              {
                step: 1,
                title: 'Hoạch định',
                sub: 'Mục tiêu & Ngân sách',
                tab: 'attribution',
                status: 'DONE',
                badge: 'Hoàn tất'
              },
              {
                step: 2,
                title: 'Sáng tạo AI',
                sub: 'AIDA, PAS & An toàn',
                tab: 'copilot',
                status: draftContents.length > 0 ? 'DONE' : 'IN_PROGRESS',
                badge: draftContents.length > 0 ? `${draftContents.length} Bản nháp` : 'Sáng tạo'
              },
              {
                step: 3,
                title: 'Kiểm duyệt HITL',
                sub: 'Sếp duyệt & Phản hồi',
                tab: 'pipeline',
                status: inReviewContents.length > 0 ? 'ATTENTION' : 'DONE',
                badge: inReviewContents.length > 0 ? `${inReviewContents.length} Chờ duyệt` : 'Đã duyệt'
              },
              {
                step: 4,
                title: 'Phát sóng & Lịch',
                sub: 'Khung giờ vàng kênh',
                tab: 'calendar',
                status: approvedContents.length > 0 ? 'ATTENTION' : 'DONE',
                badge: approvedContents.length > 0 ? 'Chờ lên lịch' : 'Đã xếp lịch'
              },
              {
                step: 5,
                title: 'Vận hành AI',
                sub: 'Pacing & Tối ưu dòng tiền',
                tab: 'doctor',
                status: 'LIVE',
                badge: 'Thời gian thực'
              },
              {
                step: 6,
                title: 'Đóng gói Tri thức',
                sub: 'Quy kết ROI & Bài học',
                tab: 'attribution',
                status: 'VAULT',
                badge: 'Kho tri thức'
              }
            ].map((s) => (
              <button
                key={s.step}
                onClick={() => setActiveTab(s.tab as any)}
                className={`p-2.5 rounded-xl border text-left transition-all group relative ${
                  (activeTab === s.tab && (s.step !== 1 && s.step !== 6 || activeTab === 'attribution'))
                    ? 'bg-slate-800 border-indigo-500 ring-2 ring-indigo-500/30 shadow-md'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="w-5 h-5 rounded-md bg-slate-800 group-hover:bg-indigo-600 text-slate-300 group-hover:text-white font-mono text-[10px] font-bold flex items-center justify-center transition-colors">
                    0{s.step}
                  </span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full ${
                    s.status === 'ATTENTION' 
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse'
                      : s.status === 'LIVE'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-slate-800 text-slate-400'
                  }`}>
                    {s.badge}
                  </span>
                </div>
                <div className="text-xs font-bold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                  {s.title}
                </div>
                <div className="text-[10px] text-slate-400 line-clamp-1">
                  {s.sub}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 2. NAVIGATION TABS FOR MARKETING WORKFLOW */}
        <div className="flex items-center gap-1 px-6 bg-slate-50/70 border-t border-slate-100 overflow-x-auto">
          <button
            onClick={() => setActiveTab('brief')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'brief'
                ? 'border-indigo-600 text-indigo-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Target className="w-4 h-4 text-indigo-600" />
            <span>Brief & Mục Tiêu Vận Hành</span>
          </button>

          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'tasks'
                ? 'border-indigo-600 text-indigo-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <ListTodo className="w-4 h-4 text-indigo-600" />
            <span>Tác Vụ Chiến Dịch (Tasks)</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-50 text-indigo-700 border border-indigo-200 font-bold">
              {campaignTasks.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('pipeline')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'pipeline'
                ? 'border-indigo-600 text-indigo-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Bảng Điều phối Nội dung (Pipeline)</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-50 text-indigo-700 border border-indigo-200 font-bold">
              {campaignContents.length}
            </span>
          </button>


          <button
            onClick={() => setActiveTab('calendar')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'calendar'
                ? 'border-blue-600 text-blue-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <CalendarCheck className="w-4 h-4 text-blue-500" />
            <span>Lịch Tiếp thị Đa Kênh (Calendar)</span>
          </button>

          <button
            onClick={() => setActiveTab('attribution')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'attribution'
                ? 'border-teal-600 text-teal-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <PieChart className="w-4 h-4 text-teal-500" />
            <span>Phân bổ Ngân sách & ROI Kênh</span>
          </button>

          <button
            onClick={() => setActiveTab('copilot')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'copilot'
                ? 'border-violet-600 text-violet-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Sparkles className="w-4 h-4 text-violet-500" />
            <span>AI Sáng tạo Nội dung</span>
          </button>

          <button
            onClick={() => setActiveTab('doctor')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'doctor'
                ? 'border-emerald-600 text-emerald-600 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Stethoscope className="w-4 h-4 text-emerald-500" />
            <span>Bác sĩ AI Chẩn đoán</span>
          </button>

          <button
            onClick={() => setActiveTab('lifecycle')}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'lifecycle'
                ? 'border-slate-800 text-slate-900 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Play className="w-4 h-4 text-slate-600" />
            <span>Sơ đồ Vòng đời (Visual)</span>
          </button>
        </div>
      </div>

      {/* 2.1 TAB BRIEF & MỤC TIÊU VẬN HÀNH (OVERVIEW TAB) */}
      {activeTab === 'brief' && (
        <OverviewTab
          campaign={campaign}
          campaignKpi={campaignKpi}
          isEditingBrief={isEditingBrief}
          setIsEditingBrief={setIsEditingBrief}
          briefKeyMessage={briefKeyMessage}
          setBriefKeyMessage={setBriefKeyMessage}
          briefPrimaryCta={briefPrimaryCta}
          setBriefPrimaryCta={setBriefPrimaryCta}
          briefTargetKpiName={briefTargetKpiName}
          setBriefTargetKpiName={setBriefTargetKpiName}
          briefTargetKpiValue={briefTargetKpiValue}
          setBriefTargetKpiValue={setBriefTargetKpiValue}
          isSavingBrief={isSavingBrief}
          handleSaveBrief={handleSaveBrief}
          channelAllocations={channelAllocations}
          setChannelAllocations={setChannelAllocations}
          isEditingBudget={isEditingBudget}
          setIsEditingBudget={setIsEditingBudget}
          handleSaveBudgetAllocations={handleSaveBudgetAllocations}
        />
      )}

      {/* 2.2 TAB TÁC VỤ CHIẾN DỊCH (TASKS TAB) */}
      {activeTab === 'tasks' && (
        <TasksTab
          campaign={campaign}
          campaignTasks={campaignTasks}
          loadingTasks={loadingTasks}
          newTaskTitle={newTaskTitle}
          setNewTaskTitle={setNewTaskTitle}
          newTaskType={newTaskType}
          setNewTaskType={setNewTaskType}
          newTaskPriority={newTaskPriority}
          setNewTaskPriority={setNewTaskPriority}
          newTaskDueDate={newTaskDueDate}
          setNewTaskDueDate={setNewTaskDueDate}
          isCreatingTask={isCreatingTask}
          handleCreateCampaignTask={handleCreateCampaignTask}
          handleUpdateCampaignTaskStatus={handleUpdateCampaignTaskStatus}
          handleDeleteCampaignTask={handleDeleteCampaignTask}
        />
      )}

      {/* 3. TAB 1: BẢNG ĐIỀU PHỐI NỘI DUNG (CONTENT TAB) */}
      {activeTab === 'pipeline' && (
        <ContentTab
          campaignId={campaign?.id}
          draftContents={draftContents}
          rejectedContents={rejectedContents}
          inReviewContents={inReviewContents}
          approvedContents={approvedContents}
          publishedContents={publishedContents}
          isApprover={isApprover}
          submittingId={submittingId}
          approvingId={approvingId}
          getChannelBadge={getChannelBadge}
          handleAskAIToFixRejection={handleAskAIToFixRejection}
          handleSubmitContent={handleSubmitContent}
          handleApproveContentItem={handleApproveContentItem}
          setRejectModalContent={setRejectModalContent}
          setScheduleModalContent={setScheduleModalContent}
          onOpenCopilot={() => setActiveTab('copilot')}
          onOpenCalendar={() => setActiveTab('calendar')}
          onOpenDoctor={() => setActiveTab('doctor')}
          // Nội dung do prop `contents` cấp xuống; sau khi tạo bài thủ công thì
          // gọi `onRefreshData` để App nạp lại danh sách chiến dịch.
          onRefresh={() => onRefreshData?.()}
        />
      )}

      {/* 4. TAB 2: LỊCH TIẾP THỊ ĐA KÊNH (MARKETING CALENDAR) */}
      {activeTab === 'calendar' && (
        <CalendarTab
          campaign={campaign}
          campaigns={campaigns}
          contents={contents}
          onSelectCampaign={onSelectCampaign}
          onNavigateToDoctor={() => setActiveTab('doctor')}
        />
      )}

      {/* 5. TAB 3: PHÂN BỔ NGÂN SÁCH & ROI KÊNH (CHANNEL ATTRIBUTION) */}
      {activeTab === 'attribution' && (
        <BudgetTab
          campaign={campaign}
          campaignKpi={campaignKpi}
        />
      )}

      {/* 6. TAB 4: AI SÁNG TẠO NỘI DUNG CHIẾN DỊCH (AI MARKETING COPILOT) */}
      {activeTab === 'copilot' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Form & Configuration */}
          <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 p-5 space-y-5 shadow-sm">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-600" />
                <span>Thiết lập Sáng tạo Nội dung</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                AI tự động kế thừa dữ liệu sản phẩm, mục tiêu và tệp khách hàng từ Chiến dịch <strong className="text-slate-700">{campaign.name}</strong>.
              </p>
            </div>

            {/* Grounded Context Box */}
            <div className="bg-slate-50 rounded-xl p-3 border border-slate-200 space-y-1.5 text-xs">
              <div className="flex items-center justify-between text-slate-500">
                <span>Chiến dịch liên kết:</span>
                <span className="font-bold text-slate-800">{campaign.name}</span>
              </div>
              <div className="flex items-center justify-between text-slate-500">
                <span>Đối tượng tiếp cận:</span>
                <span className="font-semibold text-slate-700">{campaign.audience}</span>
              </div>
              <div className="flex items-center justify-between text-slate-500">
                <span>Mục tiêu cốt lõi:</span>
                <span className="font-semibold text-slate-700">{campaign.objective}</span>
              </div>
            </div>

            {/* Select Channel */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Kênh truyền thông phân phối</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setChannel('facebook')}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center gap-2 transition-all ${
                    channel === 'facebook'
                      ? 'border-blue-500 bg-blue-50 text-blue-700 ring-2 ring-blue-500/20'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <ThumbsUp className="w-4 h-4 text-blue-600" />
                  <span>Facebook Post</span>
                </button>

                <button
                  type="button"
                  onClick={() => setChannel('tiktok')}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center gap-2 transition-all ${
                    channel === 'tiktok'
                      ? 'border-slate-900 bg-slate-900 text-white ring-2 ring-slate-900/20'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Video className="w-4 h-4 text-rose-500" />
                  <span>Kịch bản TikTok</span>
                </button>

                <button
                  type="button"
                  onClick={() => setChannel('email')}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center gap-2 transition-all ${
                    channel === 'email'
                      ? 'border-purple-500 bg-purple-50 text-purple-700 ring-2 ring-purple-500/20'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Mail className="w-4 h-4 text-purple-600" />
                  <span>Email Marketing</span>
                </button>

                <button
                  type="button"
                  onClick={() => setChannel('google_ads')}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center gap-2 transition-all ${
                    channel === 'google_ads'
                      ? 'border-amber-500 bg-amber-50 text-amber-700 ring-2 ring-amber-500/20'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <ExternalLink className="w-4 h-4 text-amber-600" />
                  <span>Google Ads</span>
                </button>
              </div>
            </div>

            {/* Select Framework */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center justify-between">
                <span>Khung thông điệp Marketing (Framework)</span>
                <span className="text-[10px] text-slate-400 font-normal">Chuẩn chuyển đổi cao</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'AIDA', label: 'AIDA', desc: 'Chú ý → Quan tâm → Khao khát → Hành động' },
                  { id: 'PAS', label: 'PAS', desc: 'Vấn đề → Xoáy sâu → Giải pháp cứu cánh' },
                  { id: 'FAB', label: 'FAB', desc: 'Tính năng → Ưu điểm → Lợi ích thực tế' }
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFramework(f.id as any)}
                    className={`p-2 rounded-lg border text-left transition-all ${
                      framework === f.id
                        ? 'border-indigo-600 bg-indigo-50/70 text-indigo-700 ring-2 ring-indigo-600/20'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <div className="font-bold text-xs">{f.label}</div>
                    <div className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">{f.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Tone of voice */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Giọng văn thương hiệu (Brand Tone)</label>
              <input
                type="text"
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                placeholder="VD: Hào hứng, uy tín, trẻ trung, dí dỏm..."
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 font-medium text-slate-800"
              />
            </div>

            {/* Step 1: Trigger Angles Generator */}
            <div className="pt-2">
              <button
                type="button"
                onClick={handleGenerateIdeas}
                disabled={generatingIdeas}
                className="w-full py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-violet-600/20 transition-all active:scale-95"
              >
                <Sparkles className="w-4 h-4" />
                <span>{generatingIdeas ? 'Gemini đang tìm góc tiếp cận...' : '1. Tìm ý tưởng góc nhìn sáng tạo'}</span>
              </button>
            </div>

            {/* Ideas Selector */}
            {ideas.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <label className="text-xs font-bold text-slate-700">Chọn 1 góc tiếp cận tâm đắc nhất:</label>
                <div className="space-y-2">
                  {ideas.map((item, idx) => (
                    // Dùng <button> gốc vì đây là lựa chọn (selectable option) trong danh sách,
                    // cần hoạt động được bằng chuột lẫn bàn phím.
                    <button
                      key={item.id || idx}
                      type="button"
                      aria-pressed={selectedIdea === item.headline}
                      onClick={() => setSelectedIdea(item.headline)}
                      className={`w-full text-left p-2.5 rounded-lg border cursor-pointer text-xs transition-all ${
                        selectedIdea === item.headline
                          ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-600/20 font-semibold text-slate-900'
                          : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] text-indigo-600 font-bold mb-0.5">
                        <span>Góc nhìn #{idx + 1}: {item.angle}</span>
                        <span className="text-[10px] text-slate-400 uppercase">{item.target_emotion}</span>
                      </div>
                      <p className="line-clamp-2">{item.headline}</p>
                    </button>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={handleGenerateDraft}
                  disabled={generatingDraft || !selectedIdea}
                  className="w-full mt-2 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 transition-all active:scale-95"
                >
                  <FileText className="w-4 h-4" />
                  <span>{generatingDraft ? 'AI đang viết bài hoàn chỉnh...' : '2. Viết nội dung hoàn chỉnh'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Right Column: Live Channel Preview Mockup & Compliance Guardrail */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Eye className="w-4 h-4 text-indigo-600" />
                    <span>Trực quan hóa Thực tế trên Kênh (Live Channel Mockup)</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Mô phỏng hiển thị chân thực bài viết trên giao diện người dùng cuối.
                  </p>
                </div>

                {generatedDraft && (
                  <div className="flex items-center gap-2">
                    {/* Compliance Check Button */}
                    <button
                      onClick={handleCheckCompliance}
                      disabled={checkingCompliance}
                      className="px-2.5 py-1 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg flex items-center gap-1 transition-colors"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{checkingCompliance ? 'Đang quét...' : 'AI Quét Vi phạm'}</span>
                    </button>

                    <button
                      onClick={() => handleCopyText(`${generatedDraft.title}\n\n${generatedDraft.body}\n\n${generatedDraft.cta}`)}
                      className="px-2.5 py-1 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 rounded-lg flex items-center gap-1 transition-colors"
                    >
                      {copiedDraft ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedDraft ? 'Đã chép' : 'Sao chép'}</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Compliance Shield Alert Card */}
              {complianceResult && (
                <div className={`p-4 rounded-xl border text-xs space-y-2.5 ${
                  complianceResult.status === 'PASSED'
                    ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                    : complianceResult.status === 'WARNING'
                    ? 'bg-amber-50/70 border-amber-200 text-amber-900'
                    : 'bg-rose-50/70 border-rose-200 text-rose-900'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-bold">
                      {complianceResult.status === 'PASSED' ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <ShieldAlert className="w-4 h-4 text-amber-600" />
                      )}
                      <span>Điểm số Tuân thủ Chính sách Quảng cáo: {complianceResult.score}/100</span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider bg-white/80">
                      {complianceResult.status}
                    </span>
                  </div>

                  <p className="text-[11px] leading-relaxed">{complianceResult.summary}</p>

                  {complianceResult.flagged_items.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <div className="font-bold text-[11px]">Từ ngữ/vấn đề cần chú ý:</div>
                      {complianceResult.flagged_items.map((item, i) => (
                        <div key={i} className="bg-white/80 p-2 rounded border text-[11px] space-y-0.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-rose-700">&ldquo;{item.phrase}&rdquo;</span>
                            <span className="text-[9px] uppercase font-bold text-slate-400">Rủi ro: {item.risk_level}</span>
                          </div>
                          <div className="text-slate-600">{item.reason}</div>
                          <div className="text-emerald-700 font-semibold">💡 Gợi ý: {item.suggestion}</div>
                        </div>
                      ))}

                      <button
                        onClick={handleAutoFixCompliance}
                        className="mt-2 text-[11px] font-bold text-emerald-800 bg-white hover:bg-emerald-100 px-3 py-1.5 rounded-lg border border-emerald-300 transition-colors flex items-center gap-1.5 shadow-sm"
                      >
                        <Wand2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Tự động sửa các từ rủi ro bằng ngôn từ an toàn</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Mockup Display */}
              <div>
                {!generatedDraft ? (
                  <div className="bg-slate-50 border border-dashed border-slate-200 rounded-2xl p-12 text-center text-slate-400 space-y-3">
                    <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                      <Sparkles className="w-6 h-6 text-violet-400 animate-pulse" />
                    </div>
                    <p className="text-xs font-semibold text-slate-600">Khung xem trước bài viết tự động</p>
                    <p className="text-[11px] max-w-sm mx-auto">
                      Hãy chọn kênh và bấm &ldquo;Viết nội dung hoàn chỉnh&rdquo;. Bản nháp định dạng đúng chuẩn của kênh sẽ xuất hiện ngay tại đây.
                    </p>
                  </div>
                ) : channel === 'facebook' ? (
                  /* Realistic Facebook Post Mockup */
                  <div className="max-w-md mx-auto bg-white rounded-xl border border-slate-200 shadow-md overflow-hidden">
                    {/* Header */}
                    <div className="p-3.5 flex items-center gap-2.5">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-sm">
                        MF
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <h4 className="font-bold text-xs text-slate-900">MarketFlow Official Page</h4>
                          <span className="w-3 h-3 rounded-full bg-blue-500 text-white flex items-center justify-center text-[8px]">✓</span>
                        </div>
                        <p className="text-[10px] text-slate-400">Vừa xong · Được tài trợ (Sponsored) · 🌐</p>
                      </div>
                    </div>

                    {/* Post Text */}
                    <div className="px-3.5 pb-3 text-xs text-slate-800 space-y-2 whitespace-pre-line leading-relaxed">
                      <p className="font-bold text-slate-900">{generatedDraft.title}</p>
                      <p>{generatedDraft.body}</p>
                    </div>

                    {/* Creative Banner Placeholder */}
                    <div className="h-48 bg-gradient-to-br from-indigo-900 via-slate-900 to-violet-950 flex flex-col items-center justify-center text-white p-6 text-center">
                      <span className="text-[10px] uppercase font-bold tracking-widest text-indigo-400">CHIẾN DỊCH TIẾP THỊ</span>
                      <h3 className="font-black text-base mt-1 line-clamp-2">{campaign.name}</h3>
                      <span className="mt-3 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-[11px] font-semibold border border-white/20">
                        {campaign.audience}
                      </span>
                    </div>

                    {/* CTA Bar */}
                    <div className="bg-slate-50 px-3.5 py-2.5 border-t border-b border-slate-100 flex items-center justify-between">
                      <div className="text-[11px] text-slate-500 truncate max-w-[200px]">
                        kienhieu.id.vn
                      </div>
                      <span className="px-3 py-1 bg-indigo-600 text-white font-bold text-xs rounded-md shadow-sm">
                        {generatedDraft.cta || 'ĐĂNG KÝ NGAY'}
                      </span>
                    </div>

                    {/* Engagement Bar */}
                    <div className="p-2 flex items-center justify-around text-slate-500 text-xs font-semibold">
                      <button className="flex items-center gap-1.5 hover:text-blue-600 py-1 px-3 rounded hover:bg-slate-50 transition-colors">
                        <ThumbsUp className="w-3.5 h-3.5" /> Thích
                      </button>
                      <button className="flex items-center gap-1.5 hover:text-slate-800 py-1 px-3 rounded hover:bg-slate-50 transition-colors">
                        <MessageSquare className="w-3.5 h-3.5" /> Bình luận
                      </button>
                      <button className="flex items-center gap-1.5 hover:text-slate-800 py-1 px-3 rounded hover:bg-slate-50 transition-colors">
                        <Share2 className="w-3.5 h-3.5" /> Chia sẻ
                      </button>
                    </div>
                  </div>
                ) : channel === 'tiktok' ? (
                  /* Realistic TikTok Video Script Mockup */
                  <div className="max-w-md mx-auto bg-slate-950 text-white rounded-2xl border border-slate-800 p-5 shadow-xl space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                      <span className="text-xs font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                        <Video className="w-4 h-4 text-rose-500" /> Kịch bản Video ngắn (TikTok / Reels)
                      </span>
                      <span className="text-[10px] bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded font-mono font-bold">
                        30s - 45s
                      </span>
                    </div>

                    <div className="space-y-3 text-xs">
                      <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">1. Hook (3 giây đầu giữ chân):</span>
                        <p className="font-bold text-slate-100">{generatedDraft.title}</p>
                      </div>

                      <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">2. Lời thoại & Bối cảnh diễn xuất:</span>
                        <p className="text-slate-300 whitespace-pre-line leading-relaxed">{generatedDraft.body}</p>
                      </div>

                      <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">3. Call to Action (Kêu gọi):</span>
                        <p className="font-semibold text-emerald-300">{generatedDraft.cta || 'Bấm vào link bio để nhận ưu đãi!'}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Realistic Email Marketing Mockup */
                  <div className="max-w-lg mx-auto bg-white rounded-xl border border-slate-200 shadow-md overflow-hidden text-xs">
                    <div className="bg-slate-100 p-3 border-b border-slate-200 space-y-1 text-slate-600">
                      <div><strong className="text-slate-800">Từ:</strong> MarketFlow Campaign &lt;marketing@enterprise.io&gt;</div>
                      <div><strong className="text-slate-800">Đến:</strong> Tệp khách hàng: {campaign.audience}</div>
                      <div><strong className="text-slate-800">Tiêu đề:</strong> {generatedDraft.title}</div>
                    </div>
                    <div className="p-5 space-y-4 text-slate-800 leading-relaxed whitespace-pre-line">
                      <p>Xin chào quý khách,</p>
                      <p>{generatedDraft.body}</p>
                      <div className="text-center py-4">
                        <span className="inline-block px-5 py-2.5 bg-purple-600 text-white font-bold rounded-lg shadow-sm">
                          {generatedDraft.cta || 'ĐĂNG KÝ THAM GIA NGAY'}
                        </span>
                      </div>
                      <p className="text-slate-500 text-[11px] pt-4 border-t border-slate-100">
                        Trân trọng,<br />Đội ngũ Marketing - MarketFlow AI
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons: Save to Campaign */}
              {generatedDraft && (
                <div className="mt-6 pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-end gap-3">
                  <button
                    onClick={() => handleSaveToCampaign(false)}
                    disabled={savingAction}
                    className="w-full sm:w-auto px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-xs font-semibold transition-colors"
                  >
                    Lưu thành Bản nháp (Draft)
                  </button>

                  <button
                    onClick={() => handleSaveToCampaign(true)}
                    disabled={savingAction}
                    className="w-full sm:w-auto px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-lg text-xs font-bold shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all active:scale-95"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Lưu vào Chiến dịch & Gửi Sếp duyệt ngay (HITL)</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 7. TAB 5: BÁC SĨ AI: CHẨN ĐOÁN & TỐI ƯU HIỆU QUẢ (PERFORMANCE TAB) */}
      {activeTab === 'doctor' && (
        <PerformanceTab
          campaign={campaign}
          campaignKpi={campaignKpi}
          onOpenCopilot={() => setActiveTab('copilot')}
          onOpenAttribution={() => setActiveTab('attribution')}
        />
      )}

      {/* 8. TAB 6: SƠ ĐỒ CHU TRÌNH VÒNG ĐỜI (VISUAL LIFECYCLE FLOW) */}
      {activeTab === 'lifecycle' && (
        <div className="bg-slate-900 rounded-2xl border border-slate-800 shadow-xl overflow-hidden flex flex-col h-[650px] relative">
          {/* Canvas Controls Topbar */}
          <div className="bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-5 py-3 flex items-center justify-between z-10">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span>
              <span className="text-white text-xs font-bold uppercase tracking-wider">Sơ đồ Vòng đời Chiến dịch 5 Giai đoạn</span>
              <span className="text-slate-500 text-xs">•</span>
              <span className="text-indigo-400 text-xs font-semibold">{campaign.name}</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] text-slate-400 bg-slate-800/80 px-2 py-1 rounded border border-slate-700">
                Zoom: {zoomLevel}%
              </span>
              <button 
                onClick={() => setZoomLevel(prev => Math.min(prev + 10, 130))}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-colors"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button 
                onClick={() => setZoomLevel(prev => Math.max(prev - 10, 70))}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-colors"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Interactive Grid Canvas */}
          <div 
            className="flex-1 overflow-auto p-10 flex items-center justify-center bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:20px_20px]"
            style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'center center' }}
          >
            <div className="flex items-center gap-6 relative max-w-6xl">

              {/* Các node bên dưới dùng role="button" + tabIndex + onKeyDown thay vì <button> vì
                  Node 2/3 chứa <button> con; <button> lồng nhau sẽ không hợp lệ về HTML. */}
              {/* Node 1: Trigger / Brief */}
              <div 
                role="button"
                tabIndex={0}
                aria-pressed={activeNode === 'trigger'}
                aria-label="Node 1: Khởi động (Trigger)"
                onClick={() => setActiveNode('trigger')}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setActiveNode('trigger');
                  }
                }}
                className={`w-60 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg ${
                  activeNode === 'trigger' ? 'border-indigo-500 ring-2 ring-indigo-500/30' : 'border-slate-700 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase text-slate-400 flex items-center gap-1">
                    <Play className="w-3 h-3 text-indigo-400" /> 1. Khởi động (Trigger)
                  </span>
                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded font-bold">START</span>
                </div>
                <h4 className="text-white text-xs font-bold truncate">{campaign.name}</h4>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{campaign.objective}</p>
                <div className="mt-3 pt-2 border-t border-slate-700/60 text-[10px] text-slate-400">
                  <span>Đối tượng: {campaign.audience}</span>
                </div>
              </div>

              {/* Arrow */}
              <div className="text-indigo-400 animate-pulse">
                <ArrowRight className="w-5 h-5" />
              </div>

              {/* Node 2: AI Content Copilot */}
              <div 
                role="button"
                tabIndex={0}
                aria-pressed={activeNode === 'ai_gen'}
                aria-label="Node 2: AI Content Copilot"
                onClick={() => setActiveNode('ai_gen')}
                onKeyDown={(e) => {
                  if (e.target !== e.currentTarget) return;
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setActiveNode('ai_gen');
                  }
                }}
                className={`w-60 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg relative ${
                  activeNode === 'ai_gen' ? 'border-violet-500 ring-2 ring-violet-500/30' : 'border-slate-700 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase text-violet-400 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-violet-400" /> 2. AI Copilot
                  </span>
                  <span className="text-[10px] bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded font-bold">GEMINI</span>
                </div>
                <h4 className="text-white text-xs font-bold">Ý tưởng & Bản thảo Đa kênh</h4>
                <p className="text-[11px] text-slate-400 mt-1">Khung AIDA, PAS, FAB chuẩn SEO & Quảng cáo</p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveTab('copilot');
                  }}
                  className="mt-3 w-full py-1.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1 shadow-md transition-all"
                >
                  <Sparkles className="w-3 h-3" /> Mở AI Sáng tạo
                </button>
              </div>

              {/* Arrow */}
              <div className="text-violet-400 animate-pulse">
                <ArrowRight className="w-5 h-5" />
              </div>

              {/* Node 3: Manager Approval Gate (Human-in-the-loop) */}
              <div 
                role="button"
                tabIndex={0}
                aria-pressed={activeNode === 'approval'}
                aria-label="Node 3: Chốt chặn duyệt (HITL)"
                onClick={() => setActiveNode('approval')}
                onKeyDown={(e) => {
                  if (e.target !== e.currentTarget) return;
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setActiveNode('approval');
                  }
                }}
                className={`w-60 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg relative ${
                  activeNode === 'approval' ? 'border-amber-500 ring-2 ring-amber-500/30' : 'border-slate-700 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase text-amber-400 flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3 text-amber-400" /> 3. Chốt chặn duyệt (HITL)
                  </span>
                  <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-bold">
                    {inReviewContents.length} CHỜ
                  </span>
                </div>
                <h4 className="text-white text-xs font-bold">Human-in-the-loop Gate</h4>
                <p className="text-[11px] text-slate-400 mt-1">
                  Chỉ Manager có thẩm quyền duyệt nội dung lên kênh.
                </p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveTab('pipeline');
                  }}
                  className="mt-3 w-full py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-all"
                >
                  <Layers className="w-3 h-3" /> Quản lý Pipeline
                </button>
              </div>

              {/* Arrow */}
              <div className="text-emerald-400 animate-pulse">
                <ArrowRight className="w-5 h-5" />
              </div>

              {/* Node 4: Dispatch & Analytics */}
              <div 
                role="button"
                tabIndex={0}
                aria-pressed={activeNode === 'dispatch'}
                aria-label="Node 4: Đo lường & Bác sĩ AI"
                onClick={() => setActiveNode('dispatch')}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setActiveNode('dispatch');
                  }
                }}
                className={`w-60 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg ${
                  activeNode === 'dispatch' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-slate-700 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase text-blue-400 flex items-center gap-1">
                    <BarChart3 className="w-3 h-3 text-blue-400" /> 4. Đo lường & Bác sĩ AI
                  </span>
                  <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded font-bold">ANALYTICS</span>
                </div>
                <h4 className="text-white text-xs font-bold">Hiệu quả Facebook, Email, Ads</h4>
                <div className="mt-2 space-y-1 text-[11px] text-slate-300">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Views:</span>
                    <span className="font-bold">{campaignKpi ? campaignKpi.total_views.toLocaleString('vi-VN') : '15,700'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Clicks:</span>
                    <span className="font-bold text-emerald-400">
                      {campaignKpi ? `${campaignKpi.total_clicks.toLocaleString('vi-VN')} (${campaignKpi.ctr_percent}%)` : '1,260 (8.0%)'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">ROI:</span>
                    <span className="font-bold text-indigo-400">+{campaignKpi?.roi_percent || 410}%</span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveTab('doctor');
                  }}
                  className="mt-3 w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-all"
                >
                  <Stethoscope className="w-3 h-3" /> Mở Bác sĩ AI
                </button>
              </div>

            </div>
          </div>

          {/* Bottom Info Status Bar */}
          <div className="bg-slate-950 px-5 py-2.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Luồng nghiệp vụ tự động hóa Marketing tuân thủ 100% nguyên tắc kiểm duyệt con người (Human-in-the-loop).</span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              AI: nhà cung cấp theo cấu hình workspace · marketing.kienhieu.id.vn
            </div>
          </div>
        </div>
      )}

      {/* 9. MODAL: LẬP LỊCH XUẤT BẢN (SCHEDULE MODAL) */}
      {scheduleModalContent && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <CalendarCheck className="w-5 h-5 text-indigo-600" />
                <h3 className="font-black text-sm text-slate-900">Lập Lịch Xuất Bản Đa Kênh</h3>
              </div>
              <button 
                onClick={() => setScheduleModalContent(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
              <span className="text-[10px] font-bold uppercase text-slate-400">Bài viết đã được duyệt:</span>
              <p className="font-bold text-slate-800 line-clamp-1">{scheduleModalContent.title}</p>
              <div className="text-[11px] text-slate-500 flex items-center gap-2 pt-1">
                {getChannelBadge(scheduleModalContent.channel_id)}
                <span>Chiến dịch: {campaign.name}</span>
              </div>
            </div>

            {/* AI Golden Hour recommendation chip */}
            <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <strong>Khung giờ vàng AI khuyến nghị:</strong> 19:30 - 21:00 (Thời điểm tập trung đông đảo người dùng trực tuyến, tăng 35% lượt tương tác).
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Ngày xuất bản:</label>
                <input
                  type="date"
                  value={scheduledDate}
                  onChange={(e) => setScheduledDate(e.target.value)}
                  className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Giờ phát hành:</label>
                <input
                  type="time"
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setScheduleModalContent(null)}
                className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg text-xs font-semibold"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleScheduleConfirm}
                disabled={schedulingAction}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
              >
                {schedulingAction ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CalendarCheck className="w-4 h-4" />}
                <span>Xác nhận Lên lịch</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 10. MODAL: TỪ CHỐI BÀI VIẾT KÈM LÝ DO (REJECT REASON MODAL) */}
      {rejectModalContent && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-rose-600">
                <XCircle className="w-5 h-5" />
                <h3 className="font-black text-sm text-slate-900">Từ Chối Phê Duyệt & Góp Ý</h3>
              </div>
              <button 
                onClick={() => setRejectModalContent(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
              <span className="text-[10px] font-bold uppercase text-slate-400">Bài viết cần chỉnh sửa:</span>
              <p className="font-bold text-slate-800 line-clamp-1">{rejectModalContent.title}</p>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1 flex items-center justify-between">
                <span>Lý do từ chối & Yêu cầu chỉnh sửa cụ thể cho Marketer (tối thiểu 3 ký tự):</span>
                <span className={`text-[10px] font-semibold ${rejectReason.trim().length >= 3 ? 'text-emerald-600' : 'text-slate-500'}`}>
                  {rejectReason.trim().length}/3
                </span>
              </label>
              <textarea
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Nhập yêu cầu hiệu chỉnh (VD: Giọng điệu quá suồng sã, cần đổi CTA - tối thiểu 3 ký tự)..."
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:border-rose-500"
              />
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setRejectModalContent(null)}
                className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg text-xs font-semibold"
              >
                Đóng
              </button>
              <button
                type="button"
                onClick={handleRejectConfirm}
                disabled={rejectingAction || rejectReason.trim().length < 3}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-rose-600/20"
              >
                {rejectingAction ? <RefreshCw className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                <span>Xác nhận Từ chối</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};