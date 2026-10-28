import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Eye, Edit3, Trash2, Filter } from 'lucide-react';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Button,
  IconButton,
  Input,
  Select,
  Table,
  THead,
  TBody,
  TR,
  TH,
  TD,
  StatusBadge,
  Badge,
  Pagination,
  EmptyState,
  ErrorState,
  SkeletonRows,
  PageHeader,
  ConfirmDialog,
  Dialog,
  FormField,
  Textarea,
  useToast,
  Callout,
} from '@/components/ui';
import { contentsApi, campaignsApi } from '@/lib/api/endpoints';
import { toApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth';
import { canEditContent, canDeleteContent } from '@/lib/permissions';
import { useChannels, useUserOptions, useDebounced, useDocumentTitle } from '@/lib/hooks';
import { formatDate } from '@/lib/format';
import {
  CONTENT_STATUS_LABEL,
  CONTENT_TYPE_LABEL,
  GOAL_KPI_META,
  GOAL_LABEL,
  GOAL_TONE,
  ORIGIN_LABEL,
  buildGoalContentDraft,
} from '@/lib/labels';
import type {
  Content,
  ContentFilters,
  ContentOrigin,
  ContentStatus,
  ContentType,
} from '@/lib/types';

export default function ContentsPage() {
  useDocumentTitle('Nội dung');
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const toast = useToast();

  // Filters state
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounced(searchInput, 350);
  const [statusFilter, setStatusFilter] = useState<string>(params.get('status') || '');
  const [campaignFilter, setCampaignFilter] = useState<string>(params.get('campaign_id') || '');
  const [channelFilter, setChannelFilter] = useState<string>(params.get('channel_id') || '');
  const [originFilter, setOriginFilter] = useState<string>('');
  const [createdByFilter, setCreatedByFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('-created_at');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  // Create content dialog state
  const [isCreating, setIsCreating] = useState(false);
  const [newCampaignId, setNewCampaignId] = useState<number | ''>('');
  const [newChannelId, setNewChannelId] = useState<number | ''>('');
  const [newContentType, setNewContentType] = useState<ContentType>('SOCIAL_POST');
  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');
  const [newCta, setNewCta] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

  // Delete dialog state
  const [deletingContent, setDeletingContent] = useState<Content | null>(null);

  const channelsQ = useChannels();
  const usersOpt = useUserOptions();
  const campaignsListQ = useQuery({
    queryKey: ['campaigns', { page_size: 100 }],
    queryFn: () => campaignsApi.list({ page_size: 100 }),
    staleTime: 5 * 60_000,
  });

  const filters: ContentFilters = {
    q: debouncedSearch || undefined,
    status: (statusFilter as ContentStatus) || undefined,
    campaign_id: campaignFilter ? Number(campaignFilter) : undefined,
    channel_id: channelFilter ? Number(channelFilter) : undefined,
    origin: (originFilter as ContentOrigin) || undefined,
    created_by: createdByFilter ? Number(createdByFilter) : undefined,
    sort: sortBy || undefined,
    page,
    page_size: pageSize,
  };

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['contents', filters],
    queryFn: () => contentsApi.list(filters),
  });

  const createMutation = useMutation({
    mutationFn: contentsApi.create,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      toast.success('Tạo bài viết thành công', `Bài viết "${res.title}" đã được lưu nháp.`);
      setIsCreating(false);
      setNewTitle('');
      setNewBody('');
      setNewCta('');
      setCreateError(null);
      navigate(`/contents/${res.id}`);
    },
    onError: (err) => {
      setCreateError(toApiError(err).message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => contentsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      toast.success('Đã xoá nội dung');
      setDeletingContent(null);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi xoá bài viết');
    },
  });

  // Available channels for the selected campaign
  const campaignsMap = new Map((campaignsListQ.data?.items ?? []).map((c) => [c.id, c]));
  const selectedCampaignChannels =
    campaignsListQ.data?.items.find((c) => c.id === Number(newCampaignId))?.channels ?? [];
  const selectedCampaignDetailQ = useQuery({
    queryKey: ['campaigns', Number(newCampaignId)],
    queryFn: () => campaignsApi.get(Number(newCampaignId)),
    enabled: isCreating && Boolean(newCampaignId),
  });
  const selectedChannelRule = (channelsQ.data ?? []).find((ch) => ch.id === Number(newChannelId));

  return (
    <PageContainer>
      <PageHeader
        title="Quản lý nội dung"
        description="Soạn thảo, kiểm duyệt và quản lý các bài đăng mạng xã hội, email, kịch bản quảng cáo."
        actions={
          <Button variant="primary" onClick={() => setIsCreating(true)}>
            <Plus className="h-4 w-4" />
            Soạn nội dung mới
          </Button>
        }
      />

      {/* Filter bar */}
      <div className="mb-6 space-y-3 rounded-lg border border-border bg-surface p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Tìm theo tiêu đề bài viết..."
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              setPage(1);
            }}
          />
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            options={[
              { value: '', label: 'Tất cả trạng thái' },
              { value: 'DRAFT', label: CONTENT_STATUS_LABEL.DRAFT },
              { value: 'PENDING_REVIEW', label: CONTENT_STATUS_LABEL.PENDING_REVIEW },
              { value: 'APPROVED', label: CONTENT_STATUS_LABEL.APPROVED },
              { value: 'REJECTED', label: CONTENT_STATUS_LABEL.REJECTED },
              { value: 'PUBLISHED', label: CONTENT_STATUS_LABEL.PUBLISHED },
            ]}
          />
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

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-40">
              <Select
                value={originFilter}
                onChange={(e) => {
                  setOriginFilter(e.target.value);
                  setPage(1);
                }}
                options={[
                  { value: '', label: 'Tất cả nguồn' },
                  { value: 'MANUAL', label: ORIGIN_LABEL.MANUAL },
                  { value: 'AI', label: ORIGIN_LABEL.AI },
                ]}
              />
            </div>
            {usersOpt.enabled && (
              <div className="w-48">
                <Select
                  value={createdByFilter}
                  onChange={(e) => {
                    setCreatedByFilter(e.target.value);
                    setPage(1);
                  }}
                  options={[
                    { value: '', label: 'Tất cả người tạo' },
                    ...usersOpt.users.map((u) => ({ value: String(u.id), label: u.full_name })),
                  ]}
                />
              </div>
            )}
            <div className="w-44">
              <Select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setPage(1);
                }}
                options={[
                  { value: '-created_at', label: 'Mới nhất' },
                  { value: 'created_at', label: 'Cũ nhất' },
                  { value: 'title', label: 'Tiêu đề A-Z' },
                ]}
              />
            </div>
          </div>
          {(searchInput || statusFilter || campaignFilter || channelFilter || originFilter || createdByFilter) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchInput('');
                setStatusFilter('');
                setCampaignFilter('');
                setChannelFilter('');
                setOriginFilter('');
                setCreatedByFilter('');
                setPage(1);
              }}
            >
              Đặt lại bộ lọc
            </Button>
          )}
        </div>
      </div>

      {/* Main Table */}
      {isLoading ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <SkeletonRows rows={6} />
        </div>
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<Filter className="h-8 w-8" />}
          title="Không tìm thấy nội dung nào"
          description={
            searchInput || statusFilter || campaignFilter || channelFilter || originFilter
              ? 'Thử thay đổi hoặc xoá các điều kiện lọc để tìm kiếm rộng hơn.'
              : 'Chưa có nội dung nào được tạo trong hệ thống.'
          }
          action={
            <Button variant="primary" onClick={() => setIsCreating(true)}>
              <Plus className="h-4 w-4" />
              Soạn nội dung mới
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-sm">
            <Table>
              <THead>
                <TR>
                  <TH>Tiêu đề</TH>
                  <TH>Chiến dịch</TH>
                  <TH>Kênh</TH>
                  <TH>Định dạng</TH>
                  <TH>Nguồn gốc</TH>
                  <TH>Trạng thái</TH>
                  <TH>Người tạo</TH>
                  <TH>Ngày tạo</TH>
                  <TH className="text-right">Thao tác</TH>
                </TR>
              </THead>
              <TBody>
                {data.items.map((item) => {
                  const canEdit = canEditContent(user, item);
                  const canDelete = canDeleteContent(user, item);

                  return (
                    <TR key={item.id}>
                      <TD className="min-w-[220px] max-w-[300px]">
                        <Link
                          to={`/contents/${item.id}`}
                          className="line-clamp-1 font-medium text-fg hover:text-accent hover:underline"
                          title={item.title}
                        >
                          {item.title}
                        </Link>
                      </TD>
                      <TD className="min-w-[180px] max-w-[240px]">
                        <div className="space-y-1">
                          <Link
                            to={`/campaigns/${item.campaign_id}`}
                            className="line-clamp-1 text-xs font-medium text-fg hover:underline"
                            title={item.campaign.name}
                          >
                            {item.campaign.name}
                          </Link>
                          {campaignsMap.get(item.campaign_id) && (
                            <div>
                              <Badge tone={GOAL_TONE[campaignsMap.get(item.campaign_id)!.goal]}>
                                {GOAL_LABEL[campaignsMap.get(item.campaign_id)!.goal]}
                              </Badge>
                            </div>
                          )}
                        </div>
                      </TD>
                      <TD className="whitespace-nowrap">
                        <Badge tone="neutral">
                          {item.channel.name}
                        </Badge>
                      </TD>
                      <TD className="whitespace-nowrap text-xs text-fg-muted">{CONTENT_TYPE_LABEL[item.content_type]}</TD>
                      <TD className="whitespace-nowrap">
                        <Badge tone={item.origin === 'AI' ? 'accent' : 'neutral'}>
                          {ORIGIN_LABEL[item.origin]}
                        </Badge>
                      </TD>
                      <TD className="whitespace-nowrap">
                        <StatusBadge kind="content" status={item.status} />
                      </TD>
                      <TD className="whitespace-nowrap text-xs text-fg-muted">{item.created_by.full_name}</TD>
                      <TD className="whitespace-nowrap text-xs text-fg-muted tabular-nums">{formatDate(item.created_at)}</TD>
                      <TD className="whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-1 whitespace-nowrap">
                          <IconButton
                            label="Xem chi tiết"
                            size="sm"
                            variant="ghost"
                            onClick={() => navigate(`/contents/${item.id}`)}
                          >
                            <Eye className="h-4 w-4" />
                          </IconButton>
                          {canEdit && (
                            <IconButton
                              label="Chỉnh sửa"
                              size="sm"
                              variant="ghost"
                              onClick={() => navigate(`/contents/${item.id}`)}
                            >
                              <Edit3 className="h-4 w-4" />
                            </IconButton>
                          )}
                          {canDelete && (
                            <IconButton
                              label="Xoá bài viết"
                              size="sm"
                              variant="ghost"
                              className="text-danger hover:bg-danger/10"
                              onClick={() => setDeletingContent(item)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </IconButton>
                          )}
                        </div>
                      </TD>
                    </TR>
                  );
                })}
              </TBody>
            </Table>
          </div>

          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            onPageChange={setPage}
          />
        </div>
      )}

      {/* Create Content Dialog */}
      <Dialog
        open={isCreating}
        onClose={() => setIsCreating(false)}
        title="Soạn thảo nội dung mới"
        size="lg"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!newCampaignId) {
              setCreateError('Vui lòng chọn chiến dịch.');
              return;
            }
            if (!newChannelId) {
              setCreateError('Vui lòng chọn kênh triển khai.');
              return;
            }
            if (!newTitle.trim()) {
              setCreateError('Vui lòng nhập tiêu đề bài viết.');
              return;
            }
            if (!newBody.trim()) {
              setCreateError('Vui lòng nhập nội dung chi tiết.');
              return;
            }
            createMutation.mutate({
              campaign_id: Number(newCampaignId),
              channel_id: Number(newChannelId),
              content_type: newContentType,
              title: newTitle.trim(),
              body: newBody.trim(),
              cta: newCta.trim() || null,
            });
          }}
          className="space-y-4"
        >
          {createError && <Callout tone="danger">{createError}</Callout>}

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Chiến dịch" required>
              {(p) => (
                <Select
                  {...p}
                  value={newCampaignId}
                  onChange={(e) => {
                    setNewCampaignId(e.target.value ? Number(e.target.value) : '');
                    setNewChannelId('');
                  }}
                  options={[
                    { value: '', label: 'Chọn chiến dịch...' },
                    ...(campaignsListQ.data?.items ?? []).map((c) => ({
                      value: String(c.id),
                      label: `${c.name} (${GOAL_LABEL[c.goal]})`,
                    })),
                  ]}
                />
              )}
            </FormField>

            <FormField label="Kênh triển khai" required>
              {(p) => (
                <Select
                  {...p}
                  disabled={!newCampaignId}
                  value={newChannelId}
                  onChange={(e) => setNewChannelId(e.target.value ? Number(e.target.value) : '')}
                  options={[
                    { value: '', label: newCampaignId ? 'Chọn kênh...' : 'Vui lòng chọn chiến dịch trước' },
                    ...(selectedCampaignChannels.length > 0
                      ? selectedCampaignChannels.map((ch) => ({ value: String(ch.id), label: ch.name }))
                      : (channelsQ.data ?? []).map((ch) => ({ value: String(ch.id), label: ch.name }))),
                  ]}
                />
              )}
            </FormField>
          </div>

          {selectedCampaignDetailQ.data && (
            <div className="rounded-md border border-border bg-subtle/60 p-3 text-xs space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-fg">Định hướng chiến dịch:</span>
                  <Badge tone={GOAL_TONE[selectedCampaignDetailQ.data.goal]}>
                    {GOAL_LABEL[selectedCampaignDetailQ.data.goal]}
                  </Badge>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    const draft = buildGoalContentDraft(selectedCampaignDetailQ.data!);
                    setNewTitle(draft.title);
                    setNewBody(draft.body);
                    setNewCta(draft.cta);
                  }}
                >
                  Điền khung sườn theo mục tiêu
                </Button>
              </div>
              <p className="text-fg-muted">
                <strong className="text-fg">Chỉ tiêu:</strong> {selectedCampaignDetailQ.data.objective} ·{' '}
                <strong className="text-fg">Sản phẩm:</strong> {selectedCampaignDetailQ.data.product}
              </p>
              {selectedCampaignDetailQ.data.key_message && (
                <p className="text-fg-muted">
                  <strong className="text-fg">Thông điệp cốt lõi:</strong> &ldquo;{selectedCampaignDetailQ.data.key_message}&rdquo;
                </p>
              )}
              <p className="text-fg-muted">
                <strong className="text-fg">Gợi ý triển khai:</strong>{' '}
                {GOAL_KPI_META[selectedCampaignDetailQ.data.goal].contentDirection}
              </p>
              {selectedChannelRule?.format_rules && (
                <p className="text-fg-muted">
                  <strong className="text-fg">Quy chuẩn kênh ({selectedChannelRule.name}):</strong>{' '}
                  {selectedChannelRule.format_rules}
                </p>
              )}
            </div>
          )}

          <FormField label="Định dạng nội dung" required>
            {(p) => (
              <Select
                {...p}
                value={newContentType}
                onChange={(e) => setNewContentType(e.target.value as ContentType)}
                options={[
                  { value: 'SOCIAL_POST', label: CONTENT_TYPE_LABEL.SOCIAL_POST },
                  { value: 'EMAIL', label: CONTENT_TYPE_LABEL.EMAIL },
                  { value: 'AD_COPY', label: CONTENT_TYPE_LABEL.AD_COPY },
                  { value: 'VIDEO_SCRIPT', label: CONTENT_TYPE_LABEL.VIDEO_SCRIPT },
                  { value: 'OTHER', label: CONTENT_TYPE_LABEL.OTHER },
                ]}
              />
            )}
          </FormField>

          <FormField label="Tiêu đề / Chủ đề email" required>
            {(p) => (
              <Input
                {...p}
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Nhập tiêu đề hoặc dòng chủ đề bài viết..."
              />
            )}
          </FormField>

          <FormField label="Nội dung chính" required>
            {(p) => (
              <Textarea
                {...p}
                rows={6}
                value={newBody}
                onChange={(e) => setNewBody(e.target.value)}
                placeholder="Soạn nội dung bài đăng (hỗ trợ định dạng Markdown)..."
              />
            )}
          </FormField>

          <FormField label="Lời kêu gọi hành động (CTA)">
            {(p) => (
              <Input
                {...p}
                value={newCta}
                onChange={(e) => setNewCta(e.target.value)}
                placeholder="Ví dụ: Đặt mua ngay, Tìm hiểu thêm..."
              />
            )}
          </FormField>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" type="button" onClick={() => setIsCreating(false)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={createMutation.isPending}>
              Lưu bản nháp
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Delete Content Dialog */}
      <ConfirmDialog
        open={!!deletingContent}
        title={`Xoá bài viết "${deletingContent?.title}"`}
        confirmLabel="Xác nhận xoá"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setDeletingContent(null)}
        onConfirm={() => {
          if (deletingContent) deleteMutation.mutate(deletingContent.id);
        }}
      >
        <p className="text-sm text-fg-muted">
          Bạn có chắc chắn muốn xoá bản nháp bài viết này? Hành động này không thể hoàn tác.
        </p>
      </ConfirmDialog>
    </PageContainer>
  );
}
