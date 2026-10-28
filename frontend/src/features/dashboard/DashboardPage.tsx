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
  Sparkles,
  Download,
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
import { openContextualCopilot } from '@/features/assistant/CopilotDrawer';
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
import {
  addDays,
  formatDate,
  formatMoney,
  formatNumber,
  formatPct,
  formatRate,
  startOfMonth,
  todayKey,
} from '@/lib/format';
import type { Granularity, StatsFilters } from '@/lib/types';

/** Biểu đồ đường thu nhỏ (Sparkline) hiển thị xu hướng ngay trong thẻ KPI. */
function MiniSparkline({
  values,
  color = 'var(--chart-1, #2563EB)',
}: {
  values: number[];
  color?: string;
}) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 84;
  const height = 28;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - 3 - ((v - min) / range) * (height - 6);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="shrink-0 overflow-visible" aria-hidden>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={pts}
      />
    </svg>
  );
}

export default function DashboardPage() {
  useDocumentTitle('Tổng quan');
  const { user } = useAuth();

  // Filters state
  const [dateRange, setDateRange] = useState<DateRange>({ from: '', to: '' });
  const [campaignIdFilter, setCampaignIdFilter] = useState<string>('');
  const [channelIdFilter, setChannelIdFilter] = useState<string>('');
  const [granularity, setGranularity] = useState<Granularity>('day');
  const [chartMetric, setChartMetric] = useState<'views' | 'clicks' | 'conversions' | 'cost'>('views');
  const [hoveredMetricMode, setHoveredMetricMode] = useState<'views' | 'clicks' | 'conversions' | 'cost' | null>(null);

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
    // Tính theo NGÀY VIỆT NAM (toISOString() dùng UTC nên lệch ngày trước 07:00 sáng)
    const to = todayKey();
    setDateRange({ from: days === 'month' ? startOfMonth(to) : addDays(to, -days), to });
  };

  const overview = overviewQ.data;

  const handleExportReport = () => {
    if (!overview) return;
    const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const rows: string[] = [
      ['BÁO CÁO TỔNG QUAN HIỆU QUẢ MARKETING - MARKETFLOW'].map(esc).join(','),
      ['Ngày xuất báo cáo', formatDate(todayKey())].map(esc).join(','),
      '',
      ['1. CHỈ SỐ TỔNG HỢP'].map(esc).join(','),
      ['Lượt hiển thị (Views)', 'Lượt nhấp (Clicks)', 'Chuyển đổi (Conversions)', 'Tổng chi phí (VNĐ)', 'CTR (%)', 'CPC (VNĐ)', 'CPA (VNĐ)', 'CPM (VNĐ)'].map(esc).join(','),
      [
        overview.totals.views,
        overview.totals.clicks,
        overview.totals.conversions,
        overview.totals.cost,
        overview.rates.ctr !== null ? (overview.rates.ctr * 100).toFixed(2) : '0.00',
        overview.rates.cpc ?? 0,
        overview.rates.cpa ?? 0,
        overview.rates.cpm ?? 0,
      ].map(esc).join(','),
      '',
      ['2. HIỆU QUẢ THEO CHIẾN DỊCH'].map(esc).join(','),
      ['Mã CD', 'Tên chiến dịch', 'Trạng thái', 'Ngân sách (VNĐ)', 'Chi phí thực tế (VNĐ)', 'Lượt hiển thị', 'Lượt nhấp', 'Chuyển đổi', 'CTR (%)', 'CPA (VNĐ)'].map(esc).join(','),
      ...(byCampaignQ.data ?? []).map((c) =>
        [
          c.campaign.id,
          c.campaign.name,
          c.campaign.status,
          c.budget,
          c.cost,
          c.views,
          c.clicks,
          c.conversions,
          c.ctr !== null ? (c.ctr * 100).toFixed(2) : '0.00',
          c.cpa ?? 0,
        ].map(esc).join(',')
      ),
      '',
      ['3. HIỆU QUẢ THEO KÊNH TRIỂN KHAI'].map(esc).join(','),
      ['Kênh', 'Lượt hiển thị', 'Lượt nhấp', 'Chuyển đổi', 'Chi phí (VNĐ)', 'CTR (%)', 'CPC (VNĐ)', 'CPA (VNĐ)'].map(esc).join(','),
      ...(byChannelQ.data ?? []).map((ch) =>
        [
          ch.channel.name,
          ch.views,
          ch.clicks,
          ch.conversions,
          ch.cost,
          ch.ctr !== null ? (ch.ctr * 100).toFixed(2) : '0.00',
          ch.cpc ?? 0,
          ch.cpa ?? 0,
        ].map(esc).join(',')
      ),
    ];
    const blob = new Blob(['\uFEFF' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bao-cao-marketing-${todayKey()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={handleExportReport} disabled={!overview}>
              <Download className="h-4 w-4" />
              Xuất báo cáo Excel
            </Button>
            <Button
              variant="primary"
              onClick={() =>
                openContextualCopilot({
                  prompt:
                    'Hãy lập báo cáo phân tích tổng quan hiệu quả các chiến dịch marketing hiện tại, chỉ ra kênh hiệu quả nhất, chiến dịch cần tối ưu chi phí CPA và đề xuất hành động cụ thể.',
                })
              }
            >
              <Sparkles className="h-4 w-4" />
              Báo cáo AI chuyên sâu
            </Button>
          </div>
        }
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
          {/* Top Summary Stat Cards (kèm Sparkline & tương tác lọc nhanh biểu đồ) */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card
              className={`cursor-pointer transition-all ${
                chartMetric === 'views' ? 'ring-1 ring-accent/40 border-accent/40' : 'hover:border-border-strong'
              }`}
              onClick={() => setChartMetric('views')}
              onMouseEnter={() => setHoveredMetricMode('views')}
              onMouseLeave={() => setHoveredMetricMode(null)}
            >
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Lượt hiển thị (Views)</span>
                  <Eye className="h-4 w-4 text-accent" />
                </div>
                <div className="mt-2 flex items-end justify-between gap-2">
                  <p className="text-2xl font-semibold tracking-tight text-fg font-mono tabular-nums">
                    {formatNumber(overview.totals.views)}
                  </p>
                  <MiniSparkline
                    values={(timeseriesQ.data ?? []).map((d) => d.views)}
                    color="var(--chart-1, #2563EB)"
                  />
                </div>
                <div className="mt-2 text-xs text-fg-muted tabular-nums">
                  CPM: <span className="font-medium text-fg">{formatMoney(overview.rates.cpm)}</span>
                </div>
              </CardBody>
            </Card>

            <Card
              className={`cursor-pointer transition-all ${
                chartMetric === 'clicks' ? 'ring-1 ring-accent/40 border-accent/40' : 'hover:border-border-strong'
              }`}
              onClick={() => setChartMetric('clicks')}
              onMouseEnter={() => setHoveredMetricMode('clicks')}
              onMouseLeave={() => setHoveredMetricMode(null)}
            >
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Lượt bấm (Clicks)</span>
                  <MousePointer className="h-4 w-4 text-accent" />
                </div>
                <div className="mt-2 flex items-end justify-between gap-2">
                  <p className="text-2xl font-semibold tracking-tight text-fg font-mono tabular-nums">
                    {formatNumber(overview.totals.clicks)}
                  </p>
                  <MiniSparkline
                    values={(timeseriesQ.data ?? []).map((d) => d.clicks)}
                    color="var(--chart-1, #2563EB)"
                  />
                </div>
                <div className="mt-2 flex items-center justify-between text-xs text-fg-muted tabular-nums">
                  <span>CTR: <span className="font-medium text-fg">{formatRate(overview.rates.ctr)}</span></span>
                  <span>CPC: <span className="font-medium text-fg">{formatMoney(overview.rates.cpc)}</span></span>
                </div>
              </CardBody>
            </Card>

            <Card
              className={`cursor-pointer transition-all ${
                chartMetric === 'conversions' ? 'ring-1 ring-ai/40 border-ai/40' : 'hover:border-border-strong'
              }`}
              onClick={() => setChartMetric('conversions')}
              onMouseEnter={() => setHoveredMetricMode('conversions')}
              onMouseLeave={() => setHoveredMetricMode(null)}
            >
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Chuyển đổi (Conversions)</span>
                  <Target className="h-4 w-4 text-ai" />
                </div>
                <div className="mt-2 flex items-end justify-between gap-2">
                  <p className="text-2xl font-semibold tracking-tight text-fg font-mono tabular-nums">
                    {formatNumber(overview.totals.conversions)}
                  </p>
                  <MiniSparkline
                    values={(timeseriesQ.data ?? []).map((d) => d.conversions)}
                    color="var(--chart-2, #0D9488)"
                  />
                </div>
                <div className="mt-2 flex items-center justify-between text-xs text-fg-muted tabular-nums">
                  <span>CVR: <span className="font-medium text-fg">{formatRate(overview.rates.cvr)}</span></span>
                  <span>CPA: <span className="font-medium text-fg">{formatMoney(overview.rates.cpa)}</span></span>
                </div>
              </CardBody>
            </Card>

            <Card
              className={`cursor-pointer transition-all ${
                chartMetric === 'cost' ? 'ring-1 ring-warning/40 border-warning/40' : 'hover:border-border-strong'
              }`}
              onClick={() => setChartMetric('cost')}
              onMouseEnter={() => setHoveredMetricMode('cost')}
              onMouseLeave={() => setHoveredMetricMode(null)}
            >
              <CardBody>
                <div className="flex items-center justify-between text-xs text-fg-muted">
                  <span>Tổng chi phí / Ngân sách</span>
                  <DollarSign className="h-4 w-4 text-warning" />
                </div>
                <div className="mt-2 flex items-end justify-between gap-2">
                  <p className="text-xl font-semibold tracking-tight text-fg font-mono tabular-nums">
                    {formatMoney(overview.budget.spent)}
                  </p>
                  <MiniSparkline
                    values={(timeseriesQ.data ?? []).map((d) => d.cost)}
                    color="var(--chart-3, #D97706)"
                  />
                </div>
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-xs text-fg-muted tabular-nums">
                    <span>Ngân sách: {formatMoney(overview.budget.total_budget)}</span>
                    <span className="font-medium text-fg">{formatPct(overview.budget.used_pct)}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-subtle">
                    <div
                      className="h-full rounded-full bg-warning"
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
                          <stop
                            offset="5%"
                            stopColor={
                              chartMetric === 'conversions'
                                ? 'var(--chart-2, #0D9488)'
                                : chartMetric === 'cost'
                                  ? 'var(--chart-3, #D97706)'
                                  : 'var(--chart-1, #2563EB)'
                            }
                            stopOpacity={0.22}
                          />
                          <stop
                            offset="95%"
                            stopColor={
                              chartMetric === 'conversions'
                                ? 'var(--chart-2, #0D9488)'
                                : chartMetric === 'cost'
                                  ? 'var(--chart-3, #D97706)'
                                  : 'var(--chart-1, #2563EB)'
                            }
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid, #E2E8F0)" />
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
                          backgroundColor: 'var(--bg-surface, #FFFFFF)',
                          borderColor: 'var(--border-subtle, #E2E8F0)',
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
                        stroke={
                          chartMetric === 'conversions'
                            ? 'var(--chart-2, #0D9488)'
                            : chartMetric === 'cost'
                              ? 'var(--chart-3, #D97706)'
                              : 'var(--chart-1, #2563EB)'
                        }
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
          <div className="contain-panel grid gap-6 lg:grid-cols-2">
            {/* Channel Performance Table */}
            <Card>
              <CardHeader
                title="Hiệu quả theo kênh triển khai"
                description="Tổng hợp số liệu tương tác và chi phí phân bổ cho từng kênh."
              />
              <Table className="rounded-none border-0">
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
                        <TR
                          key={c.channel.id}
                          className={
                            hoveredMetricMode === 'conversions' && c.conversions > 0
                              ? 'bg-ai-soft/40'
                              : hoveredMetricMode === 'cost' && c.cost > 0
                                ? 'bg-warning-soft/40'
                                : ''
                          }
                        >
                          <TD className="font-medium text-fg">{c.channel.name}</TD>
                          <TD className="text-right text-xs font-mono tabular-nums">{formatNumber(c.views)}</TD>
                          <TD className="text-right text-xs font-mono tabular-nums">{formatNumber(c.clicks)}</TD>
                          <TD className="text-right text-xs font-mono tabular-nums">{formatRate(c.ctr)}</TD>
                          <TD className="text-right text-xs font-mono tabular-nums">{formatNumber(c.conversions)}</TD>
                          <TD className="text-right text-xs font-mono font-medium tabular-nums">{formatMoney(c.cost)}</TD>
                        </TR>
                      ))
                    )}
                  </TBody>
                </Table>
            </Card>

            {/* Campaign Budget Usage Table */}
            <Card>
              <CardHeader
                title="Tiến độ ngân sách chiến dịch"
                description="So sánh chi phí thực tế phát sinh với ngân sách đã phân bổ."
              />
              <Table className="rounded-none border-0">
                  <THead>
                    <TR>
                      <TH>Chiến dịch</TH>
                      <TH className="text-right">Ngân sách</TH>
                      <TH className="text-right">Đã chi</TH>
                      <TH className="text-right">Tỷ lệ</TH>
                      <TH>Trạng thái</TH>
                      <TH className="text-right">Tác vụ AI</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {byCampaignQ.isLoading ? (
                      <TR>
                        <TD colSpan={6}>
                          <SkeletonRows rows={4} />
                        </TD>
                      </TR>
                    ) : !byCampaignQ.data || byCampaignQ.data.length === 0 ? (
                      <TR>
                        <TD colSpan={6} className="py-6 text-center text-xs text-fg-muted">
                          Chưa có dữ liệu chiến dịch trong khoảng thời gian này.
                        </TD>
                      </TR>
                    ) : (
                      byCampaignQ.data.map((item) => {
                        const isOverOrHigh = (item.used_pct ?? 0) > 85;
                        return (
                          <TR key={item.campaign.id} className="group">
                            <TD className="min-w-[160px] max-w-[220px]">
                              <Link
                                to={`/campaigns/${item.campaign.id}`}
                                className="line-clamp-1 font-medium text-fg hover:text-accent hover:underline"
                                title={item.campaign.name}
                              >
                                {item.campaign.name}
                              </Link>
                            </TD>
                            <TD className="whitespace-nowrap text-right text-xs font-mono tabular-nums">{formatMoney(item.budget)}</TD>
                            <TD className="whitespace-nowrap text-right text-xs font-mono font-medium tabular-nums">{formatMoney(item.cost)}</TD>
                            <TD className="whitespace-nowrap text-right text-xs font-mono tabular-nums">
                              <span
                                className={
                                  (item.used_pct ?? 0) > 100
                                    ? 'font-semibold text-danger'
                                    : (item.used_pct ?? 0) > 85
                                      ? 'font-medium text-warning'
                                      : 'text-fg'
                                }
                              >
                                {formatPct(item.used_pct)}
                              </span>
                            </TD>
                            <TD className="whitespace-nowrap">
                              <StatusBadge kind="campaign" status={item.campaign.status} />
                            </TD>
                            <TD className="whitespace-nowrap text-right">
                              <button
                                type="button"
                                onClick={() =>
                                  openContextualCopilot({
                                    campaignId: item.campaign.id,
                                    campaignName: item.campaign.name,
                                    prompt: isOverOrHigh
                                      ? `Phân tích nguyên nhân chi phí chiến dịch "${item.campaign.name}" đã dùng ${formatPct(item.used_pct)} ngân sách (${formatMoney(item.cost)} / ${formatMoney(item.budget)}) và đề xuất phương án tối ưu ngân sách ngay.`
                                      : `Đánh giá hiệu quả hiện tại của chiến dịch "${item.campaign.name}" và đề xuất cách tối ưu tỷ lệ chuyển đổi.`,
                                  })
                                }
                                className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-ai/30 bg-ai-soft px-2 py-1 text-[11px] font-medium text-ai-soft-fg transition-colors hover:bg-ai hover:text-ai-fg"
                              >
                                <Sparkles className="h-3 w-3 shrink-0" aria-hidden />
                                <span>{isOverOrHigh ? 'Phân tích AI' : 'Tối ưu AI'}</span>
                              </button>
                            </TD>
                          </TR>
                        );
                      })
                    )}
                  </TBody>
                </Table>
            </Card>
          </div>
        </div>
      ) : null}
    </PageContainer>
  );
}
