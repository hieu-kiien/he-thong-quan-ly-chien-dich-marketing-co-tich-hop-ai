import { useLocation, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, ChevronDown, ChevronLeft, LogOut, Moon, Sparkles, Sun, UserRound } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useAuth } from '@/lib/auth';
import { useTheme } from '@/lib/theme';
import { ROLE_LABEL } from '@/lib/labels';
import { formatRelative } from '@/lib/format';
import { notificationsApi } from '@/lib/api/endpoints';
import { IconButton, Popover, Spinner, useToast } from '@/components/ui';
import { toggleContextualCopilot, useCopilotDrawerState } from '@/features/assistant/CopilotDrawer';
import { AI_PROVIDER_PILLS } from '@/features/assistant/components/ModelSelector';
import type { Notification } from '@/lib/types';

function NotificationsMenu() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const list = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list({ page: 1, page_size: 20 }),
    refetchInterval: 60_000,
  });
  const unread = list.data ? (list.data.unread_count ?? list.data.items.filter((n) => !n.is_read).length) : 0;

  const readOne = useMutation({
    mutationFn: (id: number) => notificationsApi.read(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
  const readAll = useMutation({
    mutationFn: () => notificationsApi.readAll(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
    onError: (e) => toast.apiError(e),
  });

  const open = (n: Notification, close: () => void) => {
    if (!n.is_read) readOne.mutate(n.id);
    close();
    if (n.link) navigate(n.link);
  };

  return (
    <Popover
      label="Thông báo"
      className="w-[22rem]"
      trigger={(p) => (
        <IconButton label={unread ? `Thông báo, ${unread} chưa đọc` : 'Thông báo'} {...p} className="relative">
          <Bell className="h-[18px] w-[18px]" />
          {unread > 0 && (
            <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-none text-white">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </IconButton>
      )}
    >
      {(close) => (
        <div>
          <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
            <p className="text-sm font-semibold">Thông báo</p>
            <button
              type="button"
              className="text-xs font-medium text-accent hover:underline disabled:text-fg-subtle disabled:no-underline"
              disabled={unread === 0 || readAll.isPending}
              onClick={() => readAll.mutate()}
            >
              Đánh dấu tất cả đã đọc
            </button>
          </div>
          <div className="max-h-[24rem] overflow-y-auto">
            {list.isLoading ? (
              <Spinner />
            ) : list.isError ? (
              <p className="px-4 py-6 text-center text-sm text-fg-muted">Không tải được thông báo.</p>
            ) : list.data && list.data.items.length > 0 ? (
              <ul className="divide-y divide-border">
                {list.data.items.map((n) => (
                  <li key={n.id}>
                    <button
                      type="button"
                      onClick={() => open(n, close)}
                      className="flex w-full gap-3 px-4 py-3 text-left hover:bg-subtle"
                    >
                      <span
                        className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', n.is_read ? 'bg-transparent' : 'bg-accent')}
                        aria-hidden
                      />
                      <span className="min-w-0">
                        <span className={cn('block text-[0.8125rem]', n.is_read ? 'text-fg-muted' : 'text-fg')}>
                          {n.message}
                        </span>
                        <span className="mt-0.5 block text-xs text-fg-subtle">{formatRelative(n.created_at)}</span>
                        {!n.is_read && <span className="sr-only">Chưa đọc</span>}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-4 py-8 text-center text-sm text-fg-muted">Chưa có thông báo nào.</p>
            )}
          </div>
        </div>
      )}
    </Popover>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  const initials = user.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  return (
    <Popover
      role="menu"
      label="Tài khoản"
      className="w-60 py-1"
      trigger={(p) => (
        <button
          type="button"
          {...p}
          className="flex h-9 items-center gap-2 rounded-md px-1.5 text-left hover:bg-subtle"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-semibold text-fg">
            {initials || <UserRound className="h-4 w-4" aria-hidden />}
          </span>
          <span className="hidden min-w-0 md:block">
            <span className="block max-w-[10rem] truncate text-[0.8125rem] font-medium leading-4 text-fg">{user.full_name}</span>
            <span className="block text-xs leading-4 text-fg-subtle">{ROLE_LABEL[user.role]}</span>
          </span>
          <ChevronDown className="hidden h-4 w-4 text-fg-subtle md:block" aria-hidden />
        </button>
      )}
    >
      {(close) => (
        <>
          <div className="border-b border-border px-3 py-2.5">
            <p className="truncate text-sm font-medium">{user.full_name}</p>
            <p className="truncate text-xs text-fg-subtle">{user.email}</p>
          </div>
          <div className="py-1">
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-fg hover:bg-subtle"
              onClick={() => {
                close();
                navigate('/settings');
              }}
            >
              <UserRound className="h-4 w-4 text-fg-subtle" aria-hidden />
              Tài khoản của tôi
            </button>
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-fg hover:bg-subtle"
              onClick={async () => {
                close();
                await logout();
                navigate('/login', { replace: true });
              }}
            >
              <LogOut className="h-4 w-4 text-fg-subtle" aria-hidden />
              Đăng xuất
            </button>
          </div>
        </>
      )}
    </Popover>
  );
}

export function Topbar() {
  const { mode, toggle } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const copilotState = useCopilotDrawerState();
  const isAssistantRoute = location.pathname.startsWith('/assistant');

  return (
    <header className="flex min-h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-surface px-4 py-2 lg:px-6">
      {/* Vùng tiêu đề ngữ cảnh của trang (nhận portal từ PageHeader hoặc hiển thị thông tin Trợ lý AI) */}
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {isAssistantRoute ? (
          <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg border border-border bg-subtle/70 px-2.5 text-xs font-medium text-fg-muted transition-colors hover:border-border-strong hover:bg-subtle hover:text-fg"
                title="Quay lại trang trước"
              >
                <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
                <span>Quay lại</span>
              </button>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="truncate text-sm font-bold tracking-tight text-fg sm:text-base">
                    Không gian Trợ lý AI Chiến lược
                  </h2>
                  <span className="hidden items-center gap-1 rounded-full bg-success-soft px-2 py-0.5 text-[10px] font-semibold text-success-soft-fg md:inline-flex">
                    <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden />
                    Miễn phí vĩnh viễn • 5 nền tảng
                  </span>
                </div>
                <div className="mt-0.5 hidden items-center gap-1.5 text-[11px] text-fg-muted sm:flex">
                  {AI_PROVIDER_PILLS.map((p, idx) => (
                    <span key={p.id} className="inline-flex items-center gap-1.5">
                      {idx > 0 && <span className="text-fg-subtle">•</span>}
                      <span>{p.name}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div
            id="mf-topbar-slot"
            className="flex min-w-0 flex-1 items-center justify-between gap-3"
          />
        )}
      </div>

      {/* Cụm công cụ toàn cục bên phải */}
      <div className="flex shrink-0 items-center gap-1.5">
        {!isAssistantRoute && (
          <>
            <div className="mx-1 hidden h-6 w-px bg-border xl:block" aria-hidden />
            <button
              type="button"
              onClick={toggleContextualCopilot}
              className={cn(
                'mr-0.5 inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-medium transition-colors',
                copilotState.open
                  ? 'border-ai/40 bg-ai-soft text-ai-soft-fg shadow-xs'
                  : 'border-border bg-subtle/60 text-fg-muted hover:border-ai/40 hover:bg-ai-soft/60 hover:text-ai',
              )}
              title="Mở/đóng khung Trợ lý AI ngữ cảnh (Ctrl+K)"
            >
              <Sparkles className="h-3.5 w-3.5 text-ai" aria-hidden />
              <span className="hidden sm:inline">Trợ lý AI</span>
              <kbd className="hidden rounded border border-border bg-surface px-1 py-0.5 font-mono text-[10px] text-fg-subtle md:inline">
                Ctrl+K
              </kbd>
            </button>
          </>
        )}
        <IconButton label={mode === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'} onClick={toggle}>
          {mode === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </IconButton>
        <NotificationsMenu />
        <div className="mx-1 h-6 w-px bg-border" aria-hidden />
        <UserMenu />
      </div>
    </header>
  );
}
