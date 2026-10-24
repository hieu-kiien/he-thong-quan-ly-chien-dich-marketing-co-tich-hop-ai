import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Filter, Trash2, Edit3, Eye, AlertCircle } from 'lucide-react';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Button,
  IconButton,
  Input,
  Select,
  DateRangePicker,
  type DateRange,
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
  Drawer,
  useToast,
  Callout,
} from '@/components/ui';
import { campaignsApi } from '@/lib/api/endpoints';
import { toApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth';
import { canEditCampaign } from '@/lib/permissions';
import { useChannels, useUserOptions, useDebounced, useDocumentTitle } from '@/lib/hooks';
import { formatDate, formatMoney } from '@/lib/format';
import { CAMPAIGN_STATUS_LABEL, GOAL_LABEL } from '@/lib/labels';
import type { CampaignFilters, CampaignGoal, CampaignListItem, CampaignStatus, CampaignInput } from '@/lib/types';
import { CampaignForm } from './CampaignForm';

export default function CampaignsPage() {
  useDocumentTitle('Chiến dịch');
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const toast = useToast();

  // Filters state
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounced(searchInput, 350);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [goalFilter, setGoalFilter] = useState<string>('');
  const [channelFilter, setChannelFilter] = useState<string>('');
  const [ownerFilter, setOwnerFilter] = useState<string>('');
  const [dateRange, setDateRange] = useState<DateRange>({ from: '', to: '' });
  const [sortBy, setSortBy] = useState<string>('-created_at');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  // Edit Drawer & Delete dialog state
  const [editingCampaignId, setEditingCampaignId] = useState<number | null>(null);
  const [deletingCampaign, setDeletingCampaign] = useState<CampaignListItem | null>(null);
  const [deleteConflictError, setDeleteConflictError] = useState<string | null>(null);

  const channelsQ = useChannels();
  const usersOpt = useUserOptions();

  const filters: CampaignFilters = {
    q: debouncedSearch || undefined,
    status: (statusFilter as CampaignStatus) || undefined,
    goal: (goalFilter as CampaignGoal) || undefined,
    channel_id: channelFilter ? Number(channelFilter) : undefined,
    owner_id: ownerFilter ? Number(ownerFilter) : undefined,
    date_from: dateRange.from || undefined,
    date_to: dateRange.to || undefined,
    sort: sortBy || undefined,
    page,
    page_size: pageSize,
  };

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['campaigns', filters],
    queryFn: () => campaignsApi.list(filters),
  });

  // Query for editing campaign details in Drawer
  const editingCampaignQ = useQuery({
    queryKey: ['campaigns', editingCampaignId],
    queryFn: () => (editingCampaignId ? campaignsApi.get(editingCampaignId) : null),
    enabled: !!editingCampaignId,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<CampaignInput> }) => campaignsApi.update(id, body),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Cập nhật thành công', `Chiến dịch "${updated.name}" đã được cập nhật.`);
      setEditingCampaignId(null);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi cập nhật chiến dịch');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Đã xoá chiến dịch');
      setDeletingCampaign(null);
      setDeleteConflictError(null);
    },
    onError: (err) => {
      const apiErr = toApiError(err);
      if (apiErr.code === 'CAMPAIGN_HAS_DATA' || apiErr.status === 409) {
        setDeleteConflictError(
          'Chiến dịch đã có nội dung hoặc số liệu phát sinh, không thể xoá hoàn toàn. Bạn có thể chuyển trạng thái sang "Đã huỷ".'
        );
      } else {
        toast.apiError(err, 'Lỗi xoá chiến dịch');
      }
    },
  });

  const cancelCampaignMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.update(id, { status: 'CANCELLED' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Đã chuyển chiến dịch sang trạng thái Đã huỷ');
      setDeletingCampaign(null);
      setDeleteConflictError(null);
    },
    onError: (err) => {
      toast.apiError(err);
    },
  });

  const handleUpdate = async (body: CampaignInput) => {
    if (!editingCampaignId) return;
    await updateMutation.mutateAsync({ id: editingCampaignId, body });
  };

  return (
    <PageContainer>
      <PageHeader
        title="Chiến dịch"
        description="Quản lý các chiến dịch marketing, mục tiêu, kênh triển khai và phân bổ ngân sách."
        actions={
          <Button variant="primary" onClick={() => navigate('/campaigns/new')}>
            <Plus className="h-4 w-4" />
            Tạo chiến dịch
          </Button>
        }
      />

      {/* Filter bar */}
      <div className="mb-6 space-y-3 rounded-lg border border-border bg-surface p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Tìm theo tên chiến dịch..."
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
              { value: 'PLANNED', label: CAMPAIGN_STATUS_LABEL.PLANNED },
              { value: 'ACTIVE', label: CAMPAIGN_STATUS_LABEL.ACTIVE },
              { value: 'PAUSED', label: CAMPAIGN_STATUS_LABEL.PAUSED },
              { value: 'COMPLETED', label: CAMPAIGN_STATUS_LABEL.COMPLETED },
              { value: 'CANCELLED', label: CAMPAIGN_STATUS_LABEL.CANCELLED },
            ]}
          />
          <Select
            value={goalFilter}
            onChange={(e) => {
              setGoalFilter(e.target.value);
              setPage(1);
            }}
            options={[
              { value: '', label: 'Tất cả mục tiêu' },
              { value: 'AWARENESS', label: GOAL_LABEL.AWARENESS },
              { value: 'TRAFFIC', label: GOAL_LABEL.TRAFFIC },
              { value: 'LEADS', label: GOAL_LABEL.LEADS },
              { value: 'SALES', label: GOAL_LABEL.SALES },
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
            <DateRangePicker
              value={dateRange}
              onChange={(range) => {
                setDateRange(range);
                setPage(1);
              }}
            />
            {usersOpt.enabled && (
              <div className="w-48">
                <Select
                  value={ownerFilter}
                  onChange={(e) => {
                    setOwnerFilter(e.target.value);
                    setPage(1);
                  }}
                  options={[
                    { value: '', label: 'Tất cả người phụ trách' },
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
                  { value: 'start_date', label: 'Bắt đầu sớm nhất' },
                  { value: '-budget', label: 'Ngân sách cao nhất' },
                  { value: 'budget', label: 'Ngân sách thấp nhất' },
                  { value: 'name', label: 'Tên chiến dịch A-Z' },
                ]}
              />
            </div>
          </div>
          {(searchInput || statusFilter || goalFilter || channelFilter || ownerFilter || dateRange.from || dateRange.to) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchInput('');
                setStatusFilter('');
                setGoalFilter('');
                setChannelFilter('');
                setOwnerFilter('');
                setDateRange({ from: '', to: '' });
                setPage(1);
              }}
            >
              Đặt lại bộ lọc
            </Button>
          )}
        </div>
      </div>

      {/* Main Table Content */}
      {isLoading ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <SkeletonRows rows={6} />
        </div>
      ) : isError ? (
        <ErrorState
          error={error}
          onRetry={() => refetch()}
        />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<Filter className="h-8 w-8" />}
          title="Không tìm thấy chiến dịch nào"
          description={
            searchInput || statusFilter || goalFilter || channelFilter || ownerFilter || dateRange.from
              ? 'Thử thay đổi hoặc xoá các điều kiện lọc để tìm kiếm rộng hơn.'
              : 'Chưa có chiến dịch nào được tạo trong hệ thống.'
          }
          action={
            <Button variant="primary" onClick={() => navigate('/campaigns/new')}>
              <Plus className="h-4 w-4" />
              Tạo chiến dịch mới
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-sm">
            <Table>
              <THead>
                <TR>
                  <TH>Chiến dịch</TH>
                  <TH>Mục tiêu</TH>
                  <TH>Kênh</TH>
                  <TH>Thời gian</TH>
                  <TH>Ngân sách / Đã chi</TH>
                  <TH>Trạng thái</TH>
                  <TH>Nội dung</TH>
                  <TH className="text-right">Thao tác</TH>
                </TR>
              </THead>
              <TBody>
                {data.items.map((item) => {
                  const spentPct = item.budget > 0 ? Math.round((item.spent / item.budget) * 100) : 0;
                  const canEdit = canEditCampaign(user, item);

                  return (
                    <TR key={item.id}>
                      <TD>
                        <div>
                          <Link
                            to={`/campaigns/${item.id}`}
                            className="font-medium text-fg hover:underline focus:outline-none"
                          >
                            {item.name}
                          </Link>
                          <p className="text-xs text-fg-subtle">Phụ trách: {item.owner.full_name}</p>
                        </div>
                      </TD>
                      <TD>
                        <span className="text-sm text-fg-muted">{GOAL_LABEL[item.goal] ?? item.goal}</span>
                      </TD>
                      <TD>
                        <div className="flex flex-wrap gap-1">
                          {item.channels.length > 0 ? (
                            item.channels.map((ch) => (
                              <Badge key={ch.id} tone="neutral">
                                {ch.name}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-xs text-fg-subtle">—</span>
                          )}
                        </div>
                      </TD>
                      <TD className="text-xs text-fg-muted">
                        <div>{formatDate(item.start_date)}</div>
                        <div>đến {formatDate(item.end_date)}</div>
                      </TD>
                      <TD>
                        <div className="space-y-1">
                          <div className="text-xs font-medium text-fg">
                            {formatMoney(item.spent)} / {formatMoney(item.budget)}
                          </div>
                          {item.budget > 0 && (
                            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-subtle">
                              <div
                                className={`h-full rounded-full ${
                                  spentPct > 100 ? 'bg-danger' : spentPct > 80 ? 'bg-warning' : 'bg-accent'
                                }`}
                                style={{ width: `${Math.min(spentPct, 100)}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </TD>
                      <TD>
                        <StatusBadge kind="campaign" status={item.status} />
                      </TD>
                      <TD>
                        <div className="flex flex-wrap items-center gap-1.5 text-xs text-fg-muted">
                          {item.content_counts.PENDING_REVIEW ? (
                            <span className="inline-flex items-center rounded bg-amber-500/10 px-1.5 py-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">
                              {item.content_counts.PENDING_REVIEW} chờ duyệt
                            </span>
                          ) : null}
                          {item.content_counts.APPROVED ? (
                            <span className="inline-flex items-center rounded bg-blue-500/10 px-1.5 py-0.5 text-[11px] font-medium text-blue-600 dark:text-blue-400">
                              {item.content_counts.APPROVED} đã duyệt
                            </span>
                          ) : null}
                          {item.content_counts.PUBLISHED ? (
                            <span className="inline-flex items-center rounded bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                              {item.content_counts.PUBLISHED} đã đăng
                            </span>
                          ) : null}
                          {!item.content_counts.PENDING_REVIEW &&
                            !item.content_counts.APPROVED &&
                            !item.content_counts.PUBLISHED && (
                              <span className="text-fg-subtle">
                                {Object.values(item.content_counts).reduce((a, b) => (a ?? 0) + (b ?? 0), 0)} nội dung
                              </span>
                            )}
                        </div>
                      </TD>
                      <TD className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <IconButton
                            label="Xem chi tiết"
                            size="sm"
                            variant="ghost"
                            onClick={() => navigate(`/campaigns/${item.id}`)}
                          >
                            <Eye className="h-4 w-4" />
                          </IconButton>
                          {canEdit && (
                            <>
                              <IconButton
                                label="Chỉnh sửa"
                                size="sm"
                                variant="ghost"
                                onClick={() => setEditingCampaignId(item.id)}
                              >
                                <Edit3 className="h-4 w-4" />
                              </IconButton>
                              <IconButton
                                label="Xoá chiến dịch"
                                size="sm"
                                variant="ghost"
                                className="text-danger hover:bg-danger/10"
                                onClick={() => {
                                  setDeletingCampaign(item);
                                  setDeleteConflictError(null);
                                }}
                              >
                                <Trash2 className="h-4 w-4" />
                              </IconButton>
                            </>
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
            onPageChange={(p) => setPage(p)}
          />
        </div>
      )}

      {/* Edit Campaign Drawer */}
      <Drawer
        open={!!editingCampaignId}
        onClose={() => setEditingCampaignId(null)}
        title={editingCampaignQ.data ? `Sửa: ${editingCampaignQ.data.name}` : 'Chỉnh sửa chiến dịch'}
        width="lg"
      >
        {editingCampaignQ.isLoading ? (
          <div className="p-6">
            <SkeletonRows rows={6} />
          </div>
        ) : editingCampaignQ.data ? (
          <div className="p-6">
            <CampaignForm
              campaign={editingCampaignQ.data}
              submitLabel="Lưu thay đổi"
              onSubmit={handleUpdate}
              onCancel={() => setEditingCampaignId(null)}
            />
          </div>
        ) : null}
      </Drawer>

      {/* Delete Campaign Confirm Dialog */}
      <ConfirmDialog
        open={!!deletingCampaign}
        title={`Xoá chiến dịch "${deletingCampaign?.name}"`}
        confirmLabel={deleteConflictError ? 'Đóng' : 'Xác nhận xoá'}
        destructive={!deleteConflictError}
        loading={deleteMutation.isPending || cancelCampaignMutation.isPending}
        onClose={() => {
          setDeletingCampaign(null);
          setDeleteConflictError(null);
        }}
        onConfirm={() => {
          if (deleteConflictError) {
            setDeletingCampaign(null);
            setDeleteConflictError(null);
          } else if (deletingCampaign) {
            deleteMutation.mutate(deletingCampaign.id);
          }
        }}
      >
        {deleteConflictError ? (
          <div className="space-y-4">
            <Callout tone="warning" icon={<AlertCircle className="h-5 w-5" />}>
              {deleteConflictError}
            </Callout>
            <p className="text-sm text-fg-muted">
              Hệ thống không cho phép xoá vật lý để bảo toàn lịch sử số liệu và nội dung đã duyệt/lên lịch.
            </p>
            <div className="flex justify-end pt-2">
              <Button
                variant="primary"
                onClick={() => deletingCampaign && cancelCampaignMutation.mutate(deletingCampaign.id)}
              >
                Chuyển trạng thái sang Đã huỷ
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-fg-muted">
            Hành động này sẽ xoá chiến dịch nếu chiến dịch chưa có nội dung hoặc số liệu phát sinh. Bạn có chắc chắn muốn xoá không?
          </p>
        )}
      </ConfirmDialog>
    </PageContainer>
  );
}
