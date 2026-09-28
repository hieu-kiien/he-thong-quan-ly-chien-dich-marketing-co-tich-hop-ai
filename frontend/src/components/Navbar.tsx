import React, { useState, useEffect, useRef } from 'react';
import { Search, Sparkles, Menu, Palette, LogOut, Shield, AlertTriangle, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';
import { NotificationCenter } from './NotificationCenter';
import { isOfflineDemoEnabled, isBackendConnected } from '../services/api';

interface NavbarProps {
  onOpenBrandKit: () => void;
  onOpenAIDrawer: () => void;
  onToggleSidebar?: () => void;
  onNavigateTab?: (tab: string) => void;
  pendingReviewsCount?: number;
  activeCampaignsCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenBrandKit,
  onOpenAIDrawer,
  onToggleSidebar,
  onNavigateTab,
  pendingReviewsCount = 0,
  activeCampaignsCount = 0
}) => {
  const { user, userRole, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  // Keyboard shortcut Cmd+K / Ctrl+K to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    if (onNavigateTab) {
      onNavigateTab('campaigns');
    }
  };

  const getRoleBadge = (role?: string | null) => {
    switch (role) {
      case 'ADMIN':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-purple-950/80 text-purple-200 border border-purple-500/40 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Admin</span>
          </span>
        );
      case 'AGENCY_MANAGER':
      case 'MANAGER':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-950/80 text-emerald-200 border border-emerald-500/40 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Quản lý</span>
          </span>
        );
      case 'CLIENT_APPROVER':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-950/80 text-amber-200 border border-amber-500/40 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Approver</span>
          </span>
        );
      case 'MARKETER':
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-indigo-950/80 text-indigo-200 border border-indigo-500/40 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Marketer</span>
          </span>
        );
    }
  };

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-3 sm:px-6 flex items-center justify-between sticky top-0 z-20 shadow-xs text-slate-100 no-print">
      {/* Left Area: Mobile Hamburger + Search Input + Workspace Switcher */}
      <div className="flex items-center gap-2 sm:gap-3 max-w-xl min-w-0">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            aria-label="Mở thanh điều hướng"
            // Padding/negative-margin nhỏ hơn ở breakpoint gốc. Lý do có số liệu:
            // ở viewport 320px @ zoom 200% (tức 160 CSS px khả dụng sau padding),
            // header cần 146px cho [hamburger 32 + AI 34 + chuông 34 + logout 34 + gap]
            // nhưng chỉ có 136px -> nút hamburger CHỒNG LÊN nút AI Copilot, tạo ra
            // vùng 260px^2 hai phần tử tương tác chồng nhau (WCAG 2.5.8 Target Size /
            // không thể bấm xác định). Các giá trị dưới đây tiết kiệm 12px, đủ dư.
            className="p-1.5 sm:p-2 -ml-0.5 sm:-ml-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg md:hidden transition-colors shrink-0"
            title="Mở thanh điều hướng"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Workspace Switcher */}
        <div className="hidden sm:block shrink-0">
          <WorkspaceSwitcher onOpenBrandKit={onOpenBrandKit} />
        </div>

        {/* Search Input Form */}
        <form onSubmit={handleSearchSubmit} className="relative w-full max-w-xs hidden sm:block">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Tìm kiếm chiến dịch"
            placeholder="Tìm kiếm chiến dịch (Cmd+K)..."
            className="w-full bg-slate-950/60 hover:bg-slate-950 focus:bg-slate-950 text-xs sm:text-sm pl-9 pr-8 py-1.5 rounded-xl border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all outline-none text-slate-200 placeholder-slate-500"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-1 sm:gap-3 shrink-0">
        {/* Offline Demo Indicator Badge */}
        {isOfflineDemoEnabled() && !isBackendConnected() && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/20 border border-amber-500/40 text-amber-300 rounded-xl text-xs font-bold shrink-0"
            title="Chế độ Demo Offline dự phòng có sẵn khi mất kết nối"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="hidden sm:inline">Demo Offline Fallback</span>
            <span className="sm:hidden">Offline</span>
          </div>
        )}

        {/* Brand Kit Quick Trigger */}
        <button
          onClick={onOpenBrandKit}
          aria-label="Cấu hình Brand Kit"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-xl text-xs font-medium text-slate-300 hover:text-white transition-all shadow-xs"
          title="Cấu hình Brand Kit"
        >
          <Palette className="w-3.5 h-3.5 text-violet-400" />
          <span>Brand Kit</span>
        </button>

        {/* AI Assistant Quick Trigger */}
        <button
          onClick={onOpenAIDrawer}
          aria-label="Mở AI Copilot"
          className="flex items-center gap-1.5 sm:gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-semibold px-2 sm:px-3 py-1.5 rounded-xl shadow-md shadow-indigo-600/20 transition-all active:scale-95 shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span className="hidden sm:inline">AI Copilot</span>
        </button>

        {/* Centralized Notification Center */}
        <NotificationCenter
          pendingReviewsCount={pendingReviewsCount}
          activeCampaignsCount={activeCampaignsCount}
          onNavigateTab={onNavigateTab}
        />

        {/* User Info & Role Badge */}
        {user && (
          <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-slate-800 shrink-0">
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
          aria-label="Đăng xuất tài khoản"
          className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl border border-transparent hover:border-rose-500/20 transition-colors shrink-0"
          title="Đăng xuất tài khoản"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
