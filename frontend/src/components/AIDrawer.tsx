import React, { useState, useEffect } from 'react';
import { 
  X, 
  Sparkles, 
  Lightbulb, 
  FileText, 
  BarChart3, 
  Check, 
  AlertCircle, 
  Copy, 
  Loader2,
  ArrowRight,
  Send,
  SendHorizontal,
  CheckCircle2,
  Clock,
  Zap,
  Video,
  Mail,
  ShieldCheck,
  ShieldAlert,
  Lock
} from 'lucide-react';
import { Campaign, AIIdeaResponse, AIDraftResponse, AISummaryResponse, MarketingContent, OmnichannelResponse, ComplianceCheckResponse } from '../types';
import { aiApi, contentApi, getApiErrorMessage } from '../services/api';
import { useToast } from './Toast';
import { ComplianceAlertBadge } from './ComplianceAlertBadge';

interface AIDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  campaign: Campaign | null;
  campaigns?: Campaign[];
  onSelectCampaign?: (c: Campaign | null) => void;
  onContentCreated?: () => void;
}

export const AIDrawer: React.FC<AIDrawerProps> = ({
  isOpen,
  onClose,
  campaign,
  campaigns = [],
  onSelectCampaign,
  onContentCreated
}) => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'omnichannel' | 'idea' | 'draft' | 'summary'>('omnichannel');
  const [promptVersion, setPromptVersion] = useState<string>('v3');
  const [channelCode, setChannelCode] = useState<string>('facebook');
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [createdContent, setCreatedContent] = useState<MarketingContent | null>(null);
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);
  const [complianceResult, setComplianceResult] = useState<ComplianceCheckResponse | null>(null);
  const [isCheckingCompliance, setIsCheckingCompliance] = useState<boolean>(false);

  // Omnichannel States
  const [omniBrief, setOmniBrief] = useState<string>('');
  const [omniData, setOmniData] = useState<OmnichannelResponse | null>(null);
  const [omniSubTab, setOmniSubTab] = useState<'facebook' | 'tiktok' | 'email'>('facebook');

  // AI Output States
  const [ideaData, setIdeaData] = useState<AIIdeaResponse | null>(null);
  const [selectedIdeaText, setSelectedIdeaText] = useState<string>('');
  const [draftData, setDraftData] = useState<AIDraftResponse | null>(null);
  const [summaryData, setSummaryData] = useState<AISummaryResponse | null>(null);

  // Đóng Drawer khi nhấn phím Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Active campaign: use passed campaign or first available from list
  const activeCampaign = campaign || (campaigns.length > 0 ? campaigns[0] : null);

  // Reset createdContent khi đổi draft hoặc campaign
  useEffect(() => {
    setCreatedContent(null);
    setSaveSuccess(false);
  }, [activeCampaign?.id, draftData?.title]);

  if (!isOpen) return null;

  const handleGenerateIdeas = async () => {
    setLoading(true);
    try {
      const res = await aiApi.generateIdeas(activeCampaign?.id || null, channelCode, promptVersion);
      setIdeaData(res);
      toast.success(`Đã sinh thành công ${res.ideas.length} góc ý tưởng tiếp thị!`);
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI sinh ý tưởng');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDraft = async () => {
    setLoading(true);
    try {
      const ideaToUse = selectedIdeaText || 'Giải pháp đột phá nâng cao năng suất cùng AI';
      const res = await aiApi.generateDraft(activeCampaign?.id || null, ideaToUse, channelCode, promptVersion);
      setDraftData(res);
      setCreatedContent(null);
      toast.success('Bản nháp nội dung đã được khởi tạo thành công!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI sinh bản nháp');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!activeCampaign) {
      toast.warning('Vui lòng chọn một chiến dịch để phân tích số liệu!');
      return;
    }
    setLoading(true);
    try {
      const res = await aiApi.generateSummary(activeCampaign.id, promptVersion);
      setSummaryData(res);
      toast.success('Đã phân tích và tóm tắt chỉ số chiến dịch!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI phân tích chỉ số');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDraftToDB = async (): Promise<MarketingContent | null> => {
    if (!draftData) return null;
    const targetCampaignId = activeCampaign?.id || (campaigns.length > 0 ? campaigns[0].id : 1);
    setLoading(true);
    try {
      const res = await contentApi.create({
        campaign_id: targetCampaignId,
        channel_id: channelCode === 'email' ? 2 : channelCode === 'tiktok' ? 5 : 1,
        title: draftData.title,
        body: draftData.body,
        cta: draftData.cta,
        status: 'AI_DRAFT'
      });
      setCreatedContent(res);
      setSaveSuccess(true);
      toast.success('Đã lưu bản nháp vào hệ thống (AI_DRAFT)');
      if (onContentCreated) onContentCreated();
      return res;
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi lưu bản nháp');
      return null;
    } finally {
      setLoading(false);
    }
  };

  const handleCheckDraftCompliance = async () => {
    if (!draftData) return;
    setIsCheckingCompliance(true);
    try {
      const res = await contentApi.checkCompliance({
        workspace_id: activeCampaign?.workspace_id || 1,
        channel: channelCode,
        title: draftData.title,
        body: draftData.body,
        cta: draftData.cta
      });
      setComplianceResult(res);
      if (res.status === 'PASSED') {
        toast.success(`Nội dung đạt chuẩn tuân thủ (${res.score}/100)!`);
      } else if (res.status === 'WARNING') {
        toast.warning(`Có cảnh báo chính sách (${res.score}/100).`);
      } else {
        toast.error(`Vi phạm chính sách (${res.score}/100). Đã khóa nút gửi duyệt!`);
      }
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi kiểm tra tuân thủ');
    } finally {
      setIsCheckingCompliance(false);
    }
  };

  const handleSubmitForReview = async () => {
    if (!draftData) return;
    if (complianceResult && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH'))) {
      toast.error('Bài viết chứa vi phạm an toàn thương hiệu nghiêm trọng (HIGH). Vui lòng sửa lại trước khi gửi duyệt!');
      return;
    }
    setIsSubmittingReview(true);
    try {
      let contentToSubmit = createdContent;
      if (!contentToSubmit) {
        contentToSubmit = await handleSaveDraftToDB();
        if (!contentToSubmit) return;
      }
      const updated = await contentApi.submitForReview(contentToSubmit.id);
      setCreatedContent(updated);
      toast.success('Đã gửi bài viết vào Hàng đợi phê duyệt của Quản lý (IN_REVIEW)!');
      if (onContentCreated) onContentCreated();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gửi duyệt nội dung');
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.info('Đã sao chép nội dung vào khay nhớ tạm');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAutoFixViolation = (orig: string, repl: string) => {
    if (!draftData) return;
    const newTitle = draftData.title.split(orig).join(repl);
    const newBody = draftData.body.split(orig).join(repl);
    const newCta = draftData.cta.split(orig).join(repl);
    setDraftData({
      ...draftData,
      title: newTitle,
      body: newBody,
      cta: newCta
    });
    setComplianceResult(null);
    toast.info(`Đã thay thế "${orig}" thành "${repl}". Vui lòng bấm Quét lại!`);
  };

  // Omnichannel Generation & HITL Handlers
  const handleGenerateOmnichannel = async () => {
    const briefToUse = omniBrief.trim() || (activeCampaign ? `Chiến dịch: ${activeCampaign.name}. Mục tiêu: ${activeCampaign.objective || ''}. Khán giả: ${activeCampaign.audience || ''}` : '');
    if (!briefToUse) {
      toast.warning('Vui lòng nhập brief yêu cầu chiến dịch!');
      return;
    }
    setLoading(true);
    try {
      const res = await aiApi.generateOmnichannel({
        brief: briefToUse,
        campaign_id: activeCampaign?.id || null,
        channels: ['facebook', 'tiktok', 'email']
      });
      setOmniData(res);
      toast.success('Đã sinh thành công nội dung sáng tạo cho cả 3 kênh!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI sinh nội dung đa kênh');
    } finally {
      setLoading(false);
    }
  };

  const [omniCreatedStatus, setOmniCreatedStatus] = useState<Record<string, { status: string; id: number }>>({});
  const [isSavingOmni, setIsSavingOmni] = useState<boolean>(false);

  const handleSaveOmniChannel = async (channel: 'facebook' | 'tiktok' | 'email', submitReview: boolean = false) => {
    if (!omniData) return;
    const targetCampaignId = activeCampaign?.id || (campaigns.length > 0 ? campaigns[0].id : 1);
    setIsSavingOmni(true);
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
      setIsSavingOmni(false);
    }
  };

  const formatFacebookCopy = () => {
    if (!omniData?.facebook) return '';
    const fb = omniData.facebook;
    const hashtags = fb.hashtags?.length ? `\n\n${fb.hashtags.join(' ')}` : '';
    return `[TIÊU ĐỀ]: ${fb.headline || fb.title}\n\n[NỘI DUNG]:\n${fb.primary_text || fb.body}${hashtags}\n\n[LỜI KÊU GỌI]: ${fb.cta}`;
  };

  const formatTikTokCopy = () => {
    if (!omniData?.tiktok) return '';
    const tt = omniData.tiktok;
    const scenesText = tt.scenes?.map(s => 
      `🎬 Cảnh ${s.scene_number}: ${s.scene_name || s.title || ''} (${s.duration_seconds || 5}s)\n- Hành động: ${s.visual_action || s.visual || ''}\n- Lời thoại: ${s.voiceover || s.audio || ''}\n- Hiệu ứng âm thanh: ${s.audio || ''}`
    ).join('\n\n') || '';
    return `🔥 HOOK 3S:\n${tt.hook_3s}\n\n${scenesText}\n\n🎵 GỢI Ý NHẠC NỀN:\n${tt.sound_recommendation || tt.suggested_audio || ''}`;
  };

  const formatEmailCopy = () => {
    if (!omniData?.email) return '';
    const em = omniData.email;
    return `📧 TIÊU ĐỀ A: ${em.subject_line_a || em.subject}\n📧 TIÊU ĐỀ B: ${em.subject_line_b || ''}\n[PREHEADER]: ${em.preheader || ''}\n\n[NỘI DUNG]:\n${em.body_content || em.body}\n\n👉 [NÚT CTA]: ${em.cta_button || em.cta}\n\n[P.S.]: ${em.ps_note || ''}`;
  };

  return (
    <div 
      onClick={onClose}
      className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-slate-900/40 backdrop-blur-xs transition-opacity"
    >
      <div 
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-300"
      >
        
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-200/80 bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="w-4 h-4 animate-pulse" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                AI Marketing Copilot
                <span className="text-[10px] font-bold bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
                  OpenRouter
                </span>
              </h3>
              {campaigns && campaigns.length > 0 ? (
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[11px] text-slate-400 font-medium">Chiến dịch:</span>
                  <select
                    value={activeCampaign?.id || ''}
                    onChange={(e) => {
                      const found = campaigns.find(c => c.id === Number(e.target.value));
                      if (onSelectCampaign) onSelectCampaign(found || null);
                    }}
                    className="text-xs text-indigo-700 font-bold bg-slate-100/90 border border-slate-200 rounded px-2 py-0.5 max-w-[220px] truncate outline-hidden cursor-pointer"
                  >
                    {campaigns.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              ) : (
                <p className="text-xs text-slate-500 truncate max-w-xs">{activeCampaign?.name || 'Chế độ tự do'}</p>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Prompt Version & Channel Selector */}
        <div className="px-5 py-3 border-b border-slate-100 bg-white flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Phiên bản Prompt:</span>
            <select
              value={promptVersion}
              onChange={(e) => setPromptVersion(e.target.value)}
              className="bg-slate-100 border border-slate-200 rounded px-2 py-1 font-semibold text-indigo-700 outline-hidden"
            >
              <option value="v3">V3: Ràng buộc & Cấm ảo giác (98% Acc)</option>
              <option value="v2">V2: Structured JSON Schema</option>
              <option value="v1">V1: Zero-shot thô</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Kênh:</span>
            <select
              value={channelCode}
              onChange={(e) => setChannelCode(e.target.value)}
              className="bg-slate-100 border border-slate-200 rounded px-2 py-1 font-semibold text-slate-700 outline-hidden"
            >
              <option value="facebook">Facebook Ads</option>
              <option value="tiktok">TikTok Video Script</option>
              <option value="email">Email Newsletter</option>
            </select>
          </div>
        </div>

        {/* Tabs Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600 px-5 overflow-x-auto">
          <button
            onClick={() => setActiveTab('omnichannel')}
            className={`py-3 px-3.5 border-b-2 flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
              activeTab === 'omnichannel' 
                ? 'border-indigo-600 text-indigo-600 bg-white font-bold' 
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            <span>⚡ Đa kênh 3-in-1</span>
          </button>
          <button
            onClick={() => setActiveTab('idea')}
            className={`py-3 px-3.5 border-b-2 flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
              activeTab === 'idea' 
                ? 'border-indigo-600 text-indigo-600 bg-white font-bold' 
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <Lightbulb className="w-3.5 h-3.5" />
            <span>1. Sinh ý tưởng (IDEA)</span>
          </button>
          <button
            onClick={() => setActiveTab('draft')}
            className={`py-3 px-3.5 border-b-2 flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
              activeTab === 'draft' 
                ? 'border-indigo-600 text-indigo-600 bg-white font-bold' 
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>2. Viết bản nháp (DRAFT)</span>
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`py-3 px-3.5 border-b-2 flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
              activeTab === 'summary' 
                ? 'border-indigo-600 text-indigo-600 bg-white font-bold' 
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>3. Tóm tắt KPI (SUMMARY)</span>
          </button>
        </div>

        {/* Drawer Body Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          
          {/* TAB 0: OMNICHANNEL 3-IN-1 */}
          {activeTab === 'omnichannel' && (
            <div className="space-y-4">
              <div className="bg-gradient-to-r from-amber-50 to-indigo-50 border border-amber-200/60 rounded-xl p-3.5 text-xs text-slate-700 space-y-2">
                <div className="flex items-center gap-1.5 font-bold text-slate-900">
                  <Zap className="w-4 h-4 text-amber-500" />
                  <span>1-Click Sáng tạo Đa kênh (R2 • Gemini 2.5 Flash)</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Nhập một Brief tiếp thị duy nhất để AI tự động sinh trọn bộ 3 kênh: <strong>Facebook Feed/Ads</strong>, <strong>TikTok Script (4 cảnh)</strong> và <strong>Email Sequence (A/B testing)</strong> kế thừa Brand Kit.
                </p>
                {activeCampaign && (
                  <button
                    type="button"
                    onClick={() => {
                      const text = `Chiến dịch: ${activeCampaign.name}\nMục tiêu: ${activeCampaign.objective || ''}\nKhách hàng: ${activeCampaign.audience || ''}`;
                      setOmniBrief(text);
                    }}
                    className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 bg-white/80 border border-indigo-200 px-2 py-1 rounded cursor-pointer transition-colors"
                  >
                    ⚡ Lấy dữ liệu từ {activeCampaign.name}
                  </button>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Bản tóm tắt chiến dịch (Marketing Brief):
                </label>
                <textarea
                  value={omniBrief}
                  onChange={(e) => setOmniBrief(e.target.value)}
                  placeholder="Ví dụ: Chiến dịch tuyển sinh Khóa kỹ sư Trí tuệ nhân tạo thực chiến ICTU 2026. Đối tượng: Sinh viên CNTT, người chuyển ngành. USP: Học thực hành GPU xịn, cam kết đầu ra..."
                  className="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 focus:bg-white h-24"
                />
              </div>

              <button
                onClick={handleGenerateOmnichannel}
                disabled={loading}
                className="w-full py-2.5 bg-gradient-to-r from-amber-500 via-indigo-600 to-violet-600 hover:from-amber-600 hover:to-violet-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                <span>Sáng tạo 3 kênh đồng thời (Facebook, TikTok, Email)</span>
              </button>

              {omniData && (
                <div className="space-y-3 mt-4">
                  {/* Channel Subtabs */}
                  <div className="flex bg-slate-100 p-1 rounded-xl text-xs font-semibold gap-1">
                    <button
                      onClick={() => setOmniSubTab('facebook')}
                      className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        omniSubTab === 'facebook'
                          ? 'bg-white text-blue-700 shadow-xs font-bold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                      <span>Facebook</span>
                    </button>
                    <button
                      onClick={() => setOmniSubTab('tiktok')}
                      className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        omniSubTab === 'tiktok'
                          ? 'bg-white text-rose-600 shadow-xs font-bold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <Video className="w-3.5 h-3.5 text-rose-600" />
                      <span>TikTok Video</span>
                    </button>
                    <button
                      onClick={() => setOmniSubTab('email')}
                      className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        omniSubTab === 'email'
                          ? 'bg-white text-purple-700 shadow-xs font-bold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <Mail className="w-3.5 h-3.5 text-purple-600" />
                      <span>Email</span>
                    </button>
                  </div>

                  {/* Channel Content Card */}
                  <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                      <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                        {omniSubTab === 'facebook' && 'Nội dung Facebook Feed & Ads'}
                        {omniSubTab === 'tiktok' && 'Kịch bản TikTok 4 Phân cảnh (Shorts/Reels)'}
                        {omniSubTab === 'email' && 'Email Marketing Sequence (A/B Test)'}
                      </span>
                      <button
                        onClick={() => {
                          const text = omniSubTab === 'facebook' ? formatFacebookCopy() : omniSubTab === 'tiktok' ? formatTikTokCopy() : formatEmailCopy();
                          copyToClipboard(text);
                        }}
                        className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 cursor-pointer"
                      >
                        {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copied ? 'Đã sao chép' : 'Sao chép kênh này'}</span>
                      </button>
                    </div>

                    {/* Subtab: FACEBOOK */}
                    {omniSubTab === 'facebook' && omniData.facebook && (
                      <div className="space-y-2 text-xs">
                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase">Tiêu đề (Headline):</span>
                          <p className="font-bold text-slate-900 bg-white p-2.5 rounded border border-slate-200 mt-1">
                            {omniData.facebook.headline || omniData.facebook.title}
                          </p>
                        </div>
                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase">Nội dung chính (Primary Text):</span>
                          <p className="text-slate-700 bg-white p-2.5 rounded border border-slate-200 mt-1 whitespace-pre-line leading-relaxed">
                            {omniData.facebook.primary_text || omniData.facebook.body}
                          </p>
                        </div>
                        {omniData.facebook.hashtags && omniData.facebook.hashtags.length > 0 && (
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Hashtags:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {omniData.facebook.hashtags.map((tag, idx) => (
                                <span key={idx} className="bg-blue-50 text-blue-700 text-[11px] px-2 py-0.5 rounded font-mono">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase">Kêu gọi hành động (CTA):</span>
                          <p className="font-semibold text-blue-700 bg-blue-50/60 p-2 rounded border border-blue-100 mt-1">
                            {omniData.facebook.cta}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Subtab: TIKTOK */}
                    {omniSubTab === 'tiktok' && omniData.tiktok && (
                      <div className="space-y-3 text-xs">
                        <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-lg">
                          <span className="text-[10px] font-bold text-rose-700 uppercase">🔥 Hook 3 giây đầu:</span>
                          <p className="font-bold text-rose-950 mt-0.5">{omniData.tiktok.hook_3s}</p>
                        </div>

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase">4 Phân cảnh chi tiết:</span>
                          <div className="space-y-2 mt-1">
                            {omniData.tiktok.scenes?.map((scene, idx) => (
                              <div key={idx} className="p-2.5 bg-white rounded border border-slate-200 space-y-1">
                                <div className="flex items-center justify-between text-[11px] font-bold text-slate-800">
                                  <span className="text-indigo-600">Cảnh {scene.scene_number}: {scene.scene_name || scene.title || `Phân đoạn ${idx+1}`}</span>
                                  <span className="text-slate-400 font-mono text-[10px]">{scene.duration_seconds || 5}s</span>
                                </div>
                                <div className="text-[11px] text-slate-600">
                                  <strong>Hình ảnh:</strong> {scene.visual_action || scene.visual}
                                </div>
                                <div className="text-[11px] text-slate-700">
                                  <strong>Lời thoại:</strong> "{scene.voiceover || scene.audio}"
                                </div>
                                {scene.audio && (
                                  <div className="text-[10px] text-slate-500 italic">
                                    <strong>Âm thanh:</strong> {scene.audio}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="p-2 bg-slate-100 rounded text-[11px] text-slate-700">
                          <strong>🎵 Gợi ý âm nhạc:</strong> {omniData.tiktok.sound_recommendation || omniData.tiktok.suggested_audio}
                        </div>
                      </div>
                    )}

                    {/* Subtab: EMAIL */}
                    {omniSubTab === 'email' && omniData.email && (
                      <div className="space-y-2 text-xs">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          <div className="p-2 bg-purple-50/70 border border-purple-200 rounded">
                            <span className="text-[10px] font-bold text-purple-700 uppercase">Tiêu đề (Option A):</span>
                            <p className="font-bold text-purple-950 mt-0.5 text-xs">{omniData.email.subject_line_a || omniData.email.subject}</p>
                          </div>
                          <div className="p-2 bg-indigo-50/70 border border-indigo-200 rounded">
                            <span className="text-[10px] font-bold text-indigo-700 uppercase">Tiêu đề (Option B - Thử nghiệm):</span>
                            <p className="font-bold text-indigo-950 mt-0.5 text-xs">{omniData.email.subject_line_b || 'N/A'}</p>
                          </div>
                        </div>

                        {omniData.email.preheader && (
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Preheader:</span>
                            <p className="text-slate-600 bg-white p-2 rounded border border-slate-200 mt-1 italic">
                              {omniData.email.preheader}
                            </p>
                          </div>
                        )}

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase">Nội dung thư:</span>
                          <p className="text-slate-700 bg-white p-2.5 rounded border border-slate-200 mt-1 whitespace-pre-line leading-relaxed">
                            {omniData.email.body_content || omniData.email.body}
                          </p>
                        </div>

                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase">Nút kêu gọi (CTA Button):</span>
                          <p className="font-bold text-purple-700 bg-purple-50 p-2 rounded border border-purple-100 mt-1">
                            {omniData.email.cta_button || omniData.email.cta}
                          </p>
                        </div>

                        {omniData.email.ps_note && (
                          <div className="text-[11px] text-slate-600 italic bg-amber-50/60 p-2 rounded border border-amber-200">
                            <strong>P.S.</strong> {omniData.email.ps_note}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Channel HITL Action Buttons */}
                    <div className="pt-2 border-t border-slate-200 flex flex-col sm:flex-row items-center gap-2">
                      {omniCreatedStatus[omniSubTab]?.status === 'IN_REVIEW' ? (
                        <div className="w-full p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            Đã gửi Sếp duyệt kênh {omniSubTab.toUpperCase()}!
                          </span>
                          <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold">
                            IN_REVIEW
                          </span>
                        </div>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => handleSaveOmniChannel(omniSubTab, false)}
                            disabled={isSavingOmni}
                            className="w-full sm:flex-1 py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 border border-slate-200 transition-all cursor-pointer"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Lưu nháp ({omniSubTab.toUpperCase()})</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSaveOmniChannel(omniSubTab, true)}
                            disabled={isSavingOmni}
                            className="w-full sm:flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
                          >
                            {isSavingOmni ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <SendHorizontal className="w-3.5 h-3.5" />}
                            <span>Gửi duyệt Sếp (HITL)</span>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* TAB 1: IDEAS */}
          {activeTab === 'idea' && (
            <div className="space-y-4">
              <div className="bg-indigo-50/70 border border-indigo-100 rounded-lg p-3 text-xs text-indigo-900 flex items-start gap-2">
                <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                <span>AI sẽ phân tích mục tiêu chiến dịch, đối tượng và đặc tính USP sản phẩm để đề xuất 5 góc nội dung độc đáo.</span>
              </div>

              <button
                onClick={handleGenerateIdeas}
                disabled={loading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                <span>Khởi tạo 5 ý tưởng tiếp thị</span>
              </button>

              {ideaData && (
                <div className="space-y-3 mt-4">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold text-slate-800">Kết quả ({ideaData.ideas.length} ý tưởng):</span>
                    <span className="text-[11px] font-mono text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      {ideaData.model_used}
                    </span>
                  </div>

                  {ideaData.ideas.map((item) => (
                    <div 
                      key={item.id} 
                      className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-400 bg-white transition-all shadow-2xs group"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wide bg-indigo-50 px-2 py-0.5 rounded">
                          {item.angle}
                        </span>
                        <span className="text-[11px] text-slate-400 italic">Cảm xúc: {item.target_emotion}</span>
                      </div>
                      <h4 className="font-bold text-slate-900 text-xs mt-1">{item.headline}</h4>
                      <p className="text-xs text-slate-600 mt-1">{item.concept}</p>
                      
                      <button
                        onClick={() => {
                          setSelectedIdeaText(`${item.headline} - ${item.concept}`);
                          setActiveTab('draft');
                        }}
                        className="mt-2 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors"
                      >
                        <span>Dùng ý tưởng này để viết bài</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: DRAFT */}
          {activeTab === 'draft' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Ý tưởng hoặc góc nhìn đã chọn:</label>
                <textarea
                  value={selectedIdeaText}
                  onChange={(e) => setSelectedIdeaText(e.target.value)}
                  placeholder="Nhập hoặc chọn ý tưởng từ Tab 1 để AI viết thành bài hoàn chỉnh..."
                  className="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 h-20"
                />
              </div>

              <button
                onClick={handleGenerateDraft}
                disabled={loading}
                className="w-full py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-violet-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                <span>Sinh nội dung nháp (Title, Body, CTA)</span>
              </button>

              {draftData && (
                <div className="space-y-3 mt-4 p-4 rounded-xl border border-slate-200 bg-slate-50/50">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">Bản nháp AI đề xuất</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleCheckDraftCompliance}
                        disabled={isCheckingCompliance}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded transition-colors"
                        title="Quét tuân thủ chính sách quảng cáo và thương hiệu"
                      >
                        {isCheckingCompliance ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldAlert className="w-3 h-3" />}
                        <span>Quét Tuân thủ</span>
                      </button>
                      <button
                        onClick={() => copyToClipboard(`${draftData.title}\n\n${draftData.body}\n\n${draftData.cta}`)}
                        className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
                      >
                        {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copied ? 'Đã sao chép' : 'Sao chép'}</span>
                      </button>
                    </div>
                  </div>

                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Tiêu đề:</span>
                    <p className="text-xs font-bold text-slate-900 bg-white p-2.5 rounded border border-slate-200 mt-1">{draftData.title}</p>
                  </div>

                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Nội dung bài viết:</span>
                    <p className="text-xs text-slate-700 bg-white p-2.5 rounded border border-slate-200 mt-1 whitespace-pre-line leading-relaxed">{draftData.body}</p>
                  </div>

                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Lời kêu gọi (CTA):</span>
                    <p className="text-xs font-semibold text-indigo-700 bg-indigo-50/60 p-2 rounded border border-indigo-100 mt-1">{draftData.cta}</p>
                  </div>

                  {draftData.warnings?.length > 0 && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800 flex items-start gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                      <span>{draftData.warnings.join(', ')}</span>
                    </div>
                  )}

                  {complianceResult && (
                    <ComplianceAlertBadge
                      result={complianceResult}
                      onAutoFix={handleAutoFixViolation}
                    />
                  )}

                  {/* Action Buttons & Status */}
                  <div className="pt-2 space-y-2">
                    {createdContent?.status === 'IN_REVIEW' ? (
                      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          Đã gửi duyệt thành công! Trạng thái: <strong className="font-bold">IN_REVIEW</strong>
                        </span>
                        <span className="text-[11px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold">
                          Chờ Sếp duyệt
                        </span>
                      </div>
                    ) : createdContent?.status === 'AI_DRAFT' ? (
                      <div className="space-y-2">
                        <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800 flex items-center justify-between">
                          <span className="flex items-center gap-1.5 font-medium">
                            <Clock className="w-4 h-4 text-blue-600" />
                            Đã lưu thành bản nháp (AI_DRAFT).
                          </span>
                        </div>
                        <button
                          onClick={handleSubmitForReview}
                          disabled={isSubmittingReview || loading || (complianceResult !== null && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH')))}
                          className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all active:scale-95"
                          title={complianceResult && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH')) ? 'Khóa gửi duyệt do có vi phạm mức độ HIGH' : undefined}
                        >
                          {complianceResult && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH')) ? (
                            <>
                              <Lock className="w-4 h-4 text-red-500" />
                              <span className="text-slate-500">Khóa gửi duyệt (Có vi phạm HIGH)</span>
                            </>
                          ) : (
                            <>
                              {isSubmittingReview ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizontal className="w-4 h-4" />}
                              <span>Gửi Sếp phê duyệt ngay (Submit for Review)</span>
                            </>
                          )}
                        </button>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <button
                          onClick={handleSaveDraftToDB}
                          disabled={loading}
                          className="py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 border border-slate-200 transition-all active:scale-95"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Lưu nháp (AI_DRAFT)</span>
                        </button>
                        <button
                          onClick={handleSubmitForReview}
                          disabled={isSubmittingReview || loading || (complianceResult !== null && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH')))}
                          className="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all active:scale-95"
                          title={complianceResult && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH')) ? 'Khóa gửi duyệt do có vi phạm mức độ HIGH' : undefined}
                        >
                          {complianceResult && (!complianceResult.can_submit || complianceResult.violations.some(v => v.severity === 'HIGH')) ? (
                            <>
                              <Lock className="w-3.5 h-3.5 text-red-500" />
                              <span className="text-slate-500">Khóa gửi</span>
                            </>
                          ) : (
                            <>
                              {isSubmittingReview ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <SendHorizontal className="w-3.5 h-3.5" />}
                              <span>Gửi duyệt (Submit)</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: SUMMARY */}
          {activeTab === 'summary' && (
            <div className="space-y-4">
              <div className="bg-slate-100 border border-slate-200 rounded-lg p-3 text-xs text-slate-700">
                AI sẽ tổng hợp các dữ liệu thực tế (views, clicks, CTR, chi phí, ROI) để đưa ra nhận định khách quan và khuyến nghị tối ưu.
              </div>

              <button
                onClick={handleGenerateSummary}
                disabled={loading || !activeCampaign}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                <span>Phân tích hiệu quả chiến dịch này</span>
              </button>

              {summaryData && (
                <div className="space-y-3 mt-4">
                  <div className="p-3.5 bg-indigo-50/60 border border-indigo-100 rounded-lg">
                    <span className="text-[11px] font-bold text-indigo-700 uppercase">Tóm tắt đánh giá:</span>
                    <p className="text-xs text-slate-800 font-medium mt-1 leading-relaxed">{summaryData.executive_summary}</p>
                  </div>

                  <div className="p-3.5 bg-emerald-50/50 border border-emerald-100 rounded-lg">
                    <span className="text-[11px] font-bold text-emerald-700 uppercase">Điểm mạnh ghi nhận:</span>
                    <ul className="list-disc list-inside text-xs text-slate-700 mt-1 space-y-1">
                      {summaryData.strengths.map((s, idx) => <li key={idx}>{s}</li>)}
                    </ul>
                  </div>

                  <div className="p-3.5 bg-amber-50/50 border border-amber-100 rounded-lg">
                    <span className="text-[11px] font-bold text-amber-700 uppercase">Khuyến nghị tối ưu tiếp theo:</span>
                    <ul className="list-disc list-inside text-xs text-slate-700 mt-1 space-y-1">
                      {summaryData.recommendations.map((r, idx) => <li key={idx}>{r}</li>)}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
