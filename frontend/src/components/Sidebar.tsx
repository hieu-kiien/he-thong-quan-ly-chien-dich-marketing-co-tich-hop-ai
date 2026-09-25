import React from 'react';
import { 
  LayoutDashboard, 
  Megaphone, 
  GitBranch, 
  CheckSquare, 
  Sparkles, 
  LogOut,
  Layers,
  ShieldCheck,
  X,
  Settings,
  Calendar
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  currentUser: User | null;
  onLogout: () => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentTab, 
  onSelectTab, 
  currentUser,
  onLogout,
  isOpen = false,
  onClose
}) => {
  const menuItems = [
    { id: 'dashboard', label: 'Bảng Điều Khiển', icon: LayoutDashboard },
    { id: 'campaigns', label: 'Quản Lý Chiến Dịch', icon: Megaphone, highlight: true },
    { 
      id: 'reviews', 
      label: 'Hàng Đợi Phê Duyệt', 
      icon: CheckSquare,
      badge: currentUser?.role === 'MANAGER' || currentUser?.role === 'AGENCY_MANAGER' ? 'Duyệt bài' : undefined 
    },
    { id: 'calendar', label: 'Lịch Xuất Bản', icon: Calendar },
    { id: 'ai_studio', label: 'Xưởng Sáng Tạo AI', icon: Sparkles },
    { id: 'settings', label: 'Cài Đặt & Brand Kit', icon: Settings }
  ];

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs z-40 md:hidden transition-opacity no-print"
        />
      )}

      {/* Sidebar Aside */}
      <aside
        className={`w-64 bg-slate-900 text-slate-300 flex flex-col h-screen border-r border-slate-800 shrink-0 z-50 fixed md:static inset-y-0 left-0 transition-transform duration-300 ease-in-out no-print ${
          isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 flex items-center justify-between border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/30">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-white text-base tracking-tight">MarketFlow AI</h1>
              <p className="text-[11px] text-indigo-400 font-semibold tracking-wide">Enterprise Omnichannel</p>
            </div>
          </div>

          {/* Close button on Mobile */}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg md:hidden hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Role Badge */}
        <div className="px-5 py-3 border-b border-slate-800/50 bg-slate-950/40">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Vai trò:</span>
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 ${
              currentUser?.role === 'MANAGER' || currentUser?.role === 'AGENCY_MANAGER'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                : currentUser?.role === 'CLIENT_APPROVER'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
            }`}>
              <ShieldCheck className="w-3 h-3" />
              {currentUser?.role === 'AGENCY_MANAGER'
                ? 'Agency Manager'
                : currentUser?.role === 'MANAGER'
                ? 'Quản lý (Manager)'
                : currentUser?.role === 'CLIENT_APPROVER'
                ? 'Client Approver'
                : 'Marketer'}
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
                onClick={() => {
                  onSelectTab(item.id);
                  if (onClose) onClose();
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 font-semibold'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : item.highlight ? 'text-indigo-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/30 font-bold">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Subdomain status */}
        <div className="px-4 py-2 border-t border-slate-800/60 bg-slate-950/30 flex items-center justify-between text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-mono text-[10px] text-slate-300">marketflow.ictu.edu.vn</span>
          </div>
          <span className="text-[9px] uppercase tracking-wider font-bold bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded">
            PROD
          </span>
        </div>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-white shrink-0">
                {currentUser?.full_name?.charAt(0) || 'U'}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-white truncate">{currentUser?.full_name || 'Người dùng'}</p>
                <p className="text-[11px] text-slate-400 truncate">{currentUser?.email || ''}</p>
              </div>
            </div>
            <button
              onClick={onLogout}
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
