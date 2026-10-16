import React, { useState, useEffect, useRef } from 'react';
import { Search, Sparkles, Menu, Palette, LogOut, Shield, AlertTriangle, X, Sun, Moon, ChevronDown, Check } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';
import { NotificationCenter } from './NotificationCenter';
import { isOfflineDemoEnabled, isBackendConnected, getApiErrorMessage } from '../services/api';
import { useColorScheme } from '../utils/colorScheme';
import { useToast } from './Toast';

interface NavbarProps {
  onOpenBrandKit: () => void;
  onOpenAIDrawer: () => void;
  onToggleSidebar?: () => void;
  onNavigateTab?: (tab: string) => void;
  /** Nhận truy vấn tìm kiếm để điều hướng sang màn hình có thực sự lọc theo đó. */
  onSearchCampaigns?: (query: string) => void;
  pendingReviewsCount?: number;
  activeCampaignsCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenBrandKit,
  onOpenAIDrawer,
  onToggleSidebar,
  onNavigateTab,
  onSearchCampaigns,
  pendingReviewsCount = 0,
  activeCampaignsCount = 0
}) => {
  const { user, userRole, switchDemoRole, logout } = useAuth();
  const toast = useToast();
  const { scheme, toggle: toggleColorScheme } = useColorScheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [roleSwitcherOpen, setRoleSwitcherOpen] = useState(false);
  const [switchingRole, setSwitchingRole] = useState(false);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const roleSwitcherRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (roleSwitcherRef.current && !roleSwitcherRef.current.contains(e.target as Node)) {
        setRoleSwitcherOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSwitchDemoRole = async (roleKey: 'manager' | 'marketer' | 'approver') => {
    if (switchingRole) return;
    setSwitchingRole(true);
    try {
      const nextUser = await switchDemoRole(roleKey);
      setRoleSwitcherOpen(false);
      toast.success(`Đã chuyển sang tài khoản: ${nextUser.full_name}`);
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể chuyển tài khoản');
    } finally {
      setSwitchingRole(false);
    }
  };

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
    const query = searchQuery.trim();
    if (!query) return;
    if (onSearchCampaigns) {
      onSearchCampaigns(query);
      return;
    }
    if (onNavigateTab) {
      onNavigateTab('campaigns');
    }
  };

  const getRoleBadge = (role?: string | null) => {
    switch (role) {
      case 'ADMIN':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-[#1E2025] text-slate-200 border border-slate-700 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Quản trị</span>
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
            <span>Người duyệt</span>
          </span>
        );
      case 'MARKETER':
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-[#1E2025] text-slate-200 border border-slate-700 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Chuyên viên</span>
          </span>
        );
    }
  };

  return (
    <header className="min-h-16 py-1.5 sm:py-0 bg-[#141518] border-b border-[#26282D] px-3 sm:px-6 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 sticky top-0 z-20 shadow-sm text-slate-100 no-print">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 basis-[45%] sm:basis-auto">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            aria-label="Mở thanh điều hướng"
            className="p-1.5 sm:p-2 -ml-0.5 sm:-ml-1 text-slate-400 hover:text-white hover:bg-[#1E2025] rounded-lg md:hidden transition-colors shrink-0"
            title="Mở thanh điều hướng"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="min-w-0 max-w-[168px] shrink basis-0 flex-1 sm:basis-auto sm:flex-none">
          <WorkspaceSwitcher onOpenBrandKit={onOpenBrandKit} />
        </div>

        <form onSubmit={handleSearchSubmit} role="search" className="relative min-w-0 flex-1 max-w-xs hidden md:block">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Tìm kiếm chiến dịch"
            placeholder="Tìm chiến dịch (Ctrl+K)..."
            className="w-full bg-[#101114] hover:bg-[#18191D] focus:bg-[#101114] text-xs sm:text-sm pl-9 pr-8 py-1.5 rounded-xl border border-[#26282D] focus:border-[#D95D39] transition-all outline-none text-slate-200 placeholder-slate-500"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              aria-label="Xóa từ khoá tìm kiếm"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-1 sm:gap-3 shrink-0 basis-[45%] sm:basis-auto justify-end">
        {isOfflineDemoEnabled() && !isBackendConnected() && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/20 border border-amber-500/40 text-amber-300 rounded-xl text-xs font-bold shrink-0"
            title="Chế độ ngoại tuyến dự phòng"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="hidden sm:inline">Ngoại tuyến</span>
            <span className="sm:hidden">Offline</span>
          </div>
        )}

        {/* Brand Kit Quick Trigger */}
        <button
          onClick={onOpenBrandKit}
          aria-label="Cấu hình Brand Kit"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-[#1E2025] hover:bg-[#26282D] border border-[#2E3138] rounded-xl text-xs font-medium text-slate-200 hover:text-white transition-all shadow-sm"
          title="Quy chuẩn giọng văn và từ cấm thương hiệu"
        >
          <Palette className="w-3.5 h-3.5 text-[#F08A6C]" />
          <span>Quy chuẩn thương hiệu</span>
        </button>

        {/* AI Assistant Quick Trigger */}
        <button
          onClick={onOpenAIDrawer}
          aria-label="Mở AI Copilot"
          className="flex items-center gap-1.5 sm:gap-2 bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-semibold px-2 sm:px-3 py-1.5 rounded-xl transition-all active:scale-95 shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Soạn nhanh</span>
        </button>

        {/* Centralized Notification Center */}
        <NotificationCenter
          pendingReviewsCount={pendingReviewsCount}
          activeCampaignsCount={activeCampaignsCount}
          onNavigateTab={onNavigateTab}
        />

        {user && (
          <div
            ref={roleSwitcherRef}
            className="hidden lg:flex items-center gap-2 pl-2 border-l border-[#26282D] shrink-0 relative"
          >
            <div className="flex flex-col text-right bg-[#141518]">
              <span className="text-xs font-semibold text-slate-200 leading-tight">
                {user.full_name}
              </span>
              <span className="text-[10px] text-slate-300 truncate max-w-[120px]">
                {user.email}
              </span>
            </div>
            <button
              type="button"
              data-testid="navbar-role-switcher-btn"
              onClick={() => setRoleSwitcherOpen((prev) => !prev)}
              aria-expanded={roleSwitcherOpen}
              aria-label="Đổi nhanh tài khoản phân quyền"
              title="Bấm để chuyển nhanh giữa 3 cấp tài khoản (Quản lý / Chuyên viên / Người duyệt)"
              className="flex items-center gap-0.5 cursor-pointer hover:opacity-90 transition-opacity"
            >
              {getRoleBadge(userRole)}
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {roleSwitcherOpen && (
              <div
                data-testid="navbar-role-switcher-menu"
                className="absolute right-0 top-full mt-2 w-72 bg-[#141518] border border-[#26282D] rounded-xl shadow-2xl p-3 z-50 text-left space-y-2"
              >
                <div className="pb-2 border-b border-[#26282D]">
                  <div className="text-xs font-bold text-white flex items-center justify-between">
                    <span>Chuyển tài khoản theo chức danh</span>
                    <span className="text-[10px] font-mono bg-[#1E2025] text-slate-300 px-1.5 py-0.5 rounded">
                      3 cấp quyền
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                    Kiểm tra quy trình người viết gửi bài và sếp duyệt chéo:
                  </p>
                </div>

                {[
                  {
                    key: 'manager' as const,
                    label: 'Nguyễn Quản Lý (Trưởng phòng)',
                    email: 'manager@gmail.com',
                    desc: 'Tạo chiến dịch, phân bổ ngân sách, duyệt hoặc trả bài',
                    active: user.email === 'manager@gmail.com',
                  },
                  {
                    key: 'marketer' as const,
                    label: 'Trần Chuyên Viên (Người viết bài)',
                    email: 'marketer@gmail.com',
                    desc: 'Soạn mẫu quảng cáo, sửa theo góp ý và gửi duyệt',
                    active: user.email === 'marketer@gmail.com',
                  },
                  {
                    key: 'approver' as const,
                    label: 'Lê Duyệt Bài (Giám đốc / Khách hàng)',
                    email: 'approver@gmail.com',
                    desc: 'Kiểm soát độc lập: Phê duyệt đăng hoặc trả bài yêu cầu sửa',
                    active: user.email === 'approver@gmail.com',
                  },
                ].map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    disabled={switchingRole}
                    onClick={() => handleSwitchDemoRole(item.key)}
                    className={`w-full p-2.5 rounded-xl border text-left transition-all cursor-pointer flex items-start justify-between gap-2 ${
                      item.active
                        ? 'bg-[#1E2025] border-[#D95D39] text-white'
                        : 'bg-[#101114] hover:bg-[#1E2025] border-[#26282D] text-slate-200'
                    }`}
                  >
                    <div className="space-y-0.5 min-w-0">
                      <div className="text-xs font-bold truncate">{item.label}</div>
                      <div className="text-[10px] font-mono text-[#F08A6C]">{item.email}</div>
                      <div className="text-[10px] text-slate-400 leading-tight">{item.desc}</div>
                    </div>
                    {item.active && <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Chuyển giao diện sáng/tối. Trước đây các lớp `dark:` tồn tại trong
            code nhưng không có đường nào để kích hoạt hay tắt, và Tailwind mặc
            định bám `prefers-color-scheme` khiến giao diện tự đổi theo thiết bị. */}
        <button
          type="button"
          onClick={toggleColorScheme}
          aria-label={scheme === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
          title={scheme === 'dark' ? 'Giao diện sáng' : 'Giao diện tối'}
          className="p-2 text-slate-400 hover:text-amber-300 hover:bg-slate-800 rounded-xl border border-transparent hover:border-slate-700 transition-colors shrink-0"
        >
          {scheme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

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
