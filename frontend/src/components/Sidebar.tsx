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
      {/* Lớp nền mobile chỉ là phím tắt chuột; nút đóng (icon X) bên trong sidebar là
          cách đóng bằng bàn phím, nên backdrop không mang ý nghĩa tương tác. */}
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
        <div className="p-5 flex items-center justify-between border-b border-[#26282D]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#D95D39] flex items-center justify-center text-white font-bold shadow-sm">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-white text-base tracking-tight">MarketFlow</h1>
              <p className="text-[11px] text-slate-400 font-medium">Quản lý quảng cáo &amp; nội dung</p>
            </div>
          </div>

          {/* Close button on Mobile */}
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

        {/* Role Badge */}
        <div className="px-5 py-3 border-b border-[#26282D] bg-[#101114]">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Vai trò:</span>
            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1 ${
              currentUser?.role === 'MANAGER' || currentUser?.role === 'AGENCY_MANAGER'
                ? 'bg-emerald-950 text-emerald-200 border border-emerald-500/40'
                : currentUser?.role === 'CLIENT_APPROVER'
                ? 'bg-amber-950 text-amber-200 border border-amber-500/40'
                : 'bg-[#1E2025] text-slate-200 border border-slate-700'
            }`}>
              <ShieldCheck className="w-3 h-3" />
              {/* Bảng nhãn: role không có trong bảng thì hiện CHÍNH role đó, thay
                  vì rơi về 'Marketer' — fallback sai khiến người dùng ADMIN tưởng
                  mình là Marketer. */}
              {ROLE_LABELS[currentUser?.role ?? ''] ?? currentUser?.role ?? '—'}
            </span>
          </div>
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
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[#D95D39] text-white font-semibold'
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

        {/* Subdomain status */}
        {/* Nhãn môi trường lấy từ chế độ build, không hardcode "PROD".
            Trước đây mọi bản chạy — kể cả `npm run dev` trên localhost:5173 —
            đều hiện badge PROD và tên miền production, tức là một chỉ báo môi
            trường sai trong 100% phiên chạy thật. */}
        <div className="px-4 py-2 border-t border-[#26282D] bg-[#101114] flex items-center justify-between text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-400">
            <span
              className={`w-2 h-2 rounded-full ${isProd ? 'bg-emerald-400' : 'bg-amber-400'}`}
              aria-hidden="true"
            ></span>
            <span className="font-mono text-[10px] text-slate-300">
              {isProd ? 'production' : 'development'}
            </span>
          </div>
          <span
            className={`text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded ${
              isProd
                ? 'bg-emerald-500/20 text-emerald-300'
                : 'bg-amber-500/20 text-amber-300'
            }`}
          >
            {isProd ? 'PROD' : 'DEV'}
          </span>
        </div>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-[#26282D] bg-[#101114]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-[#1E2025] border border-slate-700 flex items-center justify-center font-bold text-xs text-white shrink-0">
                {currentUser?.full_name?.charAt(0) || 'U'}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-white truncate">{currentUser?.full_name || 'Người dùng'}</p>
                <p className="text-[11px] text-slate-400 truncate">{currentUser?.email || ''}</p>
              </div>
            </div>
            <button
              onClick={onLogout}
              aria-label="Đăng xuất"
              title="Đăng xuất"
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
