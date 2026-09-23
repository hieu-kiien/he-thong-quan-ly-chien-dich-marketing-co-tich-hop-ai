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
  Clock
} from 'lucide-react';
import { Campaign, AIIdeaResponse, AIDraftResponse, AISummaryResponse, MarketingContent } from '../types';
import { aiApi, contentApi, getApiErrorMessage } from '../services/api';
import { useToast } from './Toast';

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
  const [activeTab, setActiveTab] = useState<'idea' | 'draft' | 'summary'>('idea');
  const [promptVersion, setPromptVersion] = useState<string>('v3');
  const [channelCode, setChannelCode] = useState<string>('facebook');
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [createdContent, setCreatedContent] = useState<MarketingContent | null>(null);
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);

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
        channel_id: channelCode === 'email' ? 2 : 1,
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

  const handleSubmitForReview = async () => {
    if (!draftData) return;
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
              <option value="email">Email Newsletter</option>
            </select>
          </div>
        </div>

        {/* Tabs Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600 px-5">
          <button
            onClick={() => setActiveTab('idea')}
            className={`py-3 px-4 border-b-2 flex items-center gap-1.5 transition-all ${
              activeTab === 'idea' 
                ? 'border-indigo-600 text-indigo-600 bg-white' 
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <Lightbulb className="w-3.5 h-3.5" />
            <span>1. Sinh ý tưởng (IDEA)</span>
          </button>
          <button
            onClick={() => setActiveTab('draft')}
            className={`py-3 px-4 border-b-2 flex items-center gap-1.5 transition-all ${
              activeTab === 'draft' 
                ? 'border-indigo-600 text-indigo-600 bg-white' 
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>2. Viết bản nháp (DRAFT)</span>
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`py-3 px-4 border-b-2 flex items-center gap-1.5 transition-all ${
              activeTab === 'summary' 
                ? 'border-indigo-600 text-indigo-600 bg-white' 
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>3. Tóm tắt KPI (SUMMARY)</span>
          </button>
        </div>

        {/* Drawer Body Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          
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
                    <button
                      onClick={() => copyToClipboard(`${draftData.title}\n\n${draftData.body}\n\n${draftData.cta}`)}
                      className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      <span>{copied ? 'Đã sao chép' : 'Sao chép'}</span>
                    </button>
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
                          disabled={isSubmittingReview || loading}
                          className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all active:scale-95"
                        >
                          {isSubmittingReview ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizontal className="w-4 h-4" />}
                          <span>Gửi Sếp phê duyệt ngay (Submit for Review)</span>
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
                          disabled={isSubmittingReview || loading}
                          className="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all active:scale-95"
                        >
                          {isSubmittingReview ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizontal className="w-3.5 h-3.5" />}
                          <span>Gửi duyệt (Submit)</span>
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
