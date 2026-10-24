import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Check,
  XCircle,
  Eye,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Button,
  Badge,
  Card,
  CardHeader,
  CardBody,
  PageHeader,
  Dialog,
  FormField,
  Textarea,
  useToast,
  Pagination,
  EmptyState,
  ErrorState,
  SkeletonRows,
  Callout,
  Select,
} from '@/components/ui';
import { contentsApi, campaignsApi } from '@/lib/api/endpoints';
import { useAuth } from '@/lib/auth';
import { reviewBlockReason } from '@/lib/permissions';
import { useChannels, useDocumentTitle } from '@/lib/hooks';
import { formatDateTime } from '@/lib/format';
import { CONTENT_TYPE_LABEL, ORIGIN_LABEL } from '@/lib/labels';
import type { Content, ContentFilters } from '@/lib/types';

export default function ReviewsPage() {
  useDocumentTitle('Hàng đợi duyệt nội dung');
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const toast = useToast();

  const [campaignFilter, setCampaignFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Expanded cards
  const [expandedIds, setExpandedIds] = useState<Record<number, boolean>>({});

  // Approve dialog
  const [approvingItem, setApprovingItem] = useState<Content | null>(null);
  const [approveComment, setApproveComment] = useState('');

  // Reject dialog
  const [rejectingItem, setRejectingItem] = useState<Content | null>(null);
  const [rejectComment, setRejectComment] = useState('');

  const channelsQ = useChannels();
  const campaignsListQ = useQuery({
    queryKey: ['campaigns', { page_size: 100 }],
    queryFn: () => campaignsApi.list({ page_size: 100 }),
    staleTime: 5 * 60_000,
  });

  const filters: ContentFilters = {
    status: 'PENDING_REVIEW',
    campaign_id: campaignFilter ? Number(campaignFilter) : undefined,
    channel_id: channelFilter ? Number(channelFilter) : undefined,
    sort: '-created_at',
    page,
    page_size: pageSize,
  };

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['contents', filters],
    queryFn: () => contentsApi.list(filters),
  });

  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const approveMutation = useMutation({
    mutationFn: ({ id, comment }: { id: number; comment?: string }) =>
      contentsApi.approve(id, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      toast.success('Đã phê duyệt nội dung');
      setApprovingItem(null);
      setApproveComment('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi phê duyệt');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, comment }: { id: number; comment: string }) =>
      contentsApi.reject(id, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      toast.success('Đã từ chối nội dung');
      setRejectingItem(null);
      setRejectComment('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi từ chối');
    },
  });

  return (
    <PageContainer>
      <PageHeader
        title="Hàng đợi duyệt nội dung"
        description="Dành cho Quản lý marketing xem xét, phê duyệt hoặc yêu cầu chỉnh sửa các bài viết trước khi xuất bản."
      />

      {/* Filter bar */}
      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface p-4">
        <div className="w-64">
          <Select
            value={campaignFilter}
            onChange={(e) => {
              setCampaignFilter(e.target.value);
              setPage(1);
            }}
            options={[
              { value: '', label: 'Tất cả chiến dịch' },
              ...(campaignsListQ.data?.items ?? []).map((c) => ({ value: String(c.id), label: c.name })),
            ]}
          />
        </div>
        <div className="w-52">
          <Select
            value={channelFilter}
            onChange={(e) => {
              setChannelFilter(e.target.value);
              setPage(1);
            }}
            options={[
              { value: '', label: 'Tất cả kênh' },
              ...(channelsQ.data ?? []).map((ch) => ({ value: String(ch.id), label: ch.name })),
            ]}
          />
        </div>
        {(campaignFilter || channelFilter) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setCampaignFilter('');
              setChannelFilter('');
              setPage(1);
            }}
          >
            Đặt lại bộ lọc
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <SkeletonRows rows={4} />
        </div>
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<ShieldAlert className="h-8 w-8" />}
          title="Không có nội dung nào chờ duyệt"
          description={
            campaignFilter || channelFilter
              ? 'Thử điều chỉnh lại bộ lọc để tìm kiếm các nội dung khác.'
              : 'Tuyệt vời! Hiện tại tất cả bài viết gửi lên đã được xem xét hoàn tất.'
          }
        />
      ) : (
        <div className="space-y-4">
          {data.items.map((item) => {
            const isExpanded = !!expandedIds[item.id];
            const blockReason = reviewBlockReason(user, item);

            return (
              <Card key={item.id} className="overflow-hidden">
                <CardHeader
                  title={
                    <div className="flex flex-wrap items-center gap-3">
                      <Link
                        to={`/contents/${item.id}`}
                        className="text-base font-semibold text-fg hover:underline"
                      >
                        {item.title}
                      </Link>
                      <Badge tone="neutral">{item.channel.name}</Badge>
                      <Badge tone={item.origin === 'AI' ? 'accent' : 'neutral'}>
                        {ORIGIN_LABEL[item.origin]}
                      </Badge>
                      <span className="text-xs text-fg-muted">
                        {CONTENT_TYPE_LABEL[item.content_type]}
                      </span>
                    </div>
                  }
                  description={
                    <div className="flex flex-wrap items-center gap-3 text-xs text-fg-muted">
                      <span>Chiến dịch: <Link to={`/campaigns/${item.campaign_id}`} className="font-medium text-fg hover:underline">{item.campaign.name}</Link></span>
                      <span>•</span>
                      <span>Người tạo: <span className="font-medium text-fg">{item.created_by.full_name}</span></span>
                      <span>•</span>
                      <span>Gửi lúc: {formatDateTime(item.created_at)}</span>
                    </div>
                  }
                  actions={
                    <div className="flex flex-wrap items-center gap-2">
                      <Link to={`/contents/${item.id}`}>
                        <Button variant="ghost" size="sm">
                          <Eye className="h-4 w-4" />
                          Xem chi tiết
                        </Button>
                      </Link>

                      {blockReason ? (
                        <span className="rounded bg-subtle px-2.5 py-1 text-xs text-fg-muted">
                          {blockReason}
                        </span>
                      ) : (
                        <>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => {
                              setApprovingItem(item);
                              setApproveComment('');
                            }}
                          >
                            <Check className="h-4 w-4" />
                            Duyệt
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => {
                              setRejectingItem(item);
                              setRejectComment('');
                            }}
                          >
                            <XCircle className="h-4 w-4" />
                            Từ chối
                          </Button>
                        </>
                      )}
                    </div>
                  }
                />

                <CardBody className="border-t border-border bg-canvas/30 py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-fg-muted">Nội dung bài viết:</span>
                    <Button variant="ghost" size="sm" onClick={() => toggleExpand(item.id)}>
                      {isExpanded ? (
                        <>
                          Thu gọn <ChevronUp className="h-3 w-3" />
                        </>
                      ) : (
                        <>
                          Xem toàn văn <ChevronDown className="h-3 w-3" />
                        </>
                      )}
                    </Button>
                  </div>

                  <div className={`mt-2 text-sm text-fg ${isExpanded ? '' : 'line-clamp-3'}`}>
                    <div className="prose prose-stone max-w-none text-xs dark:prose-invert">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.body}</ReactMarkdown>
                    </div>
                  </div>

                  {item.cta && (
                    <div className="mt-3 rounded border border-accent/20 bg-accent/5 px-3 py-1.5 text-xs">
                      <span className="font-semibold text-fg-muted">CTA: </span>
                      <span className="font-medium text-accent">{item.cta}</span>
                    </div>
                  )}
                </CardBody>
              </Card>
            );
          })}

          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            onPageChange={setPage}
          />
        </div>
      )}

      {/* Approve Dialog */}
      <Dialog
        open={!!approvingItem}
        onClose={() => setApprovingItem(null)}
        title={`Duyệt bài: "${approvingItem?.title}"`}
        size="md"
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-muted">
            Bài viết sẽ được duyệt và chuyển sang trạng thái <strong>Đã duyệt (APPROVED)</strong>.
          </p>
          <FormField label="Ghi chú phản hồi (tuỳ chọn)">
            {(p) => (
              <Textarea
                {...p}
                rows={3}
                value={approveComment}
                onChange={(e) => setApproveComment(e.target.value)}
                placeholder="Ghi chú thêm cho tác giả..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setApprovingItem(null)}>
              Huỷ
            </Button>
            <Button
              variant="primary"
              loading={approveMutation.isPending}
              onClick={() => {
                if (approvingItem) {
                  approveMutation.mutate({
                    id: approvingItem.id,
                    comment: approveComment.trim() || undefined,
                  });
                }
              }}
            >
              Xác nhận duyệt
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog
        open={!!rejectingItem}
        onClose={() => setRejectingItem(null)}
        title={`Từ chối: "${rejectingItem?.title}"`}
        size="md"
      >
        <div className="space-y-4">
          <Callout tone="danger">
            Bắt buộc nhập lý do từ chối để người soạn nội dung biết cần chỉnh sửa điểm nào.
          </Callout>
          <FormField label="Lý do từ chối" required>
            {(p) => (
              <Textarea
                {...p}
                rows={4}
                value={rejectComment}
                onChange={(e) => setRejectComment(e.target.value)}
                placeholder="Nêu rõ lý do hoặc điểm cần sửa..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setRejectingItem(null)}>
              Huỷ
            </Button>
            <Button
              variant="danger"
              disabled={!rejectComment.trim()}
              loading={rejectMutation.isPending}
              onClick={() => {
                if (rejectingItem && rejectComment.trim()) {
                  rejectMutation.mutate({
                    id: rejectingItem.id,
                    comment: rejectComment.trim(),
                  });
                }
              }}
            >
              Xác nhận từ chối
            </Button>
          </div>
        </div>
      </Dialog>
    </PageContainer>
  );
}
