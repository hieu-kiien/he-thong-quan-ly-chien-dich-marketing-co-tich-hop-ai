import React, { useState } from 'react';
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
  BookmarkPlus
} from 'lucide-react';
import { Campaign, AIIdeaResponse, AIDraftResponse, MarketingContent } from '../types';
import { aiApi, contentApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';

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
  const [customTopic, setCustomTopic] = useState<string>('Khóa học Lập trình AI Ứng Dụng Thực Chiến');
  const [customProduct, setCustomProduct] = useState<string>('Khóa học Lập trình GenAI Masterclass');
  const [customUsp, setCustomUsp] = useState<string>('Cầm tay chỉ việc 1-1, học xong làm được dự án thực tế ngay');
  const [tone, setTone] = useState<string>('trẻ trung, năng động');
  const [channelCode, setChannelCode] = useState<string>('facebook');
  const [promptVersion, setPromptVersion] = useState<string>('v3');

  // AI Output States
  const [activeTab, setActiveTab] = useState<'ideas' | 'draft'>('ideas');
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [selectedIdeaText, setSelectedIdeaText] = useState<string>('');
  const [ideaData, setIdeaData] = useState<AIIdeaResponse | null>(null);
  const [draftData, setDraftData] = useState<AIDraftResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submittedSuccess, setSubmittedSuccess] = useState<boolean>(false);

  // Quick Preset Samples
  const presets = [
    {
      label: '🚀 Khóa học AI',
      topic: 'Chiến dịch Tuyển sinh Khóa học Lập trình AI',
      product: 'Khóa học GenAI & LLM Thực Chiến',
      usp: 'Cầm tay chỉ việc 1-1, cấp chứng chỉ hoàn thành, cam kết chất lượng đầu ra'
    },
    {
      label: '💼 Mini CRM',
      topic: 'Chiến dịch Ra mắt Bản thử nghiệm Mini CRM',
      product: 'Phần mềm Quản lý Khách hàng Mini CRM',
      usp: 'Giao diện kéo thả trực quan, tự động hóa gửi email và chăm sóc khách hàng 24/7'
    },
    {
      label: '🥤 Trà sữa Gen Z',
      topic: 'Khai trương Chi nhánh Trà Sữa Mới',
      product: 'Trà Sữa Oolong Kem Phô Mai Nướng',
      usp: 'Mua 1 tặng 1 trong tuần lễ khai trương, không gian check-in sống ảo cực chất'
    }
  ];

  const applyPreset = (p: typeof presets[0]) => {
    setMode('custom');
    setCustomTopic(p.topic);
    setCustomProduct(p.product);
    setCustomUsp(p.usp);
    toast.info(`Đã áp dụng mẫu: ${p.label}`);
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
        tone: tone
      } : undefined;

      const res = await aiApi.generateIdeas(cid, channelCode, promptVersion, customData);
      setIdeaData(res);
      setActiveTab('ideas');
      toast.success(`Đã sinh thành công ${res.ideas.length} góc ý tưởng tiếp thị từ OpenRouter!`);
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

      const ideaToUse = ideaOverride || selectedIdeaText || (ideaData?.ideas[0]?.headline ? `${ideaData.ideas[0].headline} - ${ideaData.ideas[0].concept}` : 'Giải pháp đột phá nâng cao năng suất cùng AI');

      const res = await aiApi.generateDraft(cid, ideaToUse, channelCode, promptVersion, customData);
      setDraftData(res);
      setActiveTab('draft');
      toast.success('Bản nháp bài viết đã được AI khởi tạo thành công!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gọi AI sinh bản nháp');
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

  const handleSubmitForReview = async () => {
    if (!draftData) return;
    setIsSubmitting(true);
    try {
      // Tìm campaign_id và channel_id hợp lệ
      let targetCampaignId = selectedCampaign?.id || campaigns[0]?.id;
      if (!targetCampaignId && campaigns.length > 0) {
        targetCampaignId = campaigns[0].id;
      }

      if (!targetCampaignId) {
        toast.warning('Vui lòng tạo ít nhất một chiến dịch trong hệ thống để lưu bài viết gửi Sếp duyệt');
        setIsSubmitting(false);
        return;
      }

      // 1. Tạo MarketingContent ở trạng thái DRAFT
      const newContent = await contentApi.create({
        campaign_id: targetCampaignId,
        channel_id: 1, // Kênh mặc định
        title: draftData.title,
        body: draftData.body,
        cta: draftData.cta,
        status: 'AI_DRAFT'
      });

      // 2. Gửi duyệt chuyển sang IN_REVIEW
      await contentApi.submitForReview(newContent.id);
      setSubmittedSuccess(true);
      toast.success('Đã gửi bài viết vào Hàng đợi duyệt (IN_REVIEW) thành công!');
      if (onContentCreated) onContentCreated();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gửi duyệt bài');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 rounded-2xl p-6 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-indigo-500/30 text-indigo-200 border border-indigo-400/30 text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400 fill-amber-400" /> OpenRouter Model Nex-N2.5 Mini (100% Free)
            </span>
            <span className="text-xs text-indigo-300">● Sẵn sàng phục vụ</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black tracking-tight">Xưởng Trợ Lý Sáng Tạo Nội Dung (AI Content Studio)</h1>
          <p className="text-xs sm:text-sm text-indigo-200 mt-1 max-w-2xl">
            Tự động sinh 5 góc ý tưởng tiếp thị độc đáo và viết trọn bài đăng đa kênh (Facebook, TikTok, Email, SEO) chỉ trong 2 giây.
          </p>
        </div>

        {/* Quick presets */}
        <div className="flex flex-wrap items-center gap-2 bg-indigo-950/50 p-2 rounded-xl border border-indigo-500/20">
          <span className="text-xs text-indigo-300 font-medium px-1">Mẫu gợi ý:</span>
          {presets.map((p, idx) => (
            <button
              key={idx}
              onClick={() => applyPreset(p)}
              className="text-xs bg-indigo-800/60 hover:bg-indigo-700 text-white px-2.5 py-1 rounded-lg transition-colors font-semibold"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Creator Studio Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span>1. Thiết Lập Đầu Vào Sáng Tạo</span>
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
                Gắn với Chiến dịch ({campaigns.length})
              </button>
              <button
                onClick={() => setMode('custom')}
                className={`flex-1 py-1.5 rounded-lg transition-all ${
                  mode === 'custom'
                    ? 'bg-white text-indigo-700 shadow-xs font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Tự do sáng tạo (Tùy chỉnh)
              </button>
            </div>

            {/* Campaign Selector if mode is campaign */}
            {mode === 'campaign' ? (
              <div className="space-y-1.5">
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
                    Chưa có chiến dịch nào trong CSDL. Bạn có thể chuyển sang tab <strong>Tự do sáng tạo</strong> để thử nghiệm ngay!
                  </div>
                )}
                {selectedCampaign && (
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-[11px] text-slate-600 space-y-1">
                    <div><strong>Mục tiêu:</strong> {selectedCampaign.objective}</div>
                    <div><strong>Đối tượng:</strong> {selectedCampaign.audience}</div>
                  </div>
                )}
              </div>
            ) : (
              /* Custom Input Fields */
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Chủ đề hoặc Tên chiến dịch:</label>
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

            {/* Target Channel & Tone Controls */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Kênh tiếp thị:</label>
                <select
                  value={channelCode}
                  onChange={(e) => setChannelCode(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 font-semibold"
                >
                  <option value="facebook">Facebook Ads / Post</option>
                  <option value="email">Email Newsletter</option>
                  <option value="blog">Blog SEO / Website</option>
                  <option value="google_ads">Google Search Ads</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Giọng văn (Tone):</label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 font-semibold"
                >
                  <option value="trẻ trung, năng động">Trẻ trung & Trendy</option>
                  <option value="chuyên nghiệp, trang trọng">Chuyên gia & Uy tín</option>
                  <option value="hào hứng, thôi thúc">Thôi thúc hành động</option>
                  <option value="đồng cảm, sâu lắng">Đồng cảm & Câu chuyện</option>
                </select>
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
                <span>Khởi tạo 5 Góc Ý Tưởng Tiếp Thị</span>
              </button>

              <button
                onClick={() => handleGenerateDraft()}
                disabled={loading}
                className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-60 rounded-xl text-xs font-bold flex items-center justify-center gap-2 border border-slate-200 transition-all cursor-pointer"
              >
                <FileText className="w-4 h-4 text-indigo-600" />
                <span>Viết Ngay Bản Nháp Hoàn Chỉnh</span>
              </button>
            </div>
          </div>

          {/* Quick Explainer: Hệ thống này giúp gì? */}
          <div className="bg-indigo-50/60 border border-indigo-100 rounded-2xl p-4 text-xs text-slate-600 space-y-2">
            <h3 className="font-bold text-indigo-900 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-indigo-600" />
              <span>Giá trị AI mang lại cho bạn:</span>
            </h3>
            <ul className="space-y-1.5 pl-4 list-disc text-slate-700">
              <li><strong>Giải quyết bí ý tưởng:</strong> Tự động đề xuất 5 hướng tiếp cận tâm lý khách hàng khác nhau.</li>
              <li><strong>Viết bài chuẩn kênh:</strong> Tạo tiêu đề bắt mắt, thân bài súc tích kèm CTA và hashtag.</li>
              <li><strong>Phát hiện rủi ro:</strong> Cảnh báo từ ngữ vi phạm chính sách quảng cáo của Facebook & Google.</li>
            </ul>
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
                  <p className="text-xs font-bold text-slate-700">Mô hình OpenRouter đang suy nghĩ và tính toán 5 góc ý tưởng tiếp thị...</p>
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
                    Chọn chiến dịch hoặc nhập chủ đề ở cột bên trái và bấm nút <strong>"Khởi tạo 5 Góc Ý Tưởng Tiếp Thị"</strong> để trải nghiệm sức mạnh của AI.
                  </p>
                </div>
              )}

              {ideaData?.warnings && ideaData.warnings.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-amber-800">
                    <AlertCircle className="w-4 h-4 text-amber-600" /> Cảnh báo rủi ro tiếp thị từ AI:
                  </div>
                  <ul className="list-disc pl-5 space-y-0.5 text-[11px]">
                    {ideaData.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: DRAFT DISPLAY */}
          {activeTab === 'draft' && (
            <div className="space-y-4">
              {loading && !draftData ? (
                <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center space-y-3">
                  <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
                  <p className="text-xs font-bold text-slate-700">AI đang viết tiêu đề, phân đoạn nội dung và lời kêu gọi CTA...</p>
                </div>
              ) : draftData ? (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
                  {/* Top Bar of Draft */}
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200">
                        Bản Nháp AI Hoàn Chỉnh
                      </span>
                      <span className="text-xs text-slate-400">Kênh: {channelCode.toUpperCase()}</span>
                    </div>

                    <button
                      onClick={() => copyToClipboard(`${draftData.title}\n\n${draftData.body}\n\n${draftData.cta}`)}
                      className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Đã sao chép' : 'Sao chép bài'}</span>
                    </button>
                  </div>

                  {/* Title Area */}
                  <div>
                    <label className="text-[11px] font-bold text-slate-400 uppercase block mb-1">Tiêu đề bài viết:</label>
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl font-bold text-sm text-slate-900">
                      {draftData.title}
                    </div>
                  </div>

                  {/* Body Area */}
                  <div>
                    <label className="text-[11px] font-bold text-slate-400 uppercase block mb-1">Nội dung tiếp thị chi tiết:</label>
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 whitespace-pre-line leading-relaxed">
                      {draftData.body}
                    </div>
                  </div>

                  {/* CTA Area */}
                  <div>
                    <label className="text-[11px] font-bold text-slate-400 uppercase block mb-1">Lời kêu gọi hành động (Call To Action):</label>
                    <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl font-bold text-xs text-indigo-800">
                      {draftData.cta}
                    </div>
                  </div>

                  {/* Action Bar: Submit for Review */}
                  <div className="pt-2 border-t border-slate-100">
                    {submittedSuccess ? (
                      <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                          Đã gửi bài viết vào Hàng đợi duyệt thành công! Trạng thái: IN_REVIEW
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
                          Bản nháp đã sẵn sàng. Bạn có thể gửi bài này để <strong>Quản lý (Manager)</strong> phê duyệt.
                        </p>

                        <button
                          onClick={handleSubmitForReview}
                          disabled={isSubmitting}
                          className="w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20 transition-all cursor-pointer active:scale-98"
                        >
                          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizontal className="w-4 h-4" />}
                          <span>Gửi Sếp Phê Duyệt Ngay (Submit)</span>
                        </button>
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
  );
};
