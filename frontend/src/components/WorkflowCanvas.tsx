import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Sparkles, 
  ShieldCheck, 
  Send, 
  BarChart3, 
  ArrowRight, 
  CheckCircle2, 
  Clock, 
  XCircle,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  Maximize2
} from 'lucide-react';
import { Campaign, MarketingContent, KPISummary } from '../types';
import { campaignApi, contentApi, getApiErrorMessage } from '../services/api';
import { useToast } from './Toast';

interface WorkflowCanvasProps {
  campaign: Campaign | null;
  contents: MarketingContent[];
  onOpenAI: (campaign: Campaign) => void;
  onApproveContent?: (id: number) => void;
  onSubmitForReview?: (id: number) => void;
  userRole?: string;
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  campaign,
  contents,
  onOpenAI,
  onApproveContent,
  onSubmitForReview,
  userRole
}) => {
  const toast = useToast();
  const [activeNode, setActiveNode] = useState<string>('ai_gen');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const [campaignKpi, setCampaignKpi] = useState<KPISummary | null>(null);

  useEffect(() => {
    if (campaign?.id) {
      campaignApi.getKpi(campaign.id)
        .then(res => setCampaignKpi(res))
        .catch(() => setCampaignKpi(null));
    }
  }, [campaign?.id]);

  const handleSubmitForReview = async (id: number) => {
    try {
      setSubmittingId(id);
      await contentApi.submitForReview(id);
      toast.success('Đã gửi bài viết vào Hàng đợi phê duyệt (IN_REVIEW)!');
      if (onSubmitForReview) {
        onSubmitForReview(id);
      }
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gửi duyệt nội dung');
    } finally {
      setSubmittingId(null);
    }
  };

  if (!campaign) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center text-slate-500">
        <p>Vui lòng chọn một chiến dịch để xem sơ đồ luồng (Workflow Canvas).</p>
      </div>
    );
  }

  const latestContent = contents.find(c => c.campaign_id === campaign.id);

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 shadow-xl overflow-hidden flex flex-col h-[650px] relative">
      {/* Canvas Controls Topbar */}
      <div className="bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-5 py-3 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span>
          <span className="text-white text-xs font-bold uppercase tracking-wider">Workflow Canvas</span>
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
        <div className="flex items-center gap-8 relative max-w-5xl">

          {/* Node 1: Trigger / Brief */}
          <div 
            onClick={() => setActiveNode('trigger')}
            className={`w-64 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg ${
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
            <div className="mt-3 pt-2 border-t border-slate-700/60 flex items-center justify-between text-[10px] text-slate-400">
              <span>Đối tượng: {campaign.audience}</span>
            </div>
          </div>

          {/* Animated Connecting Arrow */}
          <div className="flex items-center text-indigo-400 animate-pulse">
            <ArrowRight className="w-6 h-6" />
          </div>

          {/* Node 2: AI Content Generator */}
          <div 
            onClick={() => setActiveNode('ai_gen')}
            className={`w-64 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg relative ${
              activeNode === 'ai_gen' ? 'border-violet-500 ring-2 ring-violet-500/30' : 'border-slate-700 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase text-violet-400 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-violet-400" /> 2. AI Content Engine
              </span>
              <span className="text-[10px] bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded font-bold">V3 PROMPT</span>
            </div>
            <h4 className="text-white text-xs font-bold">Sinh ý tưởng & Bản nháp</h4>
            <p className="text-[11px] text-slate-400 mt-1">OpenCode Muse Spark 1.3 (+ Smart Fallback Guardrail)</p>
            
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOpenAI(campaign);
              }}
              className="mt-3 w-full py-1.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md shadow-violet-600/30 transition-all"
            >
              <Sparkles className="w-3 h-3" /> Gọi AI sinh nội dung
            </button>
          </div>

          {/* Animated Connecting Arrow */}
          <div className="flex items-center text-violet-400 animate-pulse">
            <ArrowRight className="w-6 h-6" />
          </div>

          {/* Node 3: Manager Approval Gate (Human-in-the-loop) */}
          <div 
            onClick={() => setActiveNode('approval')}
            className={`w-64 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg relative ${
              activeNode === 'approval' ? 'border-amber-500 ring-2 ring-amber-500/30' : 'border-slate-700 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase text-amber-400 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-amber-400" /> 3. Chốt chặn duyệt (Gate)
              </span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                latestContent?.status === 'APPROVED' 
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : latestContent?.status === 'AI_DRAFT'
                  ? 'bg-blue-500/20 text-blue-400'
                  : latestContent?.status === 'REJECTED'
                  ? 'bg-rose-500/20 text-rose-400'
                  : 'bg-amber-500/20 text-amber-400'
              }`}>
                {latestContent?.status || 'CHƯA CÓ'}
              </span>
            </div>
            <h4 className="text-white text-xs font-bold">Human-in-the-loop</h4>
            <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">
              {latestContent ? latestContent.title : 'Chưa có bài viết'}
            </p>

            {/* Action 1: Marketer submits AI_DRAFT for manager review */}
            {latestContent?.status === 'AI_DRAFT' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleSubmitForReview(latestContent.id);
                }}
                disabled={submittingId === latestContent.id}
                className="mt-3 w-full py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:bg-slate-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md shadow-blue-600/30 transition-all active:scale-95"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{submittingId === latestContent.id ? 'Đang gửi...' : 'Gửi Sếp phê duyệt (Submit)'}</span>
              </button>
            )}

            {/* Action 2: Manager approves IN_REVIEW content */}
            {latestContent?.status === 'IN_REVIEW' && userRole === 'MANAGER' && onApproveContent && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onApproveContent(latestContent.id);
                }}
                className="mt-3 w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/30 transition-all active:scale-95"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Sếp phê duyệt ngay
              </button>
            )}
          </div>

          {/* Animated Connecting Arrow */}
          <div className="flex items-center text-emerald-400 animate-pulse">
            <ArrowRight className="w-6 h-6" />
          </div>

          {/* Node 4: Dispatch & Analytics */}
          <div 
            onClick={() => setActiveNode('dispatch')}
            className={`w-64 bg-slate-800/90 backdrop-blur-md rounded-xl p-4 border transition-all cursor-pointer shadow-lg ${
              activeNode === 'dispatch' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-slate-700 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase text-blue-400 flex items-center gap-1">
                <BarChart3 className="w-3 h-3 text-blue-400" /> 4. Đo lường KPI
              </span>
              <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded font-bold">LIVE</span>
            </div>
            <h4 className="text-white text-xs font-bold">Facebook & Email Ads</h4>
            <div className="mt-2 space-y-1 text-[11px] text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-400">Views:</span>
                <span className="font-bold">
                  {campaignKpi ? campaignKpi.total_views.toLocaleString('vi-VN') : '15,700'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Clicks:</span>
                <span className="font-bold text-emerald-400">
                  {campaignKpi ? `${campaignKpi.total_clicks.toLocaleString('vi-VN')} (CTR ${campaignKpi.ctr_percent}%)` : '1,260 (CTR 8.0%)'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">ROI ước tính:</span>
                <span className="font-bold text-indigo-400">
                  {campaignKpi ? `+${campaignKpi.roi_percent}%` : '+410%'}
                </span>
              </div>
            </div>
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
          Model: OpenCode Muse Spark 1.3 • Guardrails Active
        </div>
      </div>
    </div>
  );
};
