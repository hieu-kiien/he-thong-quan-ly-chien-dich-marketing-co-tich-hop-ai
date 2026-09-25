import React from 'react';
import { Search, Sparkles, Bell, Menu, Palette, LogOut, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';

interface NavbarProps {
  onOpenBrandKit: () => void;
  onOpenAIDrawer: () => void;
  onToggleSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenBrandKit,
  onOpenAIDrawer,
  onToggleSidebar
}) => {
  const { user, userRole, logout } = useAuth();

  const getRoleBadge = (role?: string | null) => {
    switch (role) {
      case 'AGENCY_MANAGER':
      case 'MANAGER':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Quản lý</span>
          </span>
        );
      case 'CLIENT_APPROVER':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Approver</span>
          </span>
        );
      case 'MARKETER':
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Marketer</span>
          </span>
        );
    }
  };

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20 shadow-xs text-slate-100 no-print">
      {/* Left Area: Mobile Hamburger + Search Input + Workspace Switcher */}
      <div className="flex items-center gap-3 max-w-xl w-full">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-2 -ml-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg md:hidden transition-colors shrink-0"
            title="Mở thanh điều hướng"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Workspace Switcher */}
        <WorkspaceSwitcher onOpenBrandKit={onOpenBrandKit} />

        {/* Search Input */}
        <div className="relative w-full max-w-xs hidden sm:block">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Tìm kiếm chiến dịch (Cmd+K)..."
            className="w-full bg-slate-950/60 hover:bg-slate-950 focus:bg-slate-950 text-xs sm:text-sm pl-9 pr-4 py-1.5 rounded-xl border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all outline-none text-slate-200 placeholder-slate-500"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Brand Kit Quick Trigger */}
        <button
          onClick={onOpenBrandKit}
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-xl text-xs font-medium text-slate-300 hover:text-white transition-all shadow-xs"
          title="Cấu hình Brand Kit"
        >
          <Palette className="w-3.5 h-3.5 text-violet-400" />
          <span>Brand Kit</span>
        </button>

        {/* AI Assistant Quick Trigger */}
        <button
          onClick={onOpenAIDrawer}
          className="flex items-center gap-1.5 sm:gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-semibold px-3 py-1.5 rounded-xl shadow-md shadow-indigo-600/20 transition-all active:scale-95 shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span className="hidden sm:inline">AI Copilot</span>
        </button>

        {/* User Info & Role Badge */}
        {user && (
          <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
            <div className="hidden lg:flex flex-col text-right">
              <span className="text-xs font-semibold text-slate-200 leading-tight">
                {user.full_name}
              </span>
              <span className="text-[10px] text-slate-400 truncate max-w-[120px]">
                {user.email}
              </span>
            </div>
            {getRoleBadge(userRole)}
          </div>
        )}

        {/* Real Logout Button */}
        <button
          onClick={logout}
          className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl border border-transparent hover:border-rose-500/20 transition-colors"
          title="Đăng xuất tài khoản"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
