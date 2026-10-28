import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  CalendarDays,
  ClipboardCheck,
  FileText,
  LayoutDashboard,
  Megaphone,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { useAuth } from '@/lib/auth';
import { isManager } from '@/lib/permissions';
import { contentsApi } from '@/lib/api/endpoints';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  managerOnly?: boolean;
  badgeKey?: 'reviews';
}

const NAV: NavItem[] = [
  { to: '/', label: 'Tổng quan', icon: LayoutDashboard, end: true },
  { to: '/campaigns', label: 'Chiến dịch', icon: Megaphone },
  { to: '/contents', label: 'Nội dung', icon: FileText },
  { to: '/reviews', label: 'Duyệt nội dung', icon: ClipboardCheck, managerOnly: true, badgeKey: 'reviews' },
  { to: '/calendar', label: 'Lịch đăng', icon: CalendarDays },
  { to: '/assistant', label: 'Trợ lý AI', icon: MessageSquareText },
];

export function Logo({ compact }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <span
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-teal-400 text-sm font-bold text-white shadow-sm"
        aria-hidden
      >
        M
      </span>
      {!compact && (
        <span className="text-[0.95rem] font-bold tracking-tight text-white">
          MarketFlow
        </span>
      )}
    </span>
  );
}

function usePendingReviewCount(enabled: boolean) {
  return useQuery({
    queryKey: ['contents', 'pending-count'],
    queryFn: () => contentsApi.list({ status: 'PENDING_REVIEW', page: 1, page_size: 1 }),
    enabled,
    refetchInterval: 60_000,
    select: (d) => d.total,
  });
}

export function Sidebar() {
  const { user } = useAuth();
  const manager = isManager(user);
  const pending = usePendingReviewCount(manager);
  const items = NAV.filter((n) => !n.managerOnly || manager);
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('mf.sidebar.collapsed') === '1';
    } catch {
      return false;
    }
  });

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('mf.sidebar.collapsed', next ? '1' : '0');
      } catch {
        // Bỏ qua nếu trình duyệt chặn localStorage
      }
      return next;
    });
  };

  const linkCls = ({ isActive }: { isActive: boolean }, isAiNav?: boolean) =>
    cn(
      'group flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-all',
      'justify-center',
      !collapsed && 'lg:justify-start',
      isActive
        ? isAiNav
          ? 'bg-teal-600 text-white shadow-xs'
          : 'bg-blue-600 text-white shadow-xs'
        : 'text-slate-300 hover:bg-slate-800/80 hover:text-white',
    );

  return (
    <aside
      className={cn(
        'flex w-16 shrink-0 flex-col border-r border-slate-800 bg-slate-900 text-slate-100 transition-[width] duration-200',
        collapsed ? 'lg:w-16' : 'lg:w-60',
      )}
      aria-label="Điều hướng chính"
    >
      <div
        className={cn(
          'flex h-14 items-center justify-center border-b border-slate-800/90 px-4',
          !collapsed && 'lg:justify-start',
        )}
      >
        <NavLink to="/" className="rounded-md focus:outline-none" aria-label="MarketFlow — Tổng quan">
          <span className={collapsed ? '' : 'lg:hidden'}>
            <Logo compact />
          </span>
          {!collapsed && (
            <span className="hidden lg:inline">
              <Logo />
            </span>
          )}
        </NavLink>
      </div>
      <nav className="flex-1 px-2.5 py-3.5">
        <ul className="space-y-1">
          {items.map((item) => {
            const Icon = item.icon;
            const badge = item.badgeKey === 'reviews' ? pending.data : undefined;
            const isAiNav = item.to === '/assistant';
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={(navState) => linkCls(navState, isAiNav)}
                  title={item.label}
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={cn(
                          'h-[18px] w-[18px] shrink-0 transition-colors',
                          isActive
                            ? 'text-white'
                            : isAiNav
                              ? 'text-teal-400 group-hover:text-teal-300'
                              : 'text-slate-400 group-hover:text-white',
                        )}
                        aria-hidden
                      />
                      {!collapsed && <span className="hidden flex-1 truncate lg:inline">{item.label}</span>}
                      {!collapsed && badge ? (
                        <span className="hidden rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-semibold tabular-nums text-amber-300 lg:inline">
                          {badge}
                          <span className="sr-only"> nội dung chờ duyệt</span>
                        </span>
                      ) : null}
                    </>
                  )}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="space-y-1 border-t border-slate-800/90 px-2.5 py-2.5">
        <NavLink to="/settings" className={(navState) => linkCls(navState, false)} title="Cài đặt">
          {({ isActive }) => (
            <>
              <Settings
                className={cn(
                  'h-[18px] w-[18px] shrink-0',
                  isActive ? 'text-white' : 'text-slate-400 group-hover:text-white',
                )}
                aria-hidden
              />
              {!collapsed && <span className="hidden lg:inline">Cài đặt</span>}
            </>
          )}
        </NavLink>
        <button
          type="button"
          onClick={toggleCollapsed}
          className={cn(
            'hidden h-8 w-full items-center gap-3 rounded-lg px-3 text-xs font-medium text-slate-400 transition-colors hover:bg-slate-800 hover:text-white lg:flex',
            collapsed ? 'justify-center' : 'justify-start',
          )}
          title={collapsed ? 'Mở rộng thanh điều hướng (240px)' : 'Thu gọn thanh điều hướng (64px)'}
          aria-label={collapsed ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng'}
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4 shrink-0" aria-hidden />
          ) : (
            <>
              <PanelLeftClose className="h-4 w-4 shrink-0" aria-hidden />
              <span className="truncate">Thu gọn menu</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
