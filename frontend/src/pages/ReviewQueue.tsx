import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  Check, 
  ShieldCheck, 
  Send,
  Sparkles,
  FileText,
  Loader2,
  History,
  Info
} from 'lucide-react';
import { MarketingContent } from '../types';
import { contentApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { ReviewQueueSkeleton } from '../components/Skeleton';

interface ReviewQueueProps {
  userRole?: string;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({ userRole }) => {
  const toast = useToast();
  const [contents, setContents] = useState<MarketingContent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'drafts' | 'history'>('pending');
  const [rejectId, setRejectId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [submittingId, setSubmittingId] = useState<number | null>(null);

  useEffect(() => {
    loadContents();
  }, []);

  const loadContents = async () => {
    try {
      setLoading(true);
      const data = await contentApi.getAll();
      setContents(data);
    } catch (e) {
      console.error(e);
      toast.error(getApiErrorMessage(e), 'Lỗi khi tải danh sách nội dung');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await contentApi.approve(id);
      toast.success('Đã phê duyệt bài viết thành công (APPROVED)!');
      loadContents();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi duyệt bài');
    }
  };

  const handleReject = async (id: number) => {
    if (rejectReason.trim().length < 3) {
      toast.warning('Lý do từ chối phải có ít nhất 3 ký tự');
      return;
    }
    try {
      await contentApi.reject(id, rejectReason.trim());
      setRejectId(null);
      setRejectReason('');
      toast.success('Đã gửi phản hồi từ chối bài viết (REJECTED)');
      loadContents();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi từ chối bài');
    }
  };

  const handleSubmitDraft = async (id: number) => {
    try {
      setSubmittingId(id);
      await contentApi.submitForReview(id);
      toast.success('Đã chuyển bài viết sang Hàng đợi phê duyệt (IN_REVIEW)!');
      loadContents();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi gửi duyệt bản nháp');
    } finally {
      setSubmittingId(null);
    }
  };

  const pendingList = contents.filter(c => c.status === 'IN_REVIEW');
  const draftList = contents.filter(c => c.status === 'AI_DRAFT' || c.status === 'DRAFT');
  const historyList = contents.filter(c => c.status === 'APPROVED' || c.status === 'REJECTED');

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black text-slate-900 tracking-tight">Hàng đợi Phê duyệt Nội dung</h2>
            <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full border border-emerald-300">
              Quy trình Kiểm duyệt con người (Human-in-the-loop)
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Nội dung do AI hoặc nhân viên soạn thảo bắt buộc phải được Quản lý (Manager) kiểm duyệt trước khi xuất bản hoặc lập lịch.
          </p>
        </div>

        {userRole !== 'MANAGER' && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2 rounded-lg flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Bạn đang xem dưới vai trò <strong>Marketer</strong>. Chuyển sang <strong>Manager</strong> ở thanh trên để bấm duyệt.</span>
          </div>
        )}
      </div>

      {/* Filter Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('pending')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            activeTab === 'pending'
              ? 'bg-amber-500 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Chờ phê duyệt</span>
          <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${
            activeTab === 'pending' ? 'bg-amber-600 text-white' : 'bg-slate-200 text-slate-700'
          }`}>
            {pendingList.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('drafts')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            activeTab === 'drafts'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Bản nháp chờ gửi duyệt</span>
          <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${
            activeTab === 'drafts' ? 'bg-blue-700 text-white' : 'bg-slate-200 text-slate-700'
          }`}>
            {draftList.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            activeTab === 'history'
              ? 'bg-slate-800 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Lịch sử duyệt bài</span>
          <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${
            activeTab === 'history' ? 'bg-slate-700 text-white' : 'bg-slate-200 text-slate-700'
          }`}>
            {historyList.length}
          </span>
        </button>
      </div>

      {/* Main Content Areas */}
      {loading ? (
        <ReviewQueueSkeleton count={3} />
      ) : (
        <>
          {/* TAB 1: PENDING (IN_REVIEW) */}
          {activeTab === 'pending' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-500" />
                  <span>Bài viết đang chờ duyệt ({pendingList.length})</span>
                </h3>
              </div>

              {pendingList.length === 0 ? (
                <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center text-slate-400 text-xs space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <p className="font-semibold text-slate-600">Tuyệt vời! Không còn bài viết nào đang chờ duyệt.</p>
                  <p>Mọi nội dung gửi lên đã được xử lý xong.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {pendingList.map((item) => (
                    <div key={item.id} className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-indigo-300 transition-all">
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] bg-amber-50 text-amber-700 font-bold px-2 py-0.5 rounded border border-amber-200">
                              CHỜ DUYỆT (IN_REVIEW)
                            </span>
                            <span className="text-xs text-slate-400 font-medium">Kênh: {item.channel?.name || 'Mạng xã hội'}</span>
                          </div>
                          <h4 className="text-base font-bold text-slate-900 mt-1">{item.title}</h4>
                          <p className="text-xs text-slate-700 whitespace-pre-line bg-slate-50 p-3 rounded-lg border border-slate-100 mt-2 leading-relaxed">
                            {item.body}
                          </p>
                          {item.cta && (
                            <div className="mt-2 text-xs">
                              <span className="text-slate-400 font-semibold">Lời kêu gọi (CTA): </span>
                              <span className="font-bold text-indigo-600">{item.cta}</span>
                            </div>
                          )}
                        </div>

                        {/* Actions for Manager */}
                        <div className="flex flex-col gap-2 shrink-0">
                          <button
                            onClick={() => handleApprove(item.id)}
                            disabled={userRole !== 'MANAGER'}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all active:scale-95"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Phê duyệt (Approve)</span>
                          </button>
                          <button
                            onClick={() => setRejectId(item.id)}
                            disabled={userRole !== 'MANAGER'}
                            className="px-4 py-2 bg-rose-50 hover:bg-rose-100 disabled:bg-slate-100 text-rose-700 rounded-lg text-xs font-bold flex items-center gap-1.5 border border-rose-200 transition-all active:scale-95"
                          >
                            <XCircle className="w-4 h-4" />
                            <span>Từ chối (Reject)</span>
                          </button>
                        </div>
                      </div>

                      {/* Reject Input Box */}
                      {rejectId === item.id && (
                        <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
                          <label className="block text-xs font-semibold text-rose-700">Nhập lý do từ chối yêu cầu chỉnh sửa:</label>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={rejectReason}
                              onChange={(e) => setRejectReason(e.target.value)}
                              placeholder="Ví dụ: Cần điều chỉnh lại giọng văn trang trọng hơn..."
                              className="flex-1 text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-rose-500"
                            />
                            <button
                              onClick={() => handleReject(item.id)}
                              className="px-3 py-2 bg-rose-600 text-white text-xs font-bold rounded-lg"
                            >
                              Gửi từ chối
                            </button>
                            <button
                              onClick={() => setRejectId(null)}
                              className="px-3 py-2 bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                            >
                              Hủy
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: DRAFTS (AI_DRAFT / DRAFT) */}
          {activeTab === 'drafts' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-600" />
                    <span>Bản nháp chờ gửi duyệt ({draftList.length})</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Các bài viết do AI Copilot hoặc Marketer soạn thảo, cần được gửi vào hàng đợi phê duyệt để Quản lý kiểm duyệt.
                  </p>
                </div>
              </div>

              {draftList.length === 0 ? (
                <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center text-slate-400 text-xs space-y-2">
                  <Sparkles className="w-8 h-8 text-indigo-400 mx-auto animate-pulse" />
                  <p className="font-semibold text-slate-600">Hiện không có bản nháp nào đang chờ gửi.</p>
                  <p>Mở AI Copilot Studio để sinh thêm ý tưởng và bản nháp chiến dịch mới.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {draftList.map((item) => (
                    <div key={item.id} className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-blue-300 transition-all">
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] bg-blue-50 text-blue-700 font-bold px-2 py-0.5 rounded border border-blue-200">
                              BẢN NHÁP ({item.status})
                            </span>
                            <span className="text-xs text-slate-400 font-medium">Kênh: {item.channel?.name || 'Mạng xã hội'}</span>
                          </div>
                          <h4 className="text-base font-bold text-slate-900 mt-1">{item.title}</h4>
                          <p className="text-xs text-slate-700 whitespace-pre-line bg-slate-50 p-3 rounded-lg border border-slate-100 mt-2 leading-relaxed">
                            {item.body}
                          </p>
                          {item.cta && (
                            <div className="mt-2 text-xs">
                              <span className="text-slate-400 font-semibold">Lời kêu gọi (CTA): </span>
                              <span className="font-bold text-indigo-600">{item.cta}</span>
                            </div>
                          )}
                        </div>

                        {/* Submit Action */}
                        <div className="shrink-0">
                          <button
                            onClick={() => handleSubmitDraft(item.id)}
                            disabled={submittingId === item.id}
                            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-blue-600/20 transition-all active:scale-95"
                          >
                            {submittingId === item.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Send className="w-4 h-4" />
                            )}
                            <span>Gửi Sếp phê duyệt (Submit)</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: HISTORY (APPROVED / REJECTED) */}
          {activeTab === 'history' && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Lịch sử Phê duyệt ({historyList.length})</span>
              </h3>

              <div className="bg-white rounded-xl border border-slate-200/80 overflow-hidden shadow-xs">
                {historyList.length === 0 ? (
                  <div className="p-8 text-center text-slate-400 text-xs">
                    Chưa có lịch sử phê duyệt nào được ghi nhận.
                  </div>
                ) : (
                  <table className="w-full text-left text-xs text-slate-600">
                    <thead className="bg-slate-50 text-[11px] font-bold uppercase text-slate-500 border-b border-slate-100">
                      <tr>
                        <th className="py-3 px-4">Tiêu đề bài viết</th>
                        <th className="py-3 px-4">Quyết định</th>
                        <th className="py-3 px-4">Thời gian cập nhật</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {historyList.map((h) => (
                        <tr key={h.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3 px-4 font-medium text-slate-900">{h.title}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-block px-2.5 py-0.5 rounded text-[10px] font-bold ${
                              h.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
                            }`}>
                              {h.status === 'APPROVED' ? '✓ ĐÃ PHÊ DUYỆT' : '✕ ĐÃ TỪ CHỐI'}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-slate-400">{h.updated_at ? new Date(h.updated_at).toLocaleDateString('vi-VN') : 'Gần đây'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </>
      )}

    </div>
  );
};
