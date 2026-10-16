import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Bell, 
  CheckCheck, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles, 
  Info, 
  X, 
  ExternalLink,
  Trash2,
  Loader2
} from 'lucide-react';
import { AppNotification } from '../types';
import { useFocusTrap } from '../hooks/useFocusTrap';
import { notificationApi, getApiErrorMessage } from '../services/api';
import { useToast } from './Toast';

interface NotificationCenterProps {
  pendingReviewsCount?: number;
  activeCampaignsCount?: number;
  onNavigateTab?: (tab: string) => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  pendingReviewsCount = 0,
  onNavigateTab
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'unread'>('all');
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  // Không nuốt lỗi: chuông báo 0 thông báo là không phân biệt được với
  // "thật sự không có" và "không tải được".
  const [loadError, setLoadError] = useState<string | null>(null);

  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const toast = useToast();

  // Fetch real notifications from backend API
  const fetchNotifications = useCallback(async (signal?: AbortSignal) => {
    try {
      setLoading(true);
      setLoadError(null);
      const data = await notificationApi.getAll(signal);
      setNotifications(data);
    } catch (e: any) {
      if (e?.code === 'ERR_CANCELED' || signal?.aborted) return;
      setLoadError(getApiErrorMessage(e));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void fetchNotifications(controller.signal);
    return () => controller.abort();
  }, [fetchNotifications, pendingReviewsCount]);

  useEffect(() => {
    if (isOpen) {
      void fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  // Đây là DROPDOWN, không phải modal. Dùng focus trap ở đây khoá Tab trong danh
  // sách thông báo khiến người dùng bàn phím không Tab qua được ra trang, và
  // khoá scroll/inert cả trang nền. Chỉ giữ phần bắt phím Escape.
  const modalRef = useFocusTrap<HTMLDivElement>({
    isActive: isOpen,
    onEscape: () => setIsOpen(false),
    lockScroll: false,
    inertSiblings: false
  });

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        isOpen && 
        modalRef.current && 
        !modalRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, modalRef]);

  const unreadCount = notifications.filter(n => !n.read).length;

  // Mọi thao tác cập nhật trạng thái đều là optimistic; phải khôi phục lại trạng
  // thái cũ khi API lỗi, nếu không UI nằm im báo "đã đọc/đã xoá" cho tới lúc tải
  // lại trang dù thao tác chưa hề thành công.
  const markAllAsRead = useCallback(async () => {
    const previous = notifications;
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    try {
      await notificationApi.markAllAsRead();
    } catch (e: any) {
      setNotifications(previous);
      toast.error(getApiErrorMessage(e), 'Không đánh dấu đã đọc được');
    }
  }, [notifications, toast]);

  const markAsRead = useCallback(async (id: string) => {
    const previous = notifications;
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    try {
      await notificationApi.markAsRead(id);
    } catch (e: any) {
      setNotifications(previous);
      toast.error(getApiErrorMessage(e), 'Không cập nhật được thông báo');
    }
  }, [notifications, toast]);

  const removeNotification = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const previous = notifications;
    setNotifications(prev => prev.filter(n => n.id !== id));
    try {
      await notificationApi.markAsRead(id);
    } catch (e: any) {
      setNotifications(previous);
      toast.error(getApiErrorMessage(e), 'Không ẩn được thông báo');
    }
  }, [notifications, toast]);

  const clearAll = useCallback(async () => {
    const previous = notifications;
    setNotifications([]);
    try {
      // Backend không có "xoá hết"; mark-all-read là hành vi gần nhất tương đương.
      await notificationApi.markAllAsRead();
      toast.success(`Đã đánh dấu ${previous.length} thông báo là đã đọc`);
    } catch (e: any) {
      setNotifications(previous);
      toast.error(getApiErrorMessage(e), 'Không xử lý được danh sách thông báo');
    }
  }, [notifications, toast]);

  const handleActionClick = (notif: AppNotification) => {
    markAsRead(notif.id);
    setIsOpen(false);
    if (notif.targetTab && onNavigateTab) {
      onNavigateTab(notif.targetTab);
    }
  };

  const filteredNotifications = notifications.filter(n => {
    if (activeFilter === 'unread') return !n.read;
    return true;
  });

  const getIcon = (type: AppNotification['type']) => {
    switch (type) {
      case 'review':
        return <Clock className="w-4 h-4 text-[#B45309] shrink-0" />;
      case 'campaign':
        return <CheckCircle2 className="w-4 h-4 text-[#15803D] shrink-0" />;
      case 'ai':
        return <Sparkles className="w-4 h-4 text-[#D95D39] shrink-0" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-[#BE123C] shrink-0" />;
      case 'info':
      default:
        return <Info className="w-4 h-4 text-[#121316] shrink-0" />;
    }
  };

  return (
    <div className="relative">
      {/* Bell Trigger Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(prev => !prev)}
        aria-label="Thông báo hệ thống"
        aria-expanded={isOpen}
        title="Thông báo"
        className="relative p-2 text-[#5A5E66] hover:text-[#121316] hover:bg-[#F6F5F0] rounded-lg transition-all border border-transparent hover:border-[#E4E2DD] active:scale-95 cursor-pointer"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D95D39] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#D95D39] ring-2 ring-white" />
          </span>
        )}
      </button>

      {/* Floating Notification Panel Popover */}
      {isOpen && (
        <div
          ref={modalRef}
          role="dialog"
          aria-label="Trung tâm thông báo"
          className="absolute right-0 mt-2 w-80 sm:w-96 bg-white border border-[#E4E2DD] rounded-xl shadow-xl z-50 overflow-hidden flex flex-col text-[#121316]"
        >
          {/* Header */}
          <div className="p-3.5 border-b border-[#E4E2DD] flex items-center justify-between bg-[#F6F5F0]/60">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-[#D95D39]" />
              <h4 className="text-xs font-black uppercase tracking-wider text-[#121316]">Thông báo</h4>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 text-[10px] font-bold bg-[#FFF1EE] text-[#D95D39] border border-[#F5D0C5] rounded-md">
                  {unreadCount} mới
                </span>
              )}
            </div>

            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="px-2 py-1 text-[11px] font-bold text-[#5A5E66] hover:text-[#121316] hover:bg-[#EAE8E1] rounded-md transition-colors flex items-center gap-1 cursor-pointer"
                  title="Đánh dấu tất cả đã đọc"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span>Đã đọc</span>
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={clearAll}
                  className="p-1 text-[#5A5E66] hover:text-[#BE123C] hover:bg-[#FFF1F2] rounded-md transition-colors cursor-pointer"
                  title="Xóa tất cả thông báo"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 text-[#5A5E66] hover:text-[#121316] hover:bg-[#EAE8E1] rounded-md transition-colors cursor-pointer"
                title="Đóng bảng thông báo"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center gap-1 px-3.5 py-2 bg-white border-b border-[#E4E2DD] text-xs font-semibold">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                activeFilter === 'all'
                  ? 'bg-[#121316] text-white font-bold'
                  : 'text-[#5A5E66] hover:text-[#121316] hover:bg-[#F6F5F0]'
              }`}
            >
              Tất cả ({notifications.length})
            </button>
            <button
              onClick={() => setActiveFilter('unread')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                activeFilter === 'unread'
                  ? 'bg-[#D95D39] text-white font-bold'
                  : 'text-[#5A5E66] hover:text-[#121316] hover:bg-[#F6F5F0]'
              }`}
            >
              Chưa đọc ({unreadCount})
            </button>
          </div>

          {/* List of Notifications */}
          <div className="max-h-[380px] overflow-y-auto divide-y divide-[#F0EFEA] p-1.5">
            {loading && notifications.length === 0 ? (
              <div className="p-8 text-center text-[#5A5E66] space-y-2">
                <Loader2 className="w-5 h-5 animate-spin text-[#D95D39] mx-auto" />
                <p className="text-xs font-medium text-[#5A5E66]">Đang tải thông báo...</p>
              </div>
            ) : loadError ? (
              <div role="alert" className="p-8 text-center space-y-2">
                <AlertTriangle className="w-6 h-6 text-[#BE123C] mx-auto" />
                <p className="text-xs font-bold text-[#BE123C]">Không tải được thông báo</p>
                <p className="text-[11px] text-[#5A5E66]">{loadError}</p>
                <button
                  type="button"
                  onClick={() => void fetchNotifications()}
                  className="mt-1 px-2.5 py-1 bg-[#121316] hover:bg-[#26282D] text-white rounded-lg text-[11px] font-bold"
                >
                  Thử lại
                </button>
              </div>
            ) : filteredNotifications.length === 0 ? (
              <div className="p-8 text-center text-[#5A5E66] space-y-1.5">
                <CheckCircle2 className="w-7 h-7 text-[#15803D] mx-auto" />
                <p className="text-xs font-bold text-[#121316]">
                  {activeFilter === 'unread' ? 'Không có thông báo chưa đọc.' : 'Không có thông báo mới.'}
                </p>
                <p className="text-[11px] text-[#5A5E66]">
                  Mọi hoạt động chiến dịch và duyệt bài đã được cập nhật.
                </p>
              </div>
            ) : (
              filteredNotifications.map((n) => (
                <div
                  key={n.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`Mở thông báo: ${n.title}`}
                  onClick={() => handleActionClick(n)}
                  onKeyDown={(e) => {
                    if (e.target !== e.currentTarget) return;
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleActionClick(n);
                    }
                  }}
                  className={`p-3 rounded-lg transition-all flex items-start gap-3 cursor-pointer group ${
                    n.read 
                      ? 'bg-white hover:bg-[#F6F5F0] text-[#5A5E66]' 
                      : 'bg-[#FFF9F6] hover:bg-[#FFF1EE] text-[#121316] border-l-2 border-[#D95D39]'
                  }`}
                >
                  <div className="p-1.5 rounded-md bg-[#F6F5F0] mt-0.5 border border-[#E4E2DD]">
                    {getIcon(n.type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1 mb-0.5">
                      <h5 className="text-xs font-bold text-[#121316] truncate group-hover:text-[#D95D39] transition-colors">
                        {n.title}
                      </h5>
                      <span className="text-[10px] text-[#8A8F98] whitespace-nowrap font-mono">
                        {n.timestamp}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#5A5E66] leading-relaxed line-clamp-2">
                      {n.message}
                    </p>

                    {n.actionLabel && (
                      <div className="mt-1.5 flex items-center gap-1 text-[11px] font-bold text-[#D95D39] hover:underline">
                        <span>{n.actionLabel}</span>
                        <ExternalLink className="w-3 h-3" />
                      </div>
                    )}
                  </div>

                  <button
                    onClick={(e) => removeNotification(n.id, e)}
                    className="p-1 text-[#8A8F98] hover:text-[#BE123C] rounded-md transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                    title="Xóa thông báo này"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-2.5 bg-[#F6F5F0]/60 border-t border-[#E4E2DD] text-center text-[11px] text-[#5A5E66]">
            <span>Trung tâm thông báo chiến dịch &amp; duyệt bài</span>
          </div>
        </div>
      )}
    </div>
  );
};
export default NotificationCenter;
