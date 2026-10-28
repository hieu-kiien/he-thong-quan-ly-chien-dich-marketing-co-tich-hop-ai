import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  Edit3,
  Trash2,
  Plus,
  Upload,
  Download,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Button,
  IconButton,
  StatusBadge,
  Badge,
  SeedDataBadge,
  Tabs,
  TabPanel,
  Table,
  THead,
  TBody,
  TR,
  TH,
  TD,
  Card,
  CardHeader,
  CardBody,
  PageHeader,
  ConfirmDialog,
  Drawer,
  Dialog,
  FormField,
  Input,
  Select,
  Textarea,
  MoneyInput,
  useToast,
  Pagination,
  ErrorState,
  SkeletonRows,
  Callout,
  type TabItem,
} from '@/components/ui';
import { campaignsApi, contentsApi, schedulesApi, metricsApi, statsApi } from '@/lib/api/endpoints';
import { toApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth';
import { canEditCampaign, canEditMetric } from '@/lib/permissions';
import { useDocumentTitle } from '@/lib/hooks';
import { formatDate, formatDateTime, formatMoney, formatNumber, formatPct, formatRate, todayKey } from '@/lib/format';
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
  CampaignInput,
  ChannelStats,
  Content,
  ContentType,
  Metric,
  MetricImportPreview,
  Schedule,
} from '@/lib/types';
import { CampaignForm } from './CampaignForm';

type CampaignTabKey = 'info' | 'contents' | 'metrics';

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const campaignId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const toast = useToast();

  const [activeTab, setActiveTab] = useState<CampaignTabKey>('info');
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteConflictError, setDeleteConflictError] = useState<string | null>(null);

  // Content creation dialog state
  const [isCreatingContent, setIsCreatingContent] = useState(false);
  const [newContentChannelId, setNewContentChannelId] = useState<number | ''>('');
  const [newContentType, setNewContentType] = useState<ContentType>('SOCIAL_POST');
  const [newContentTitle, setNewContentTitle] = useState('');
  const [newContentBody, setNewContentBody] = useState('');
  const [newContentCta, setNewContentCta] = useState('');
  const [contentFormError, setContentFormError] = useState<string | null>(null);

  // Schedule creation dialog state
  const [isCreatingSchedule, setIsCreatingSchedule] = useState(false);
  const [scheduleContentId, setScheduleContentId] = useState<number | ''>('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [scheduleNote, setScheduleNote] = useState('');

  // Metric manual create dialog state
  const [isCreatingMetric, setIsCreatingMetric] = useState(false);
  const [metricDate, setMetricDate] = useState(todayKey());
  const [metricChannelId, setMetricChannelId] = useState<number | ''>('');
  const [metricViews, setMetricViews] = useState<number | null>(0);
  const [metricClicks, setMetricClicks] = useState<number | null>(0);
  const [metricConversions, setMetricConversions] = useState<number | null>(0);
  const [metricCost, setMetricCost] = useState<number | null>(0);
  const [metricFormError, setMetricFormError] = useState<string | null>(null);
  const [deletingMetricId, setDeletingMetricId] = useState<number | null>(null);

  // CSV Import state
  const [isImportingCsv, setIsImportingCsv] = useState(false);
  const [csvPreview, setCsvPreview] = useState<MetricImportPreview | null>(null);
  const [csvLoading, setCsvLoading] = useState(false);
  const [csvError, setCsvError] = useState<string | null>(null);

  // Metrics page state
  const [metricPage, setMetricPage] = useState(1);
  const metricsPageSize = 10;

  const {
    data: campaign,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['campaigns', campaignId],
    queryFn: () => campaignsApi.get(campaignId),
    enabled: !!campaignId,
  });

  useDocumentTitle(campaign ? campaign.name : 'Chi tiết chiến dịch');

  // Queries for tab 2: Contents & Schedules
  const contentsQ = useQuery({
    queryKey: ['contents', { campaign_id: campaignId, page_size: 50 }],
    queryFn: () => contentsApi.list({ campaign_id: campaignId, page_size: 50 }),
    enabled: !!campaignId && activeTab === 'contents',
  });

  const schedulesQ = useQuery({
    queryKey: ['schedules', { campaign_id: campaignId }],
    queryFn: () => schedulesApi.list({ campaign_id: campaignId }),
    enabled: !!campaignId && activeTab === 'contents',
  });

  // Queries for tab 3: Metrics & Per-channel breakdown
  const metricsQ = useQuery({
    queryKey: ['metrics', { campaign_id: campaignId, page: metricPage, page_size: metricsPageSize }],
    queryFn: () => metricsApi.list({ campaign_id: campaignId, page: metricPage, page_size: metricsPageSize }),
    enabled: !!campaignId && activeTab === 'metrics',
  });

  const channelStatsQ = useQuery({
    queryKey: ['stats', 'by-channel', { campaign_id: campaignId }],
    queryFn: () => statsApi.byChannel({ campaign_id: campaignId }),
    enabled: !!campaignId,
  });

  // Mutations
  const updateCampaignMutation = useMutation({
    mutationFn: (body: Partial<CampaignInput>) => campaignsApi.update(campaignId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Cập nhật thành công', 'Thông tin chiến dịch đã được lưu.');
      setIsEditing(false);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi cập nhật chiến dịch');
    },
  });

  const deleteCampaignMutation = useMutation({
    mutationFn: () => campaignsApi.remove(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Đã xoá chiến dịch');
      navigate('/campaigns');
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
    mutationFn: () => campaignsApi.update(campaignId, { status: 'CANCELLED' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Đã chuyển chiến dịch sang trạng thái Đã huỷ');
      setIsDeleting(false);
      setDeleteConflictError(null);
    },
    onError: (err) => {
      toast.apiError(err);
    },
  });

  const createContentMutation = useMutation({
    mutationFn: contentsApi.create,
    onSuccess: (newContent) => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
      toast.success('Đã tạo nội dung mới', `Nội dung "${newContent.title}" đã được lưu nháp.`);
      setIsCreatingContent(false);
      setNewContentTitle('');
      setNewContentBody('');
      setNewContentCta('');
      setContentFormError(null);
    },
    onError: (err) => {
      setContentFormError(toApiError(err).message);
    },
  });

  const createScheduleMutation = useMutation({
    mutationFn: schedulesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success('Đã lên lịch đăng thành công');
      setIsCreatingSchedule(false);
      setScheduleContentId('');
      setScheduledAt('');
      setScheduleNote('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi lên lịch');
    },
  });

  const createMetricMutation = useMutation({
    mutationFn: metricsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['stats', 'by-channel', { campaign_id: campaignId }] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
      toast.success('Đã ghi nhận số liệu');
      setIsCreatingMetric(false);
      setMetricViews(0);
      setMetricClicks(0);
      setMetricConversions(0);
      setMetricCost(0);
      setMetricFormError(null);
    },
    onError: (err) => {
      setMetricFormError(toApiError(err).message);
    },
  });

  const deleteMetricMutation = useMutation({
    mutationFn: metricsApi.remove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['stats', 'by-channel', { campaign_id: campaignId }] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
      toast.success('Đã xoá bản ghi số liệu');
      setDeletingMetricId(null);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi xoá số liệu');
    },
  });

  const handleDownloadTemplate = async () => {
    try {
      const blob = await metricsApi.template();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `marketflow_metrics_template.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      toast.apiError(err, 'Lỗi tải mẫu CSV');
    }
  };

  const handlePreviewCsv = async (file: File) => {
    setCsvLoading(true);
    setCsvError(null);
    try {
      const res = await metricsApi.preview(file);
      setCsvPreview(res);
    } catch (err) {
      setCsvError(toApiError(err).message);
    } finally {
      setCsvLoading(false);
    }
  };

  const handleCommitCsv = async () => {
    if (!csvPreview) return;
    const validRows = csvPreview.rows.filter((r) => !csvPreview.errors.some((e) => e.row === r.row));
    if (validRows.length === 0) {
      toast.error('Không có dòng dữ liệu hợp lệ để nhập');
      return;
    }
    setCsvLoading(true);
    try {
      const res = await metricsApi.commit(validRows);
      toast.success(
        'Nhập CSV thành công',
        `Đã thêm mới ${res.inserted} dòng, cập nhật ${res.updated} dòng (mã lô: ${res.import_batch}).`
      );
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['stats', 'by-channel', { campaign_id: campaignId }] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
      setIsImportingCsv(false);
      setCsvPreview(null);
    } catch (err) {
      setCsvError(toApiError(err).message);
    } finally {
      setCsvLoading(false);
    }
  };

  if (isLoading) {
    return (
      <PageContainer>
        <div className="space-y-4">
          <SkeletonRows rows={3} />
          <SkeletonRows rows={4} />
        </div>
      </PageContainer>
    );
  }

  if (isError || !campaign) {
    return (
      <PageContainer>
        <ErrorState
          error={error}
          onRetry={() => refetch()}
        />
      </PageContainer>
    );
  }

  const canEdit = canEditCampaign(user, campaign);
  const tabs: TabItem<CampaignTabKey>[] = [
    { key: 'info', label: 'Thông tin chung' },
    { key: 'contents', label: 'Nội dung & Lịch' },
    { key: 'metrics', label: 'Số liệu & Báo cáo' },
  ];

  // Tính toán Tiến độ thời gian & Nhịp giải ngân (Budget Pacing)
  const startMs = new Date(`${campaign.start_date}T00:00:00`).getTime();
  const endMs = new Date(`${campaign.end_date}T00:00:00`).getTime();
  const nowMs = new Date(`${todayKey()}T00:00:00`).getTime();
  const daysTotal = Math.max(1, Math.round((endMs - startMs) / 86_400_000) + 1);
  const daysElapsed =
    nowMs < startMs
      ? 0
      : nowMs > endMs
        ? daysTotal
        : Math.round((nowMs - startMs) / 86_400_000) + 1;
  const timeElapsedPct = Math.round((daysElapsed / daysTotal) * 1000) / 10;
  const budgetUsedPct = campaign.stats.budget_used_pct ?? 0;

  const pacingBadge: { label: string; tone: 'neutral' | 'success' | 'warning' | 'info' } =
    campaign.stats.cost <= 0
      ? { label: 'Chưa giải ngân', tone: 'neutral' }
      : budgetUsedPct > timeElapsedPct + 15
        ? { label: 'Tiêu nhanh hơn tiến độ', tone: 'warning' }
        : timeElapsedPct >= 20 && budgetUsedPct < timeElapsedPct - 20
          ? { label: 'Giải ngân chậm hơn tiến độ', tone: 'info' }
          : { label: 'Đúng nhịp kế hoạch', tone: 'success' };

  const channelStatsByCode = new Map<string, ChannelStats>(
    (channelStatsQ.data ?? []).map((item) => [item.channel.code, item]),
  );

  return (
    <PageContainer>
      <PageHeader
        back={{ to: '/campaigns', label: 'Chiến dịch' }}
        title={
          <div className="flex flex-wrap items-center gap-3">
            <span>{campaign.name}</span>
            <StatusBadge kind="campaign" status={campaign.status} />
          </div>
        }
        description={
          <div className="flex flex-wrap items-center gap-4 text-xs text-fg-muted">
            <span>Mục tiêu: {GOAL_LABEL[campaign.goal]}</span>
            <span>•</span>
            <span>Thời gian: {formatDate(campaign.start_date)} — {formatDate(campaign.end_date)}</span>
            <span>•</span>
            <span>Người phụ trách: {campaign.owner.full_name}</span>
          </div>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => navigate(`/assistant?campaign_id=${campaign.id}`)}
              className="border-accent/40 bg-accent/5 hover:bg-accent/10"
            >
              <Sparkles className="h-4 w-4 text-accent" />
              Hỏi Trợ lý AI
            </Button>
            {canEdit && (
              <>
                <Button variant="secondary" onClick={() => setIsEditing(true)}>
                  <Edit3 className="h-4 w-4" />
                  Chỉnh sửa
                </Button>
                <IconButton
                  label="Xoá chiến dịch"
                  variant="ghost"
                  className="text-danger hover:bg-danger/10"
                  onClick={() => {
                    setIsDeleting(true);
                    setDeleteConflictError(null);
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </IconButton>
              </>
            )}
          </div>
        }
      />

      <Tabs items={tabs} value={activeTab} onChange={(k) => setActiveTab(k)} />

      {/* TAB 1: THÔNG TIN CHUNG */}
      {activeTab === 'info' && (
        <TabPanel tabKey="info" className="mt-6 space-y-6">
          {/* Key Metric Summary Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className={GOAL_KPI_META[campaign.goal].primaryMetricKey === 'views' ? 'border-accent/40 ring-1 ring-accent/20' : ''}>
              <CardBody>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-fg-muted">Lượt hiển thị (Views)</p>
                  {GOAL_KPI_META[campaign.goal].primaryMetricKey === 'views' && (
                    <Badge tone="accent">KPI trọng tâm</Badge>
                  )}
                </div>
                <p className="mt-1 text-2xl font-semibold text-fg">{formatNumber(campaign.stats.views)}</p>
                <div className="mt-2 text-xs text-fg-muted">CTR: {formatRate(campaign.stats.ctr)}</div>
              </CardBody>
            </Card>

            <Card className={GOAL_KPI_META[campaign.goal].primaryMetricKey === 'clicks' ? 'border-accent/40 ring-1 ring-accent/20' : ''}>
              <CardBody>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-fg-muted">Lượt bấm (Clicks)</p>
                  {GOAL_KPI_META[campaign.goal].primaryMetricKey === 'clicks' && (
                    <Badge tone="accent">KPI trọng tâm</Badge>
                  )}
                </div>
                <p className="mt-1 text-2xl font-semibold text-fg">{formatNumber(campaign.stats.clicks)}</p>
                <div className="mt-2 text-xs text-fg-muted">CPC: {formatMoney(campaign.stats.cpc)}</div>
              </CardBody>
            </Card>

            <Card className={GOAL_KPI_META[campaign.goal].primaryMetricKey === 'conversions' ? 'border-accent/40 ring-1 ring-accent/20' : ''}>
              <CardBody>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-fg-muted">Chuyển đổi (Conversions)</p>
                  {GOAL_KPI_META[campaign.goal].primaryMetricKey === 'conversions' && (
                    <Badge tone="accent">KPI trọng tâm</Badge>
                  )}
                </div>
                <p className="mt-1 text-2xl font-semibold text-fg">{formatNumber(campaign.stats.conversions)}</p>
                <div className="mt-2 text-xs text-fg-muted">CVR: {formatRate(campaign.stats.cvr)}</div>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <p className="text-xs text-fg-muted">Chi phí / Ngân sách</p>
                <p className="mt-1 text-xl font-semibold text-fg">
                  {formatMoney(campaign.stats.cost)} <span className="text-xs font-normal text-fg-muted">/ {formatMoney(campaign.budget)}</span>
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-subtle">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${Math.min(campaign.stats.budget_used_pct ?? 0, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-fg">{formatPct(campaign.stats.budget_used_pct)}</span>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Campaign Strategy & Details */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader
                title="Mục tiêu & Sản phẩm"
                actions={
                  <Badge tone={GOAL_TONE[campaign.goal]}>{GOAL_LABEL[campaign.goal]}</Badge>
                }
              />
              <CardBody className="space-y-4 text-sm">
                <div className="rounded-md border border-border bg-subtle/60 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-medium text-fg-muted">Thước đo KPI trọng tâm theo mục tiêu</span>
                    <span className="text-xs font-semibold text-fg">{GOAL_KPI_META[campaign.goal].primaryKpiLabel}</span>
                  </div>
                  <p className="mt-1.5 text-xs text-fg-muted">
                    {GOAL_KPI_META[campaign.goal].contentDirection}
                  </p>
                </div>
                <div>
                  <h4 className="text-xs font-medium text-fg-muted">Mục tiêu cụ thể (Chỉ tiêu định lượng)</h4>
                  <p className="mt-1 font-medium text-fg whitespace-pre-line">{campaign.objective || '—'}</p>
                </div>
                <div>
                  <h4 className="text-xs font-medium text-fg-muted">Sản phẩm / Dịch vụ</h4>
                  <p className="mt-1 text-fg whitespace-pre-line">{campaign.product || '—'}</p>
                </div>
                <div>
                  <h4 className="text-xs font-medium text-fg-muted">Thông điệp cốt lõi</h4>
                  <p className="mt-1 text-fg whitespace-pre-line">{campaign.key_message || '—'}</p>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Đối tượng mục tiêu & Tiến độ giải ngân" />
              <CardBody className="space-y-4 text-sm">
                <div>
                  <h4 className="text-xs font-medium text-fg-muted">Chân dung khách hàng</h4>
                  <p className="mt-1 text-fg whitespace-pre-line">{campaign.target_audience || '—'}</p>
                </div>
                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-medium text-fg-muted">Chỉ số hiệu quả & Nhịp giải ngân</h4>
                    <Badge tone={pacingBadge.tone}>{pacingBadge.label}</Badge>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded bg-subtle p-2">
                      <span className="text-fg-muted">Chi phí / chuyển đổi (CPA):</span>
                      <p className="font-semibold text-fg">{formatMoney(campaign.stats.cpa)}</p>
                    </div>
                    <div className="rounded bg-subtle p-2">
                      <span className="text-fg-muted">Tỷ lệ sử dụng ngân sách:</span>
                      <p className="font-semibold text-fg">{formatPct(campaign.stats.budget_used_pct)}</p>
                    </div>
                    <div className="rounded bg-subtle p-2">
                      <span className="text-fg-muted">Tiến độ thời gian:</span>
                      <p className="font-semibold text-fg">
                        {daysElapsed}/{daysTotal} ngày ({timeElapsedPct.toFixed(1)}%)
                      </p>
                    </div>
                    <div className="rounded bg-subtle p-2">
                      <span className="text-fg-muted">Ngân sách còn lại:</span>
                      <p className="font-semibold text-fg">
                        {formatMoney(Math.max(0, campaign.budget - campaign.stats.cost))}
                      </p>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Channels & Budget Allocation */}
          <Card>
            <CardHeader
              title="Kênh triển khai & Ngân sách dự kiến"
              description="Đối chiếu ngân sách kế hoạch với chi tiêu thực tế và hiệu quả chuyển đổi theo từng kênh."
            />
            <div className="overflow-x-auto">
              <Table>
                <THead>
                  <TR>
                    <TH>Kênh</TH>
                    <TH>Mã kênh</TH>
                    <TH>Ngân sách dự kiến</TH>
                    <TH>Tỷ trọng</TH>
                    <TH className="text-right">Chi tiêu thực tế</TH>
                    <TH className="text-right">% Giải ngân kênh</TH>
                    <TH className="text-right">Chuyển đổi</TH>
                    <TH className="text-right">CPA</TH>
                  </TR>
                </THead>
                <TBody>
                  {campaign.channels.length === 0 ? (
                    <TR>
                      <TD colSpan={8} className="py-6 text-center text-sm text-fg-muted">
                        Chưa chọn kênh nào cho chiến dịch này.
                      </TD>
                    </TR>
                  ) : (
                    campaign.channels.map((ch) => {
                      const pct = campaign.budget > 0 && ch.planned_budget ? (ch.planned_budget / campaign.budget) * 100 : null;
                      const chStat = channelStatsByCode.get(ch.code);
                      const actualCost = chStat?.cost ?? 0;
                      const chUsedPct =
                        ch.planned_budget && ch.planned_budget > 0
                          ? (actualCost / ch.planned_budget) * 100
                          : null;
                      return (
                        <TR key={ch.id}>
                          <TD className="font-medium text-fg">{ch.name}</TD>
                          <TD>
                            <Badge tone="neutral">
                              {ch.code}
                            </Badge>
                          </TD>
                          <TD>{formatMoney(ch.planned_budget)}</TD>
                          <TD>{pct !== null ? `${pct.toFixed(1)}%` : '—'}</TD>
                          <TD className="text-right font-mono text-xs">{formatMoney(actualCost)}</TD>
                          <TD className="text-right font-mono text-xs">
                            {chUsedPct !== null ? `${chUsedPct.toFixed(1)}%` : '—'}
                          </TD>
                          <TD className="text-right font-mono text-xs">{formatNumber(chStat?.conversions ?? 0)}</TD>
                          <TD className="text-right font-mono text-xs">{formatMoney(chStat?.cpa ?? null)}</TD>
                        </TR>
                      );
                    })
                  )}
                </TBody>
              </Table>
            </div>
          </Card>
        </TabPanel>
      )}

      {/* TAB 2: NỘI DUNG & LỊCH */}
      {activeTab === 'contents' && (
        <TabPanel tabKey="contents" className="mt-6 space-y-6">
          {/* Contents Section */}
          <Card>
            <CardHeader
              title="Danh sách nội dung bám sát chiến dịch"
              description={`Mục tiêu: ${GOAL_LABEL[campaign.goal]} · Sản phẩm: ${campaign.product}${campaign.key_message ? ` · Thông điệp: "${campaign.key_message}"` : ''}`}
              actions={
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate(`/assistant?campaign_id=${campaign.id}`)}
                  >
                    <Sparkles className="h-4 w-4 text-accent" />
                    Trợ lý AI soạn theo mục tiêu
                  </Button>
                  <Button variant="primary" size="sm" onClick={() => setIsCreatingContent(true)}>
                    <Plus className="h-4 w-4" />
                    Soạn nội dung mới
                  </Button>
                </div>
              }
            />
            {contentsQ.isLoading ? (
              <div className="p-4">
                <SkeletonRows rows={4} />
              </div>
            ) : !contentsQ.data || contentsQ.data.items.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm text-fg-muted">Chưa có nội dung nào trong chiến dịch này.</p>
                <Button variant="secondary" size="sm" className="mt-3" onClick={() => setIsCreatingContent(true)}>
                  <Plus className="h-4 w-4" />
                  Tạo bài viết đầu tiên
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>Tiêu đề</TH>
                      <TH>Kênh</TH>
                      <TH>Loại</TH>
                      <TH>Nguồn gốc</TH>
                      <TH>Trạng thái</TH>
                      <TH>Người tạo</TH>
                      <TH className="text-right">Thao tác</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {contentsQ.data.items.map((item: Content) => (
                      <TR key={item.id}>
                        <TD>
                          <Link to={`/contents/${item.id}`} className="font-medium text-fg hover:underline">
                            {item.title}
                          </Link>
                        </TD>
                        <TD>
                          <Badge tone="neutral">
                            {item.channel.name}
                          </Badge>
                        </TD>
                        <TD className="text-xs text-fg-muted">{CONTENT_TYPE_LABEL[item.content_type]}</TD>
                        <TD>
                          <Badge tone={item.origin === 'AI' ? 'accent' : 'neutral'}>
                            {ORIGIN_LABEL[item.origin]}
                          </Badge>
                        </TD>
                        <TD>
                          <StatusBadge kind="content" status={item.status} />
                        </TD>
                        <TD className="text-xs text-fg-muted">{item.created_by.full_name}</TD>
                        <TD className="text-right">
                          <Link to={`/contents/${item.id}`}>
                            <Button variant="ghost" size="sm">
                              Chi tiết
                            </Button>
                          </Link>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </Card>

          {/* Schedules Section */}
          <Card>
            <CardHeader
              title="Lịch đăng bài"
              description="Kế hoạch đăng tải các nội dung đã chuẩn bị."
              actions={
                <Button variant="secondary" size="sm" onClick={() => setIsCreatingSchedule(true)}>
                  <Calendar className="h-4 w-4" />
                  Lập lịch đăng
                </Button>
              }
            />
            {schedulesQ.isLoading ? (
              <div className="p-4">
                <SkeletonRows rows={3} />
              </div>
            ) : !schedulesQ.data || schedulesQ.data.length === 0 ? (
              <div className="p-8 text-center text-sm text-fg-muted">
                Chưa có lịch đăng nào được thiết lập cho chiến dịch này.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>Thời điểm đăng</TH>
                      <TH>Nội dung</TH>
                      <TH>Kênh</TH>
                      <TH>Người phụ trách</TH>
                      <TH>Trạng thái</TH>
                      <TH>Ghi chú</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {schedulesQ.data.map((sch: Schedule) => (
                      <TR key={sch.id}>
                        <TD className="text-xs font-medium text-fg">{formatDateTime(sch.scheduled_at)}</TD>
                        <TD>
                          <Link to={`/contents/${sch.content.id}`} className="text-sm text-fg hover:underline">
                            {sch.content.title}
                          </Link>
                        </TD>
                        <TD>
                          <Badge tone="neutral">
                            {sch.channel.name}
                          </Badge>
                        </TD>
                        <TD className="text-xs text-fg-muted">{sch.assignee?.full_name ?? '—'}</TD>
                        <TD>
                          <StatusBadge kind="schedule" status={sch.status} />
                        </TD>
                        <TD className="text-xs text-fg-subtle">{sch.note || '—'}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </Card>
        </TabPanel>
      )}

      {/* TAB 3: SỐ LIỆU & BÁO CÁO */}
      {activeTab === 'metrics' && (
        <TabPanel tabKey="metrics" className="mt-6 space-y-6">
          {/* Bảng Phân tích Phễu & Đối soát Kênh */}
          <Card>
            <CardHeader
              title="Phân tích phễu chuyển đổi & hiệu quả theo kênh"
              description="Tổng hợp CTR, CVR, CPC, CPA và nhịp giải ngân của từng kênh từ dữ liệu thực tế."
              actions={
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="border-accent/40 bg-accent/5 hover:bg-accent/10"
                    onClick={() => {
                      const promptText = `Hãy chẩn đoán phễu hiệu quả (CTR, CVR, CPC, CPA) và nhịp giải ngân của chiến dịch #${campaign.id} "${campaign.name}" theo từng kênh, chỉ ra điểm nghẽn và đề xuất phương án điều chỉnh ngân sách hoặc tối ưu nội dung cụ thể.`;
                      navigate(
                        `/assistant?campaign_id=${campaign.id}&prompt=${encodeURIComponent(promptText)}`,
                      );
                    }}
                  >
                    <Sparkles className="h-3.5 w-3.5 text-accent" />
                    Chẩn đoán phễu & ngân sách (AI)
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      const promptText = `Hãy tổng kết bài học thực chiến (Post-Campaign Retrospective) cho chiến dịch #${campaign.id} "${campaign.name}": kênh nào hiệu quả nhất, kênh nào tốn chi phí, thông điệp/định dạng nào nên phát huy cho chiến dịch kế tiếp.`;
                      navigate(
                        `/assistant?campaign_id=${campaign.id}&prompt=${encodeURIComponent(promptText)}`,
                      );
                    }}
                  >
                    <Sparkles className="h-3.5 w-3.5 text-accent" />
                    Đúc kết chiến dịch (AI)
                  </Button>
                </div>
              }
            />
            {!channelStatsQ.data || channelStatsQ.data.length === 0 ? (
              <div className="p-6 text-center text-sm text-fg-muted">
                Chưa có số liệu phân bổ theo kênh cho chiến dịch này.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>Kênh</TH>
                      <TH className="text-right">Hiển thị</TH>
                      <TH className="text-right">Bấm (Clicks)</TH>
                      <TH className="text-right">CTR</TH>
                      <TH className="text-right">Chuyển đổi</TH>
                      <TH className="text-right">CVR</TH>
                      <TH className="text-right">CPC</TH>
                      <TH className="text-right">CPA</TH>
                      <TH className="text-right">Chi phí / Dự kiến</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {channelStatsQ.data.map((row: ChannelStats) => {
                      const planned = campaign.channels.find((c) => c.code === row.channel.code)?.planned_budget;
                      return (
                        <TR key={row.channel.id}>
                          <TD>
                            <Badge tone="neutral">{row.channel.name}</Badge>
                          </TD>
                          <TD className="text-right font-mono text-xs">{formatNumber(row.views)}</TD>
                          <TD className="text-right font-mono text-xs">{formatNumber(row.clicks)}</TD>
                          <TD className="text-right font-mono text-xs">{formatRate(row.ctr)}</TD>
                          <TD className="text-right font-mono text-xs font-medium">{formatNumber(row.conversions)}</TD>
                          <TD className="text-right font-mono text-xs">{formatRate(row.cvr)}</TD>
                          <TD className="text-right font-mono text-xs">{formatMoney(row.cpc)}</TD>
                          <TD className="text-right font-mono text-xs font-semibold text-fg">{formatMoney(row.cpa)}</TD>
                          <TD className="text-right font-mono text-xs">
                            {formatMoney(row.cost)}{' '}
                            <span className="text-fg-subtle">/ {formatMoney(planned ?? null)}</span>
                          </TD>
                        </TR>
                      );
                    })}
                  </TBody>
                </Table>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader
              title="Lịch sử số liệu thực tế"
              description="Ghi nhận lượt hiển thị, click, chuyển đổi và chi phí theo từng kênh và ngày."
              actions={
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="secondary" size="sm" onClick={handleDownloadTemplate}>
                    <Download className="h-4 w-4" />
                    Tải mẫu CSV
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setIsImportingCsv(true)}>
                    <Upload className="h-4 w-4" />
                    Nhập CSV
                  </Button>
                  <Button variant="primary" size="sm" onClick={() => setIsCreatingMetric(true)}>
                    <Plus className="h-4 w-4" />
                    Nhập số liệu
                  </Button>
                </div>
              }
            />

            {metricsQ.isLoading ? (
              <div className="p-4">
                <SkeletonRows rows={4} />
              </div>
            ) : !metricsQ.data || metricsQ.data.items.length === 0 ? (
              <div className="p-8 text-center text-sm text-fg-muted">
                Chưa có dữ liệu số liệu nào được ghi nhận cho chiến dịch này.
              </div>
            ) : (
              <div className="space-y-4 p-4">
                <div className="overflow-x-auto rounded-lg border border-border">
                  <Table>
                    <THead>
                      <TR>
                        <TH>Ngày</TH>
                        <TH>Kênh</TH>
                        <TH className="text-right">Hiển thị (Views)</TH>
                        <TH className="text-right">Bấm (Clicks)</TH>
                        <TH className="text-right">Chuyển đổi</TH>
                        <TH className="text-right">Chi phí</TH>
                        <TH>Nguồn</TH>
                        <TH className="text-right">Thao tác</TH>
                      </TR>
                    </THead>
                    <TBody>
                      {metricsQ.data.items.map((m: Metric) => {
                        const canDelete = canEditMetric(user, m);
                        return (
                          <TR key={m.id}>
                            <TD className="text-xs font-medium text-fg">{formatDate(m.metric_date)}</TD>
                            <TD>
                              <Badge tone="neutral">
                                {m.channel.name}
                              </Badge>
                            </TD>
                            <TD className="text-right text-xs font-mono">{formatNumber(m.views)}</TD>
                            <TD className="text-right text-xs font-mono">{formatNumber(m.clicks)}</TD>
                            <TD className="text-right text-xs font-mono">{formatNumber(m.conversions)}</TD>
                            <TD className="text-right text-xs font-mono font-medium">{formatMoney(m.cost)}</TD>
                            <TD>
                              {m.source === 'SEED' ? (
                                <SeedDataBadge />
                              ) : (
                                <span className="text-xs text-fg-muted">
                                  {m.source === 'CSV' ? 'CSV' : 'Nhập tay'}
                                </span>
                              )}
                            </TD>
                            <TD className="text-right">
                              {canDelete && (
                                <IconButton
                                  label="Xoá số liệu"
                                  size="sm"
                                  variant="ghost"
                                  className="text-danger hover:bg-danger/10"
                                  onClick={() => setDeletingMetricId(m.id)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </IconButton>
                              )}
                            </TD>
                          </TR>
                        );
                      })}
                    </TBody>
                  </Table>
                </div>

                <Pagination
                  page={metricsQ.data.page}
                  pageSize={metricsQ.data.page_size}
                  total={metricsQ.data.total}
                  onPageChange={setMetricPage}
                />
              </div>
            )}
          </Card>
        </TabPanel>
      )}

      {/* Edit Campaign Drawer */}
      <Drawer
        open={isEditing}
        onClose={() => setIsEditing(false)}
        title={`Chỉnh sửa: ${campaign.name}`}
        width="lg"
      >
        <div className="p-6">
          <CampaignForm
            campaign={campaign}
            submitLabel="Lưu thay đổi"
            onSubmit={async (body) => {
              await updateCampaignMutation.mutateAsync(body);
            }}
            onCancel={() => setIsEditing(false)}
          />
        </div>
      </Drawer>

      {/* Delete Campaign Dialog */}
      <ConfirmDialog
        open={isDeleting}
        title={`Xoá chiến dịch "${campaign.name}"`}
        confirmLabel={deleteConflictError ? 'Đóng' : 'Xác nhận xoá'}
        destructive={!deleteConflictError}
        loading={deleteCampaignMutation.isPending || cancelCampaignMutation.isPending}
        onClose={() => {
          setIsDeleting(false);
          setDeleteConflictError(null);
        }}
        onConfirm={() => {
          if (deleteConflictError) {
            setIsDeleting(false);
            setDeleteConflictError(null);
          } else {
            deleteCampaignMutation.mutate();
          }
        }}
      >
        {deleteConflictError ? (
          <div className="space-y-4">
            <Callout tone="warning" icon={<AlertCircle className="h-5 w-5" />}>
              {deleteConflictError}
            </Callout>
            <p className="text-sm text-fg-muted">
              Hệ thống không cho phép xoá vật lý để bảo toàn lịch sử số liệu và nội dung.
            </p>
            <div className="flex justify-end pt-2">
              <Button variant="primary" onClick={() => cancelCampaignMutation.mutate()}>
                Chuyển trạng thái sang Đã huỷ
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-fg-muted">
            Hành động này sẽ xoá hoàn toàn chiến dịch nếu chưa có nội dung hoặc số liệu phát sinh. Bạn có chắc chắn muốn xoá?
          </p>
        )}
      </ConfirmDialog>

      {/* Create Content Dialog */}
      <Dialog
        open={isCreatingContent}
        onClose={() => setIsCreatingContent(false)}
        title="Tạo nội dung cho chiến dịch"
        size="lg"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!newContentChannelId) {
              setContentFormError('Vui lòng chọn kênh triển khai.');
              return;
            }
            if (!newContentTitle.trim()) {
              setContentFormError('Vui lòng nhập tiêu đề bài viết.');
              return;
            }
            if (!newContentBody.trim()) {
              setContentFormError('Vui lòng nhập nội dung chi tiết.');
              return;
            }
            createContentMutation.mutate({
              campaign_id: campaignId,
              channel_id: Number(newContentChannelId),
              content_type: newContentType,
              title: newContentTitle.trim(),
              body: newContentBody.trim(),
              cta: newContentCta.trim() || null,
            });
          }}
          className="space-y-4"
        >
          {contentFormError && <Callout tone="danger">{contentFormError}</Callout>}
          <div className="rounded-md border border-border bg-subtle/60 p-3 text-xs space-y-1.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-fg">Định hướng chiến dịch:</span>
                <Badge tone={GOAL_TONE[campaign.goal]}>{GOAL_LABEL[campaign.goal]}</Badge>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  const draft = buildGoalContentDraft(campaign);
                  setNewContentTitle(draft.title);
                  setNewContentBody(draft.body);
                  setNewContentCta(draft.cta);
                }}
              >
                Điền khung sườn theo mục tiêu
              </Button>
            </div>
            <p className="text-fg-muted">
              <strong className="text-fg">Chỉ tiêu:</strong> {campaign.objective} · <strong className="text-fg">Sản phẩm:</strong> {campaign.product}
            </p>
            {campaign.key_message && (
              <p className="text-fg-muted">
                <strong className="text-fg">Thông điệp cốt lõi:</strong> &ldquo;{campaign.key_message}&rdquo;
              </p>
            )}
            <p className="text-fg-muted">
              <strong className="text-fg">Gợi ý triển khai:</strong> {GOAL_KPI_META[campaign.goal].contentDirection}
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Kênh triển khai" required>
              {(p) => (
                <Select
                  {...p}
                  value={newContentChannelId}
                  onChange={(e) => setNewContentChannelId(e.target.value ? Number(e.target.value) : '')}
                  options={[
                    { value: '', label: 'Chọn kênh...' },
                    ...campaign.channels.map((ch) => ({ value: String(ch.id), label: ch.name })),
                  ]}
                />
              )}
            </FormField>
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
          </div>
          <FormField label="Tiêu đề / Tiêu đề email" required>
            {(p) => (
              <Input
                {...p}
                value={newContentTitle}
                onChange={(e) => setNewContentTitle(e.target.value)}
                placeholder="Nhập tiêu đề hoặc dòng chủ đề..."
              />
            )}
          </FormField>
          <FormField label="Nội dung chính" required>
            {(p) => (
              <Textarea
                {...p}
                rows={6}
                value={newContentBody}
                onChange={(e) => setNewContentBody(e.target.value)}
                placeholder="Soạn nội dung bài đăng hoặc email..."
              />
            )}
          </FormField>
          <FormField label="Lời kêu gọi hành động (CTA)">
            {(p) => (
              <Input
                {...p}
                value={newContentCta}
                onChange={(e) => setNewContentCta(e.target.value)}
                placeholder="Ví dụ: Đặt mua ngay, Đăng ký tư vấn miễn phí..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" type="button" onClick={() => setIsCreatingContent(false)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={createContentMutation.isPending}>
              Lưu bản nháp
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Create Schedule Dialog */}
      <Dialog
        open={isCreatingSchedule}
        onClose={() => setIsCreatingSchedule(false)}
        title="Lập lịch đăng bài"
        size="md"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!scheduleContentId) {
              toast.error('Vui lòng chọn nội dung cần lên lịch');
              return;
            }
            if (!scheduledAt) {
              toast.error('Vui lòng chọn thời gian đăng');
              return;
            }
            createScheduleMutation.mutate({
              content_id: Number(scheduleContentId),
              scheduled_at: new Date(scheduledAt).toISOString(),
              note: scheduleNote.trim() || null,
            });
          }}
          className="space-y-4"
        >
          <FormField label="Nội dung cần đăng" required>
            {(p) => (
              <Select
                {...p}
                value={scheduleContentId}
                onChange={(e) => setScheduleContentId(e.target.value ? Number(e.target.value) : '')}
                options={[
                  { value: '', label: 'Chọn nội dung...' },
                  ...(contentsQ.data?.items ?? [])
                    .filter((c: Content) => c.status !== 'REJECTED' && c.status !== 'PUBLISHED')
                    .map((c: Content) => ({
                      value: String(c.id),
                      label: `[${c.channel.name}] ${c.title} (${CONTENT_STATUS_LABEL[c.status]})`,
                    })),
                ]}
              />
            )}
          </FormField>
          <FormField label="Thời điểm đăng" required>
            {(p) => (
              <Input
                {...p}
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
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
            <Button variant="secondary" type="button" onClick={() => setIsCreatingSchedule(false)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={createScheduleMutation.isPending}>
              Xác nhận lên lịch
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Manual Metric Entry Dialog */}
      <Dialog
        open={isCreatingMetric}
        onClose={() => setIsCreatingMetric(false)}
        title="Nhập số liệu thực tế"
        size="md"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!metricChannelId) {
              setMetricFormError('Vui lòng chọn kênh.');
              return;
            }
            if (!metricDate) {
              setMetricFormError('Vui lòng chọn ngày.');
              return;
            }
            const views = metricViews ?? 0;
            const clicks = metricClicks ?? 0;
            const conversions = metricConversions ?? 0;
            if (views > 0 && clicks > views) {
              setMetricFormError('Lượt click không thể lớn hơn lượt xem (views).');
              return;
            }
            if (clicks > 0 && conversions > clicks) {
              setMetricFormError('Lượt chuyển đổi không thể lớn hơn lượt click.');
              return;
            }
            createMetricMutation.mutate({
              campaign_id: campaignId,
              channel_id: Number(metricChannelId),
              metric_date: metricDate,
              views,
              clicks,
              conversions,
              cost: metricCost ?? 0,
            });
          }}
          className="space-y-4"
        >
          {metricFormError && <Callout tone="danger">{metricFormError}</Callout>}
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Kênh" required>
              {(p) => (
                <Select
                  {...p}
                  value={metricChannelId}
                  onChange={(e) => setMetricChannelId(e.target.value ? Number(e.target.value) : '')}
                  options={[
                    { value: '', label: 'Chọn kênh...' },
                    ...campaign.channels.map((ch) => ({ value: String(ch.id), label: ch.name })),
                  ]}
                />
              )}
            </FormField>
            <FormField label="Ngày ghi nhận" required>
              {(p) => (
                <Input
                  {...p}
                  type="date"
                  value={metricDate}
                  onChange={(e) => setMetricDate(e.target.value)}
                />
              )}
            </FormField>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Lượt xem (Views)" required>
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  min="0"
                  value={metricViews ?? ''}
                  onChange={(e) => setMetricViews(e.target.value ? Number(e.target.value) : null)}
                />
              )}
            </FormField>
            <FormField label="Lượt bấm (Clicks)" required>
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  min="0"
                  value={metricClicks ?? ''}
                  onChange={(e) => setMetricClicks(e.target.value ? Number(e.target.value) : null)}
                />
              )}
            </FormField>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Chuyển đổi (Conversions)" required>
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  min="0"
                  value={metricConversions ?? ''}
                  onChange={(e) => setMetricConversions(e.target.value ? Number(e.target.value) : null)}
                />
              )}
            </FormField>
            <FormField label="Chi phí thực tế (VND)" required>
              {() => (
                <MoneyInput
                  value={metricCost}
                  onChange={setMetricCost}
                />
              )}
            </FormField>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" type="button" onClick={() => setIsCreatingMetric(false)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={createMetricMutation.isPending}>
              Lưu số liệu
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Delete Metric Confirm Dialog */}
      <ConfirmDialog
        open={!!deletingMetricId}
        title="Xoá bản ghi số liệu"
        confirmLabel="Xác nhận xoá"
        destructive
        loading={deleteMetricMutation.isPending}
        onClose={() => setDeletingMetricId(null)}
        onConfirm={() => {
          if (deletingMetricId) deleteMetricMutation.mutate(deletingMetricId);
        }}
      >
        <p className="text-sm text-fg-muted">
          Bạn có chắc chắn muốn xoá bản ghi số liệu này? Số liệu tổng hợp của chiến dịch sẽ được tính toán lại.
        </p>
      </ConfirmDialog>

      {/* CSV Import Preview & Commit Dialog */}
      <Dialog
        open={isImportingCsv}
        onClose={() => {
          setIsImportingCsv(false);
          setCsvPreview(null);
          setCsvError(null);
        }}
        title="Nhập số liệu từ tệp CSV"
        size="xl"
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-muted">
            Tải lên tệp CSV chứa số liệu hiệu quả. Cột bắt buộc: <code className="rounded bg-subtle px-1">date,campaign_id|campaign_name,channel_code,views,clicks,conversions,cost</code>.
          </p>

          <div className="flex items-center gap-3">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-border bg-subtle px-3.5 py-1.5 text-xs font-medium text-fg transition-colors hover:bg-border/60">
              <Upload className="h-3.5 w-3.5 text-fg-muted" />
              <span>Chọn tệp báo cáo (.csv)</span>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handlePreviewCsv(file);
                  }
                }}
                className="sr-only"
              />
            </label>
            {csvPreview && (
              <span className="text-xs font-medium text-fg-muted">
                Đã nạp dữ liệu kiểm tra ({csvPreview.summary.total} dòng)
              </span>
            )}
            {csvLoading && <span className="text-xs text-fg-muted">Đang xử lý tệp...</span>}
          </div>

          {csvError && <Callout tone="danger">{csvError}</Callout>}

          {csvPreview && (
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-3 text-center text-xs">
                <div className="rounded border border-border p-2">
                  <span className="text-fg-muted">Tổng dòng</span>
                  <p className="text-base font-semibold text-fg">{csvPreview.summary.total}</p>
                </div>
                <div className="rounded border border-border p-2">
                  <span className="text-fg-muted">Hợp lệ</span>
                  <p className="text-base font-semibold text-emerald-600 dark:text-emerald-400">
                    {csvPreview.summary.valid}
                  </p>
                </div>
                <div className="rounded border border-border p-2">
                  <span className="text-fg-muted">Lỗi</span>
                  <p className="text-base font-semibold text-rose-600 dark:text-rose-400">
                    {csvPreview.summary.invalid}
                  </p>
                </div>
                <div className="rounded border border-border p-2">
                  <span className="text-fg-muted">Cập nhật / Thêm</span>
                  <p className="text-base font-semibold text-fg">
                    {csvPreview.summary.updates} / {csvPreview.summary.inserts}
                  </p>
                </div>
              </div>

              {csvPreview.errors.length > 0 && (
                <div className="max-h-32 overflow-y-auto rounded border border-rose-200 bg-rose-50 p-2 text-xs text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300">
                  <p className="font-semibold">Danh sách dòng lỗi:</p>
                  <ul className="list-disc pl-4">
                    {csvPreview.errors.map((err, idx) => (
                      <li key={idx}>
                        Dòng {err.row}: {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="max-h-64 overflow-x-auto overflow-y-auto rounded border border-border text-xs">
                <Table>
                  <THead>
                    <TR>
                      <TH className="whitespace-nowrap">Dòng</TH>
                      <TH className="whitespace-nowrap">Ngày</TH>
                      <TH className="min-w-[230px]">Chiến dịch</TH>
                      <TH className="whitespace-nowrap">Kênh</TH>
                      <TH className="whitespace-nowrap text-right">Views</TH>
                      <TH className="whitespace-nowrap text-right">Clicks</TH>
                      <TH className="whitespace-nowrap text-right">Chuyển đổi</TH>
                      <TH className="whitespace-nowrap text-right">Chi phí</TH>
                      <TH className="whitespace-nowrap">Thao tác</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {csvPreview.rows.slice(0, 50).map((r) => (
                      <TR key={r.row}>
                        <TD className="whitespace-nowrap">{r.row}</TD>
                        <TD className="whitespace-nowrap">{formatDate(r.metric_date)}</TD>
                        <TD className="min-w-[230px] font-medium text-fg">{r.campaign_name}</TD>
                        <TD className="whitespace-nowrap">
                          <Badge tone="neutral">{r.channel_code}</Badge>
                        </TD>
                        <TD className="whitespace-nowrap text-right tabular-nums">{formatNumber(r.views)}</TD>
                        <TD className="whitespace-nowrap text-right tabular-nums">{formatNumber(r.clicks)}</TD>
                        <TD className="whitespace-nowrap text-right tabular-nums">{formatNumber(r.conversions)}</TD>
                        <TD className="whitespace-nowrap text-right font-medium tabular-nums">{formatMoney(r.cost)}</TD>
                        <TD className="whitespace-nowrap">{r.exists ? 'Cập nhật' : 'Thêm mới'}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setIsImportingCsv(false);
                    setCsvPreview(null);
                  }}
                >
                  Đóng
                </Button>
                <Button
                  variant="primary"
                  onClick={handleCommitCsv}
                  loading={csvLoading}
                  disabled={csvPreview.summary.valid === 0}
                >
                  Xác nhận nhập ({csvPreview.summary.valid} dòng hợp lệ)
                </Button>
              </div>
            </div>
          )}
        </div>
      </Dialog>
    </PageContainer>
  );
}
