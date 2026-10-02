import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Sparkles, CalendarCheck, ShieldCheck, Lock, X, AlertTriangle, Loader2 } from 'lucide-react';
import { Campaign, MarketingContent, MarketingSchedule } from '../types';
import { scheduleApi, getApiErrorMessage } from '../services/api';
import { channelPresentation, channelCodeById } from '../utils/channels';
import { useToast } from './Toast';
import { useFocusTrap } from '../hooks/useFocusTrap';

/**
 * `scheduled_at` được backend lưu dạng chuỗi "YYYY-MM-DD HH:MM" (xem ScheduleCreate).
 * new Date() trên chuỗi đó phụ thuộc timezone trình duyệt và có thể lệch ngày, nên
 * tách thủ công từng trường thay vì đưa vào Date.
 */
const parseScheduledAt = (raw: string): { date: string; time: string } | null => {
  const match = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(raw);
  if (!match) return null;
  const [, y, m, d, hh, mm] = match;
  return { date: `${y}-${m}-${d}`, time: `${hh}:${mm}` };
};

const todayLocalISO = (): string => {
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${mm}-${dd}`;
};

interface CalendarItem {
  key: string;
  scheduleId: number;
  contentId: number;
  title: string;
  channelId: number;
  channelCode: string;
  contentStatus: string;
  scheduleStatus: MarketingSchedule['status'];
  day: number;
  dateStr: string;
  time: string;
  timedOut: boolean;
}

interface MarketingCalendarProps {
  campaigns: Campaign[];
  contents: MarketingContent[];
  selectedCampaign: Campaign | null;
  onSelectCampaign: (c: Campaign | null) => void;
  onOpenScheduleModal?: (content: MarketingContent) => void;
}

export const MarketingCalendar: React.FC<MarketingCalendarProps> = ({
  campaigns,
  contents,
  selectedCampaign,
  onSelectCampaign,
  onOpenScheduleModal
}) => {
  const toast = useToast();
  const [schedules, setSchedules] = useState<MarketingSchedule[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>('ALL');
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState<boolean>(false);
  const [selectedContentId, setSelectedContentId] = useState<number | null>(null);
  const [scheduledDate, setScheduledDate] = useState<string>(todayLocalISO());
  const [scheduledTime, setScheduledTime] = useState<string>('19:30');
  const [isSubmittingSchedule, setIsSubmittingSchedule] = useState<boolean>(false);

  const scheduleModalRef = useFocusTrap<HTMLDivElement>({
    isActive: isScheduleModalOpen,
    onEscape: () => setIsScheduleModalOpen(false)
  });

  // Month navigation: default to current month
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  const loadSchedules = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await scheduleApi.getAll(signal);
      setSchedules(data);
    } catch (e: any) {
      if (e?.code === 'ERR_CANCELED' || signal?.aborted) return;
      // KHÔNG rơi về dữ liệu dựng sẵn: một lịch bị bỏ trống phải được báo lỗi,
      // không được thay bằng ngày/giờ bịa ra.
      setLoadError(getApiErrorMessage(e));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadSchedules(controller.signal);
    return () => controller.abort();
  }, [loadSchedules]);

  // Helper for month navigation
  const prevMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const monthNames = [
    'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
    'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
  ];

  // Days in current month
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstDayIndex = new Date(year, month, 1).getDay(); // 0 is Sunday
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const todayISO = todayLocalISO();

  const contentsById = useMemo(() => {
    const map = new Map<number, MarketingContent>();
    contents.forEach((c) => map.set(c.id, c));
    return map;
  }, [contents]);

  /**
   * Lịch hiển thị là duy nhất `schedules` đã lưu trong database. Trước đây component
   * nạp /schedules rồi bỏ qua, dựng lịch từ `contents` bằng công thức
   * `day = (idx*4+3) % daysInMonth` và giờ `[9,11,15,19,20][idx%5]`, nên mọi bài
   * APPROVED hiện ở một ngày tùy ý của tháng hiện tại với giờ bịa đặt.
   */
  const calendarItems = useMemo<CalendarItem[]>(() => {
    return schedules
      .map((s) => {
        const parsed = parseScheduledAt(s.scheduled_at);
        if (!parsed) return null;
        const content = contentsById.get(s.content_id);
        if (selectedCampaign && content && content.campaign_id !== selectedCampaign.id) return null;

        const channelId = content?.channel_id ?? 0;
        const channelCode = channelCodeById(channelId);
        if (selectedChannel !== 'ALL' && channelCode !== selectedChannel) return null;

        const [, mm, dd] = parsed.date.split('-');
        const monthNum = Number(mm);
        const day = Number(dd);

        return {
          key: `schedule-${s.id}`,
          scheduleId: s.id,
          contentId: s.content_id,
          title: content?.title ?? `Nội dung #${s.content_id}`,
          channelId,
          channelCode,
          contentStatus: content?.status ?? 'UNKNOWN',
          scheduleStatus: s.status,
          day,
          dateStr: parsed.date,
          time: parsed.time,
          // Chỉ hiển thị trong ô ngày khi tháng/năm khớp tháng đang xem.
          timedOut: monthNum - 1 !== month || Number(parsed.date.slice(0, 4)) !== year
        } satisfies CalendarItem;
      })
      .filter((item): item is CalendarItem => item !== null);
  }, [schedules, contentsById, selectedCampaign, selectedChannel, month, year]);

  const itemsByDay = useMemo(() => {
    const map = new Map<number, CalendarItem[]>();
    calendarItems.forEach((item) => {
      const list = map.get(item.day) ?? [];
      list.push(item);
      map.set(item.day, list);
    });
    return map;
  }, [calendarItems]);

  // Thống kê thật, không phải số liệu marketing bịa đặt.
  const monthItemCount = calendarItems.filter((i) => !i.timedOut).length;
  const upcoming = useMemo(() => {
    return calendarItems
      .filter((i) => i.scheduleStatus === 'PLANNED' && !i.timedOut && `${i.dateStr} ${i.time}` >= `${todayISO} 00:00`)
      .sort((a, b) => `${a.dateStr} ${a.time}`.localeCompare(`${b.dateStr} ${b.time}`));
  }, [calendarItems, todayISO]);
  const nextItem = upcoming[0];

  const channelOptions = useMemo(() => {
    const codes = new Set<string>();
    contents.forEach((c) => codes.add(channelCodeById(c.channel_id)));
    return Array.from(codes).sort();
  }, [contents]);

  const eligibleContents = useMemo(
    () => contents.filter((c) => c.status === 'APPROVED' || c.status === 'PUBLISHED'),
    [contents]
  );

  return (
    <div className="space-y-6">
      {/* Banner: trạng thái lịch thật */}
      {/* `lg:flex-row` vì sidebar 256px làm bề rộng nội dung thực thấp hơn
          viewport; ở `md:` hai khối bị ép còn ~600px và tràn ngang. */}
      <div className="bg-gradient-to-r from-indigo-900 via-indigo-950 to-slate-900 rounded-2xl p-5 text-white shadow-md flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-1 min-w-0">
          {/* `flex-wrap`: badge + dòng nguồn xếp cạnh nhau trước đây bị ép
              khiến tiêu đề banner dài hơn hẳn vùng chứa. */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-400" /> Lịch Xuất Bản Đa Kênh
            </span>
            <span className="text-xs text-indigo-300">• nguồn: /api/v1/schedules</span>
          </div>
          <h3 className="text-base font-black tracking-tight">Lịch Xuất Bản & Điều Phối Tiếp Thị Đa Kênh</h3>
          <p className="text-xs text-indigo-200 max-w-xl">
            Mỗi ô lịch là một bản ghi <strong className="text-white">MarketingSchedule</strong> đã lưu trong
            database, hiển thị đúng <code className="text-amber-300">scheduled_at</code> mà quản lý đã đặt.
            Bài chưa được lên lịch sẽ không xuất hiện trên lịch.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs bg-white/10 backdrop-blur-md p-3 rounded-xl border border-white/10 shrink-0">
          <div>
            <span className="text-indigo-300 block text-[10px]">Bài trong tháng {month + 1}/{year}:</span>
            <strong className="text-white font-bold">{monthItemCount} lịch đã lưu</strong>
          </div>
          <div>
            <span className="text-purple-300 block text-[10px]">Lịch sắp tới:</span>
            <strong className="text-white font-bold">
              {nextItem ? `${nextItem.time} · ${nextItem.dateStr}` : 'Chưa có lịch'}
            </strong>
          </div>
        </div>
      </div>

      {/* Brand Safety & HITL Guardrail Notice */}
      <div className="bg-emerald-50/70 border border-emerald-200/90 rounded-2xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-emerald-950 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center text-white shrink-0">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-emerald-900 block">Brand Safety & HITL Guardrail nghiêm ngặt:</span>
            <span className="text-emerald-800 text-[11px]">
              Chỉ các bài viết đã được Quản lý phê duyệt (<strong>APPROVED</strong>) hoặc đang xuất bản (<strong>PUBLISHED</strong>) mới xuất hiện trên Lịch tiếp thị. Các bản nháp <strong>AI_DRAFT</strong> hoặc đang chờ duyệt <strong>IN_REVIEW</strong> bị khóa tuyệt đối để phòng tránh rủi ro thương hiệu.
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 font-bold text-[10px] bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full border border-emerald-300 w-fit">
          <Lock className="w-3 h-3 text-emerald-700" />
          <span>Strict HITL Lock Active</span>
        </div>
      </div>

      {/* Load error */}
      {loadError && (
        <div role="alert" className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-rose-900">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="block font-bold mb-0.5">Không tải được lịch xuất bản</strong>
            <span className="text-rose-800">{loadError}</span>
          </div>
          <button
            type="button"
            onClick={() => void loadSchedules()}
            className="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-[10px] font-bold shrink-0"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Control Bar: Filters & Month Switcher */}
      {/* `lg:flex-row`: ở viewport 929px, hai `<select>` + nhóm nút điều hướng
          tháng vượt quá bề rộng sẵn có nên bị tràn ngang. */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2.5 min-w-0">
          {/* Campaign Filter */}
          <select
            value={selectedCampaign?.id || ''}
            onChange={(e) => {
              const cid = Number(e.target.value);
              const found = campaigns.find(c => c.id === cid) || null;
              onSelectCampaign(found);
            }}
            aria-label="Lọc theo chiến dịch"
            className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-800"
          >
            <option value="">Tất cả Chiến dịch ({campaigns.length})</option>
            {campaigns.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          {/* Channel Filter */}
          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            aria-label="Lọc theo kênh tiếp thị"
            className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-800"
          >
            <option value="ALL">Tất cả Kênh tiếp thị</option>
            {channelOptions.map(code => (
              <option key={code} value={code}>{channelPresentation(code).label}</option>
            ))}
          </select>
        </div>

        {/* Month Navigation & Schedule Trigger */}
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => {
              const approvedFirst = eligibleContents[0];
              if (approvedFirst) setSelectedContentId(approvedFirst.id);
              setIsScheduleModalOpen(true);
            }}
            disabled={eligibleContents.length === 0}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-sm transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-indigo-600"
          >
            <CalendarCheck className="w-4 h-4" />
            <span>Lên lịch xuất bản</span>
          </button>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={prevMonth}
              aria-label="Th\u00e1ng tr\u01b0\u1edbc"
              className="p-1.5 hover:bg-slate-100 text-slate-600 rounded-lg transition-colors border border-slate-200"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-bold text-slate-900 min-w-[120px] text-center">
              {monthNames[month]} Năm {year}
            </span>
            <button
              type="button"
              onClick={nextMonth}
              aria-label="Tháng sau"
              className="p-1.5 hover:bg-slate-100 text-slate-600 rounded-lg transition-colors border border-slate-200"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        {/* Day-of-week header */}
        <div className="grid grid-cols-7 border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase text-center py-2.5">
          <div>Chủ Nhật</div>
          <div>Thứ Hai</div>
          <div>Thứ Ba</div>
          <div>Thứ Tư</div>
          <div>Thứ Năm</div>
          <div>Thứ Sáu</div>
          <div>Thứ Bảy</div>
        </div>

        {/* Days cells */}
        <div className="grid grid-cols-7 auto-rows-fr divide-x divide-y divide-slate-100 bg-slate-50/30">
          {/* Empty cells before month start */}
          {Array.from({ length: firstDayIndex }).map((_, i) => (
            <div key={`empty-${i}`} className="min-h-[110px] bg-slate-50/50 p-2 text-slate-300 text-xs"></div>
          ))}

          {/* Actual days */}
          {Array.from({ length: daysInMonth }).map((_, idx) => {
            const dayNum = idx + 1;
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
            const isToday = dateStr === todayISO;
            const itemsForDay = itemsByDay.get(dayNum) ?? [];

            return (
              <div
                key={`day-${dayNum}`}
                className={`min-h-[110px] p-2 transition-colors relative flex flex-col justify-between ${
                  isToday ? 'bg-indigo-50/40 ring-1 ring-inset ring-indigo-500/30' : 'bg-white hover:bg-slate-50/80'
                }`}
              >
                {/* Day Header */}
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    aria-current={isToday ? 'date' : undefined}
                    className={`text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center ${
                      isToday ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-700'
                    }`}
                  >
                    {dayNum}
                  </span>
                  {itemsForDay.length > 0 && (
                    <span className="text-[10px] font-bold text-slate-600">
                      {itemsForDay.length} bài
                    </span>
                  )}
                </div>

                {/* Event Chips */}
                <div
                  className="space-y-1.5 flex-1 overflow-y-auto max-h-[80px]"
                >
                  {itemsForDay.map((ev) => {
                    const chInfo = channelPresentation(ev.channelCode);
                    const Icon = chInfo.icon;
                    const isCancelled = ev.scheduleStatus === 'CANCELLED';
                    return (
                      <button
                        type="button"
                        key={ev.key}
                        onClick={() => {
                          const content = contentsById.get(ev.contentId);
                          if (content && onOpenScheduleModal) onOpenScheduleModal(content);
                          else if (content) setSelectedContentId(content.id);
                        }}
                        title={`${ev.time} - ${ev.title} (${chInfo.label})`}
                        className={`w-full text-left p-1.5 rounded-lg border text-[11px] leading-tight transition-all hover:shadow-sm ${chInfo.chip} ${
                          isCancelled ? 'opacity-50 line-through' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] font-bold mb-0.5">
                          <span className="flex items-center gap-1">
                            <span className={`w-1.5 h-1.5 rounded-full ${chInfo.dot}`}></span>
                            <Icon className="w-3 h-3" />
                            {ev.time}
                          </span>
                          <span className="uppercase text-[9px] font-bold text-slate-700">
                            {ev.scheduleStatus}
                          </span>
                        </div>
                        <p className="font-semibold truncate text-[10px]">{ev.title}</p>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Empty / loading state */}
        {!loadError && calendarItems.length === 0 && (
          <div className="px-6 py-10 text-center">
            {loading ? (
              <div className="flex flex-col items-center gap-2 text-slate-500">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                <span className="text-xs font-semibold">Đang tải lịch xuất bản…</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 text-slate-500">
                <CalendarIcon className="w-7 h-7 text-slate-300" />
                <span className="text-xs font-bold text-slate-700">Chưa có lịch xuất bản nào</span>
                <span className="text-[11px] max-w-md text-center">
                  Bài viết chỉ xuất hiện trên lịch sau khi quản lý bấm “Lên lịch xuất bản”.
                  Nội dung trạng thái <strong>APPROVED</strong> hiện có {eligibleContents.length} bài.
                </span>
                <button
                  type="button"
                  onClick={() => {
                    const approvedFirst = eligibleContents[0];
                    if (approvedFirst) setSelectedContentId(approvedFirst.id);
                    setIsScheduleModalOpen(true);
                  }}
                  disabled={eligibleContents.length === 0}
                  className="mt-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-[11px] font-bold disabled:opacity-50 disabled:hover:bg-indigo-600"
                >
                  Lên lịch ngay
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Schedule Modal */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            ref={scheduleModalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="schedule-modal-title"
            tabIndex={-1}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in"
          >
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <CalendarCheck className="w-5 h-5 text-indigo-600" />
                <h3 id="schedule-modal-title" className="font-black text-sm text-slate-900">Lập Lịch Xuất Bản Đa Kênh</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsScheduleModalOpen(false)}
                aria-label="Đóng modal lên lịch"
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label htmlFor="calendar-content-select" className="text-xs font-bold text-slate-700 block mb-1">Chọn bài viết đã duyệt:</label>
                <select
                  id="calendar-content-select"
                  value={selectedContentId || ''}
                  onChange={(e) => setSelectedContentId(Number(e.target.value))}
                  className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800"
                >
                  <option value="">— Chọn bài viết —</option>
                  {eligibleContents.map(c => (
                    <option key={c.id} value={c.id}>#{c.id} - {c.title}</option>
                  ))}
                </select>
                {eligibleContents.length === 0 && (
                  <p className="text-[10px] text-amber-700 mt-1">
                    Chưa có bài nào ở trạng thái APPROVED/PUBLISHED để lên lịch.
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="calendar-schedule-date" className="text-xs font-bold text-slate-700 block mb-1">Ngày xuất bản:</label>
                  <input
                    id="calendar-schedule-date"
                    type="date"
                    value={scheduledDate}
                    onChange={(e) => setScheduledDate(e.target.value)}
                    className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800"
                  />
                </div>
                <div>
                  <label htmlFor="calendar-schedule-time" className="text-xs font-bold text-slate-700 block mb-1">Giờ phát hành:</label>
                  <input
                    id="calendar-schedule-time"
                    type="time"
                    value={scheduledTime}
                    onChange={(e) => setScheduledTime(e.target.value)}
                    className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsScheduleModalOpen(false)}
                className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg text-xs font-semibold"
              >
                Hủy
              </button>
              <button
                type="button"
                disabled={isSubmittingSchedule || !selectedContentId}
                onClick={async () => {
                  if (!selectedContentId) return;
                  try {
                    setIsSubmittingSchedule(true);
                    await scheduleApi.create(selectedContentId, `${scheduledDate} ${scheduledTime}`);
                    toast.success(`Đã lập lịch xuất bản bài viết thành công vào lúc ${scheduledTime} ngày ${scheduledDate}!`);
                    setIsScheduleModalOpen(false);
                    await loadSchedules();
                  } catch (e: any) {
                    toast.error(getApiErrorMessage(e), 'Lỗi khi lập lịch xuất bản');
                  } finally {
                    setIsSubmittingSchedule(false);
                  }
                }}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-indigo-600/20 disabled:opacity-60 disabled:hover:bg-indigo-600"
              >
                {isSubmittingSchedule ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CalendarCheck className="w-4 h-4" />
                )}
                <span>Xác nhận Lên lịch</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};