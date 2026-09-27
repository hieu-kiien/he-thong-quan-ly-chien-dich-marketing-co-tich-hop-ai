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
  Trash2
} from 'lucide-react';
import { AppNotification } from '../types';
import { useFocusTrap } from '../hooks/useFocusTrap';

interface NotificationCenterProps {
  pendingReviewsCount?: number;
  activeCampaignsCount?: number;
  onNavigateTab?: (tab: string) => void;
}

const DEFAULT_NOTIFICATIONS: AppNotification[] = [
  {
    id: 'notif-system-1',
    title: 'Hệ thống MarketFlow AI sẵn sàng',
    message: 'Chào mừng bạn đến với MarketFlow AI. Toàn bộ tính năng AI Copilot, Quản lý Chiến dịch và Hàng đợi Phê duyệt đã sẵn sàng.',
    type: 'info',
    timestamp: 'Vừa xong',
    read: false,
    targetTab: 'dashboard',
    actionLabel: 'Xem Tổng quan'
  },
  {
    id: 'notif-ai-1',
    title: 'Trợ lý AI Đa Kênh đã tối ưu',
    message: 'Bộ mô hình Google Gemini & OpenRouter đã được cấu hình với độ trễ tối ưu cho việc sinh ý tưởng và bài viết.',
    type: 'ai',
    timestamp: '15 phút trước',
    read: false,
    targetTab: 'ai_studio',
    actionLabel: 'Mở AI Studio'
  }
];

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  pendingReviewsCount = 0,
  activeCampaignsCount = 0,
  onNavigateTab
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'unread'>('all');
  const [notifications, setNotifications] = useState<AppNotification[]>(() => {
    try {
      const saved = localStorage.getItem('mf_notifications');
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.error(e);
    }
    return DEFAULT_NOTIFICATIONS;
  });

  const buttonRef = useRef<HTMLButtonElement | null>(null);

  // Sync real-time pending reviews into notifications if count > 0
  useEffect(() => {
    if (pendingReviewsCount > 0) {
      setNotifications(prev => {
        const reviewNotifExists = prev.some(n => n.id === 'notif-pending-reviews');
        if (reviewNotifExists) {
          return prev.map(n => 
            n.id === 'notif-pending-reviews' 
              ? { 
                  ...n, 
                  message: `Hiện có ${pendingReviewsCount} bài viết đang chờ quản lý phê duyệt trong Hàng đợi.`,
                  read: false,
                  timestamp: 'Vừa cập nhật'
                } 
              : n
          );
        } else {
          const newNotif: AppNotification = {
            id: 'notif-pending-reviews',
            title: 'Bài viết đang chờ duyệt',
            message: `Hiện có ${pendingReviewsCount} bài viết đang chờ quản lý phê duyệt trong Hàng đợi.`,
            type: 'review',
            timestamp: 'Vừa cập nhật',
            read: false,
            targetTab: 'reviews',
            actionLabel: 'Mở Hàng đợi'
          };
          return [newNotif, ...prev];
        }
      });
    }
  }, [pendingReviewsCount]);

  // Persist notifications
  useEffect(() => {
    try {
      localStorage.setItem('mf_notifications', JSON.stringify(notifications));
    } catch (e) {
      console.error(e);
    }
  }, [notifications]);

  const modalRef = useFocusTrap<HTMLDivElement>({
    isActive: isOpen,
    onEscape: () => setIsOpen(false)
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

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }, []);

  const removeNotification = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

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
        return <Clock className="w-4 h-4 text-amber-400 shrink-0" />;
      case 'campaign':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
      case 'ai':
        return <Sparkles className="w-4 h-4 text-violet-400 shrink-0" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />;
      case 'info':
      default:
        return <Info className="w-4 h-4 text-indigo-400 shrink-0" />;
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
        className="relative p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-all border border-transparent hover:border-slate-700/80 active:scale-95"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500 ring-2 ring-slate-900" />
          </span>
        )}
      </button>

      {/* Floating Notification Panel Popover */}
      {isOpen && (
        <div
          ref={modalRef}
          role="dialog"
          aria-label="Trung tâm thông báo"
          className="absolute right-0 mt-2 w-80 sm:w-96 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col text-slate-100 animate-in fade-in slide-in-from-top-2 duration-150"
        >
          {/* Header */}
          <div className="p-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/40">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-indigo-400" />
              <h4 className="text-sm font-bold text-white">Thông báo</h4>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 text-[10px] font-extrabold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full">
                  {unreadCount} mới
                </span>
              )}
            </div>

            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="px-2 py-1 text-[11px] font-medium text-slate-400 hover:text-indigo-300 hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-1"
                  title="Đánh dấu tất cả đã đọc"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span>Đã đọc</span>
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={clearAll}
                  className="p-1 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                  title="Xóa tất cả thông báo"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                title="Đóng bảng thông báo"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center gap-1 px-4 py-2 bg-slate-950/20 border-b border-slate-800 text-xs font-semibold">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                activeFilter === 'all'
                  ? 'bg-slate-800 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Tất cả ({notifications.length})
            </button>
            <button
              onClick={() => setActiveFilter('unread')}
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                activeFilter === 'unread'
                  ? 'bg-indigo-600/30 text-indigo-200 font-bold border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Chưa đọc ({unreadCount})
            </button>
          </div>

          {/* List of Notifications */}
          <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-800/60 p-1">
            {filteredNotifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400/80 mx-auto" />
                <p className="text-xs font-medium text-slate-300">
                  {activeFilter === 'unread' ? 'Không có thông báo chưa đọc nào.' : 'Không có thông báo nào.'}
                </p>
                <p className="text-[11px] text-slate-500">
                  Bạn đã cập nhật mọi hoạt động mới nhất của hệ thống!
                </p>
              </div>
            ) : (
              filteredNotifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleActionClick(n)}
                  className={`p-3 rounded-xl transition-all flex items-start gap-3 cursor-pointer group ${
                    n.read 
                      ? 'bg-transparent hover:bg-slate-800/40 text-slate-300' 
                      : 'bg-indigo-950/30 hover:bg-indigo-950/50 text-white border-l-2 border-indigo-500'
                  }`}
                >
                  <div className="p-1.5 rounded-lg bg-slate-800/80 mt-0.5 border border-slate-700/60">
                    {getIcon(n.type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1 mb-0.5">
                      <h5 className="text-xs font-bold truncate group-hover:text-indigo-300 transition-colors">
                        {n.title}
                      </h5>
                      <span className="text-[10px] text-slate-500 whitespace-nowrap">
                        {n.timestamp}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">
                      {n.message}
                    </p>

                    {n.actionLabel && (
                      <div className="mt-2 flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300">
                        <span>{n.actionLabel}</span>
                        <ExternalLink className="w-3 h-3" />
                      </div>
                    )}
                  </div>

                  <button
                    onClick={(e) => removeNotification(n.id, e)}
                    className="p-1 text-slate-500 hover:text-rose-400 rounded-md transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                    title="Xóa thông báo này"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-2.5 bg-slate-950/40 border-t border-slate-800 text-center text-[11px] text-slate-500">
            <span>MarketFlow AI • Cập nhật tự động thời gian thực</span>
          </div>
        </div>
      )}
    </div>
  );
};
export default NotificationCenter;
