import React from 'react';
import { 
  FileText, 
  Send, 
  CheckCircle2, 
  XCircle, 
  CalendarCheck, 
  TrendingUp, 
  Clock, 
  ShieldCheck, 
  Wand2, 
  Zap, 
  ArrowRight 
} from 'lucide-react';
import { MarketingContent } from '../../types';

interface ContentTabProps {
  draftContents: MarketingContent[];
  rejectedContents: MarketingContent[];
  inReviewContents: MarketingContent[];
  approvedContents: MarketingContent[];
  publishedContents: MarketingContent[];
  isApprover: boolean;
  submittingId: number | null;
  approvingId: number | null;
  getChannelBadge: (channelId: number) => React.ReactNode;
  handleAskAIToFixRejection: (item: MarketingContent) => void;
  handleSubmitContent: (id: number) => void;
  handleApproveContentItem: (id: number) => void;
  setRejectModalContent: (item: MarketingContent) => void;
  setScheduleModalContent: (item: MarketingContent) => void;
  onOpenCopilot: () => void;
  onOpenCalendar: () => void;
  onOpenDoctor: () => void;
}

export const ContentTab: React.FC<ContentTabProps> = ({
  draftContents,
  rejectedContents,
  inReviewContents,
  approvedContents,
  publishedContents,
  isApprover,
  submittingId,
  approvingId,
  getChannelBadge,
  handleAskAIToFixRejection,
  handleSubmitContent,
  handleApproveContentItem,
  setRejectModalContent,
  setScheduleModalContent,
  onOpenCopilot,
  onOpenCalendar,
  onOpenDoctor,
}) => {
  return (
    <div className="space-y-4">
      {/* Operational Guidance Card for Step 3: Sau đó làm gì? */}
      <div className="bg-gradient-to-r from-indigo-50 via-blue-50 to-emerald-50 p-4 rounded-xl border border-indigo-200/80 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs shadow-2xs">
        <div className="flex items-start sm:items-center gap-3">
          <span className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-sm shrink-0 mt-0.5 sm:mt-0">
            3
          </span>
          <div>
            <span className="font-bold text-slate-900">Chu trình Kiểm duyệt: "Duyệt bài xong thì sau đó làm gì?"</span>
            <p className="text-slate-600 text-[11px] mt-0.5 leading-relaxed">
              Khi Quản lý phê duyệt bài viết ở cột <strong>"Đã phê duyệt"</strong>, hệ thống tự động kích hoạt nút <strong className="text-indigo-700">"🚀 Xếp lịch phát sóng vào Giờ vàng"</strong>. Sau khi xếp lịch, bài viết tự động chuyển sang cột LIVE và được Bác sĩ AI giám sát dòng tiền.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onOpenCopilot}
            className="px-3.5 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold rounded-lg text-xs shadow-2xs transition-colors"
          >
            + Sáng tạo bài mới
          </button>
          <button
            onClick={onOpenCalendar}
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs shadow-xs transition-colors flex items-center gap-1"
          >
            <span>Xem Lịch Đa Kênh</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start">
        {/* Column 1: Bản nháp / AI Draft & Rejected */}
        <div className="bg-slate-50 rounded-xl border border-slate-200/80 p-3 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-blue-500" /> Bản nháp ({draftContents.length + rejectedContents.length})
            </span>
            <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">DRAFT</span>
          </div>

          {/* Rejected items waiting for marketer fix */}
          {rejectedContents.map((item) => (
            <div key={`rej-${item.id}`} className="bg-rose-50/70 rounded-lg p-3 border border-rose-200 shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                {getChannelBadge(item.channel_id)}
                <span className="text-[10px] font-bold text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded">Bị Sếp từ chối</span>
              </div>
              <h4 className="text-xs font-bold text-slate-800 line-clamp-1">{item.title}</h4>
              <div className="p-2 bg-white/80 rounded border border-rose-200 text-[10px] text-rose-800">
                <strong>Góp ý của Sếp:</strong> {item.warnings_json ? item.warnings_json : 'Cần chỉnh sửa lại CTA và phong cách bài viết.'}
              </div>
              <button
                onClick={() => handleAskAIToFixRejection(item)}
                className="w-full py-1 text-[11px] font-bold text-white bg-gradient-to-r from-rose-600 to-indigo-600 hover:from-rose-500 hover:to-indigo-500 rounded transition-all flex items-center justify-center gap-1"
              >
                <Wand2 className="w-3 h-3" /> Nhờ AI sửa bài theo góp ý Sếp
              </button>
            </div>
          ))}

          {/* Draft items */}
          {draftContents.map((item) => (
            <div key={item.id} className="bg-white rounded-lg p-3 border border-slate-200 shadow-xs space-y-2 hover:border-indigo-300 transition-colors">
              <div className="flex items-center justify-between">
                {getChannelBadge(item.channel_id)}
                <span className="text-[10px] font-semibold text-slate-400">#{item.id}</span>
              </div>
              <h4 className="text-xs font-bold text-slate-800 line-clamp-1">{item.title}</h4>
              <p className="text-[11px] text-slate-500 line-clamp-2">{item.body}</p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[10px] text-slate-400">{item.body.split(/\s+/).length} từ</span>
                <button
                  onClick={() => handleSubmitContent(item.id)}
                  disabled={submittingId === item.id}
                  className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded transition-colors flex items-center gap-1"
                >
                  <Send className="w-3 h-3" />
                  <span>{submittingId === item.id ? 'Đang gửi...' : 'Gửi Sếp duyệt'}</span>
                </button>
              </div>
            </div>
          ))}

          {draftContents.length === 0 && rejectedContents.length === 0 && (
            <div className="p-6 text-center text-[11px] text-slate-500 bg-white rounded-lg border border-dashed border-slate-200">
              Chưa có bản nháp nào. Bấm nút phía trên để AI gợi ý nội dung.
            </div>
          )}
        </div>

        {/* Column 2: Chờ Sếp duyệt (IN_REVIEW) */}
        <div className="bg-amber-50/60 rounded-xl border border-amber-200/80 p-3 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-amber-200">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-600" /> Chờ Sếp duyệt ({inReviewContents.length})
            </span>
            <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">HITL GATE</span>
          </div>

          {inReviewContents.length === 0 ? (
            <div className="p-6 text-center text-[11px] text-slate-500 bg-white/80 rounded-lg border border-dashed border-amber-200">
              Không có nội dung nào chờ phê duyệt.
            </div>
          ) : (
            inReviewContents.map((item) => (
              <div key={item.id} className="bg-white rounded-lg p-3 border border-amber-200 shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  {getChannelBadge(item.channel_id)}
                  <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">Chờ duyệt</span>
                </div>
                <h4 className="text-xs font-bold text-slate-800 line-clamp-1">{item.title}</h4>
                <p className="text-[11px] text-slate-500 line-clamp-2">{item.body}</p>
                
                <div className="pt-2 border-t border-slate-100">
                  {isApprover ? (
                    <div className="grid grid-cols-2 gap-1.5">
                      <button
                        onClick={() => handleApproveContentItem(item.id)}
                        disabled={approvingId === item.id}
                        className="text-center text-[11px] font-bold text-white bg-emerald-600 hover:bg-emerald-700 py-1.5 rounded transition-all flex items-center justify-center gap-1 shadow-xs"
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        <span>{approvingId === item.id ? 'Đang duyệt...' : 'Phê duyệt'}</span>
                      </button>
                      <button
                        onClick={() => setRejectModalContent(item)}
                        className="text-center text-[11px] font-bold text-rose-600 bg-rose-50 hover:bg-rose-100 py-1.5 rounded transition-all flex items-center justify-center gap-1 border border-rose-200"
                      >
                        <XCircle className="w-3 h-3" />
                        <span>Từ chối</span>
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 text-[10px] text-slate-400">
                      <Clock className="w-3 h-3 text-amber-500" />
                      <span>Đang đợi tài khoản Quản lý thẩm định</span>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Column 3: Đã phê duyệt (APPROVED) */}
        <div className="bg-emerald-50/60 rounded-xl border border-emerald-200/80 p-3 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-emerald-200">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Đã phê duyệt ({approvedContents.length})
            </span>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">READY</span>
          </div>

          {approvedContents.length === 0 ? (
            <div className="p-6 text-center text-[11px] text-slate-500 bg-white/80 rounded-lg border border-dashed border-emerald-200">
              Chưa có bài viết nào được cấp phép xuất bản.
            </div>
          ) : (
            approvedContents.map((item) => (
              <div key={item.id} className="bg-white rounded-lg p-3 border border-emerald-200 shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  {getChannelBadge(item.channel_id)}
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">Hợp lệ</span>
                </div>
                <h4 className="text-xs font-bold text-slate-800 line-clamp-1">{item.title}</h4>
                <p className="text-[11px] text-slate-500 line-clamp-2">{item.body}</p>
                <div className="pt-2 border-t border-slate-100">
                  <button
                    onClick={() => setScheduleModalContent(item)}
                    className="w-full text-center text-[11px] font-bold text-white bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 py-2 rounded-lg transition-all flex items-center justify-center gap-1.5 shadow-xs active:scale-95"
                  >
                    <CalendarCheck className="w-3.5 h-3.5 text-white" />
                    <span>🚀 Xếp lịch phát sóng vào Giờ vàng</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Column 4: Đã xuất bản / Đang chạy (PUBLISHED) */}
        <div className="bg-indigo-50/60 rounded-xl border border-indigo-200/80 p-3 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-indigo-200">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-800 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-indigo-600" /> Đã xuất bản ({publishedContents.length})
            </span>
            <span className="text-[10px] font-bold bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded">LIVE</span>
          </div>

          {publishedContents.length === 0 ? (
            <div className="p-6 text-center text-[11px] text-slate-500 bg-white/80 rounded-lg border border-dashed border-indigo-200">
              Chưa có bài viết nào được phát tán tới kênh.
            </div>
          ) : (
            publishedContents.map((item) => (
              <div key={item.id} className="bg-white rounded-lg p-3 border border-indigo-200 shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  {getChannelBadge(item.channel_id)}
                  <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">Đang chạy</span>
                </div>
                <h4 className="text-xs font-bold text-slate-800 line-clamp-1">{item.title}</h4>
                <p className="text-[11px] text-slate-500 line-clamp-2">{item.body}</p>
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                  <span className="text-slate-500">CTA: <strong>{item.cta || 'Đăng ký'}</strong></span>
                  <button
                    onClick={onOpenDoctor}
                    className="text-[10px] font-bold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded transition-colors flex items-center gap-1 border border-indigo-200"
                  >
                    <Zap className="w-3 h-3 text-indigo-600" />
                    <span>⚡ Theo dõi & Tối ưu AI</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
