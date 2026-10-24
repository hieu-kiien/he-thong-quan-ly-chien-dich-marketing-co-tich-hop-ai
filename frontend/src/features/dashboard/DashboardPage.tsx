import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  Eye,
  MousePointer,
  Target,
  DollarSign,
  Calendar,
  ArrowRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Card,
  CardHeader,
  CardBody,
  PageHeader,
  Button,
  Select,
  DateRangePicker,
  type DateRange,
  StatusBadge,
  SeedDataBadge,
  Table,
  THead,
  TBody,
  TR,
  TH,
  TD,
  Skeleton,
  SkeletonRows,
  ErrorState,
} from '@/components/ui';
import { statsApi, campaignsApi } from '@/lib/api/endpoints';
import { useChannels, useDocumentTitle } from '@/lib/hooks';
import { useAuth } from '@/lib/auth';
import { isManager } from '@/lib/permissions';
import { formatDate, formatMoney, formatNumber, formatPct, formatRate } from '@/lib/format';
import type { Granularity, StatsFilters } from '@/lib/types';

export default function DashboardPage() {
  useDocumentTitle('Tổng quan');
  const { user } = useAuth();

  // Filters state
  const [dateRange, setDateRange] = useState<DateRange>({ from: '', to: '' });
  const [campaignIdFilter, setCampaignIdFilter] = useState<string>('');
  const [channelIdFilter, setChannelIdFilter] = useState<string>('');
  const [granularity, setGranularity] = useState<Granularity>('day');
  const [chartMetric, setChartMetric] = useState<'views' | 'clicks' | 'conversions' | 'cost'>('views');

  const channelsQ = useChannels();
  const campaignsListQ = useQuery({
    queryKey: ['campaigns', { page_size: 100 }],
    queryFn: () => campaignsApi.list({ page_size: 100 }),
    staleTime: 5 * 60_000,
  });

  const filters: StatsFilters = {
    date_from: dateRange.from || undefined,
    date_to: dateRange.to || undefined,
    campaign_id: campaignIdFilter ? Number(campaignIdFilter) : undefined,
    channel_id: channelIdFilter ? Number(channelIdFilter) : undefined,
  };

  const overviewQ = useQuery({
    queryKey: ['stats', 'overview', filters],
    queryFn: () => statsApi.overview(filters),
  });

  const timeseriesQ = useQuery({
    queryKey: ['stats', 'timeseries', { ...filters, granularity }],
    queryFn: () => statsApi.timeseries({ ...filters, granularity }),
  });

  const byChannelQ = useQuery({
    queryKey: ['stats', 'by-channel', filters],
    queryFn: () => statsApi.byChannel(filters),
  });

  const byCampaignQ = useQuery({
    queryKey: ['stats', 'by-campaign', filters],
    queryFn: () => statsApi.byCampaign(filters),
  });

  // Helper date preset updater
  const setPreset = (days: number | 'month' | 'all') => {
    if (days === 'all') {
      setDateRange({ from: '', to: '' });
      return;
    }
    const today = new Date();
    const to = today.toISOString().slice(0, 10);
    if (days === 'month') {
      const from = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
      setDateRange({ from, to });
    } else {
      const past = new Date(today);
      past.setDate(past.getDate() - days);
      setDateRange({ from: past.toISOString().slice(0, 10), to });
    }
  };

  const overview = overviewQ.data;

  return (
    <PageContainer>
      <PageHeader
        title={
          <div className="flex flex-wrap items-center gap-3">
            <span>Tổng quan marketing</span>
            {overview?.has_seed_data && <SeedDataBadge />}
          </div>
        }
        description="Hiệu quả và chi phí chiến dịch tổng hợp từ số liệu đã nhập hoặc import."
      />

      {/* Filter bar */}
      <div className="mb-6 space-y-3 rounded-lg border border-border bg-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-fg-muted">Khoảng thời gian:</span>
            <Button variant="ghost" size="sm" onClick={() => setPreset(7)}>
              7 ngày qua
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setPreset(30)}>
              30 ngày qua
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setPreset('month')}>
              Tháng này
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setPreset('all')}>
              Toàn thời gian
            </Button>
          </div>
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </div>

        <div className="grid gap-3 pt-2 sm:grid-cols-2">
          <Select
            value={campaignIdFilter}
            onChange={(e) => setCampaignIdFilter(e.target.value)}
            options={[
              { value: '', label: 'Tất cả chiến dịch' },
              ...(campaignsListQ.data?.items ?? []).map((c) => ({ value: String(c.id), label: c.name })),
            ]}
          />
          <Select
            value={channelIdFilter}
            onChange={(e) => setChannelIdFilter(e.target.value)}
            options={[
              { value: '', label: 'Tất cả kênh triển khai' },
              ...(channelsQ.data ?? []).map((ch) => ({ value: String(ch.id), label: ch.name })),
            ]}
          />
        </div>
      </div>

      {overviewQ.isLoading ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </div>
          <Skeleton className="h-72" />
        </div>
      ) : overviewQ.isError ? (
        <ErrorState error={overviewQ.error} onRetry={() => overviewQ.refetch()} />
      ) : overview ? (
        <div className="space-y-6">
          {/* Top Summary Stat Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Lượt hiển thị (Views)</span>
                  <Eye className="h-4 w-4 text-fg-subtle" />
                </div>
                <p className="mt-2 text-2xl font-bold tracking-tight text-fg font-mono">
                  {formatNumber(overview.totals.views)}
                </p>
                <div className="mt-2 text-xs text-fg-muted">
                  CPM: <span className="font-medium text-fg">{formatMoney(overview.rates.cpm)}</span>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Lượt bấm (Clicks)</span>
                  <MousePointer className="h-4 w-4 text-fg-subtle" />
                </div>
                <p className="mt-2 text-2xl font-bold tracking-tight text-fg font-mono">
                  {formatNumber(overview.totals.clicks)}
                </p>
                <div className="mt-2 flex items-center justify-between text-xs text-fg-muted">
                  <span>CTR: <span className="font-medium text-fg">{formatRate(overview.rates.ctr)}</span></span>
                  <span>CPC: <span className="font-medium text-fg">{formatMoney(overview.rates.cpc)}</span></span>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Chuyển đổi (Conversions)</span>
                  <Target className="h-4 w-4 text-fg-subtle" />
                </div>
                <p className="mt-2 text-2xl font-bold tracking-tight text-fg font-mono">
                  {formatNumber(overview.totals.conversions)}
                </p>
                <div className="mt-2 flex items-center justify-between text-xs text-fg-muted">
                  <span>CVR: <span className="font-medium text-fg">{formatRate(overview.rates.cvr)}</span></span>
                  <span>CPA: <span className="font-medium text-fg">{formatMoney(overview.rates.cpa)}</span></span>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Tổng chi phí / Ngân sách</span>
                  <DollarSign className="h-4 w-4 text-fg-subtle" />
                </div>
                <p className="mt-2 text-xl font-bold tracking-tight text-fg font-mono">
                  {formatMoney(overview.budget.spent)}
                </p>
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-xs text-fg-muted">
                    <span>Ngân sách: {formatMoney(overview.budget.total_budget)}</span>
                    <span className="font-medium text-fg">{formatPct(overview.budget.used_pct)}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-subtle">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${Math.min(overview.budget.used_pct ?? 0, 100)}%` }}
                    />
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Operational Status Alerts & Quick Access */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardBody className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                    <Clock className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-fg">Nội dung chờ duyệt</h3>
                    <p className="text-xs text-fg-muted">
                      Có <span className="font-semibold text-fg">{overview.pending_reviews}</span> nội dung đang cần xem xét
                    </p>
                  </div>
                </div>
                <Link to={isManager(user) ? '/reviews' : '/contents?status=PENDING_REVIEW'}>
                  <Button variant="secondary" size="sm">
                    Xem danh sách
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </CardBody>
            </Card>

            <Card>
              <CardBody className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                    <Calendar className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-fg">Lịch đăng hôm nay</h3>
                    <p className="text-xs text-fg-muted">
                      Có <span className="font-semibold text-fg">{overview.schedules_today}</span> bài viết dự kiến đăng trong ngày
                    </p>
                  </div>
                </div>
                <Link to="/calendar">
                  <Button variant="secondary" size="sm">
                    Mở lịch đăng
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </CardBody>
            </Card>
          </div>

          {/* Timeseries Trend Chart */}
          <Card>
            <CardHeader
              title="Xu hướng tăng trưởng theo thời gian"
              description="Theo dõi biến động các chỉ số chính của chiến dịch theo ngày, tuần hoặc tháng."
              actions={
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex rounded-md border border-border p-0.5">
                    <button
                      type="button"
                      className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                        chartMetric === 'views' ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg'
                      }`}
                      onClick={() => setChartMetric('views')}
                    >
                      Lượt xem
                    </button>
                    <button
                      type="button"
                      className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                        chartMetric === 'clicks' ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg'
                      }`}
                      onClick={() => setChartMetric('clicks')}
                    >
                      Lượt bấm
                    </button>
                    <button
                      type="button"
                      className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                        chartMetric === 'conversions' ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg'
                      }`}
                      onClick={() => setChartMetric('conversions')}
                    >
                      Chuyển đổi
                    </button>
                    <button
                      type="button"
                      className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                        chartMetric === 'cost' ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg'
                      }`}
                      onClick={() => setChartMetric('cost')}
                    >
                      Chi phí
                    </button>
                  </div>

                  <div className="flex rounded-md border border-border p-0.5">
                    <button
                      type="button"
                      className={`rounded px-2 py-1 text-xs font-medium ${
                        granularity === 'day' ? 'bg-subtle text-fg font-semibold' : 'text-fg-muted'
                      }`}
                      onClick={() => setGranularity('day')}
                    >
                      Ngày
                    </button>
                    <button
                      type="button"
                      className={`rounded px-2 py-1 text-xs font-medium ${
                        granularity === 'week' ? 'bg-subtle text-fg font-semibold' : 'text-fg-muted'
                      }`}
                      onClick={() => setGranularity('week')}
                    >
                      Tuần
                    </button>
                    <button
                      type="button"
                      className={`rounded px-2 py-1 text-xs font-medium ${
                        granularity === 'month' ? 'bg-subtle text-fg font-semibold' : 'text-fg-muted'
                      }`}
                      onClick={() => setGranularity('month')}
                    >
                      Tháng
                    </button>
                  </div>
                </div>
              }
            />
            <CardBody>
              {timeseriesQ.isLoading ? (
                <div className="h-72 flex items-center justify-center">
                  <Skeleton className="h-64 w-full" />
                </div>
              ) : !timeseriesQ.data || timeseriesQ.data.length === 0 ? (
                <div className="flex h-64 items-center justify-center text-sm text-fg-muted">
                  Không có dữ liệu thời gian cho khoảng lọc đã chọn.
                </div>
              ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={timeseriesQ.data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="metricGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--color-accent, #44403c)" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="var(--color-accent, #44403c)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color, #e7e5e4)" />
                      <XAxis
                        dataKey="period"
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 12, fill: 'currentColor' }}
                        className="text-fg-subtle"
                        tickFormatter={(val) => formatDate(val)}
                      />
                      <YAxis
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 12, fill: 'currentColor' }}
                        className="text-fg-subtle"
                        tickFormatter={(val) =>
                          chartMetric === 'cost' ? formatMoney(val) : formatNumber(val)
                        }
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'var(--surface-color, #ffffff)',
                          borderColor: 'var(--border-color, #e7e5e4)',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        labelFormatter={(val) => `Thời gian: ${formatDate(String(val))}`}
                        formatter={(val: number) => [
                          chartMetric === 'cost' ? formatMoney(val) : formatNumber(val),
                          chartMetric === 'views'
                            ? 'Lượt xem'
                            : chartMetric === 'clicks'
                              ? 'Lượt bấm'
                              : chartMetric === 'conversions'
                                ? 'Chuyển đổi'
                                : 'Chi phí',
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey={chartMetric}
                        stroke="var(--color-accent, #44403c)"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#metricGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Breakdown by Channel & by Campaign */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Channel Performance Table */}
            <Card>
              <CardHeader
                title="Hiệu quả theo kênh triển khai"
                description="Tổng hợp số liệu tương tác và chi phí phân bổ cho từng kênh."
              />
              <div className="overflow-x-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>Kênh</TH>
                      <TH className="text-right">Hiển thị</TH>
                      <TH className="text-right">Bấm</TH>
                      <TH className="text-right">CTR</TH>
                      <TH className="text-right">Chuyển đổi</TH>
                      <TH className="text-right">Chi phí</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {byChannelQ.isLoading ? (
                      <TR>
                        <TD colSpan={6}>
                          <SkeletonRows rows={4} />
                        </TD>
                      </TR>
                    ) : !byChannelQ.data || byChannelQ.data.length === 0 ? (
                      <TR>
                        <TD colSpan={6} className="py-6 text-center text-xs text-fg-muted">
                          Chưa có dữ liệu kênh trong khoảng thời gian này.
                        </TD>
                      </TR>
                    ) : (
                      byChannelQ.data.map((c) => (
                        <TR key={c.channel.id}>
                          <TD className="font-medium text-fg">{c.channel.name}</TD>
                          <TD className="text-right text-xs font-mono">{formatNumber(c.views)}</TD>
                          <TD className="text-right text-xs font-mono">{formatNumber(c.clicks)}</TD>
                          <TD className="text-right text-xs font-mono">{formatRate(c.ctr)}</TD>
                          <TD className="text-right text-xs font-mono">{formatNumber(c.conversions)}</TD>
                          <TD className="text-right text-xs font-mono font-medium">{formatMoney(c.cost)}</TD>
                        </TR>
                      ))
                    )}
                  </TBody>
                </Table>
              </div>
            </Card>

            {/* Campaign Budget Usage Table */}
            <Card>
              <CardHeader
                title="Tiến độ ngân sách chiến dịch"
                description="So sánh chi phí thực tế phát sinh với ngân sách đã phân bổ."
              />
              <div className="overflow-x-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>Chiến dịch</TH>
                      <TH className="text-right">Ngân sách</TH>
                      <TH className="text-right">Đã chi</TH>
                      <TH className="text-right">Tỷ lệ</TH>
                      <TH>Trạng thái</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {byCampaignQ.isLoading ? (
                      <TR>
                        <TD colSpan={5}>
                          <SkeletonRows rows={4} />
                        </TD>
                      </TR>
                    ) : !byCampaignQ.data || byCampaignQ.data.length === 0 ? (
                      <TR>
                        <TD colSpan={5} className="py-6 text-center text-xs text-fg-muted">
                          Chưa có dữ liệu chiến dịch trong khoảng thời gian này.
                        </TD>
                      </TR>
                    ) : (
                      byCampaignQ.data.map((item) => (
                        <TR key={item.campaign.id}>
                          <TD>
                            <Link
                              to={`/campaigns/${item.campaign.id}`}
                              className="font-medium text-fg hover:underline"
                            >
                              {item.campaign.name}
                            </Link>
                          </TD>
                          <TD className="text-right text-xs font-mono">{formatMoney(item.budget)}</TD>
                          <TD className="text-right text-xs font-mono font-medium">{formatMoney(item.cost)}</TD>
                          <TD className="text-right text-xs font-mono">
                            <span
                              className={
                                (item.used_pct ?? 0) > 100
                                  ? 'font-semibold text-rose-600 dark:text-rose-400'
                                  : (item.used_pct ?? 0) > 85
                                    ? 'text-amber-600 dark:text-amber-400'
                                    : 'text-fg'
                              }
                            >
                              {formatPct(item.used_pct)}
                            </span>
                          </TD>
                          <TD>
                            <StatusBadge kind="campaign" status={item.campaign.status} />
                          </TD>
                        </TR>
                      ))
                    )}
                  </TBody>
                </Table>
              </div>
            </Card>
          </div>
        </div>
      ) : null}
    </PageContainer>
  );
}
