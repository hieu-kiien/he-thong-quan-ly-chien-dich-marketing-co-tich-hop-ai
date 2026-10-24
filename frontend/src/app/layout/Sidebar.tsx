import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  CalendarDays,
  ClipboardCheck,
  FileText,
  LayoutDashboard,
  Megaphone,
  MessageSquareText,
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
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-[0.8125rem] font-bold text-accent-fg"
        aria-hidden
      >
        M
      </span>
      {!compact && <span className="text-[0.9375rem] font-semibold tracking-tight text-fg">MarketFlow</span>}
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

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    cn(
      'group flex h-9 items-center gap-3 rounded-md px-2.5 text-sm font-medium transition-colors',
      'justify-center lg:justify-start',
      isActive ? 'bg-subtle text-fg' : 'text-fg-muted hover:bg-subtle/70 hover:text-fg',
    );

  return (
    <aside
      className="flex w-16 shrink-0 flex-col border-r border-border bg-surface lg:w-60"
      aria-label="Điều hướng chính"
    >
      <div className="flex h-14 items-center justify-center border-b border-border px-4 lg:justify-start">
        <NavLink to="/" className="rounded-md" aria-label="MarketFlow — Tổng quan">
          <span className="lg:hidden">
            <Logo compact />
          </span>
          <span className="hidden lg:inline">
            <Logo />
          </span>
        </NavLink>
      </div>
      <nav className="flex-1 overflow-y-auto px-2.5 py-3">
        <ul className="space-y-0.5">
          {items.map((item) => {
            const Icon = item.icon;
            const badge = item.badgeKey === 'reviews' ? pending.data : undefined;
            return (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end} className={linkCls} title={item.label}>
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={cn('h-[18px] w-[18px] shrink-0', isActive ? 'text-accent' : 'text-fg-subtle group-hover:text-fg-muted')}
                        aria-hidden
                      />
                      <span className="hidden flex-1 truncate lg:inline">{item.label}</span>
                      {badge ? (
                        <span className="hidden rounded bg-warning-soft px-1.5 text-xs font-semibold tabular text-warning-soft-fg lg:inline">
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
      <div className="border-t border-border px-2.5 py-3">
        <NavLink to="/settings" className={linkCls} title="Cài đặt">
          {({ isActive }) => (
            <>
              <Settings
                className={cn('h-[18px] w-[18px] shrink-0', isActive ? 'text-accent' : 'text-fg-subtle')}
                aria-hidden
              />
              <span className="hidden lg:inline">Cài đặt</span>
            </>
          )}
        </NavLink>
      </div>
    </aside>
  );
}
