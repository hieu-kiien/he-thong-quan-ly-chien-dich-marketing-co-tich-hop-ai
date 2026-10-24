import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Button,
  IconButton,
  StatusBadge,
  Badge,
  PageHeader,
  Dialog,
  FormField,
  Input,
  Select,
  Textarea,
  useToast,
  ErrorState,
  Skeleton,
} from '@/components/ui';
import { schedulesApi, contentsApi, campaignsApi } from '@/lib/api/endpoints';
import { useChannels, useUserOptions, useDocumentTitle } from '@/lib/hooks';
import { formatDateTime, formatTime } from '@/lib/format';
import {
  SCHEDULE_STATUS_LABEL,
} from '@/lib/labels';
import type {
  Content,
  Schedule,
  ScheduleCreate,
  ScheduleFilters,
  ScheduleStatus,
} from '@/lib/types';

type ViewMode = 'month' | 'week';

export default function CalendarPage() {
  useDocumentTitle('Lịch đăng bài');
  const queryClient = useQueryClient();
  const toast = useToast();

  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [viewMode, setViewMode] = useState<ViewMode>('month');

  // Filters
  const [campaignFilter, setCampaignFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [assigneeFilter, setAssigneeFilter] = useState<string>('');

  // Selected schedule for detail modal
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(null);
  const [isMarkingDone, setIsMarkingDone] = useState(false);
  const [doneUrl, setDoneUrl] = useState('');

  // Create schedule modal
  const [isCreating, setIsCreating] = useState(false);
  const [newContentId, setNewContentId] = useState<number | ''>('');
  const [newScheduledAt, setNewScheduledAt] = useState('');
  const [newAssigneeId, setNewAssigneeId] = useState<number | ''>('');
  const [newNote, setNewNote] = useState('');

  const channelsQ = useChannels();
  const usersOpt = useUserOptions();
  const campaignsListQ = useQuery({
    queryKey: ['campaigns', { page_size: 100 }],
    queryFn: () => campaignsApi.list({ page_size: 100 }),
    staleTime: 5 * 60_000,
  });

  // Approved contents query for schedule creation
  const approvedContentsQ = useQuery({
    queryKey: ['contents', { status: 'APPROVED', page_size: 100 }],
    queryFn: () => contentsApi.list({ status: 'APPROVED', page_size: 100 }),
    enabled: isCreating,
  });

  // Calculate range bounds for current view
  const { dateFrom, dateTo, calendarDays } = useMemo(() => {
    const y = currentDate.getFullYear();
    const m = currentDate.getMonth();

    if (viewMode === 'month') {
      const firstDay = new Date(y, m, 1);
      const lastDay = new Date(y, m + 1, 0);

      // Start on Monday (VN standard)
      const startOffset = (firstDay.getDay() + 6) % 7;
      const startDate = new Date(y, m, 1 - startOffset);

      // End on Sunday
      const endOffset = (7 - ((lastDay.getDay() + 6) % 7) - 1) % 7;
      const endDate = new Date(y, m + 1, endOffset);

      const days: Date[] = [];
      const cur = new Date(startDate);
      while (cur <= endDate) {
        days.push(new Date(cur));
        cur.setDate(cur.getDate() + 1);
      }

      return {
        dateFrom: startDate.toISOString().slice(0, 10),
        dateTo: endDate.toISOString().slice(0, 10),
        calendarDays: days,
      };
    } else {
      // Week view
      const dayOfWeek = (currentDate.getDay() + 6) % 7;
      const startOfWeek = new Date(currentDate);
      startOfWeek.setDate(currentDate.getDate() - dayOfWeek);

      const days: Date[] = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(startOfWeek);
        d.setDate(startOfWeek.getDate() + i);
        days.push(d);
      }

      const endOfWeek = days[6];
      return {
        dateFrom: startOfWeek.toISOString().slice(0, 10),
        dateTo: endOfWeek.toISOString().slice(0, 10),
        calendarDays: days,
      };
    }
  }, [currentDate, viewMode]);

  const filters: ScheduleFilters = {
    date_from: dateFrom,
    date_to: dateTo,
    campaign_id: campaignFilter ? Number(campaignFilter) : undefined,
    channel_id: channelFilter ? Number(channelFilter) : undefined,
    status: (statusFilter as ScheduleStatus) || undefined,
    assignee_id: assigneeFilter ? Number(assigneeFilter) : undefined,
  };

  const { data: schedules, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['schedules', filters],
    queryFn: () => schedulesApi.list(filters),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (body: ScheduleCreate) => schedulesApi.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success('Lập lịch đăng bài thành công');
      setIsCreating(false);
      setNewContentId('');
      setNewScheduledAt('');
      setNewAssigneeId('');
      setNewNote('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi lập lịch');
    },
  });

  const markDoneMutation = useMutation({
    mutationFn: ({ id, url }: { id: number; url?: string | null }) =>
      schedulesApi.done(id, url),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      toast.success('Đã đánh dấu hoàn thành bài đăng');
      setIsMarkingDone(false);
      setSelectedSchedule(null);
      setDoneUrl('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi cập nhật lịch đăng');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => schedulesApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success('Đã huỷ lịch đăng');
      setSelectedSchedule(null);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi huỷ lịch');
    },
  });

  // Navigation handlers
  const handlePrev = () => {
    setCurrentDate((d) => {
      const next = new Date(d);
      if (viewMode === 'month') {
        next.setMonth(next.getMonth() - 1);
      } else {
        next.setDate(next.getDate() - 7);
      }
      return next;
    });
  };

  const handleNext = () => {
    setCurrentDate((d) => {
      const next = new Date(d);
      if (viewMode === 'month') {
        next.setMonth(next.getMonth() + 1);
      } else {
        next.setDate(next.getDate() + 7);
      }
      return next;
    });
  };

  const handleToday = () => {
    setCurrentDate(new Date());
  };

  // Group schedules by date key (YYYY-MM-DD)
  const schedulesByDay = useMemo(() => {
    const map: Record<string, Schedule[]> = {};
    (schedules ?? []).forEach((s) => {
      const dayKey = s.scheduled_at.slice(0, 10);
      if (!map[dayKey]) map[dayKey] = [];
      map[dayKey].push(s);
    });
    return map;
  }, [schedules]);

  const monthLabel = `Tháng ${currentDate.getMonth() + 1}, ${currentDate.getFullYear()}`;
  const dayNames = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'];
  const todayIso = new Date().toISOString().slice(0, 10);

  return (
    <PageContainer>
      <PageHeader
        title="Lịch đăng bài"
        description="Theo dõi và điều phối lịch xuất bản nội dung tiếp thị theo tuần và tháng."
        actions={
          <Button variant="primary" onClick={() => setIsCreating(true)}>
            <Plus className="h-4 w-4" />
            Lập lịch mới
          </Button>
        }
      />

      {/* Filter and View Controls Bar */}
      <div className="mb-6 space-y-3 rounded-lg border border-border bg-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <IconButton label="Trước" size="sm" onClick={handlePrev}>
              <ChevronLeft className="h-4 w-4" />
            </IconButton>
            <h2 className="min-w-44 text-center text-base font-semibold text-fg">{monthLabel}</h2>
            <IconButton label="Sau" size="sm" onClick={handleNext}>
              <ChevronRight className="h-4 w-4" />
            </IconButton>
            <Button variant="ghost" size="sm" onClick={handleToday}>
              Hôm nay
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex rounded-md border border-border p-0.5">
              <button
                type="button"
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  viewMode === 'month' ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg'
                }`}
                onClick={() => setViewMode('month')}
              >
                Tháng
              </button>
              <button
                type="button"
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  viewMode === 'week' ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg'
                }`}
                onClick={() => setViewMode('week')}
              >
                Tuần
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-3 pt-2 sm:grid-cols-2 lg:grid-cols-4">
          <Select
            value={campaignFilter}
            onChange={(e) => setCampaignFilter(e.target.value)}
            options={[
              { value: '', label: 'Tất cả chiến dịch' },
              ...(campaignsListQ.data?.items ?? []).map((c) => ({ value: String(c.id), label: c.name })),
            ]}
          />
          <Select
            value={channelFilter}
            onChange={(e) => setChannelFilter(e.target.value)}
            options={[
              { value: '', label: 'Tất cả kênh' },
              ...(channelsQ.data ?? []).map((ch) => ({ value: String(ch.id), label: ch.name })),
            ]}
          />
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            options={[
              { value: '', label: 'Tất cả trạng thái' },
              { value: 'PLANNED', label: SCHEDULE_STATUS_LABEL.PLANNED },
              { value: 'DONE', label: SCHEDULE_STATUS_LABEL.DONE },
              { value: 'CANCELLED', label: SCHEDULE_STATUS_LABEL.CANCELLED },
            ]}
          />
          {usersOpt.enabled && (
            <Select
              value={assigneeFilter}
              onChange={(e) => setAssigneeFilter(e.target.value)}
              options={[
                { value: '', label: 'Tất cả người phụ trách' },
                ...usersOpt.users.map((u) => ({ value: String(u.id), label: u.full_name })),
              ]}
            />
          )}
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-[600px] w-full rounded-lg" />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-sm">
          {/* Calendar Header: Day Names */}
          <div className="grid grid-cols-7 border-b border-border bg-subtle text-center text-xs font-semibold text-fg-muted">
            {dayNames.map((name, i) => (
              <div key={i} className="py-2.5">
                {name}
              </div>
            ))}
          </div>

          {/* Calendar Grid */}
          <div className={`grid grid-cols-7 divide-x divide-y divide-border ${viewMode === 'month' ? 'auto-rows-fr' : 'min-h-[450px]'}`}>
            {calendarDays.map((day, idx) => {
              const dayStr = day.toISOString().slice(0, 10);
              const isToday = dayStr === todayIso;
              const isCurrentMonth = day.getMonth() === currentDate.getMonth();
              const items = schedulesByDay[dayStr] ?? [];

              return (
                <div
                  key={idx}
                  className={`min-h-[110px] p-2 transition-colors ${
                    !isCurrentMonth ? 'bg-canvas/50 text-fg-subtle' : 'bg-surface'
                  } ${isToday ? 'bg-accent/5 font-semibold' : ''}`}
                >
                  <div className="flex items-center justify-between pb-1">
                    <span
                      className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                        isToday
                          ? 'bg-accent text-accent-fg'
                          : isCurrentMonth
                            ? 'text-fg'
                            : 'text-fg-subtle'
                      }`}
                    >
                      {day.getDate()}
                    </span>
                    {items.length > 0 && (
                      <span className="text-[10px] text-fg-subtle">{items.length} bài</span>
                    )}
                  </div>

                  {/* Scheduled Items List for this day */}
                  <div className="space-y-1">
                    {items.slice(0, 3).map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setSelectedSchedule(item)}
                        className={`w-full truncate rounded px-1.5 py-1 text-left text-[11px] transition-colors ${
                          item.status === 'DONE'
                            ? 'bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-300'
                            : item.status === 'CANCELLED'
                              ? 'bg-stone-200/50 text-fg-subtle line-through hover:bg-stone-200 dark:bg-stone-800'
                              : 'bg-blue-500/10 text-blue-700 hover:bg-blue-500/20 dark:text-blue-300'
                        }`}
                      >
                        <span className="font-mono font-medium">{formatTime(item.scheduled_at)}</span>{' '}
                        <span>[{item.channel.name}]</span> {item.content.title}
                      </button>
                    ))}
                    {items.length > 3 && (
                      <p className="text-[10px] text-fg-subtle">
                        + {items.length - 3} bài nữa...
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Schedule Detail Modal */}
      <Dialog
        open={!!selectedSchedule}
        onClose={() => {
          setSelectedSchedule(null);
          setIsMarkingDone(false);
        }}
        title="Chi tiết lịch đăng bài"
        size="md"
      >
        {selectedSchedule && (
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <StatusBadge kind="schedule" status={selectedSchedule.status} />
                <Badge tone="neutral">{selectedSchedule.channel.name}</Badge>
              </div>
              <h3 className="text-base font-semibold text-fg">
                <Link
                  to={`/contents/${selectedSchedule.content.id}`}
                  className="hover:underline"
                >
                  {selectedSchedule.content.title}
                </Link>
              </h3>
            </div>

            <div className="rounded-lg border border-border bg-subtle p-3 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-fg-muted">Chiến dịch:</span>
                <Link to={`/campaigns/${selectedSchedule.campaign.id}`} className="font-medium text-fg hover:underline">
                  {selectedSchedule.campaign.name}
                </Link>
              </div>
              <div className="flex justify-between">
                <span className="text-fg-muted">Thời điểm đăng:</span>
                <span className="font-semibold text-fg">{formatDateTime(selectedSchedule.scheduled_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-fg-muted">Người phụ trách:</span>
                <span className="font-medium text-fg">{selectedSchedule.assignee?.full_name ?? '—'}</span>
              </div>
              {selectedSchedule.note && (
                <div>
                  <span className="text-fg-muted">Ghi chú:</span>
                  <p className="mt-0.5 text-fg">{selectedSchedule.note}</p>
                </div>
              )}
            </div>

            {/* If marking done input */}
            {isMarkingDone && (
              <div className="rounded-lg border border-border p-3 space-y-3">
                <p className="text-xs font-semibold text-fg">Xác nhận hoàn thành bài đăng:</p>
                <FormField label="Đường dẫn bài viết thực tế (URL)">
                  {(p) => (
                    <Input
                      {...p}
                      type="url"
                      value={doneUrl}
                      onChange={(e) => setDoneUrl(e.target.value)}
                      placeholder="https://facebook.com/... hoặc https://..."
                    />
                  )}
                </FormField>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setIsMarkingDone(false)}>
                    Huỷ
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    loading={markDoneMutation.isPending}
                    onClick={() =>
                      markDoneMutation.mutate({
                        id: selectedSchedule.id,
                        url: doneUrl.trim() || null,
                      })
                    }
                  >
                    Xác nhận đã đăng
                  </Button>
                </div>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border">
              <Link to={`/contents/${selectedSchedule.content.id}`}>
                <Button variant="ghost" size="sm">
                  Xem nội dung <ExternalLink className="h-3 w-3" />
                </Button>
              </Link>

              {selectedSchedule.status === 'PLANNED' && !isMarkingDone && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="danger"
                    size="sm"
                    loading={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate(selectedSchedule.id)}
                  >
                    Huỷ lịch
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setIsMarkingDone(true)}
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Đánh dấu đã đăng
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </Dialog>

      {/* Create Schedule Modal */}
      <Dialog
        open={isCreating}
        onClose={() => setIsCreating(false)}
        title="Lập lịch đăng bài mới"
        size="md"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!newContentId) {
              toast.error('Vui lòng chọn bài viết đã duyệt.');
              return;
            }
            if (!newScheduledAt) {
              toast.error('Vui lòng chọn ngày giờ đăng.');
              return;
            }
            createMutation.mutate({
              content_id: Number(newContentId),
              scheduled_at: new Date(newScheduledAt).toISOString(),
              assignee_id: newAssigneeId ? Number(newAssigneeId) : null,
              note: newNote.trim() || null,
            });
          }}
          className="space-y-4"
        >
          <FormField label="Bài viết cần lên lịch" required hint="Chỉ áp dụng cho các bài viết đã ở trạng thái ĐÃ DUYỆT (APPROVED).">
            {(p) => (
              <Select
                {...p}
                value={newContentId}
                onChange={(e) => setNewContentId(e.target.value ? Number(e.target.value) : '')}
                options={[
                  { value: '', label: 'Chọn bài viết đã duyệt...' },
                  ...(approvedContentsQ.data?.items ?? []).map((c: Content) => ({
                    value: String(c.id),
                    label: `[${c.channel.name}] ${c.title} (${c.campaign.name})`,
                  })),
                ]}
              />
            )}
          </FormField>

          <FormField label="Thời điểm đăng bài" required>
            {(p) => (
              <Input
                {...p}
                type="datetime-local"
                value={newScheduledAt}
                onChange={(e) => setNewScheduledAt(e.target.value)}
              />
            )}
          </FormField>

          {usersOpt.enabled && (
            <FormField label="Người phụ trách đăng">
              {(p) => (
                <Select
                  {...p}
                  value={newAssigneeId}
                  onChange={(e) => setNewAssigneeId(e.target.value ? Number(e.target.value) : '')}
                  options={[
                    { value: '', label: 'Tự động gán / Chưa chỉ định' },
                    ...usersOpt.users.map((u) => ({ value: String(u.id), label: u.full_name })),
                  ]}
                />
              )}
            </FormField>
          )}

          <FormField label="Ghi chú thêm">
            {(p) => (
              <Textarea
                {...p}
                rows={3}
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Ghi chú cụ thể cho người đăng (vd: gắn link bio, chọn cover video...)"
              />
            )}
          </FormField>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" type="button" onClick={() => setIsCreating(false)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={createMutation.isPending}>
              Xác nhận lên lịch
            </Button>
          </div>
        </form>
      </Dialog>
    </PageContainer>
  );
}
