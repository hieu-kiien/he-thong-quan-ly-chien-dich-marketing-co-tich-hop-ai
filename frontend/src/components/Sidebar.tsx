import React from 'react';
import { LayoutDashboard, Megaphone, CheckSquare, Sparkles, LogOut, Layers, ShieldCheck, X, Settings, Calendar, ListTodo } from 'lucide-react';
import { User } from '../types';

// Nhãn hiển thị cho từng vai trò. Role không có trong bảng sẽ hiện nguyên tên
// role thay vì rơi về nhãn của vai trò khác — xem chú thích tại chỗ dùng.
const ROLE_LABELS: Record<string, string> = {
  AGENCY_MANAGER: 'Quản lý Agency',
  MANAGER: 'Quản lý (Manager)',
  CLIENT_APPROVER: 'Khách duyệt bài',
  ADMIN: 'Quản trị hệ thống',
  MARKETER: 'Chuyên viên (Marketer)',
};

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  currentUser: User | null;
  onLogout: () => void;
  isOpen?: boolean;
  onClose?: () => void;
  tasksCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentTab, 
  onSelectTab, 
  currentUser,
  onLogout,
  isOpen = false,
  onClose,
  tasksCount
}) => {
  // Chế độ build quyết định nhãn môi trường, không phải hằng số ghi cứng.
  const isProd = Boolean((import.meta as any).env?.PROD);
  const menuItems = [
    { id: 'dashboard', label: 'Tổng quan hôm nay', icon: LayoutDashboard },
    { id: 'campaigns', label: 'Danh sách chiến dịch', icon: Megaphone, highlight: true },
    { id: 'ai_studio', label: 'Viết bài & Tạo mẫu QC', icon: Sparkles },
    { 
      id: 'reviews', 
      label: 'Duyệt bài & Từ cấm', 
      icon: CheckSquare,
      badge: currentUser?.role === 'MANAGER' || currentUser?.role === 'AGENCY_MANAGER' ? 'Duyệt' : undefined 
    },
    { 
      id: 'my_tasks', 
      label: 'Việc cần làm', 
      icon: ListTodo,
      badge: tasksCount && tasksCount > 0 ? `${tasksCount}` : undefined
    },
    { id: 'calendar', label: 'Lịch đăng bài', icon: Calendar },
    { id: 'settings', label: 'Cài đặt & Thương hiệu', icon: Settings }
  ];


  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isOpen && (
        <div
          role="none"
          onClick={onClose}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden transition-opacity no-print"
        />
      )}

      {/* Sidebar Aside */}
      <aside
        className={`w-64 bg-[#141518] text-slate-300 flex flex-col h-screen border-r border-[#26282D] shrink-0 z-50 fixed md:static inset-y-0 left-0 transition-transform duration-300 ease-in-out no-print ${
          isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="px-5 py-4 flex items-center justify-between border-b border-[#26282D]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#D95D39] flex items-center justify-center text-white font-bold">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h1 className="font-bold text-white text-sm tracking-tight">MarketFlow</h1>
              <p className="text-[11px] text-slate-400">Quản lý chiến dịch &amp; nội dung</p>
            </div>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              aria-label="Đóng thanh điều hướng"
              className="p-1.5 text-slate-400 hover:text-white rounded-lg md:hidden hover:bg-[#1E2025] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                data-testid={`sidebar-tab-${item.id}`}
                aria-label={item.label}
                onClick={() => {
                  onSelectTab(item.id);
                  if (onClose) onClose();
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  isActive
                    ? 'bg-[#D95D39] text-white font-bold'
                    : 'text-slate-300 hover:bg-[#1E2025] hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                    isActive
                      ? 'bg-white text-[#121316]'
                      : 'bg-[#26282D] text-slate-200 border border-slate-700'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Info & Role Footer */}
        <div className="p-3.5 border-t border-[#26282D] bg-[#101114]">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-[#1E2025] border border-[#2E3138] flex items-center justify-center font-bold text-xs text-white shrink-0">
                {currentUser?.full_name?.charAt(0) || 'U'}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate">{currentUser?.full_name || 'Người dùng'}</p>
                <p className="text-[10px] text-slate-400 truncate flex items-center gap-1 mt-0.5">
                  <ShieldCheck className="w-3 h-3 text-[#D95D39] shrink-0" />
                  <span className="truncate">{ROLE_LABELS[currentUser?.role ?? ''] ?? currentUser?.role ?? (isProd ? 'Trực tuyến' : 'Nội bộ')}</span>
                </p>
              </div>
            </div>
            <button
              onClick={onLogout}
              aria-label="Đăng xuất"
              title="Đăng xuất"
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors cursor-pointer shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
