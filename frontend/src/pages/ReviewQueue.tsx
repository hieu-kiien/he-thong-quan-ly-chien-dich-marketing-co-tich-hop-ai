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
  Info,
  X,
  Tag,
  Lock,
  Eye,
  LayoutGrid
} from 'lucide-react';
import { MarketingContent } from '../types';
import { contentApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { ReviewQueueSkeleton } from '../components/Skeleton';
import { SocialPreviewContainer } from '../components/previews';
import { ExportActions } from '../components/ExportActions';

interface ReviewQueueProps {
  userRole?: string;
}

const REJECT_FEEDBACK_TEMPLATES = [
  'Sai lệch thông điệp thương hiệu & định vị sản phẩm',
  'Chứa từ ngữ nhạy cảm / vi phạm chính sách nền tảng (Meta/TikTok)',
  'Giọng văn chưa phù hợp (Tone & Voice) với đối tượng khách hàng mục tiêu',
  'Lời kêu gọi hành động (CTA) chưa rõ ràng hoặc thiếu động lực chuyển đổi',
  'Cần bổ sung thêm thông tin ưu đãi và thời hạn áp dụng cụ thể'
];

export const ReviewQueue: React.FC<ReviewQueueProps> = ({ userRole }) => {
  const toast = useToast();
  const [contents, setContents] = useState<MarketingContent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'drafts' | 'history'>('pending');
  const [rejectId, setRejectId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [isRejecting, setIsRejecting] = useState<boolean>(false);
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const [showSocialPreview, setShowSocialPreview] = useState<boolean>(true);

  const approverRoles = ['MANAGER', 'AGENCY_MANAGER', 'CLIENT_APPROVER'];
  const isApprover = approverRoles.includes(userRole || '');

  const handleImageChange = async (contentId: number, newImageUrl: string) => {
    try {
      const updated = await contentApi.update(contentId, { image_url: newImageUrl });
      setContents(prev => prev.map(c => c.id === contentId ? { ...c, image_url: updated.image_url || newImageUrl, status: updated.status || c.status } : c));
      toast.success('Đã cập nhật ảnh sản phẩm / banner thành công!');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi cập nhật ảnh');
    }
  };

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
    if (!isApprover) {
      toast.warning('Chỉ Quản lý (Manager, Agency Manager, Client Approver) mới có quyền duyệt nội dung!');
      return;
    }
    try {
      await contentApi.approve(id);
      toast.success('Đã phê duyệt bài viết thành công (APPROVED)!');
      loadContents();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi duyệt bài');
    }
  };

  const handleReject = async (id: number) => {
    if (!isApprover) {
      toast.warning('Chỉ Quản lý mới có quyền từ chối bài viết!');
      return;
    }
    if (rejectReason.trim().length < 5) {
      toast.warning('Vui lòng nhập lý do từ chối cụ thể (tối thiểu 5 ký tự) để nhân viên có hướng điều chỉnh!');
      return;
    }
    setIsRejecting(true);
    try {
      await contentApi.reject(id, rejectReason.trim());
      setRejectId(null);
      setRejectReason('');
      toast.success('Đã gửi phản hồi từ chối bài viết (REJECTED)');
      loadContents();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi từ chối bài');
    } finally {
      setIsRejecting(false);
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
  const rejectModalItem = contents.find(c => c.id === rejectId) || null;

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      
      {/* Print-Only Header (FEAT-FE-14 & R4) */}
      <div className="hidden print-header">
        <h1 className="text-xl font-bold text-slate-900 uppercase">Kế hoạch Phê duyệt Nội dung Chiến dịch</h1>
        <p className="text-xs text-slate-600 mt-1">Hệ thống Tiếp thị Đa kênh MarketFlow AI — Báo cáo In / Lưu PDF</p>
      </div>

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
            Nội dung do AI hoặc nhân viên soạn thảo bắt buộc phải được Quản lý (Manager / Approver) kiểm duyệt trước khi xuất bản hoặc lập lịch.
          </p>
        </div>

        {!isApprover && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2 rounded-lg flex items-center gap-2 no-print">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Bạn đang xem dưới vai trò <strong>{userRole || 'MARKETER'}</strong> (chỉ có quyền xem). Chuyển sang <strong>Manager / Client Approver</strong> ở thanh trên để bấm duyệt hoặc từ chối.</span>
          </div>
        )}
      </div>

      {/* Top Action Bar: Export & Visual View Switcher (FEAT-FE-14 & R4) */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-2xs no-print">
        <ExportActions
          campaignName="Hàng Đợi Duyệt Bài MarketFlow AI"
          contents={contents}
          className="border-0 p-0 bg-transparent"
        />

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-slate-500 font-medium hidden sm:inline">Chế độ hiển thị:</span>
          <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              onClick={() => setShowSocialPreview(false)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                !showSocialPreview ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              Thẻ tóm tắt
            </button>
            <button
              onClick={() => setShowSocialPreview(true)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                showSocialPreview ? 'bg-indigo-600 text-white shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Social Preview (R4)
            </button>
          </div>
        </div>
      </div>

      {/* Filter Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 no-print">
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
                    <div key={item.id} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs hover:border-indigo-300 transition-all space-y-4 review-item-card print-card">
                      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-amber-50 text-amber-700 font-bold px-2 py-0.5 rounded border border-amber-200">
                            CHỜ DUYỆT (IN_REVIEW)
                          </span>
                          <span className="text-xs text-slate-500 font-medium">Kênh: {item.channel?.name || 'Mạng xã hội'}</span>
                        </div>

                        {/* Actions for Manager / Approver */}
                        <div className="flex items-center gap-2 no-print review-actions">
                          <button
                            onClick={() => handleApprove(item.id)}
                            disabled={!isApprover}
                            title={!isApprover ? 'Chỉ Quản lý (Manager, Agency Manager, Client Approver) mới có quyền duyệt' : 'Phê duyệt xuất bản'}
                            className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all active:scale-95"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Phê duyệt (Approve)</span>
                          </button>
                          <button
                            onClick={() => { setRejectId(item.id); setRejectReason(''); }}
                            disabled={!isApprover}
                            title={!isApprover ? 'Chỉ Quản lý (Manager, Agency Manager, Client Approver) mới có quyền từ chối' : 'Từ chối & yêu cầu chỉnh sửa'}
                            className="px-3.5 py-1.5 bg-rose-50 hover:bg-rose-100 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed text-rose-700 rounded-lg text-xs font-bold flex items-center gap-1.5 border border-rose-200 transition-all active:scale-95"
                          >
                            <XCircle className="w-4 h-4" />
                            <span>Từ chối (Reject)</span>
                          </button>
                        </div>
                      </div>

                      {showSocialPreview ? (
                        <SocialPreviewContainer
                          content={item}
                          onImageChange={handleImageChange}
                        />
                      ) : (
                        <div>
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
                    <div key={item.id} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs hover:border-blue-300 transition-all space-y-4 review-item-card print-card">
                      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-blue-50 text-blue-700 font-bold px-2 py-0.5 rounded border border-blue-200">
                            BẢN NHÁP ({item.status})
                          </span>
                          <span className="text-xs text-slate-500 font-medium">Kênh: {item.channel?.name || 'Mạng xã hội'}</span>
                        </div>

                        {/* Submit Action */}
                        <div className="no-print review-actions">
                          <button
                            onClick={() => handleSubmitDraft(item.id)}
                            disabled={submittingId === item.id}
                            className="px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-blue-600/20 transition-all active:scale-95"
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

                      {showSocialPreview ? (
                        <SocialPreviewContainer
                          content={item}
                          onImageChange={handleImageChange}
                        />
                      ) : (
                        <div>
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
                      )}
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
                        <th className="py-3 px-4">Ghi chú & Lý do kiểm duyệt</th>
                        <th className="py-3 px-4">Thời gian cập nhật</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {historyList.map((h) => (
                        <tr key={h.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3 px-4 font-medium text-slate-900">
                            <div>{h.title}</div>
                            <span className="text-[10px] text-slate-400 font-normal">Kênh: {h.channel?.name || 'Mạng xã hội'}</span>
                          </td>
                          <td className="py-3 px-4 whitespace-nowrap">
                            <span className={`inline-block px-2.5 py-0.5 rounded text-[10px] font-bold ${
                              h.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
                            }`}>
                              {h.status === 'APPROVED' ? '✓ ĐÃ PHÊ DUYỆT' : '✕ ĐÃ TỪ CHỐI'}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-xs">
                            {h.status === 'REJECTED' ? (
                              <div className="bg-rose-50/70 border border-rose-200 text-rose-800 rounded p-2 text-[11px] max-w-md">
                                <span className="font-bold">Lý do từ chối: </span>
                                <span>{h.rejection_reason || (h.reviews && h.reviews[0]?.reason) || 'Cần điều chỉnh lại thông điệp và nội dung theo chính sách thương hiệu.'}</span>
                              </div>
                            ) : (
                              <span className="text-emerald-700 text-[11px] flex items-center gap-1 font-medium">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                Đã kiểm duyệt đạt tiêu chuẩn an toàn & chính sách
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{h.updated_at ? new Date(h.updated_at).toLocaleDateString('vi-VN') : 'Gần đây'}</td>
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

      {/* Dedicated Reject Modal with Quick Feedback Templates */}
      {rejectModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 no-print">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-rose-50/60">
              <div className="flex items-center gap-2 text-rose-700">
                <XCircle className="w-5 h-5 text-rose-600" />
                <h3 className="font-bold text-sm text-slate-900">Từ chối Phê duyệt & Yêu cầu chỉnh sửa</h3>
              </div>
              <button
                onClick={() => { setRejectId(null); setRejectReason(''); }}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase">Bài viết:</span>
                <p className="text-xs font-semibold text-slate-800 line-clamp-2 mt-0.5">{rejectModalItem.title}</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5 text-indigo-600" />
                  Mẫu phản hồi nhanh (Quick Feedback Templates):
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {REJECT_FEEDBACK_TEMPLATES.map((tmpl, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setRejectReason(tmpl)}
                      className="text-[11px] px-2.5 py-1 rounded-full border border-slate-200 bg-slate-50 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 text-slate-700 transition-colors text-left"
                    >
                      + {tmpl}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 flex items-center justify-between">
                  <span>Chi tiết lý do từ chối & hướng dẫn sửa (tối thiểu 5 ký tự):</span>
                  <span className={`text-[10px] font-semibold ${rejectReason.trim().length >= 5 ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {rejectReason.trim().length}/5
                  </span>
                </label>
                <textarea
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Nhập cụ thể lý do bài viết chưa đạt và gợi ý để Marketer điều chỉnh..."
                  className="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-rose-500 focus:bg-white transition-colors"
                />
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-[11px] text-amber-800 flex items-start gap-1.5">
                <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>Nội dung sẽ được chuyển sang trạng thái <strong>REJECTED</strong>. Marketer có thể xem lý do để sửa lại và gửi duyệt lượt tiếp theo.</span>
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => { setRejectId(null); setRejectReason(''); }}
                className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                disabled={rejectReason.trim().length < 5 || isRejecting}
                onClick={() => handleReject(rejectModalItem.id)}
                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-lg shadow-sm transition-all flex items-center gap-1.5"
              >
                {isRejecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                <span>Xác nhận Từ chối</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
