import React from 'react';
import { Search, Sparkles, UserCheck, Bell, Menu } from 'lucide-react';
import { User } from '../types';

interface NavbarProps {
  currentUser: User | null;
  onSwitchRole: (role: 'MANAGER' | 'MARKETER') => void;
  onOpenAIDrawer: () => void;
  onToggleSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onSwitchRole,
  onOpenAIDrawer,
  onToggleSidebar
}) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200/80 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20 shadow-xs">
      {/* Left Area: Mobile Hamburger + Search Input */}
      <div className="flex items-center gap-2 max-w-md w-full">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-2 -ml-1 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg md:hidden transition-colors shrink-0"
            title="Mở thanh điều hướng"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Tìm kiếm chiến dịch, nội dung (Cmd+K)..."
            className="w-full bg-slate-100/80 hover:bg-slate-100 focus:bg-white text-xs sm:text-sm pl-9 pr-4 py-2 rounded-lg border border-transparent focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all outline-hidden text-slate-800"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Fast Demo Role Switcher */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-medium text-slate-600">
          <span className="hidden sm:flex px-2 text-slate-400 items-center gap-1 font-normal">
            <UserCheck className="w-3.5 h-3.5" /> Demo vai trò:
          </span>
          <button
            onClick={() => onSwitchRole('MARKETER')}
            className={`px-2 sm:px-2.5 py-1 rounded-md transition-all font-semibold text-[11px] sm:text-xs ${
              currentUser?.role === 'MARKETER'
                ? 'bg-white text-indigo-600 shadow-xs'
                : 'hover:text-slate-900'
            }`}
          >
            Marketer
          </button>
          <button
            onClick={() => onSwitchRole('MANAGER')}
            className={`px-2 sm:px-2.5 py-1 rounded-md transition-all font-semibold text-[11px] sm:text-xs ${
              currentUser?.role === 'MANAGER'
                ? 'bg-white text-emerald-600 shadow-xs'
                : 'hover:text-slate-900'
            }`}
          >
            Manager
          </button>
        </div>

        {/* AI Assistant Quick Trigger */}
        <button
          onClick={onOpenAIDrawer}
          className="flex items-center gap-1.5 sm:gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs font-semibold px-2.5 sm:px-3.5 py-2 rounded-lg shadow-md shadow-indigo-500/20 transition-all active:scale-95 shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span className="hidden sm:inline">AI Copilot</span>
        </button>

        {/* Notification */}
        <button className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors relative">
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 bg-rose-500 rounded-full absolute top-1.5 right-1.5 ring-2 ring-white"></span>
        </button>
      </div>
    </header>
  );
};
