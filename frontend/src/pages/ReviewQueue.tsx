import React, { useState, useEffect, useCallback } from 'react';

import { CheckCircle2, XCircle, AlertTriangle, Clock, Check, ShieldCheck, Send, Sparkles, FileText, Loader2, History, Info, X, Tag, Eye, LayoutGrid, Edit2 } from 'lucide-react';
import { MarketingContent, Page, QuotaErrorDetail } from '../types';

import { contentApi, getApiErrorMessage, getQuotaError } from '../services/api';

import { useToast } from '../components/Toast';

import { ReviewQueueSkeleton } from '../components/Skeleton';

import { SocialPreviewContainer } from '../components/previews';

import { ExportActions } from '../components/ExportActions';

import { useFocusTrap } from '../hooks/useFocusTrap';

import { Pagination } from '../components/Pagination';

import { QuotaErrorCard } from '../components/QuotaBadge';



interface ReviewQueueProps {

  userRole?: string;

}



/**
 * Trạng thái của mỗi tab, ánh xạ sang tham số `status` nhiều giá trị của server.
 *
 * Nhờ có bảng này, việc "mỗi nội dung chỉ thuộc một tab" do SERVER bảo đảm: bài bị
 * từ chối (REJECTED) thuộc nhóm nháp chứ không thuộc lịch sử. Trước đây bộ lọc nằm
 * ở client nên bài REJECTED hiện ở cả hai tab và bộ đếm đếm nó hai lần.
 */
const TAB_STATUS = {
  pending: 'IN_REVIEW',
  drafts: 'AI_DRAFT,DRAFT,REJECTED',
  history: 'APPROVED,PUBLISHED',
} as const;



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

  // Phân trang theo tab: server lọc theo `TAB_STATUS` rồi cắt trang.
  const [contentPage, setContentPage] = useState<Page<MarketingContent>>({
    items: [], total: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_prev: false,
  });
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [quotaError, setQuotaError] = useState<QuotaErrorDetail | null>(null);

  const [rejectId, setRejectId] = useState<number | null>(null);

  const [rejectReason, setRejectReason] = useState<string>('');

  const [isRejecting, setIsRejecting] = useState<boolean>(false);

  const [approvingId, setApprovingId] = useState<number | null>(null);

  const [publishingId, setPublishingId] = useState<number | null>(null);

  const [submittingId, setSubmittingId] = useState<number | null>(null);

  const [showSocialPreview, setShowSocialPreview] = useState<boolean>(true);



  const rejectModalRef = useFocusTrap<HTMLDivElement>({

    isActive: !!rejectId,

    onEscape: () => {

      setRejectId(null);

      setRejectReason('');

    }

  });



  const approverRoles = ['MANAGER', 'AGENCY_MANAGER', 'CLIENT_APPROVER'];

  const isApprover = approverRoles.includes(userRole || '');



  // Confirmation Dialog State for Editing APPROVED / PUBLISHED Content (Brand Safety Warning)

  interface PendingConfirmAction {

    contentId: number;

    type: 'image' | 'content';

    newImageUrl?: string;

    updateData?: { title?: string; body?: string; cta?: string; image_url?: string };

    contentTitle: string;

  }

  const [confirmDialog, setConfirmDialog] = useState<PendingConfirmAction | null>(null);



  // Edit Content Modal State

  const [editingContent, setEditingContent] = useState<MarketingContent | null>(null);

  const [editTitle, setEditTitle] = useState('');

  const [editBody, setEditBody] = useState('');

  const [editCta, setEditCta] = useState('');

  const [isUpdating, setIsUpdating] = useState(false);



  const confirmModalRef = useFocusTrap<HTMLDivElement>({

    isActive: !!confirmDialog,

    onEscape: () => setConfirmDialog(null)

  });



  const editModalRef = useFocusTrap<HTMLDivElement>({

    isActive: !!editingContent,

    onEscape: () => setEditingContent(null)

  });



  const executeImageChange = async (contentId: number, newImageUrl: string) => {

    try {

      const updated = await contentApi.update(contentId, { image_url: newImageUrl });

      setContents(prev => prev.map(c => c.id === contentId ? { ...c, image_url: updated.image_url || newImageUrl, status: updated.status || c.status } : c));

      toast.success('Đã cập nhật ảnh sản phẩm / banner thành công!');

      if (updated.status === 'AI_DRAFT') {

        toast.info('Bài viết đã tự động chuyển về trạng thái Nháp (AI_DRAFT) để phê duyệt lại.');

        await loadContents();

      }

    } catch (e: any) {

      toast.error(getApiErrorMessage(e), 'Lỗi khi cập nhật ảnh');

    }

  };



  const executeContentUpdate = async (contentId: number, updateData: { title?: string; body?: string; cta?: string; image_url?: string }) => {

    try {

      setIsUpdating(true);

      const updated = await contentApi.update(contentId, updateData);

      setContents(prev => prev.map(c => c.id === contentId ? { ...c, ...updated } : c));

      setEditingContent(null);

      toast.success('Đã cập nhật nội dung bài viết thành công!');

      if (updated.status === 'AI_DRAFT') {

        toast.info('Bài viết đã tự động chuyển về trạng thái Nháp (AI_DRAFT) để phê duyệt lại.');

        await loadContents();

      }

    } catch (e: any) {

      toast.error(getApiErrorMessage(e), 'Lỗi khi cập nhật bài viết');

    } finally {

      setIsUpdating(false);

    }

  };



  const handleImageChange = async (contentId: number, newImageUrl: string) => {

    const target = contents.find(c => c.id === contentId);

    if (target && (target.status === 'APPROVED' || target.status === 'PUBLISHED')) {

      setConfirmDialog({

        contentId,

        type: 'image',

        newImageUrl,

        contentTitle: target.title

      });

      return;

    }

    await executeImageChange(contentId, newImageUrl);

  };



  const handleStartEdit = (content: MarketingContent) => {

    setEditingContent(content);

    setEditTitle(content.title);

    setEditBody(content.body);

    setEditCta(content.cta || '');

  };



  const handleSaveEdit = async () => {

    if (!editingContent) return;

    const updateData = {

      title: editTitle.trim(),

      body: editBody.trim(),

      cta: editCta.trim() || undefined

    };

    if (editingContent.status === 'APPROVED' || editingContent.status === 'PUBLISHED') {

      setConfirmDialog({

        contentId: editingContent.id,

        type: 'content',

        updateData,

        contentTitle: editingContent.title

      });

      return;

    }

    await executeContentUpdate(editingContent.id, updateData);

  };



  const handleConfirmAction = async () => {

    if (!confirmDialog) return;

    const action = confirmDialog;

    setConfirmDialog(null);

    if (action.type === 'image' && action.newImageUrl !== undefined) {

      await executeImageChange(action.contentId, action.newImageUrl);

    } else if (action.type === 'content' && action.updateData) {

      await executeContentUpdate(action.contentId, action.updateData);

    }

  };





  // useCallback để effect mount không thiếu dependency (xem MyTasksPage).
  const loadContents = useCallback(async () => {

    try {

      setLoading(true);

      // Lọc + cắt trang ở SERVER theo trạng thái của tab đang mở. Trước đây màn
      // hình này tải toàn bộ nội dung rồi chia ở client; sau khi có phân trang thì
      // cách đó chỉ lấy được trang đầu và những bài ở trang sau sẽ biến mất khỏi
      // hàng đợi mà bộ đếm vẫn tưởng đủ.
      const result = await contentApi.getAllPage(page, pageSize, {
        status: TAB_STATUS[activeTab],
        sort: 'newest',
      });

      setContents(result.items);
      setContentPage(result);

    } catch (e) {

      const quotaErr = getQuotaError(e);
      if (quotaErr) setQuotaError(quotaErr);
      console.error(e);

      toast.error(getApiErrorMessage(e), 'Lỗi khi tải danh sách nội dung');

    } finally {

      setLoading(false);

    }

  }, [toast, page, pageSize, activeTab]);

  // Nạp dữ liệu lúc mount (phải sau khai báo loadContents — xem MyTasksPage).
  useEffect(() => {
    void loadContents();
  }, [loadContents]);

  // Đổi tab thì về trang 1: trang 3 của tab "Chờ duyệt" không có nghĩa ở tab
  // "Lịch sử" vốn có ít bản ghi hơn.
  useEffect(() => {
    setPage(1);
  }, [activeTab]);

  const handlePageSizeChange = (nextSize: number) => {
    setPageSize(nextSize);
    setPage(1);
  };



  const handleApprove = async (id: number) => {

    if (!isApprover) {

      toast.warning('Chỉ Quản lý (Manager, Agency Manager, Client Approver) mới có quyền duyệt nội dung!');

      return;

    }

    if (approvingId !== null) return;

    setApprovingId(id);

    try {

      await contentApi.approve(id);

      toast.success('Đã phê duyệt bài viết thành công (APPROVED)!');

      await loadContents();

    } catch (e: any) {

      toast.error(getApiErrorMessage(e), 'Lỗi khi duyệt bài');

    } finally {

      setApprovingId(null);

    }

  };



  const handlePublishNow = async (id: number) => {

    if (!isApprover) {

      toast.warning('Chỉ Quản lý (Manager, Agency Manager, Client Approver) mới có quyền xuất bản nội dung!');

      return;

    }

    if (publishingId !== null) return;

    setPublishingId(id);

    try {

      await contentApi.publish(id);

      toast.success('Đã xuất bản bài viết thành công (PUBLISHED)!');

      await loadContents();

    } catch (e: any) {

      toast.error(getApiErrorMessage(e), 'Lỗi khi xuất bản bài viết');

    } finally {

      setPublishingId(null);

    }

  };



  const handleReject = async (id: number) => {

    if (!isApprover) {

      toast.warning('Chỉ Quản lý mới có quyền từ chối bài viết!');

      return;

    }

    if (isRejecting) return;

    if (rejectReason.trim().length < 3) {

      toast.warning('Vui lòng nhập lý do từ chối cụ thể (tối thiểu 3 ký tự) để nhân viên có hướng điều chỉnh!');

      return;

    }

    setIsRejecting(true);

    try {

      await contentApi.reject(id, rejectReason.trim());

      setRejectId(null);

      setRejectReason('');

      toast.success('Đã gửi phản hồi từ chối bài viết (REJECTED)');

      await loadContents();

    } catch (e: any) {

      toast.error(getApiErrorMessage(e), 'Lỗi khi từ chối bài');

    } finally {

      setIsRejecting(false);

    }

  };



  const handleSubmitDraft = async (id: number) => {

    if (submittingId !== null) return;

    try {

      setSubmittingId(id);

      await contentApi.submitForReview(id);

      toast.success('Đã chuyển bài viết sang Hàng đợi phê duyệt (IN_REVIEW)!');

      await loadContents();

    } catch (e: any) {

      toast.error(getApiErrorMessage(e), 'Lỗi khi gửi duyệt bản nháp');

    } finally {

      setSubmittingId(null);

    }

  };



  // Nội dung đến từ server ĐÃ lọc theo trạng thái của tab và đã cắt trang, nên
  // `contents` chính là danh sách của tab hiện tại — không chia ở client nữa.
  const pendingList = contents;

  // Mỗi nội dung chỉ được xuất hiện ở MỘT tab, và giờ điều đó do server đảm bảo
  // qua `TAB_STATUS`: REJECTED thuộc nhóm nháp, không thuộc nhóm lịch sử. Trước đây
  // REJECTED nằm trong CẢ draftList lẫn historyList nên một bài bị từ chối hiện ở
  // hai tab và bộ đếm cũng đếm nó hai lần.
  const draftList = contents;
  const historyList = contents;

  const rejectModalItem = contents.find(c => c.id === rejectId) || null;



  return (

    <div className="p-8 space-y-8 max-w-6xl mx-auto">

      {/* Lỗi hạn mứng gói miễn phí — giữ thành khối thay vì toast thoáng qua, để
          người dùng đọc kịp trần, số đã dùng và thời điểm hết hạn. */}

      {quotaError && <QuotaErrorCard detail={quotaError} />}

      

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

      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow no-print">

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

                !showSocialPreview ? 'bg-white text-slate-900 shadow' : 'text-slate-600 hover:text-slate-900'

              }`}

            >

              <LayoutGrid className="w-3.5 h-3.5" />

              Thẻ tóm tắt

            </button>

            <button

              onClick={() => setShowSocialPreview(true)}

              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${

                showSocialPreview ? 'bg-indigo-600 text-white shadow' : 'text-slate-600 hover:text-slate-900'

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

              ? 'bg-amber-700 text-white shadow-sm'

              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'

          }`}

        >

          <Clock className="w-3.5 h-3.5" />

          <span>Chờ phê duyệt</span>

          <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${

            activeTab === 'pending' ? 'bg-amber-800 text-white' : 'bg-slate-200 text-slate-700'

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

                <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center text-slate-500 text-xs space-y-2">

                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />

                  <p className="font-semibold text-slate-600">Tuyệt vời! Không còn bài viết nào đang chờ duyệt.</p>

                  <p>Mọi nội dung gửi lên đã được xử lý xong.</p>

                </div>

              ) : (

                <div className="grid grid-cols-1 gap-4">

                  {pendingList.map((item) => (

                    <div key={item.id} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm hover:border-indigo-300 transition-all space-y-4 review-item-card print-card">

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

                            onClick={() => handleStartEdit(item)}

                            className="px-2.5 py-1.5 border border-slate-200 text-slate-600 hover:text-indigo-600 hover:bg-slate-50 rounded-lg text-xs font-semibold flex items-center gap-1 transition-all"

                            title="Chỉnh sửa nội dung bài viết"

                          >

                            <Edit2 className="w-3.5 h-3.5" />

                            <span>Sửa</span>

                          </button>

                          <button

                            onClick={() => handleApprove(item.id)}

                            disabled={!isApprover || approvingId === item.id}

                            title={!isApprover ? 'Chỉ Quản lý (Manager, Agency Manager, Client Approver) mới có quyền duyệt' : 'Phê duyệt xuất bản'}

                            className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-200 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all active:scale-95"

                          >

                            {approvingId === item.id ? (

                              <Loader2 className="w-4 h-4 animate-spin" />

                            ) : (

                              <CheckCircle2 className="w-4 h-4" />

                            )}

                            <span>{approvingId === item.id ? 'Đang duyệt...' : 'Phê duyệt (Approve)'}</span>

                          </button>

                          <button

                            onClick={() => { setRejectId(item.id); setRejectReason(''); }}

                            disabled={!isApprover || isRejecting}

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

                              <span className="text-slate-600 font-semibold">Lời kêu gọi (CTA): </span>

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

                <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center text-slate-500 text-xs space-y-2">

                  <Sparkles className="w-8 h-8 text-indigo-400 mx-auto animate-pulse" />

                  <p className="font-semibold text-slate-600">Hiện không có bản nháp nào đang chờ gửi.</p>

                  <p>Mở AI Copilot Studio để sinh thêm ý tưởng và bản nháp chiến dịch mới.</p>

                </div>

              ) : (

                <div className="grid grid-cols-1 gap-4">

                  {draftList.map((item) => (

                    <div key={item.id} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm hover:border-blue-300 transition-all space-y-4 review-item-card print-card">

                      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">

                        <div className="flex items-center gap-2">

                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${

                            item.status === 'REJECTED'

                              ? 'bg-rose-50 text-rose-700 border-rose-200'

                              : 'bg-blue-50 text-blue-700 border-blue-200'

                          }`}>

                            {item.status === 'REJECTED' ? 'CẦN CHỈNH SỬA (REJECTED)' : `BẢN NHÁP (${item.status})`}

                          </span>

                          <span className="text-xs text-slate-500 font-medium">Kênh: {item.channel?.name || 'Mạng xã hội'}</span>

                        </div>



                        {/* Submit Action */}

                        <div className="flex items-center gap-2 no-print review-actions">

                          <button

                            onClick={() => handleStartEdit(item)}

                            className="px-2.5 py-1.5 border border-slate-200 text-slate-600 hover:text-indigo-600 hover:bg-slate-50 rounded-lg text-xs font-semibold flex items-center gap-1 transition-all"

                            title="Chỉnh sửa nội dung bản nháp"

                          >

                            <Edit2 className="w-3.5 h-3.5" />

                            <span>Sửa</span>

                          </button>

                          <button

                            onClick={() => handleSubmitDraft(item.id)}

                            disabled={submittingId === item.id}

                            className={`px-3.5 py-1.5 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md transition-all active:scale-95 ${

                              item.status === 'REJECTED'

                                ? 'bg-gradient-to-r from-amber-600 to-indigo-600 hover:from-amber-700 hover:to-indigo-700 shadow-amber-600/20'

                                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-blue-600/20'

                            }`}

                          >

                            {submittingId === item.id ? (

                              <Loader2 className="w-4 h-4 animate-spin" />

                            ) : (

                              <Send className="w-4 h-4" />

                            )}

                            <span>{item.status === 'REJECTED' ? 'Sửa & Gửi lại (Resubmit)' : 'Gửi Sếp phê duyệt (Submit)'}</span>

                          </button>

                        </div>

                      </div>



                      {item.status === 'REJECTED' && (item.rejection_reason || (item as any).rejection_feedback) && (

                        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800">

                          <span className="font-bold">Lý do từ chối: </span>

                          <span>{item.rejection_reason || (item as any).rejection_feedback}</span>

                        </div>

                      )}



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

                              <span className="text-slate-600 font-semibold">Lời kêu gọi (CTA): </span>

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



              <div className="bg-white rounded-xl border border-slate-200/80 overflow-hidden shadow-sm">

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

                        <th className="py-3 px-4 text-right">Thao tác</th>

                      </tr>

                    </thead>

                    <tbody className="divide-y divide-slate-100">

                      {historyList.map((h) => (

                        <tr key={h.id} className="hover:bg-slate-50/60 transition-colors">

                          <td className="py-3 px-4 font-medium text-slate-900">

                            <div>{h.title}</div>

                            <span className="text-[10px] text-slate-600 font-normal">Kênh: {h.channel?.name || 'Mạng xã hội'}</span>

                          </td>

                          <td className="py-3 px-4 whitespace-nowrap">

                            <span className={`inline-block px-2.5 py-0.5 rounded text-[10px] font-bold ${

                              h.status === 'PUBLISHED' ? 'bg-indigo-50 text-indigo-700 border border-indigo-200' :

                              h.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'

                            }`}>

                              {/* `historyList` chỉ chứa APPROVED/PUBLISHED nên
                                  nhánh else không bao giờ chạy; giữ "ĐÃ TỪ CHỐI" ở
                                  đây là nhãn chết dễ gây hiểu nhầm khi ai đó đọc
                                  template. Bài bị từ chối hiển thị ở tab "Cần chỉnh
                                  sửa" với nhãn CẦN CHỈNH SỬA (REJECTED). */}
                              {h.status === 'PUBLISHED' ? '✓ ĐÃ XUẤT BẢN' : '✓ ĐÃ PHÊ DUYỆT'}

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

                                {h.status === 'PUBLISHED' ? 'Đã xuất bản thành công lên kênh truyền thông' : 'Đã kiểm duyệt đạt tiêu chuẩn an toàn & chính sách'}

                              </span>

                            )}

                          </td>

                          <td className="py-3 px-4 text-slate-600 whitespace-nowrap">{h.updated_at ? new Date(h.updated_at).toLocaleDateString('vi-VN') : 'Gần đây'}</td>

                          <td className="py-3 px-4 text-right whitespace-nowrap">

                            <div className="flex items-center justify-end gap-1.5">

                              <button

                                onClick={() => handleStartEdit(h)}

                                className="px-2.5 py-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-lg text-xs font-semibold flex items-center gap-1 transition-all"

                                title="Chỉnh sửa bài viết (sẽ yêu cầu duyệt lại nếu đã duyệt)"

                              >

                                <Edit2 className="w-3.5 h-3.5" />

                                <span>Chỉnh sửa</span>

                              </button>

                              {h.status === 'APPROVED' && (

                                <button

                                  onClick={() => handlePublishNow(h.id)}

                                  disabled={!isApprover || publishingId === h.id}

                                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer disabled:cursor-not-allowed"

                                  title="Xuất bản bài viết ngay lập tức"

                                >

                                  {publishingId === h.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}

                                  <span>Xuất bản ngay</span>

                                </button>

                              )}

                              {h.status === 'PUBLISHED' && (

                                <span className="text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">

                                  ✓ Đã xuất bản

                                </span>

                              )}

                            </div>

                          </td>

                        </tr>

                      ))}

                    </tbody>

                  </table>

                )}

                {/* Bộ phân trang — chỉ hiện khi tab đang mở còn bản ghi. */}
                {!loading && pendingList.length > 0 && (

                  <Pagination

                    page={contentPage}

                    onPageChange={setPage}

                    onPageSizeChange={handlePageSizeChange}

                    itemLabel="bài viết"

                    disabled={loading}

                  />

                )}

              </div>

            </div>

          )}

        </>

      )}



      {/* Dedicated Reject Modal with Quick Feedback Templates */}

        {/* onClick chống đóng ở đây là dư: lớp backdrop ngay bên dưới đã đóng modal với

            cùng điều kiện (!isRejecting). Bỏ đi để div role="dialog" không mang sự kiện chuột.

            Cách đóng bằng bàn phím vẫn còn: phím Escape (useFocusTrap) và nút X trên header. */}

      {rejectModalItem && (

        <div 

          className="fixed inset-0 z-50 overflow-y-auto pointer-events-auto no-print"

          role="dialog"

          aria-modal="true"

          aria-labelledby="reject-modal-title"

        >

          {/* Backdrop */}

          <div 

            className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity cursor-pointer pointer-events-auto"

            aria-hidden="true"

            onClick={() => {

              if (!isRejecting) {

                setRejectId(null);

                setRejectReason('');

              }

            }}

          />

          <div className="flex items-center justify-center min-h-screen p-4 pointer-events-none">

            <div

              ref={rejectModalRef}

              className="relative bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in duration-200 z-10 pointer-events-auto"

            >

            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-rose-50/60">

              <div className="flex items-center gap-2 text-rose-700">

                <XCircle className="w-5 h-5 text-rose-600" />

                <h3 id="reject-modal-title" className="font-bold text-sm text-slate-900">Từ chối Phê duyệt & Yêu cầu chỉnh sửa</h3>

              </div>

              <button

                onClick={() => { setRejectId(null); setRejectReason(''); }}

                aria-label="Đóng modal từ chối"

                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"

              >

                <X className="w-4 h-4" />

              </button>

            </div>



            <div className="p-5 space-y-4">

              <div>

                <span className="text-[11px] font-bold text-slate-600 uppercase">Bài viết:</span>

                <p className="text-xs font-semibold text-slate-800 line-clamp-2 mt-0.5">{rejectModalItem.title}</p>

              </div>



              <div>

                <span className="block text-xs font-bold text-slate-700 mb-2 flex items-center gap-1.5">

                  <Tag className="w-3.5 h-3.5 text-indigo-600" />

                  Mẫu phản hồi nhanh (Quick Feedback Templates):

                </span>

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

                <label htmlFor="reject-reason-input" className="block text-xs font-bold text-slate-700 mb-1 flex items-center justify-between">

                  <span>Chi tiết lý do từ chối & hướng dẫn sửa (tối thiểu 3 ký tự):</span>

                  <span className={`text-[10px] font-semibold ${rejectReason.trim().length >= 3 ? 'text-emerald-700' : 'text-slate-600'}`}>

                    {rejectReason.trim().length}/3

                  </span>

                </label>

                <textarea

                  id="reject-reason-input"

                  rows={3}

                  value={rejectReason}

                  onChange={(e) => setRejectReason(e.target.value)}

                  placeholder="Nhập cụ thể lý do bài viết chưa đạt và gợi ý để Marketer điều chỉnh..."

                  className="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-rose-500 focus:bg-white transition-colors"

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

                disabled={rejectReason.trim().length < 3 || isRejecting}

                onClick={() => handleReject(rejectModalItem.id)}

                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-lg shadow-sm transition-all flex items-center gap-1.5"

              >

                {isRejecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}

                <span>Xác nhận Từ chối</span>

              </button>

            </div>

          </div>

        </div>

      </div>

      )}



      {/* Edit Content Modal */}

        {/* Lớp phủ này chỉ là phím tắt chuột để đóng modal; đóng bằng bàn phím đã có

            nút X trên header và phím Escape (useFocusTrap) nên không cần vai trò tương tác. */}

      {editingContent && (

        <div 

          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 no-print animate-in fade-in duration-150"

          role="none"

          onClick={(e) => {

            if (e.target === e.currentTarget && !isUpdating) {

              setEditingContent(null);

            }

          }}

        >

          <div

            ref={editModalRef}

            role="dialog"

            aria-modal="true"

            aria-labelledby="edit-modal-title"

            className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in duration-200"

          >

            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-indigo-50/50">

              <div className="flex items-center gap-2 text-indigo-700">

                <Edit2 className="w-5 h-5 text-indigo-600" />

                <h3 id="edit-modal-title" className="font-bold text-sm text-slate-900">Chỉnh sửa nội dung bài viết</h3>

              </div>

              <button

                onClick={() => setEditingContent(null)}

                aria-label="Đóng modal chỉnh sửa"

                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"

              >

                <X className="w-4 h-4" />

              </button>

            </div>



            <div className="p-5 space-y-4">

              {(editingContent.status === 'APPROVED' || editingContent.status === 'PUBLISHED') && (

                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800 flex items-start gap-2">

                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />

                  <div>

                    <strong className="block font-bold">Lưu ý An toàn Thương hiệu:</strong>

                    <span>Bài viết này đã được phê duyệt. Việc chỉnh sửa sẽ tự động hủy phê duyệt và đưa bài viết về trạng thái Nháp (AI_DRAFT) để phê duyệt lại.</span>

                  </div>

                </div>

              )}



              <div>

                <label className="block text-xs font-bold text-slate-700 mb-1">Tiêu đề bài viết:</label>

                <input

                  type="text"

                  value={editTitle}

                  onChange={(e) => setEditTitle(e.target.value)}

                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 focus:bg-white transition-colors"

                />

              </div>



              <div>

                <label className="block text-xs font-bold text-slate-700 mb-1">Nội dung bài viết:</label>

                <textarea

                  rows={5}

                  value={editBody}

                  onChange={(e) => setEditBody(e.target.value)}

                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 focus:bg-white transition-colors leading-relaxed"

                />

              </div>



              <div>

                <label className="block text-xs font-bold text-slate-700 mb-1">Lời kêu gọi hành động (CTA):</label>

                <input

                  type="text"

                  value={editCta}

                  onChange={(e) => setEditCta(e.target.value)}

                  placeholder="Ví dụ: Đăng ký ngay để nhận ưu đãi!"

                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 focus:bg-white transition-colors"

                />

              </div>

            </div>



            <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-2">

              <button

                type="button"

                onClick={() => setEditingContent(null)}

                className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"

              >

                Hủy bỏ

              </button>

              <button

                type="button"

                onClick={handleSaveEdit}

                disabled={isUpdating || !editTitle.trim() || !editBody.trim()}

                className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-lg shadow-sm transition-all flex items-center gap-1.5"

              >

                {isUpdating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}

                <span>Lưu thay đổi</span>

              </button>

            </div>

          </div>

        </div>

      )}



      {/* Brand Safety Confirmation Dialog on Editing APPROVED Content (Task 2) */}

        {/* Wrapper bố cục: đóng bằng bàn phím đã có nút trong alertdialog + phím Escape

            (useFocusTrap), nên wrapper không mang vai trò tương tác. */}

      {confirmDialog && (

        <div 

          className="fixed inset-0 z-[60] overflow-y-auto pointer-events-auto no-print"

          role="none"

          onClick={(e) => {

            if (e.target === e.currentTarget) {

              setConfirmDialog(null);

            }

          }}

        >

          {/* Dedicated Backdrop */}

          <div 

            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity cursor-pointer pointer-events-auto"

            aria-hidden="true"

            onClick={() => setConfirmDialog(null)}

          />

          <div className="flex items-center justify-center min-h-screen p-4 pointer-events-none">

            {/* onClick stopPropagation là dư: handler của wrapper đã kiểm tra

                e.target === e.currentTarget nên click trong alertdialog không đóng modal. */}

            <div

              ref={confirmModalRef}

              role="alertdialog"

              aria-modal="true"

              aria-labelledby="confirm-dialog-title"

              aria-describedby="confirm-dialog-desc"

              className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full border border-amber-200 overflow-hidden animate-in fade-in duration-200 z-10 pointer-events-auto"

            >

              <div className="p-5 border-b border-amber-100 flex items-center gap-3 bg-amber-50">

                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center shrink-0 border border-amber-200">

                  <AlertTriangle className="w-5 h-5 text-amber-600" />

                </div>

                <div>

                  <h3 id="confirm-dialog-title" className="font-bold text-sm text-slate-900">

                    Cảnh báo An toàn Thương hiệu

                  </h3>

                  <p className="text-[11px] text-amber-700 font-medium">

                    Hủy phê duyệt nội dung & đưa về trạng thái Nháp

                  </p>

                </div>

              </div>



              <div className="p-5 space-y-3">

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">

                  <span className="text-[10px] font-bold uppercase text-slate-400">Bài viết đang chỉnh sửa:</span>

                  <p className="font-bold text-slate-800 line-clamp-1 mt-0.5">{confirmDialog.contentTitle}</p>

                </div>



                <div id="confirm-dialog-desc" className="text-xs text-slate-700 leading-relaxed bg-amber-50/50 p-3.5 rounded-xl border border-amber-100">

                  <p className="font-medium text-slate-800">

                    Bài viết này đã được phê duyệt. Việc chỉnh sửa sẽ tự động hủy phê duyệt và đưa bài viết về trạng thái Nháp (AI_DRAFT) để phê duyệt lại. Bạn có chắc chắn muốn tiếp tục?

                  </p>

                </div>

              </div>



              <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-end gap-2">

                <button

                  type="button"

                  onClick={() => setConfirmDialog(null)}

                  className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"

                >

                  Hủy bỏ

                </button>

                <button

                  type="button"

                  onClick={handleConfirmAction}

                  className="px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-lg shadow-sm transition-all flex items-center gap-1.5"

                >

                  <Check className="w-4 h-4" />

                  <span>Xác nhận tiếp tục</span>

                </button>

              </div>

            </div>

          </div>

        </div>

      )}



    </div>

  );

};
