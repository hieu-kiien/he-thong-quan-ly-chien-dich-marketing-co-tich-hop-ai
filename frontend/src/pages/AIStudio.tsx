import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Lightbulb, 
  FileText, 
  SendHorizontal, 
  Copy, 
  Check, 
  Loader2, 
  ArrowRight, 
  AlertCircle, 
  CheckCircle2, 
  Layers, 
  Zap, 
  TrendingUp, 
  Share2,
  BookmarkPlus,
  Stethoscope,
  RefreshCw,
  AlertTriangle,
  ThumbsUp,
  MessageSquare,
  Video,
  Mail,
  ExternalLink,
  ShieldCheck,
  Eye,
  Lock,
  ShieldAlert
} from 'lucide-react';
import { Campaign, AIIdeaResponse, AIDraftResponse, MarketingContent, AISummaryResponse, KPISummary, OmnichannelResponse, ComplianceCheckResponse } from '../types';
import { aiApi, contentApi, campaignApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { ComplianceAlertBadge } from '../components/ComplianceAlertBadge';
import { FacebookPreviewCard, TikTokPhoneMockup, EmailInboxPreview } from '../components/previews';
import { ExportActions } from '../components/ExportActions';

interface AIStudioProps {
  campaigns: Campaign[];
  selectedCampaign: Campaign | null;
  onSelectCampaign: (c: Campaign | null) => void;
  onContentCreated?: () => void;
  onNavigateToReviews?: () => void;
}

export const AIStudio: React.FC<AIStudioProps> = ({
  campaigns,
  selectedCampaign,
  onSelectCampaign,
  onContentCreated,
  onNavigateToReviews
}) => {
  const toast = useToast();

  // Mode: 'campaign' or 'custom'
  const [mode, setMode] = useState<'campaign' | 'custom'>('campaign');
  
  // Custom Inputs
  const [customTopic, setCustomTopic] = useState<string>('Chiến dịch Tuyển sinh Chuyên ngành AI & Khoa học Dữ liệu 2026');
  const [customProduct, setCustomProduct] = useState<string>('Khóa đào tạo Kỹ sư Trí tuệ Nhân tạo Thực chiến ICTU');
  const [customUsp, setCustomUsp] = useState<string>('Chương trình chuẩn quốc tế, thực hành trên GPU hiệu năng cao, cam kết việc làm');
  const [tone, setTone] = useState<string>('Chuyên nghiệp, truyền cảm hứng, tin cậy');
  const [channelCode, setChannelCode] = useState<string>('facebook');
  const [framework, setFramework] = useState<'AIDA' | 'PAS' | 'FAB'>('AIDA');

  // Studio Modes: 'omnichannel' | 'create' | 'doctor'
  const [studioSection, setStudioSection] = useState<'omnichannel' | 'create' | 'doctor'>('omnichannel');

  // Omnichannel States (R2)
  const [omniBrief, setOmniBrief] = useState<string>('Chiến dịch Tuyển sinh Kỹ sư Trí tuệ Nhân tạo ICTU 2026. Khán giả: Sinh viên CNTT, người chuyển ngành công nghệ. USP: Học thực hành GPU xịn, cam kết kết nối việc làm ngay khi tốt nghiệp.');
  const [omniData, setOmniData] = useState<OmnichannelResponse | null>(null);
  const [omniLoading, setOmniLoading] = useState<boolean>(false);
  const [omniFilter, setOmniFilter] = useState<'all' | 'facebook' | 'tiktok' | 'email'>('all');
  const [omniCreatedStatus, setOmniCreatedStatus] = useState<Record<string, { status: string; id: number }>>({});
  const [omniSaving, setOmniSaving] = useState<Record<string, boolean>>({});
  const [omniPreviewMode, setOmniPreviewMode] = useState<boolean>(true);
  const [omniGlobalImage, setOmniGlobalImage] = useState<string>('https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80');

  // AI Output States
  const [activeTab, setActiveTab] = useState<'ideas' | 'draft'>('ideas');
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [selectedIdeaText, setSelectedIdeaText] = useState<string>('');
  const [ideaData, setIdeaData] = useState<AIIdeaResponse | null>(null);
  const [draftData, setDraftData] = useState<AIDraftResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submittedSuccess, setSubmittedSuccess] = useState<boolean>(false);

  // Compliance Guardrail States (M3)
  const [complianceResult, setComplianceResult] = useState<ComplianceCheckResponse | null>(null);
  const [isCheckingCompliance, setIsCheckingCompliance] = useState<boolean>(false);
  const [omniCompliance, setOmniCompliance] = useState<Record<string, ComplianceCheckResponse | null>>({});
  const [omniChecking, setOmniChecking] = useState<Record<string, boolean>>({});

  // Doctor States
  const [doctorData, setDoctorData] = useState<AISummaryResponse | null>(null);
  const [loadingDoctor, setLoadingDoctor] = useState<boolean>(false);
  const [campaignKpi, setCampaignKpi] = useState<KPISummary | null>(null);

  // Load KPI when campaign changes
  useEffect(() => {
    const activeC = selectedCampaign || (campaigns.length > 0 ? campaigns[0] : null);
    if (activeC) {
      campaignApi.getKpi(activeC.id)
        .then(k => setCampaignKpi(k))
        .catch(() => setCampaignKpi(null));
    }
  }, [selectedCampaign?.id, campaigns]);

  // Realistic Marketing Presets
  const presets = [
    {
      label: '🎓 Tuyển sinh AI ICTU',
      topic: 'Chiến dịch Tuyển sinh Kỹ sư AI 2026',
      product: 'Khóa Đào tạo Trí tuệ Nhân tạo Thực Chiến ICTU',
      usp: 'Đào tạo chuẩn quốc tế, cấp chứng chỉ đại học, cam kết kết nối thực tập tại các tập đoàn công nghệ'
    },
    {
      label: '💼 MarketFlow SaaS',
      topic: 'Chiến dịch Giới thiệu Nền tảng Tiếp thị Tự động MarketFlow',
      product: 'Hệ thống Quản lý Chiến dịch Tích hợp Trợ lý AI MarketFlow',
      usp: 'Tự động hóa luồng tiếp thị đa kênh, chốt chặn duyệt con người HITL an toàn, đo lường ROI theo thời gian thực'
    },
    {
      label: '🌟 Học bổng Tài năng',
      topic: 'Chương trình Học bổng Đột phá Đổi mới Sáng tạo 2026',
      product: 'Quỹ Học bổng Tài năng Công nghệ',
      usp: 'Hỗ trợ 100% học phí, đài thọ kinh phí nghiên cứu Lab và cơ hội du học trao đổi'
    }
  ];

  const applyPreset = (p: typeof presets[0]) => {
    setMode('custom');
    setCustomTopic(p.topic);
    setCustomProduct(p.product);
    setCustomUsp(p.usp);
    toast.info(`Đã tải mẫu chiến dịch: ${p.label}`);
  };

  const handleGenerateIdeas = async () => {
    setLoading(true);
    setSubmittedSuccess(false);
    try {
      const activeCampaign = selectedCampaign || (campaigns.length > 0 ? campaigns[0] : null);
      const cid = mode === 'campaign' && activeCampaign ? activeCampaign.id : null;
      const customData = (mode === 'custom' || !cid) ? {
        topic: customTopic,
        product: customProduct,
        usp: customUsp,
        tone: `${tone} (${framework} framework)`
      } : {
        tone: `${tone} (${framework} framework)`
      };

      const res = await aiApi.generateIdeas(cid, channelCode, 'v3', customData);
      setIdeaData(res);
      setActiveTab('ideas');
      toast.success(`Đã sinh ${res.ideas.length} góc ý tưởng tiếp thị chất lượng cao từ Gemini!`);
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI sinh ý tưởng');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDraft = async (ideaOverride?: string) => {
    setLoading(true);
    setSubmittedSuccess(false);
    try {
      const activeCampaign = selectedCampaign || (campaigns.length > 0 ? campaigns[0] : null);
      const cid = mode === 'campaign' && activeCampaign ? activeCampaign.id : null;
      const customData = (mode === 'custom' || !cid) ? {
        product: customProduct,
        usp: customUsp
      } : undefined;

      const ideaToUse = ideaOverride || selectedIdeaText || (ideaData?.ideas[0]?.headline ? `${ideaData.ideas[0].headline} - ${ideaData.ideas[0].concept}` : 'Chiến lược tiếp thị số đột phá tiếp cận đúng khách hàng tiềm năng');

      const res = await aiApi.generateDraft(cid, ideaToUse, channelCode, 'v3', customData);
      setDraftData(res);
      setActiveTab('draft');
      toast.success('Bản nháp bài viết đa kênh đã được hoàn thiện thành công!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI sinh bản thảo');
    } finally {
      setLoading(false);
    }
  };

  const handleUseIdeaForDraft = (idea: any) => {
    const text = `${idea.headline} - ${idea.concept}`;
    setSelectedIdeaText(text);
    handleGenerateDraft(text);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Đã sao chép nội dung vào Clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  // Submit to Campaign Review Queue
  const handleSubmitForReview = async () => {
    if (!draftData) return;
    setIsSubmitting(true);
    try {
      let targetCampaignId = selectedCampaign?.id || campaigns[0]?.id;
      if (!targetCampaignId && campaigns.length > 0) {
        targetCampaignId = campaigns[0].id;
      }

      if (!targetCampaignId) {
        toast.warning('Vui lòng chọn hoặc tạo một chiến dịch để lưu bài viết');
        setIsSubmitting(false);
        return;
      }

      // Map channel code to channel id
      const chMap: Record<string, number> = {
        facebook: 1,
        email: 2,
        blog: 3,
        google_ads: 4
      };
      const chId = chMap[channelCode] || 1;

      if (complianceResult && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH'))) {
        toast.error('Bài viết chứa vi phạm an toàn thương hiệu nghiêm trọng (HIGH). Vui lòng khắc phục trước khi gửi duyệt!');
        setIsSubmitting(false);
        return;
      }

      // 1. Tạo MarketingContent ở trạng thái DRAFT
      const newContent = await contentApi.create({
        campaign_id: targetCampaignId,
        channel_id: chId,
        title: draftData.title,
        body: draftData.body,
        cta: draftData.cta,
        status: 'AI_DRAFT'
      });

      // 2. Gửi duyệt chuyển sang IN_REVIEW
      await contentApi.submitForReview(newContent.id);
      setSubmittedSuccess(true);
      toast.success('Đã lưu bài viết vào Chiến dịch & Đưa vào Hàng đợi chờ Sếp duyệt (HITL)!');
      if (onContentCreated) onContentCreated();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gửi duyệt bài');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCheckDraftCompliance = async () => {
    if (!draftData) return;
    setIsCheckingCompliance(true);
    try {
      const res = await contentApi.checkCompliance({
        workspace_id: selectedCampaign?.workspace_id || 1,
        channel: channelCode,
        title: draftData.title,
        body: draftData.body,
        cta: draftData.cta
      });
      setComplianceResult(res);
      if (res.status === 'PASSED') {
        toast.success(`Nội dung đạt chuẩn tuân thủ (${res.score}/100 điểm)!`);
      } else if (res.status === 'WARNING') {
        toast.warning(`Phát hiện cảnh báo tiếp thị (${res.score}/100 điểm). Nên kiểm tra trước khi gửi.`);
      } else {
        toast.error(`Bài viết vi phạm chính sách (${res.score}/100 điểm). Nút gửi duyệt đã bị khóa!`);
      }
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi kiểm tra tuân thủ');
    } finally {
      setIsCheckingCompliance(false);
    }
  };

  const handleAutoFix = (word: string, suggestion: string) => {
    if (!draftData) return;
    let replacement = suggestion;
    const match = suggestion.match(/['"“](.+?)['"”]/);
    if (match) {
      replacement = match[1];
    }
    const regex = new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    const newTitle = draftData.title.replace(regex, replacement);
    const newBody = draftData.body.replace(regex, replacement);
    const newCta = draftData.cta ? draftData.cta.replace(regex, replacement) : draftData.cta;
    setDraftData({
      ...draftData,
      title: newTitle,
      body: newBody,
      cta: newCta
    });
    toast.success(`Đã tự động thay thế cụm từ "${word}"`);

    setTimeout(() => {
      contentApi.checkCompliance({
        workspace_id: selectedCampaign?.workspace_id || 1,
        channel: channelCode,
        title: newTitle,
        body: newBody,
        cta: newCta
      }).then(res => setComplianceResult(res)).catch(() => {});
    }, 200);
  };

  const handleCheckOmniCompliance = async (channel: 'facebook' | 'tiktok' | 'email') => {
    if (!omniData) return;
    setOmniChecking(prev => ({ ...prev, [channel]: true }));
    let title = '';
    let body = '';
    let cta = '';
    if (channel === 'facebook' && omniData.facebook) {
      title = omniData.facebook.headline || omniData.facebook.title || '';
      body = omniData.facebook.primary_text || omniData.facebook.body || '';
      cta = omniData.facebook.cta || '';
    } else if (channel === 'tiktok' && omniData.tiktok) {
      title = omniData.tiktok.hook_3s || '';
      body = omniData.tiktok.scenes?.map(s => `${s.visual_action || ''} ${s.voiceover || ''}`).join(' ') || '';
      cta = '';
    } else if (channel === 'email' && omniData.email) {
      title = omniData.email.subject_line_a || omniData.email.subject || '';
      body = omniData.email.body_content || omniData.email.body || '';
      cta = omniData.email.cta_button || omniData.email.cta || '';
    }

    try {
      const res = await contentApi.checkCompliance({
        workspace_id: selectedCampaign?.workspace_id || 1,
        channel,
        title,
        body,
        cta
      });
      setOmniCompliance(prev => ({ ...prev, [channel]: res }));
      if (res.status === 'PASSED') {
        toast.success(`Kênh ${channel.toUpperCase()} đạt chuẩn tuân thủ (${res.score}/100)!`);
      } else if (res.status === 'WARNING') {
        toast.warning(`Kênh ${channel.toUpperCase()} có cảnh báo (${res.score}/100).`);
      } else {
        toast.error(`Kênh ${channel.toUpperCase()} vi phạm chính sách (${res.score}/100)!`);
      }
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), `Lỗi khi quét tuân thủ kênh ${channel}`);
    } finally {
      setOmniChecking(prev => ({ ...prev, [channel]: false }));
    }
  };

  // Omnichannel Generation & HITL Handlers (R2)
  const handleGenerateOmnichannel = async () => {
    const activeCampaign = selectedCampaign || (campaigns.length > 0 ? campaigns[0] : null);
    const briefToUse = omniBrief.trim() || (activeCampaign ? `Chiến dịch: ${activeCampaign.name}. Mục tiêu: ${activeCampaign.objective || ''}. Khán giả: ${activeCampaign.audience || ''}` : '');
    if (!briefToUse) {
      toast.warning('Vui lòng nhập brief chiến dịch tiếp thị!');
      return;
    }
    setOmniLoading(true);
    try {
      const res = await aiApi.generateOmnichannel({
        brief: briefToUse,
        campaign_id: activeCampaign?.id || null,
        channels: ['facebook', 'tiktok', 'email']
      });
      setOmniData(res);
      toast.success('Đã tạo thành công nội dung sáng tạo cho cả 3 kênh tiếp thị (Gemini 2.5 Flash)!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI sinh nội dung đa kênh');
    } finally {
      setOmniLoading(false);
    }
  };

  const handleSaveOmniChannel = async (channel: 'facebook' | 'tiktok' | 'email', submitReview: boolean = false) => {
    if (!omniData) return;
    const targetCampaignId = selectedCampaign?.id || (campaigns.length > 0 ? campaigns[0].id : 1);
    setOmniSaving(prev => ({ ...prev, [channel]: true }));
    try {
      let title = '';
      let body = '';
      let cta = '';
      let channelId = 1;

      if (channel === 'facebook' && omniData.facebook) {
        channelId = 1;
        title = omniData.facebook.headline || omniData.facebook.title || 'Facebook Creative';
        const hashtags = omniData.facebook.hashtags?.length ? `\n\n${omniData.facebook.hashtags.join(' ')}` : '';
        body = (omniData.facebook.primary_text || omniData.facebook.body || '') + hashtags;
        cta = omniData.facebook.cta || '';
      } else if (channel === 'tiktok' && omniData.tiktok) {
        channelId = 5;
        const scenesText = omniData.tiktok.scenes?.map(s => 
          `[Cảnh ${s.scene_number}: ${s.scene_name || s.title || ''} (${s.duration_seconds || 5}s)]\n- Visual: ${s.visual_action || s.visual || ''}\n- Thoại: ${s.voiceover || s.audio || ''}\n- Âm thanh: ${s.audio || ''}`
        ).join('\n\n') || '';
        title = `TikTok Script: ${omniData.tiktok.hook_3s || 'Video ngắn'}`.slice(0, 200);
        body = `HOOK (3 GIÂY ĐẦU):\n${omniData.tiktok.hook_3s}\n\nPHÂN CẢNH:\n${scenesText}\n\nÂM NHẠC ĐỀ XUẤT:\n${omniData.tiktok.sound_recommendation || omniData.tiktok.suggested_audio || ''}`;
        cta = omniData.tiktok.scenes?.[omniData.tiktok.scenes.length - 1]?.visual_action || 'Follow & Like';
      } else if (channel === 'email' && omniData.email) {
        channelId = 2;
        const subA = omniData.email.subject_line_a || omniData.email.subject || '';
        const subB = omniData.email.subject_line_b ? ` (B: ${omniData.email.subject_line_b})` : '';
        title = (subA + subB).slice(0, 200);
        const preheader = omniData.email.preheader ? `[Preheader: ${omniData.email.preheader}]\n\n` : '';
        const ps = omniData.email.ps_note ? `\n\nP.S. ${omniData.email.ps_note}` : '';
        body = preheader + (omniData.email.body_content || omniData.email.body || '') + ps;
        cta = omniData.email.cta_button || omniData.email.cta || '';
      }

      const created = await contentApi.create({
        campaign_id: targetCampaignId,
        channel_id: channelId,
        title,
        body,
        cta,
        image_url: omniGlobalImage,
        status: 'AI_DRAFT'
      });

      if (submitReview) {
        const updated = await contentApi.submitForReview(created.id);
        setOmniCreatedStatus(prev => ({ ...prev, [channel]: { status: 'IN_REVIEW', id: updated.id } }));
        toast.success(`Đã gửi duyệt nội dung ${channel.toUpperCase()} thành công (IN_REVIEW)!`);
      } else {
        setOmniCreatedStatus(prev => ({ ...prev, [channel]: { status: 'AI_DRAFT', id: created.id } }));
        toast.success(`Đã lưu bản nháp ${channel.toUpperCase()} thành công (AI_DRAFT)!`);
      }
      if (onContentCreated) onContentCreated();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), `Lỗi khi lưu nội dung ${channel}`);
    } finally {
      setOmniSaving(prev => ({ ...prev, [channel]: false }));
    }
  };

  const formatOmniCopy = (channel: 'facebook' | 'tiktok' | 'email') => {
    if (!omniData) return '';
    if (channel === 'facebook' && omniData.facebook) {
      const fb = omniData.facebook;
      const hashtags = fb.hashtags?.length ? `\n\n${fb.hashtags.join(' ')}` : '';
      return `[TIÊU ĐỀ]: ${fb.headline || fb.title}\n\n[NỘI DUNG]:\n${fb.primary_text || fb.body}${hashtags}\n\n[LỜI KÊU GỌI]: ${fb.cta}`;
    }
    if (channel === 'tiktok' && omniData.tiktok) {
      const tt = omniData.tiktok;
      const scenesText = tt.scenes?.map(s => 
        `🎬 Cảnh ${s.scene_number}: ${s.scene_name || s.title || ''} (${s.duration_seconds || 5}s)\n- Hành động: ${s.visual_action || s.visual || ''}\n- Lời thoại: ${s.voiceover || s.audio || ''}\n- Hiệu ứng âm thanh: ${s.audio || ''}`
      ).join('\n\n') || '';
      return `🔥 HOOK 3S:\n${tt.hook_3s}\n\n${scenesText}\n\n🎵 GỢI Ý NHẠC NỀN:\n${tt.sound_recommendation || tt.suggested_audio || ''}`;
    }
    if (channel === 'email' && omniData.email) {
      const em = omniData.email;
      return `📧 TIÊU ĐỀ A: ${em.subject_line_a || em.subject}\n📧 TIÊU ĐỀ B: ${em.subject_line_b || ''}\n[PREHEADER]: ${em.preheader || ''}\n\n[NỘI DUNG]:\n${em.body_content || em.body}\n\n👉 [NÚT CTA]: ${em.cta_button || em.cta}\n\n[P.S.]: ${em.ps_note || ''}`;
    }
    return '';
  };

  // Handle run Campaign Performance Doctor
  const handleRunDoctor = async () => {
    const activeC = selectedCampaign || (campaigns.length > 0 ? campaigns[0] : null);
    if (!activeC) {
      toast.warning('Vui lòng chọn một chiến dịch để chẩn đoán');
      return;
    }
    try {
      setLoadingDoctor(true);
      const res = await aiApi.generateSummary(activeC.id);
      setDoctorData(res);
      toast.success('Bác sĩ AI đã hoàn tất phân tích sức khỏe chiến dịch!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi chạy chẩn đoán');
    } finally {
      setLoadingDoctor(false);
    }
  };

  const activeC = selectedCampaign || (campaigns.length > 0 ? campaigns[0] : null);

  // Contents formatted for ExportActions toolbar (R4)
  const omniContentsForExport: MarketingContent[] = [];
  if (omniData) {
    if (omniData.facebook) {
      omniContentsForExport.push({
        id: omniCreatedStatus['facebook']?.id || 101,
        campaign_id: selectedCampaign?.id || 1,
        channel_id: 1,
        created_by: 1,
        title: omniData.facebook.headline || omniData.facebook.title || 'Facebook Post',
        body: omniData.facebook.primary_text || omniData.facebook.body || '',
        cta: omniData.facebook.cta || '',
        image_url: omniGlobalImage,
        status: (omniCreatedStatus['facebook']?.status as any) || 'AI_DRAFT',
        version_no: 1,
        source_ids_json: '[]',
        warnings_json: '[]',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
    if (omniData.tiktok) {
      const fullScript = (omniData.tiktok.scenes || []).map(s => `[Cảnh ${s.scene_number}] ${s.visual_action || s.visual || ''}\nThoại: ${s.voiceover || s.audio || ''}`).join('\n\n');
      omniContentsForExport.push({
        id: omniCreatedStatus['tiktok']?.id || 102,
        campaign_id: selectedCampaign?.id || 1,
        channel_id: 5,
        created_by: 1,
        title: omniData.tiktok.hook_3s || 'TikTok Video Script',
        body: fullScript || omniData.tiktok.hook_3s || '',
        cta: omniData.tiktok.sound_recommendation || omniData.tiktok.suggested_audio || '',
        image_url: omniGlobalImage,
        status: (omniCreatedStatus['tiktok']?.status as any) || 'AI_DRAFT',
        version_no: 1,
        source_ids_json: '[]',
        warnings_json: '[]',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
    if (omniData.email) {
      omniContentsForExport.push({
        id: omniCreatedStatus['email']?.id || 103,
        campaign_id: selectedCampaign?.id || 1,
        channel_id: 2,
        created_by: 1,
        title: omniData.email.subject_line_a || omniData.email.subject || 'Email Campaign',
        body: omniData.email.body_content || omniData.email.body || '',
        cta: omniData.email.cta_button || omniData.email.cta || '',
        image_url: omniGlobalImage,
        status: (omniCreatedStatus['email']?.status as any) || 'AI_DRAFT',
        version_no: 1,
        source_ids_json: '[]',
        warnings_json: '[]',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 no-print">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Google AI Studio (Gemini 2.5 Flash • Hạn ngạch miễn phí 0 VNĐ)
            </span>
            <span className="text-xs text-indigo-300">● Tích hợp Chiến dịch</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black tracking-tight">AI Marketing Copilot & Performance Doctor</h1>
          <p className="text-xs sm:text-sm text-indigo-200 mt-1 max-w-2xl">
            Sáng tạo nội dung đa kênh theo khung chuẩn tiếp thị (AIDA, PAS, FAB) và Chẩn đoán hiệu quả chiến dịch bằng Gemini.
          </p>
        </div>

        {/* Section Switcher */}
        <div className="flex items-center gap-2 bg-slate-800/80 p-1.5 rounded-xl border border-slate-700 overflow-x-auto">
          <button
            onClick={() => setStudioSection('omnichannel')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
              studioSection === 'omnichannel'
                ? 'bg-gradient-to-r from-amber-500 to-indigo-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-amber-300" /> ⚡ Đa kênh 3-in-1 (R2)
          </button>
          <button
            onClick={() => setStudioSection('create')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
              studioSection === 'create'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" /> 🎯 Đơn kênh (AIDA/PAS)
          </button>
          <button
            onClick={() => setStudioSection('doctor')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
              studioSection === 'doctor'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            <Stethoscope className="w-3.5 h-3.5" /> 🩺 Bác sĩ AI Khám Bệnh
          </button>
        </div>
      </div>

      {/* SECTION 0: OMNICHANNEL 3-IN-1 (R2) */}
      {studioSection === 'omnichannel' && (
        <div className="space-y-6">
          {/* Top Context & Brand Kit Inheritance Card */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4 no-print">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-amber-500" />
                  <span>1-Brief ➔ 3-Channels Creative Engine (R2)</span>
                  <span className="text-[11px] font-mono font-bold bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">
                    Gemini 2.5 Flash
                  </span>
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Nhập một bản tóm tắt duy nhất (Brief) để tự động sinh và định dạng trọn gói cho Facebook Post/Ads, TikTok Video Script (4 cảnh) và Email Sequence (A/B Test) với cơ chế bảo toàn Brand Kit.
                </p>
              </div>

              {/* Campaign Selector & Brand Kit Pill */}
              <div className="flex flex-wrap items-center gap-2">
                {campaigns.length > 0 && (
                  <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs">
                    <span className="text-slate-400 font-medium">Chiến dịch:</span>
                    <select
                      value={selectedCampaign?.id || campaigns[0]?.id || ''}
                      onChange={(e) => {
                        const found = campaigns.find(c => c.id === Number(e.target.value)) || null;
                        onSelectCampaign(found);
                      }}
                      className="bg-transparent font-bold text-indigo-700 outline-hidden cursor-pointer"
                    >
                      {campaigns.map(c => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-semibold px-2.5 py-1 rounded-lg">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Brand Kit Kế thừa: MarketFlow AI</span>
                </div>
              </div>
            </div>

            {/* Presets */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-semibold text-slate-600">Gợi ý mẫu Brief:</span>
              {presets.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    const briefText = `Chiến dịch: ${p.topic}\nSản phẩm: ${p.product}\nUSP độc đáo: ${p.usp}\nĐối tượng mục tiêu: Khách hàng tiềm năng, học viên, doanh nghiệp chuyển đổi số.`;
                    setOmniBrief(briefText);
                    toast.info(`Đã áp dụng mẫu: ${p.label}`);
                  }}
                  className="bg-slate-100 hover:bg-amber-50 hover:text-amber-800 hover:border-amber-300 text-slate-700 px-2.5 py-1 rounded-lg transition-colors font-medium border border-slate-200 cursor-pointer"
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Brief Input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="font-bold text-slate-800">
                  Nội dung Brief Chiến dịch (Sản phẩm, USP, Khán giả, Thông điệp cốt lõi):
                </label>
                <span className="text-slate-400 font-mono text-[11px]">{omniBrief.length} ký tự</span>
              </div>
              <textarea
                rows={3}
                value={omniBrief}
                onChange={(e) => setOmniBrief(e.target.value)}
                placeholder="Nhập chi tiết yêu cầu chiến dịch..."
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-800 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-amber-500/20 leading-relaxed"
              />
            </div>

            {/* Action Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
              <div className="text-xs text-slate-500 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>Tự động áp dụng giọng văn thương hiệu & từ điển từ ngữ bị cấm (Banned Keywords)</span>
              </div>

              <button
                type="button"
                onClick={handleGenerateOmnichannel}
                disabled={omniLoading}
                className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-amber-500 via-indigo-600 to-violet-600 hover:from-amber-600 hover:to-violet-700 disabled:bg-slate-300 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/25 transition-all cursor-pointer active:scale-95 disabled:cursor-not-allowed"
              >
                {omniLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Gemini đang sáng tạo 3 kênh...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    <span>⚡ Sáng tạo 3 Kênh Đồng Thời (1-Click)</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Area */}
          {omniData && (
            <div className="space-y-4">
              {/* Filter / View Switcher */}
              <div className="flex items-center justify-between flex-wrap gap-2 bg-white p-2 rounded-xl border border-slate-200">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-xs font-bold text-slate-700 px-2">Bộ lọc hiển thị:</span>
                  <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => setOmniFilter('all')}
                      className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                        omniFilter === 'all' ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      Tất cả 3 Kênh
                    </button>
                    <button
                      type="button"
                      onClick={() => setOmniFilter('facebook')}
                      className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                        omniFilter === 'facebook' ? 'bg-white text-blue-700 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      📘 Facebook
                    </button>
                    <button
                      type="button"
                      onClick={() => setOmniFilter('tiktok')}
                      className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                        omniFilter === 'tiktok' ? 'bg-white text-rose-600 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      🎵 TikTok
                    </button>
                    <button
                      type="button"
                      onClick={() => setOmniFilter('email')}
                      className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                        omniFilter === 'email' ? 'bg-white text-purple-700 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      ✉️ Email
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => setOmniPreviewMode(true)}
                      className={`px-3 py-1 rounded-md transition-all flex items-center gap-1 cursor-pointer ${
                        omniPreviewMode ? 'bg-white text-indigo-700 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-800'
                      }`}
                      title="Xem dạng mockup mạng xã hội trực quan"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Social Mockup</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setOmniPreviewMode(false)}
                      className={`px-3 py-1 rounded-md transition-all flex items-center gap-1 cursor-pointer ${
                        !omniPreviewMode ? 'bg-white text-slate-800 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-800'
                      }`}
                      title="Xem dạng văn bản chi tiết"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>Chi tiết Raw</span>
                    </button>
                  </div>

                  <div className="text-xs text-slate-400 font-mono hidden sm:flex items-center gap-1.5 px-2">
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                    <span>Model: {omniData.model_used || 'gemini-2.5-flash'}</span>
                  </div>
                </div>
              </div>

              {/* Omnichannel Export Actions Toolbar (R4) */}
              <div className="flex items-center justify-between flex-wrap gap-3 bg-gradient-to-r from-indigo-50/90 to-blue-50/90 p-3 rounded-xl border border-indigo-100 shadow-xs no-print">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-indigo-600 text-white rounded-lg">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-900">Bộ công cụ Thao tác Nhanh Đa kênh (Action Tools)</h4>
                    <p className="text-[11px] text-slate-500">Sao chép trọn bộ chuẩn NFC, Xuất file Excel CSV (UTF-8 BOM), hoặc In kế hoạch PDF</p>
                  </div>
                </div>
                <ExportActions
                  contents={omniContentsForExport}
                  campaignName={selectedCampaign?.name || 'Chiến dịch Mạng xã hội 3-in-1'}
                />
              </div>

              {/* 3 Channels Cards Grid */}
              <div className={`grid gap-6 ${omniFilter === 'all' ? 'grid-cols-1 lg:grid-cols-3' : 'grid-cols-1'}`}>
                
                {/* 1. FACEBOOK CARD */}
                {(omniFilter === 'all' || omniFilter === 'facebook') && omniData.facebook && (
                  <div className="bg-white rounded-2xl border border-blue-200/80 shadow-xs flex flex-col justify-between overflow-hidden print-card">
                    <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-4 text-white flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-white/20 rounded-lg">
                          <ThumbsUp className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <h3 className="font-bold text-sm leading-tight">1. Facebook Feed & Ads</h3>
                          <p className="text-[11px] text-blue-100">Bài viết tiếp thị mạng xã hội</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 no-print">
                        <button
                          type="button"
                          onClick={() => handleCheckOmniCompliance('facebook')}
                          disabled={omniChecking['facebook']}
                          className="text-xs bg-white/20 hover:bg-white/30 text-white px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
                          title="Quét tuân thủ chính sách cho Facebook"
                        >
                          {omniChecking['facebook'] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                          <span>Quét</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(formatOmniCopy('facebook'))}
                          className="text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
                        >
                          {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
                          <span>Sao chép</span>
                        </button>
                      </div>
                    </div>

                    {omniPreviewMode ? (
                      <div className="p-4 flex-1">
                        <FacebookPreviewCard
                          headline={omniData.facebook.headline || omniData.facebook.title || ''}
                          primaryText={omniData.facebook.primary_text || omniData.facebook.body || ''}
                          cta={omniData.facebook.cta || 'Đăng ký ngay'}
                          hashtags={omniData.facebook.hashtags}
                          imageUrl={omniGlobalImage}
                          onImageChange={(newUrl) => setOmniGlobalImage(newUrl)}
                          showImagePicker={true}
                        />
                      </div>
                    ) : (
                      <div className="p-5 space-y-4 flex-1 text-xs">
                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tiêu đề (Headline):</span>
                          <h4 className="font-bold text-slate-900 text-sm mt-1 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                            {omniData.facebook.headline || omniData.facebook.title}
                          </h4>
                        </div>

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Nội dung bài viết (Primary Text):</span>
                          <div className="mt-1 bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-700 whitespace-pre-line leading-relaxed max-h-64 overflow-y-auto font-sans">
                            {omniData.facebook.primary_text || omniData.facebook.body}
                          </div>
                        </div>

                        {omniData.facebook.hashtags && omniData.facebook.hashtags.length > 0 && (
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Hashtags:</span>
                            <div className="flex flex-wrap gap-1.5 mt-1">
                              {omniData.facebook.hashtags.map((tag, idx) => (
                                <span key={idx} className="bg-blue-50 text-blue-700 font-mono text-[11px] px-2 py-0.5 rounded-md border border-blue-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Kêu gọi hành động (CTA):</span>
                          <div className="mt-1 bg-blue-50/70 text-blue-700 font-bold p-2.5 rounded-lg border border-blue-200 text-center">
                            {omniData.facebook.cta}
                          </div>
                        </div>
                      </div>
                    )}

                    {omniCompliance['facebook'] && (
                      <div className="px-4 pb-2">
                        <ComplianceAlertBadge
                          result={omniCompliance['facebook']}
                          isLoading={omniChecking['facebook']}
                        />
                      </div>
                    )}

                    {/* HITL Action Bar */}
                    <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center gap-2 no-print">
                      {omniCreatedStatus['facebook']?.status === 'IN_REVIEW' ? (
                        <div className="w-full p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold rounded-lg flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            Đã gửi Sếp duyệt (IN_REVIEW)
                          </span>
                          <span className="text-[10px] bg-emerald-100 px-2 py-0.5 rounded-full">Channel #1</span>
                        </div>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => handleSaveOmniChannel('facebook', false)}
                            disabled={omniSaving['facebook']}
                            className="flex-1 py-2 px-3 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-bold transition-all cursor-pointer active:scale-95"
                          >
                            Lưu nháp
                          </button>
                          {(() => {
                            const isFbBlocked = omniCompliance['facebook'] && (!omniCompliance['facebook']!.can_submit || omniCompliance['facebook']!.violations.some(v => v.severity === 'HIGH'));
                            return (
                              <button
                                type="button"
                                onClick={() => handleSaveOmniChannel('facebook', true)}
                                disabled={omniSaving['facebook'] || isFbBlocked}
                                title={isFbBlocked ? "Không thể gửi duyệt: Kênh này có vi phạm nghiêm trọng (HIGH)" : ""}
                                className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                                  isFbBlocked
                                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed border border-slate-300'
                                    : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 cursor-pointer active:scale-95'
                                }`}
                              >
                                {omniSaving['facebook'] ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : isFbBlocked ? (
                                  <Lock className="w-3.5 h-3.5 text-slate-500" />
                                ) : (
                                  <SendHorizontal className="w-3.5 h-3.5" />
                                )}
                                <span>{isFbBlocked ? 'Bị khóa (Lỗi HIGH)' : 'Gửi duyệt (HITL)'}</span>
                              </button>
                            );
                          })()}
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* 2. TIKTOK CARD */}
                {(omniFilter === 'all' || omniFilter === 'tiktok') && omniData.tiktok && (
                  <div className="bg-white rounded-2xl border border-rose-200/80 shadow-xs flex flex-col justify-between overflow-hidden print-card">
                    <div className="bg-gradient-to-r from-rose-600 to-pink-600 p-4 text-white flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-white/20 rounded-lg">
                          <Video className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <h3 className="font-bold text-sm leading-tight">2. TikTok Video Script</h3>
                          <p className="text-[11px] text-rose-100">Kịch bản 4 phân cảnh (Hook-Problem-Solution-CTA)</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 no-print">
                        <button
                          type="button"
                          onClick={() => handleCheckOmniCompliance('tiktok')}
                          disabled={omniChecking['tiktok']}
                          className="text-xs bg-white/20 hover:bg-white/30 text-white px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
                          title="Quét tuân thủ chính sách cho TikTok"
                        >
                          {omniChecking['tiktok'] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                          <span>Quét</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(formatOmniCopy('tiktok'))}
                          className="text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
                        >
                          {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
                          <span>Sao chép</span>
                        </button>
                      </div>
                    </div>

                    {omniPreviewMode ? (
                      <div className="p-4 flex-1 flex justify-center">
                        <TikTokPhoneMockup
                          hook3s={omniData.tiktok.hook_3s || ''}
                          scenes={omniData.tiktok.scenes?.map((sc, idx) => ({
                            scene_number: sc.scene_number || idx + 1,
                            scene_name: sc.scene_name || sc.title || `Cảnh ${idx + 1}`,
                            duration_seconds: sc.duration_seconds || 5,
                            visual_action: sc.visual_action || sc.visual || '',
                            voiceover: sc.voiceover || sc.audio || '',
                            audio: sc.audio,
                          })) || []}
                          soundRecommendation={omniData.tiktok.sound_recommendation || omniData.tiktok.suggested_audio || ''}
                          imageUrl={omniGlobalImage}
                        />
                      </div>
                    ) : (
                      <div className="p-5 space-y-4 flex-1 text-xs">
                        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl">
                          <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider">🔥 Hook 3 Giây Đầu:</span>
                          <p className="font-bold text-rose-950 mt-1 text-sm leading-snug">{omniData.tiktok.hook_3s}</p>
                        </div>

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">4 Phân cảnh chi tiết:</span>
                          <div className="space-y-2.5 mt-1.5 max-h-72 overflow-y-auto pr-1">
                            {omniData.tiktok.scenes?.map((sc, idx) => (
                              <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
                                <div className="flex items-center justify-between text-[11px] font-bold">
                                  <span className="text-rose-600">Cảnh {sc.scene_number}: {sc.scene_name || sc.title || `Cảnh ${idx+1}`}</span>
                                  <span className="text-slate-400 font-mono text-[10px] bg-slate-200/60 px-1.5 py-0.5 rounded">{sc.duration_seconds || 5}s</span>
                                </div>
                                <div className="text-[11px] text-slate-700">
                                  <strong className="text-slate-900">🎬 Visual:</strong> {sc.visual_action || sc.visual}
                                </div>
                                <div className="text-[11px] text-slate-800 bg-white p-2 rounded border border-slate-100 italic">
                                  <strong className="text-slate-900 not-italic">🗣️ Lời thoại:</strong> "{sc.voiceover || sc.audio}"
                                </div>
                                {sc.audio && (
                                  <div className="text-[10px] text-slate-500">
                                    <strong>🎵 Âm thanh:</strong> {sc.audio}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="p-2.5 bg-slate-100 rounded-lg text-[11px] text-slate-700 flex items-start gap-1.5">
                          <span className="font-bold text-slate-900 shrink-0">🎵 Gợi ý âm nhạc:</span>
                          <span>{omniData.tiktok.sound_recommendation || omniData.tiktok.suggested_audio}</span>
                        </div>
                      </div>
                    )}

                    {omniCompliance['tiktok'] && (
                      <div className="px-4 pb-2">
                        <ComplianceAlertBadge
                          result={omniCompliance['tiktok']}
                          isLoading={omniChecking['tiktok']}
                        />
                      </div>
                    )}

                    {/* HITL Action Bar */}
                    <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center gap-2 no-print">
                      {omniCreatedStatus['tiktok']?.status === 'IN_REVIEW' ? (
                        <div className="w-full p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold rounded-lg flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            Đã gửi Sếp duyệt (IN_REVIEW)
                          </span>
                          <span className="text-[10px] bg-emerald-100 px-2 py-0.5 rounded-full">Channel #5 (TikTok)</span>
                        </div>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => handleSaveOmniChannel('tiktok', false)}
                            disabled={omniSaving['tiktok']}
                            className="flex-1 py-2 px-3 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-bold transition-all cursor-pointer active:scale-95"
                          >
                            Lưu nháp
                          </button>
                          {(() => {
                            const isTtBlocked = omniCompliance['tiktok'] && (!omniCompliance['tiktok']!.can_submit || omniCompliance['tiktok']!.violations.some(v => v.severity === 'HIGH'));
                            return (
                              <button
                                type="button"
                                onClick={() => handleSaveOmniChannel('tiktok', true)}
                                disabled={omniSaving['tiktok'] || isTtBlocked}
                                title={isTtBlocked ? "Không thể gửi duyệt: Kênh này có vi phạm nghiêm trọng (HIGH)" : ""}
                                className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                                  isTtBlocked
                                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed border border-slate-300'
                                    : 'bg-rose-600 hover:bg-rose-700 text-white shadow-md shadow-rose-500/20 cursor-pointer active:scale-95'
                                }`}
                              >
                                {omniSaving['tiktok'] ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : isTtBlocked ? (
                                  <Lock className="w-3.5 h-3.5 text-slate-500" />
                                ) : (
                                  <SendHorizontal className="w-3.5 h-3.5" />
                                )}
                                <span>{isTtBlocked ? 'Bị khóa (Lỗi HIGH)' : 'Gửi duyệt (HITL)'}</span>
                              </button>
                            );
                          })()}
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* 3. EMAIL CARD */}
                {(omniFilter === 'all' || omniFilter === 'email') && omniData.email && (
                  <div className="bg-white rounded-2xl border border-purple-200/80 shadow-xs flex flex-col justify-between overflow-hidden print-card">
                    <div className="bg-gradient-to-r from-purple-600 to-violet-600 p-4 text-white flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-white/20 rounded-lg">
                          <Mail className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <h3 className="font-bold text-sm leading-tight">3. Email Marketing Sequence</h3>
                          <p className="text-[11px] text-purple-100">Chuỗi email chuyển đổi A/B testing</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 no-print">
                        <button
                          type="button"
                          onClick={() => handleCheckOmniCompliance('email')}
                          disabled={omniChecking['email']}
                          className="text-xs bg-white/20 hover:bg-white/30 text-white px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
                          title="Quét tuân thủ chính sách cho Email"
                        >
                          {omniChecking['email'] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                          <span>Quét</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(formatOmniCopy('email'))}
                          className="text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
                        >
                          {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
                          <span>Sao chép</span>
                        </button>
                      </div>
                    </div>

                    {omniPreviewMode ? (
                      <div className="p-4 flex-1">
                        <EmailInboxPreview
                          subjectLineA={omniData.email.subject_line_a || omniData.email.subject || ''}
                          subjectLineB={omniData.email.subject_line_b}
                          preheader={omniData.email.preheader}
                          bodyContent={omniData.email.body_content || omniData.email.body || ''}
                          ctaButton={omniData.email.cta_button || omniData.email.cta || 'Đăng ký ngay'}
                          psNote={omniData.email.ps_note}
                          imageUrl={omniGlobalImage}
                          onImageChange={(newUrl) => setOmniGlobalImage(newUrl)}
                          showImagePicker={true}
                        />
                      </div>
                    ) : (
                      <div className="p-5 space-y-4 flex-1 text-xs">
                        {/* A/B Subjects */}
                        <div className="space-y-2">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">A/B Testing Tiêu đề:</span>
                          <div className="p-2.5 bg-purple-50/70 border border-purple-200 rounded-lg">
                            <div className="text-[10px] font-bold text-purple-700">TIÊU ĐỀ A:</div>
                            <div className="font-bold text-purple-950 mt-0.5">{omniData.email.subject_line_a || omniData.email.subject}</div>
                          </div>
                          <div className="p-2.5 bg-indigo-50/70 border border-indigo-200 rounded-lg">
                            <div className="text-[10px] font-bold text-indigo-700">TIÊU ĐỀ B (THỬ NGHIỆM):</div>
                            <div className="font-bold text-indigo-950 mt-0.5">{omniData.email.subject_line_b || 'N/A'}</div>
                          </div>
                        </div>

                        {omniData.email.preheader && (
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Preheader:</span>
                            <p className="text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-200 mt-1 italic">
                              {omniData.email.preheader}
                            </p>
                          </div>
                        )}

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Nội dung thư:</span>
                          <div className="mt-1 bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-700 whitespace-pre-line leading-relaxed max-h-56 overflow-y-auto">
                            {omniData.email.body_content || omniData.email.body}
                          </div>
                        </div>

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Nút kêu gọi (CTA Button):</span>
                          <div className="mt-1 bg-purple-600 text-white font-bold p-2.5 rounded-lg text-center shadow-xs">
                            {omniData.email.cta_button || omniData.email.cta}
                          </div>
                        </div>

                        {omniData.email.ps_note && (
                          <div className="p-2 bg-amber-50/70 border border-amber-200 rounded-lg text-[11px] text-amber-900 italic">
                            <strong>P.S.</strong> {omniData.email.ps_note}
                          </div>
                        )}
                      </div>
                    )}

                    {omniCompliance['email'] && (
                      <div className="px-4 pb-2">
                        <ComplianceAlertBadge
                          result={omniCompliance['email']}
                          isLoading={omniChecking['email']}
                        />
                      </div>
                    )}

                    {/* HITL Action Bar */}
                    <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center gap-2 no-print">
                      {omniCreatedStatus['email']?.status === 'IN_REVIEW' ? (
                        <div className="w-full p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold rounded-lg flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            Đã gửi Sếp duyệt (IN_REVIEW)
                          </span>
                          <span className="text-[10px] bg-emerald-100 px-2 py-0.5 rounded-full">Channel #2</span>
                        </div>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => handleSaveOmniChannel('email', false)}
                            disabled={omniSaving['email']}
                            className="flex-1 py-2 px-3 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-bold transition-all cursor-pointer active:scale-95"
                          >
                            Lưu nháp
                          </button>
                          {(() => {
                            const isEmBlocked = omniCompliance['email'] && (!omniCompliance['email']!.can_submit || omniCompliance['email']!.violations.some(v => v.severity === 'HIGH'));
                            return (
                              <button
                                type="button"
                                onClick={() => handleSaveOmniChannel('email', true)}
                                disabled={omniSaving['email'] || isEmBlocked}
                                title={isEmBlocked ? "Không thể gửi duyệt: Kênh này có vi phạm nghiêm trọng (HIGH)" : ""}
                                className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                                  isEmBlocked
                                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed border border-slate-300'
                                    : 'bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20 cursor-pointer active:scale-95'
                                }`}
                              >
                                {omniSaving['email'] ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : isEmBlocked ? (
                                  <Lock className="w-3.5 h-3.5 text-slate-500" />
                                ) : (
                                  <SendHorizontal className="w-3.5 h-3.5" />
                                )}
                                <span>{isEmBlocked ? 'Bị khóa (Lỗi HIGH)' : 'Gửi duyệt (HITL)'}</span>
                              </button>
                            );
                          })()}
                        </>
                      )}
                    </div>
                  </div>
                )}

              </div>
            </div>
          )}
        </div>
      )}

      {/* SECTION 1: CREATIVE STUDIO */}
      {studioSection === 'create' && (
        <div className="space-y-6">
          {/* Quick Presets Bar */}
          <div className="bg-white rounded-xl p-3 border border-slate-200/80 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-700">Kịch bản chiến dịch mẫu:</span>
              <div className="flex flex-wrap gap-2">
                {presets.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => applyPreset(p)}
                    className="bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 px-2.5 py-1 rounded-lg transition-colors font-semibold border border-slate-200"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <span className="text-[11px] text-slate-400">1 click áp dụng toàn bộ bối cảnh chiến dịch</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Creator Studio Controls (5 cols) */}
            <div className="lg:col-span-5 space-y-5">
              <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  <span>1. Ngữ cảnh & Mục tiêu Tiếp thị</span>
                </h2>

                {/* Mode Tabs */}
                <div className="flex bg-slate-100 p-1 rounded-xl text-xs font-semibold">
                  <button
                    onClick={() => setMode('campaign')}
                    className={`flex-1 py-1.5 rounded-lg transition-all ${
                      mode === 'campaign'
                        ? 'bg-white text-indigo-700 shadow-xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Kế thừa từ Chiến dịch ({campaigns.length})
                  </button>
                  <button
                    onClick={() => setMode('custom')}
                    className={`flex-1 py-1.5 rounded-lg transition-all ${
                      mode === 'custom'
                        ? 'bg-white text-indigo-700 shadow-xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Nhập tay tùy chỉnh
                  </button>
                </div>

                {/* Campaign Selector if mode is campaign */}
                {mode === 'campaign' ? (
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-slate-700">Chọn chiến dịch thực hiện:</label>
                    {campaigns.length > 0 ? (
                      <select
                        value={selectedCampaign?.id || campaigns[0]?.id || ''}
                        onChange={(e) => {
                          const c = campaigns.find(item => item.id === Number(e.target.value)) || null;
                          onSelectCampaign(c);
                        }}
                        className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                      >
                        {campaigns.map(c => (
                          <option key={c.id} value={c.id}>
                            {c.name} ({c.status})
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                        Chưa có chiến dịch nào trong CSDL. Bạn có thể chuyển sang tab <strong>Nhập tay tùy chỉnh</strong> để thử nghiệm ngay!
                      </div>
                    )}
                    {activeC && (
                      <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-1">
                        <div><strong>Khách hàng mục tiêu:</strong> {activeC.audience}</div>
                        <div><strong>Mục tiêu chiến dịch:</strong> {activeC.objective}</div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Custom Input Fields */
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-bold text-slate-700 block mb-1">Tên chiến dịch / Chủ đề:</label>
                      <input
                        type="text"
                        value={customTopic}
                        onChange={(e) => setCustomTopic(e.target.value)}
                        placeholder="Ví dụ: Khóa học Lập trình AI Thực chiến 2026"
                        className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-slate-700 block mb-1">Sản phẩm / Dịch vụ quảng bá:</label>
                      <input
                        type="text"
                        value={customProduct}
                        onChange={(e) => setCustomProduct(e.target.value)}
                        placeholder="Ví dụ: Khóa học GenAI Masterclass"
                        className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-slate-700 block mb-1">Điểm nổi bật (USP) cần nhấn mạnh:</label>
                      <textarea
                        rows={2}
                        value={customUsp}
                        onChange={(e) => setCustomUsp(e.target.value)}
                        placeholder="Ví dụ: Cầm tay chỉ việc 1-1, cam kết chất lượng đầu ra..."
                        className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                  </div>
                )}

                {/* Target Channel & Framework Controls */}
                <div className="space-y-3 pt-1">
                  <div>
                    <label className="text-xs font-bold text-slate-700 block mb-1">Kênh tiếp thị dự kiến:</label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setChannelCode('facebook')}
                        className={`p-2 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
                          channelCode === 'facebook'
                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                            : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <ThumbsUp className="w-3.5 h-3.5 text-blue-600" />
                        <span>Facebook Post</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setChannelCode('email')}
                        className={`p-2 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
                          channelCode === 'email'
                            ? 'border-purple-500 bg-purple-50 text-purple-700'
                            : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <Mail className="w-3.5 h-3.5 text-purple-600" />
                        <span>Email Newsletter</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setChannelCode('blog')}
                        className={`p-2 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
                          channelCode === 'blog'
                            ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                            : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <FileText className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Blog SEO</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setChannelCode('google_ads')}
                        className={`p-2 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
                          channelCode === 'google_ads'
                            ? 'border-amber-500 bg-amber-50 text-amber-700'
                            : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <ExternalLink className="w-3.5 h-3.5 text-amber-600" />
                        <span>Google Search Ads</span>
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-700 block mb-1">Khung thông điệp (Framework):</label>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { id: 'AIDA', label: 'AIDA' },
                        { id: 'PAS', label: 'PAS' },
                        { id: 'FAB', label: 'FAB' }
                      ].map(f => (
                        <button
                          key={f.id}
                          type="button"
                          onClick={() => setFramework(f.id as any)}
                          className={`p-1.5 rounded-lg border text-xs font-bold transition-all ${
                            framework === f.id
                              ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                              : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                          }`}
                        >
                          {f.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-2 space-y-2">
                  <button
                    onClick={handleGenerateIdeas}
                    disabled={loading}
                    className="w-full py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 disabled:opacity-60 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 transition-all active:scale-98 cursor-pointer"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lightbulb className="w-4 h-4 text-amber-300" />}
                    <span>1. Khởi tạo 5 Góc Ý Tưởng Tiếp Thị</span>
                  </button>

                  <button
                    onClick={() => handleGenerateDraft()}
                    disabled={loading}
                    className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-60 rounded-xl text-xs font-bold flex items-center justify-center gap-2 border border-slate-200 transition-all cursor-pointer"
                  >
                    <FileText className="w-4 h-4 text-indigo-600" />
                    <span>2. Viết Ngay Bản Nháp Hoàn Chỉnh</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Right Column: AI Output Screen (7 cols) */}
            <div className="lg:col-span-7 space-y-4">
              {/* Output Navigation Tabs */}
              <div className="flex items-center justify-between bg-white px-5 py-2.5 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('ideas')}
                    className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                      activeTab === 'ideas'
                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <Lightbulb className="w-3.5 h-3.5" />
                    <span>Ý Tưởng ({ideaData?.ideas.length || 0})</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('draft')}
                    className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                      activeTab === 'draft'
                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Bản Nháp Bài Viết {draftData ? '●' : ''}</span>
                  </button>
                </div>

                {ideaData && (
                  <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                    Model: {ideaData.model_used}
                  </span>
                )}
              </div>

              {/* TAB 1: IDEAS DISPLAY */}
              {activeTab === 'ideas' && (
                <div className="space-y-3">
                  {loading && !ideaData ? (
                    <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center space-y-3">
                      <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
                      <p className="text-xs font-bold text-slate-700">Gemini đang suy nghĩ và tính toán 5 góc ý tưởng tiếp thị...</p>
                    </div>
                  ) : ideaData && ideaData.ideas.length > 0 ? (
                    ideaData.ideas.map((item) => (
                      <div
                        key={item.id}
                        className="bg-white p-4 rounded-2xl border border-slate-200 hover:border-indigo-400 hover:shadow-md transition-all group"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wide bg-indigo-50 px-2.5 py-0.5 rounded-md">
                            {item.angle}
                          </span>
                          <span className="text-xs text-slate-400 italic">Cảm xúc: {item.target_emotion}</span>
                        </div>

                        <h3 className="font-bold text-sm text-slate-900 leading-snug">{item.headline}</h3>
                        <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">{item.concept}</p>

                        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                          <span className="text-[11px] text-slate-400 font-medium">Góc tiếp cận #{item.id}</span>
                          <button
                            onClick={() => handleUseIdeaForDraft(item)}
                            className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                          >
                            <span>Viết thành bài hoàn chỉnh</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="bg-white rounded-2xl p-10 border border-slate-200 text-center space-y-3">
                      <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl mx-auto flex items-center justify-center">
                        <Lightbulb className="w-6 h-6" />
                      </div>
                      <h3 className="text-sm font-bold text-slate-800">Chưa có ý tưởng nào được khởi tạo</h3>
                      <p className="text-xs text-slate-500 max-w-sm mx-auto">
                        Chọn chiến dịch hoặc nhập chủ đề ở cột bên trái và bấm nút <strong>"Khởi tạo 5 Góc Ý Tưởng Tiếp Thị"</strong> để kích hoạt Gemini.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: DRAFT DISPLAY WITH LIVE MOCKUP */}
              {activeTab === 'draft' && (
                <div className="space-y-4">
                  {loading && !draftData ? (
                    <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center space-y-3">
                      <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
                      <p className="text-xs font-bold text-slate-700">AI đang viết tiêu đề, thân bài và lời kêu gọi CTA theo chuẩn kênh...</p>
                    </div>
                  ) : draftData ? (
                    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-5">
                      {/* Top Bar of Draft */}
                      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200">
                            Bản Nháp AI Hoàn Chỉnh
                          </span>
                          <span className="text-xs text-slate-400 uppercase">Kênh: {channelCode}</span>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={handleCheckDraftCompliance}
                            disabled={isCheckingCompliance}
                            className="text-xs font-semibold text-indigo-700 hover:text-indigo-900 flex items-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                          >
                            {isCheckingCompliance ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />}
                            <span>Quét Tuân thủ (Compliance Check)</span>
                          </button>

                          <button
                            onClick={() => copyToClipboard(`${draftData.title}\n\n${draftData.body}\n\n${draftData.cta}`)}
                            className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                          >
                            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>{copied ? 'Đã sao chép' : 'Sao chép bài'}</span>
                          </button>
                        </div>
                      </div>

                      {/* Title & Body */}
                      <div className="space-y-3">
                        <div>
                          <label className="text-[11px] font-bold text-slate-400 uppercase block mb-1">Tiêu đề bài viết:</label>
                          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl font-bold text-sm text-slate-900">
                            {draftData.title}
                          </div>
                        </div>

                        <div>
                          <label className="text-[11px] font-bold text-slate-400 uppercase block mb-1">Nội dung tiếp thị chi tiết:</label>
                          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 whitespace-pre-line leading-relaxed">
                            {draftData.body}
                          </div>
                        </div>

                        <div>
                          <label className="text-[11px] font-bold text-slate-400 uppercase block mb-1">Lời kêu gọi hành động (Call To Action):</label>
                          <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl font-bold text-xs text-indigo-800">
                            {draftData.cta}
                          </div>
                        </div>
                      </div>

                      {/* Compliance Result Badge */}
                      {complianceResult && (
                        <div className="pt-2">
                          <ComplianceAlertBadge
                            result={complianceResult}
                            isLoading={isCheckingCompliance}
                            onAutoFix={handleAutoFix}
                          />
                        </div>
                      )}

                      {/* Action Bar: Submit for Review */}
                      <div className="pt-3 border-t border-slate-100">
                        {submittedSuccess ? (
                          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center justify-between">
                            <span className="flex items-center gap-2">
                              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                              Đã lưu bài viết vào Chiến dịch & Đưa vào Hàng đợi duyệt thành công (IN_REVIEW)!
                            </span>
                            {onNavigateToReviews && (
                              <button
                                onClick={onNavigateToReviews}
                                className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg transition-colors font-semibold"
                              >
                                Đến trang duyệt bài ➔
                              </button>
                            )}
                          </div>
                        ) : (
                          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                            <p className="text-xs text-slate-500">
                              Lưu bài viết vào chiến dịch và đưa vào quy trình kiểm duyệt con người (Human-in-the-loop).
                            </p>

                            {(() => {
                              const isBlocked = complianceResult && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH'));
                              return (
                                <button
                                  onClick={handleSubmitForReview}
                                  disabled={isSubmitting || isBlocked}
                                  title={isBlocked ? "Không thể gửi duyệt: Bài viết có vi phạm nghiêm trọng (HIGH) cần được sửa" : ""}
                                  className={`w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-md transition-all ${
                                    isBlocked
                                      ? 'bg-slate-300 text-slate-500 cursor-not-allowed border border-slate-300'
                                      : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20 cursor-pointer active:scale-98'
                                  }`}
                                >
                                  {isSubmitting ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : isBlocked ? (
                                    <Lock className="w-4 h-4 text-slate-500" />
                                  ) : (
                                    <ShieldCheck className="w-4 h-4" />
                                  )}
                                  <span>
                                    {isBlocked
                                      ? 'Bị khóa do Vi phạm Chính sách (Cần sửa)'
                                      : 'Lưu vào Chiến dịch & Gửi Sếp duyệt ngay (HITL)'}
                                  </span>
                                </button>
                              );
                            })()}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl p-10 border border-slate-200 text-center space-y-3">
                      <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl mx-auto flex items-center justify-center">
                        <FileText className="w-6 h-6" />
                      </div>
                      <h3 className="text-sm font-bold text-slate-800">Chưa có bài viết nháp</h3>
                      <p className="text-xs text-slate-500 max-w-sm mx-auto">
                        Bấm nút <strong>"Viết Ngay Bản Nháp Hoàn Chỉnh"</strong> ở cột bên trái hoặc chọn 1 ý tưởng từ Tab 1 để AI viết thành bài đăng tiếp thị hoàn chỉnh.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: PERFORMANCE DOCTOR */}
      {studioSection === 'doctor' && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                  <Stethoscope className="w-5 h-5 text-emerald-600" />
                  <span>Bác sĩ AI: Chẩn đoán Hiệu quả Chiến dịch (Performance Doctor)</span>
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  AI tự động trích xuất các chỉ số thực tế (Views, Clicks, Spend, Revenue, ROI) và đưa ra chẩn đoán khách quan không ảo giác.
                </p>
              </div>

              {activeC && (
                <button
                  onClick={handleRunDoctor}
                  disabled={loadingDoctor}
                  className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-md shadow-emerald-600/20 transition-all cursor-pointer active:scale-95 shrink-0"
                >
                  {loadingDoctor ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Stethoscope className="w-4 h-4" />}
                  <span>{loadingDoctor ? 'Đang phân tích số liệu...' : `Khám cho: ${activeC.name}`}</span>
                </button>
              )}
            </div>

            {/* Campaign Metrics Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
                <span className="text-slate-400 font-semibold block">Lượt hiển thị (Views)</span>
                <span className="text-lg font-black text-slate-900 mt-1 block">
                  {campaignKpi?.total_views ? campaignKpi.total_views.toLocaleString('vi-VN') : '0'}
                </span>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
                <span className="text-slate-400 font-semibold block">Tương tác Click & CTR</span>
                <span className="text-lg font-black text-emerald-600 mt-1 block">
                  {campaignKpi?.total_clicks ? campaignKpi.total_clicks.toLocaleString('vi-VN') : '0'} ({campaignKpi?.ctr_percent ? campaignKpi.ctr_percent.toFixed(1) : '0.0'}%)
                </span>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
                <span className="text-slate-400 font-semibold block">Ngân sách tiêu (Cost)</span>
                <span className="text-lg font-black text-slate-900 mt-1 block">
                  {campaignKpi?.total_cost ? Number(campaignKpi.total_cost).toLocaleString('vi-VN') : '0'} đ
                </span>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
                <span className="text-slate-400 font-semibold block">Tỷ suất sinh lời ROI</span>
                <span className="text-lg font-black text-indigo-600 mt-1 block">
                  {campaignKpi?.roi_percent ? (campaignKpi.roi_percent > 0 ? '+' : '') + campaignKpi.roi_percent.toFixed(1) + '%' : '0.0%'}
                </span>
              </div>
            </div>
          </div>

          {/* Doctor Diagnostic Output */}
          {doctorData ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6 shadow-xs">
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Kết quả Chẩn đoán Sức khỏe Chiến dịch</span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  Model: {doctorData.model_used}
                </span>
              </div>

              {/* Executive Summary */}
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Tóm tắt Cấp Quản lý (Executive Summary)</h4>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed">
                  {doctorData.executive_summary}
                </div>
              </div>

              {/* Strengths & Weaknesses */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200 space-y-2">
                  <span className="text-xs font-bold uppercase text-emerald-800 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Điểm mạnh ghi nhận ({doctorData.strengths?.length || 0})
                  </span>
                  <ul className="text-xs space-y-1 text-slate-700">
                    {doctorData.strengths?.map((st, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-600 font-bold">•</span>
                        <span>{st}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-amber-50/60 p-4 rounded-xl border border-amber-200 space-y-2">
                  <span className="text-xs font-bold uppercase text-amber-800 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-600" /> Điểm nghẽn cần khắc phục ({doctorData.weaknesses?.length || 0})
                  </span>
                  <ul className="text-xs space-y-1 text-slate-700">
                    {doctorData.weaknesses?.map((wk, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-amber-600 font-bold">•</span>
                        <span>{wk}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Plan */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-700 flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-indigo-600" /> Khuyến nghị Hành động Tối ưu Ngân sách & Chuyển đổi
                </h4>
                <div className="space-y-2">
                  {doctorData.recommendations?.map((rec, i) => (
                    <div key={i} className="bg-indigo-50/50 p-3.5 rounded-xl border border-indigo-200 flex items-start gap-2.5 text-xs text-slate-800 leading-relaxed">
                      <span className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <span>{rec}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 p-12 text-center text-slate-400 text-xs space-y-2">
              <Stethoscope className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="font-semibold text-slate-600">Chưa có kết quả chẩn đoán nào</p>
              <p>Bấm nút "Khám cho: {activeC?.name}" ở trên để Bác sĩ AI phân tích toàn diện chiến dịch.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
