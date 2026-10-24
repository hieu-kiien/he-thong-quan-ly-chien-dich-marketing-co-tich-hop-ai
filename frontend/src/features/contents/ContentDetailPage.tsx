import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Sparkles,
  Send,
  Check,
  XCircle,
  Calendar,
  Globe,
  Edit3,
  Trash2,
  AlertTriangle,
  ShieldCheck,
  ExternalLink,
  MessageSquare,
} from 'lucide-react';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Button,
  StatusBadge,
  Badge,
  Card,
  CardHeader,
  CardBody,
  PageHeader,
  ConfirmDialog,
  Dialog,
  FormField,
  Input,
  Textarea,
  useToast,
  ErrorState,
  SkeletonRows,
  Callout,
  Table,
  THead,
  TBody,
  TR,
  TH,
  TD,
} from '@/components/ui';
import { contentsApi, schedulesApi } from '@/lib/api/endpoints';
import { useAuth } from '@/lib/auth';
import {
  canEditContent,
  canDeleteContent,
  canSubmitContent,
  reviewBlockReason,
  canMarkPublished,
} from '@/lib/permissions';
import { useDocumentTitle } from '@/lib/hooks';
import { formatDateTime } from '@/lib/format';
import {
  CONTENT_TYPE_LABEL,
  ORIGIN_LABEL,
  REVIEW_DECISION_LABEL,
} from '@/lib/labels';
import type {
  BannedMatch,
  ContentUpdate,
  Schedule,
} from '@/lib/types';

export default function ContentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const contentId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const toast = useToast();

  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editCta, setEditCta] = useState('');

  // Workflow modals
  const [isRejecting, setIsRejecting] = useState(false);
  const [rejectComment, setRejectComment] = useState('');
  const [isApproving, setIsApproving] = useState(false);
  const [approveComment, setApproveComment] = useState('');

  // Mark published modal
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishedUrl, setPublishedUrl] = useState('');

  // Schedule modal
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleTime, setScheduleTime] = useState('');
  const [scheduleNote, setScheduleNote] = useState('');

  // Delete modal
  const [isDeleting, setIsDeleting] = useState(false);

  // Banned keywords check
  const [bannedMatches, setBannedMatches] = useState<BannedMatch[] | null>(null);
  const [isCheckingBanned, setIsCheckingBanned] = useState(false);

  const {
    data: content,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['contents', contentId],
    queryFn: () => contentsApi.get(contentId),
    enabled: !!contentId,
  });

  useDocumentTitle(content ? content.title : 'Chi tiết nội dung');

  const reviewsQ = useQuery({
    queryKey: ['contents', contentId, 'reviews'],
    queryFn: () => contentsApi.reviews(contentId),
    enabled: !!contentId,
  });

  const schedulesQ = useQuery({
    queryKey: ['schedules', { campaign_id: content?.campaign_id }],
    queryFn: async () => {
      if (!content) return [];
      const all = await schedulesApi.list({ campaign_id: content.campaign_id });
      return all.filter((s) => s.content_id === contentId);
    },
    enabled: !!content?.campaign_id,
  });

  // Mutations
  const updateMutation = useMutation({
    mutationFn: (body: ContentUpdate) => contentsApi.update(contentId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents', contentId] });
      toast.success('Đã lưu thay đổi nội dung');
      setIsEditing(false);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi cập nhật nội dung');
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => contentsApi.submit(contentId),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['contents', contentId] });
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      if (res.banned_matches && res.banned_matches.length > 0) {
        setBannedMatches(res.banned_matches);
        toast.info(
          'Đã gửi duyệt nhưng có cảnh báo',
          `Bài viết chứa ${res.banned_matches.length} từ cấm theo chính sách thương hiệu.`
        );
      } else {
        toast.success('Đã gửi duyệt thành công', 'Nội dung đang chờ Quản lý xem xét.');
      }
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi gửi duyệt');
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => contentsApi.approve(contentId, approveComment.trim() || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents', contentId] });
      queryClient.invalidateQueries({ queryKey: ['contents', contentId, 'reviews'] });
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      toast.success('Đã phê duyệt nội dung');
      setIsApproving(false);
      setApproveComment('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi phê duyệt');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => contentsApi.reject(contentId, rejectComment.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents', contentId] });
      queryClient.invalidateQueries({ queryKey: ['contents', contentId, 'reviews'] });
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      toast.success('Đã từ chối bài viết', 'Tác giả sẽ nhận được thông báo phản hồi.');
      setIsRejecting(false);
      setRejectComment('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi từ chối');
    },
  });

  const publishMutation = useMutation({
    mutationFn: () =>
      contentsApi.markPublished(contentId, {
        published_url: publishedUrl.trim() || null,
        published_at: new Date().toISOString(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents', contentId] });
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      toast.success('Đã đánh dấu đã đăng');
      setIsPublishing(false);
      setPublishedUrl('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi đánh dấu đã đăng');
    },
  });

  const scheduleMutation = useMutation({
    mutationFn: () =>
      schedulesApi.create({
        content_id: contentId,
        scheduled_at: new Date(scheduleTime).toISOString(),
        note: scheduleNote.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success('Lập lịch đăng bài thành công');
      setIsScheduling(false);
      setScheduleTime('');
      setScheduleNote('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi lập lịch đăng');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => contentsApi.remove(contentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      toast.success('Đã xoá nội dung');
      navigate('/contents');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi xoá nội dung');
    },
  });

  const handleCheckBanned = async () => {
    if (!content) return;
    setIsCheckingBanned(true);
    try {
      const res = await contentsApi.checkBanned(`${content.title} ${content.body} ${content.cta ?? ''}`);
      setBannedMatches(res.matches);
      if (res.matches.length === 0) {
        toast.success('Nội dung an toàn', 'Không tìm thấy từ cấm nào trong văn bản.');
      } else {
        toast.info('Phát hiện từ cấm', `Tìm thấy ${res.matches.length} từ cấm theo quy định.`);
      }
    } catch (err) {
      toast.apiError(err, 'Lỗi kiểm tra từ cấm');
    } finally {
      setIsCheckingBanned(false);
    }
  };

  const startEdit = () => {
    if (!content) return;
    setEditTitle(content.title);
    setEditBody(content.body);
    setEditCta(content.cta ?? '');
    setIsEditing(true);
  };

  if (isLoading) {
    return (
      <PageContainer>
        <div className="space-y-4">
          <SkeletonRows rows={3} />
          <SkeletonRows rows={5} />
        </div>
      </PageContainer>
    );
  }

  if (isError || !content) {
    return (
      <PageContainer>
        <ErrorState
          error={error}
          onRetry={() => refetch()}
        />
      </PageContainer>
    );
  }

  const canEdit = canEditContent(user, content);
  const canDelete = canDeleteContent(user, content);
  const canSubmit = canSubmitContent(user, content);
  const blockReason = reviewBlockReason(user, content);
  const canPublish = canMarkPublished(user, content, schedulesQ.data ?? []);

  return (
    <PageContainer>
      <PageHeader
        back={{ to: '/contents', label: 'Quản lý nội dung' }}
        title={
          <div className="flex flex-wrap items-center gap-3">
            <span>{content.title}</span>
            <StatusBadge kind="content" status={content.status} />
          </div>
        }
        description={
          <div className="flex flex-wrap items-center gap-3 text-xs text-fg-muted">
            <span>Chiến dịch: <Link to={`/campaigns/${content.campaign_id}`} className="font-medium text-fg hover:underline">{content.campaign.name}</Link></span>
            <span>•</span>
            <span>Kênh: <Badge tone="neutral">{content.channel.name}</Badge></span>
            <span>•</span>
            <span>Định dạng: {CONTENT_TYPE_LABEL[content.content_type]}</span>
            <span>•</span>
            <span>Nguồn: <Badge tone={content.origin === 'AI' ? 'accent' : 'neutral'}>{ORIGIN_LABEL[content.origin]}</Badge></span>
            <span>•</span>
            <span>Tác giả: {content.created_by.full_name}</span>
          </div>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => navigate(`/assistant?campaign_id=${content.campaign_id}`)}
              className="border-accent/40 bg-accent/5 hover:bg-accent/10"
            >
              <Sparkles className="h-4 w-4 text-accent" />
              Hỏi Trợ lý AI
            </Button>

            {/* Workflow actions */}
            {canSubmit && (
              <Button
                variant="primary"
                onClick={() => submitMutation.mutate()}
                loading={submitMutation.isPending}
              >
                <Send className="h-4 w-4" />
                Gửi duyệt
              </Button>
            )}

            {content.status === 'PENDING_REVIEW' && (
              <>
                {blockReason ? (
                  <div className="rounded-md bg-subtle px-3 py-1.5 text-xs text-fg-muted">
                    {blockReason}
                  </div>
                ) : (
                  <>
                    <Button variant="primary" onClick={() => setIsApproving(true)}>
                      <Check className="h-4 w-4" />
                      Duyệt bài
                    </Button>
                    <Button variant="danger" onClick={() => setIsRejecting(true)}>
                      <XCircle className="h-4 w-4" />
                      Từ chối
                    </Button>
                  </>
                )}
              </>
            )}

            {canPublish && (
              <Button variant="primary" onClick={() => setIsPublishing(true)}>
                <Globe className="h-4 w-4" />
                Đánh dấu đã đăng
              </Button>
            )}

            {content.status === 'APPROVED' && (
              <Button variant="secondary" onClick={() => setIsScheduling(true)}>
                <Calendar className="h-4 w-4" />
                Lập lịch
              </Button>
            )}

            {canEdit && !isEditing && (
              <Button variant="secondary" onClick={startEdit}>
                <Edit3 className="h-4 w-4" />
                Chỉnh sửa
              </Button>
            )}

            {canDelete && (
              <Button
                variant="ghost"
                className="text-danger hover:bg-danger/10"
                onClick={() => setIsDeleting(true)}
              >
                <Trash2 className="h-4 w-4" />
                Xoá
              </Button>
            )}
          </div>
        }
      />

      {/* Banned Keywords Alert */}
      {bannedMatches && bannedMatches.length > 0 && (
        <Callout tone="warning" icon={<AlertTriangle className="h-5 w-5" />} className="mb-6">
          <p className="font-semibold">Cảnh báo vi phạm từ cấm theo quy định thương hiệu:</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {bannedMatches.map((m) => (
              <span key={m.keyword} className="rounded bg-amber-500/20 px-2 py-0.5 text-xs font-mono font-medium">
                &ldquo;{m.keyword}&rdquo; ({m.count} lần)
              </span>
            ))}
          </div>
          <p className="mt-1 text-xs text-fg-muted">
            Vui lòng xem xét điều chỉnh các từ trên để đảm bảo quy chuẩn thương hiệu trước khi phát hành.
          </p>
        </Callout>
      )}

      {/* Published URL info banner */}
      {content.status === 'PUBLISHED' && (
        <Callout tone="success" icon={<Globe className="h-5 w-5" />} className="mb-6">
          <div>
            <p className="font-semibold">Nội dung đã được xuất bản</p>
            <div className="mt-1 flex flex-wrap items-center gap-4 text-xs">
              {content.published_at && <span>Thời gian: {formatDateTime(content.published_at)}</span>}
              {content.published_by && <span>Người xác nhận: {content.published_by.full_name}</span>}
              {content.published_url && (
                <a
                  href={content.published_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-medium underline"
                >
                  Xem bài đăng thực tế <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        </Callout>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content Area (2 cols) */}
        <div className="space-y-6 lg:col-span-2">
          {isEditing ? (
            <Card>
              <CardHeader title="Chỉnh sửa nội dung" />
              <CardBody className="space-y-4">
                <FormField label="Tiêu đề / Tiêu đề email" required>
                  {(p) => (
                    <Input
                      {...p}
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                    />
                  )}
                </FormField>

                <FormField label="Nội dung bài viết (Markdown)" required aside={<span>{editBody.length} ký tự</span>}>
                  {(p) => (
                    <Textarea
                      {...p}
                      rows={12}
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                    />
                  )}
                </FormField>

                <FormField label="Lời kêu gọi hành động (CTA)">
                  {(p) => (
                    <Input
                      {...p}
                      value={editCta}
                      onChange={(e) => setEditCta(e.target.value)}
                    />
                  )}
                </FormField>

                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="secondary" onClick={() => setIsEditing(false)}>
                    Huỷ bỏ
                  </Button>
                  <Button
                    variant="primary"
                    loading={updateMutation.isPending}
                    onClick={() => {
                      if (!editTitle.trim()) {
                        toast.error('Tiêu đề không được để trống');
                        return;
                      }
                      if (!editBody.trim()) {
                        toast.error('Nội dung không được để trống');
                        return;
                      }
                      updateMutation.mutate({
                        title: editTitle.trim(),
                        body: editBody.trim(),
                        cta: editCta.trim() || null,
                      });
                    }}
                  >
                    Lưu nội dung
                  </Button>
                </div>
              </CardBody>
            </Card>
          ) : (
            <Card>
              <CardHeader
                title="Bản xem trước nội dung"
                actions={
                  <Button variant="ghost" size="sm" onClick={handleCheckBanned} loading={isCheckingBanned}>
                    <ShieldCheck className="h-4 w-4" />
                    Kiểm tra từ cấm
                  </Button>
                }
              />
              <CardBody className="space-y-6">
                <div>
                  <h3 className="text-xl font-bold tracking-tight text-fg">{content.title}</h3>
                  <div className="mt-1 flex items-center gap-2 text-xs text-fg-subtle">
                    <span>Độ dài: {content.body.length} ký tự</span>
                    <span>•</span>
                    <span>Khoảng {Math.ceil(content.body.split(/\s+/).length / 200)} phút đọc</span>
                  </div>
                </div>

                <div className="prose prose-stone max-w-none text-sm dark:prose-invert">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.body}</ReactMarkdown>
                </div>

                {content.cta && (
                  <div className="rounded-lg border border-accent/20 bg-accent/5 p-4 text-center">
                    <p className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Lời kêu gọi hành động (CTA)</p>
                    <p className="mt-1 text-base font-semibold text-accent">{content.cta}</p>
                  </div>
                )}
              </CardBody>
            </Card>
          )}

          {/* Schedules for this content */}
          <Card>
            <CardHeader
              title="Lịch đăng bài viết này"
              actions={
                content.status === 'APPROVED' ? (
                  <Button variant="secondary" size="sm" onClick={() => setIsScheduling(true)}>
                    <Calendar className="h-4 w-4" />
                    Lập lịch đăng
                  </Button>
                ) : null
              }
            />
            {schedulesQ.isLoading ? (
              <div className="p-4">
                <SkeletonRows rows={2} />
              </div>
            ) : !schedulesQ.data || schedulesQ.data.length === 0 ? (
              <div className="p-6 text-center text-xs text-fg-muted">
                Bài viết này chưa được xếp vào lịch đăng.
              </div>
            ) : (
              <Table>
                <THead>
                  <TR>
                    <TH>Thời điểm</TH>
                    <TH>Người phụ trách</TH>
                    <TH>Trạng thái</TH>
                    <TH>Ghi chú</TH>
                  </TR>
                </THead>
                <TBody>
                  {schedulesQ.data.map((sch: Schedule) => (
                    <TR key={sch.id}>
                      <TD className="text-xs font-medium text-fg">{formatDateTime(sch.scheduled_at)}</TD>
                      <TD className="text-xs text-fg-muted">{sch.assignee?.full_name ?? '—'}</TD>
                      <TD>
                        <StatusBadge kind="schedule" status={sch.status} />
                      </TD>
                      <TD className="text-xs text-fg-subtle">{sch.note || '—'}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </Card>
        </div>

        {/* Sidebar: Details & Review History (1 col) */}
        <div className="space-y-6">
          <Card>
            <CardHeader title="Thông tin chi tiết" />
            <CardBody className="space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-fg-muted">Trạng thái:</span>
                <StatusBadge kind="content" status={content.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-fg-muted">Nguồn gốc:</span>
                <span className="font-medium text-fg">{ORIGIN_LABEL[content.origin]}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-fg-muted">Kênh đăng:</span>
                <span className="font-medium text-fg">{content.channel.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-fg-muted">Người tạo:</span>
                <span className="font-medium text-fg">{content.created_by.full_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-fg-muted">Ngày tạo:</span>
                <span className="font-medium text-fg">{formatDateTime(content.created_at)}</span>
              </div>
              {content.published_at && (
                <div className="flex justify-between">
                  <span className="text-fg-muted">Đã đăng lúc:</span>
                  <span className="font-medium text-fg">{formatDateTime(content.published_at)}</span>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Review History */}
          <Card>
            <CardHeader
              title={
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  <span>Lịch sử kiểm duyệt</span>
                </div>
              }
            />
            <CardBody>
              {reviewsQ.isLoading ? (
                <SkeletonRows rows={3} />
              ) : !reviewsQ.data || reviewsQ.data.length === 0 ? (
                <p className="py-4 text-center text-xs text-fg-muted">Chưa có lượt kiểm duyệt nào.</p>
              ) : (
                <div className="space-y-4">
                  {reviewsQ.data.map((rev) => (
                    <div key={rev.id} className="rounded-lg border border-border p-3 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-fg">{rev.reviewer.full_name}</span>
                        <Badge tone={rev.decision === 'APPROVED' ? 'success' : 'danger'}>
                          {REVIEW_DECISION_LABEL[rev.decision]}
                        </Badge>
                      </div>
                      <p className="mt-1 text-fg-subtle">{formatDateTime(rev.created_at)}</p>
                      {rev.comment && (
                        <p className="mt-2 rounded bg-subtle p-2 text-fg whitespace-pre-line">
                          {rev.comment}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </div>

      {/* Approve Dialog */}
      <Dialog
        open={isApproving}
        onClose={() => setIsApproving(false)}
        title="Xác nhận phê duyệt nội dung"
        size="md"
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-muted">
            Bài viết sẽ chuyển sang trạng thái <strong>Đã duyệt (APPROVED)</strong> và sẵn sàng để lên lịch đăng hoặc xuất bản.
          </p>
          <FormField label="Ghi chú phản hồi (không bắt buộc)">
            {(p) => (
              <Textarea
                {...p}
                rows={3}
                value={approveComment}
                onChange={(e) => setApproveComment(e.target.value)}
                placeholder="Lời dặn dò hoặc phản hồi cho tác giả..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsApproving(false)}>
              Huỷ
            </Button>
            <Button variant="primary" loading={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
              Xác nhận duyệt
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog
        open={isRejecting}
        onClose={() => setIsRejecting(false)}
        title="Từ chối phê duyệt nội dung"
        size="md"
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-muted">
            Vui lòng nhập lý do từ chối để tác giả có thể chỉnh sửa và hoàn thiện lại bài viết.
          </p>
          <FormField label="Lý do từ chối" required>
            {(p) => (
              <Textarea
                {...p}
                rows={4}
                value={rejectComment}
                onChange={(e) => setRejectComment(e.target.value)}
                placeholder="Nêu rõ điểm cần chỉnh sửa theo quy định thương hiệu..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsRejecting(false)}>
              Huỷ
            </Button>
            <Button
              variant="danger"
              disabled={!rejectComment.trim()}
              loading={rejectMutation.isPending}
              onClick={() => rejectMutation.mutate()}
            >
              Xác nhận từ chối
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Mark Published Dialog */}
      <Dialog
        open={isPublishing}
        onClose={() => setIsPublishing(false)}
        title="Xác nhận đã đăng bài viết"
        size="md"
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-muted">
            Đánh dấu nội dung đã được phát hành thực tế. Trạng thái sẽ chuyển thành <strong>Đã đăng (PUBLISHED)</strong> và hoàn tất các lịch đăng liên quan.
          </p>
          <FormField label="Đường dẫn bài đăng thực tế (URL)">
            {(p) => (
              <Input
                {...p}
                type="url"
                value={publishedUrl}
                onChange={(e) => setPublishedUrl(e.target.value)}
                placeholder="https://facebook.com/... hoặc https://tiktok.com/..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsPublishing(false)}>
              Huỷ
            </Button>
            <Button variant="primary" loading={publishMutation.isPending} onClick={() => publishMutation.mutate()}>
              Xác nhận đã đăng
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Schedule Dialog */}
      <Dialog
        open={isScheduling}
        onClose={() => setIsScheduling(false)}
        title="Lập lịch đăng bài"
        size="md"
      >
        <div className="space-y-4">
          <FormField label="Thời điểm đăng" required>
            {(p) => (
              <Input
                {...p}
                type="datetime-local"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
              />
            )}
          </FormField>
          <FormField label="Ghi chú thêm">
            {(p) => (
              <Input
                {...p}
                value={scheduleNote}
                onChange={(e) => setScheduleNote(e.target.value)}
                placeholder="Ghi chú dành cho người thực hiện..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsScheduling(false)}>
              Huỷ
            </Button>
            <Button
              variant="primary"
              disabled={!scheduleTime}
              loading={scheduleMutation.isPending}
              onClick={() => scheduleMutation.mutate()}
            >
              Lên lịch
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        open={isDeleting}
        title={`Xoá bài viết "${content.title}"`}
        confirmLabel="Xác nhận xoá"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setIsDeleting(false)}
        onConfirm={() => deleteMutation.mutate()}
      >
        <p className="text-sm text-fg-muted">
          Bạn có chắc chắn muốn xoá bài viết này? Hành động này không thể hoàn tác.
        </p>
      </ConfirmDialog>
    </PageContainer>
  );
}
