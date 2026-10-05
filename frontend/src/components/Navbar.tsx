import React, { useState, useEffect, useRef } from 'react';
import { Search, Sparkles, Menu, Palette, LogOut, Shield, AlertTriangle, X, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';
import { NotificationCenter } from './NotificationCenter';
import { isOfflineDemoEnabled, isBackendConnected } from '../services/api';
import { useColorScheme } from '../utils/colorScheme';

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
  const { user, userRole, logout } = useAuth();
  const { scheme, toggle: toggleColorScheme } = useColorScheme();
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
    const query = searchQuery.trim();
    if (!query) return;
    // Trước đây chỉ gọi onNavigateTab('campaigns') rồi vứt mất `searchQuery`:
    // người dùng gõ tên chiến dịch rồi Enter (hoặc dùng Cmd+K) chỉ được chuyển tab,
    // không hề lọc. Truyền query xuống màn hình Campaigns để nó thật sự lọc.
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
    // `min-h-16` + `flex-wrap` thay cho `h-16` cứng. Ở viewport 320px @ zoom 200%
    // (160 CSS px) header cần ~220px cho [hamburger + switcher + AI + chuông +
    // theme + logout]: với `h-16` cứng các nút vượt mép trái và CHỒNG LÊN nhau
    // (18 vùng chồng lấn, WCAG 2.5.8). Cho phép xuống hàng giữ mọi nút bấm được
    // thay vì hy sinh chức năng nào; ở kích thước bình thường vẫn là một hàng.
    // Nền header phải đục (không phai) mới tính được độ tương phản: với
    // `bg-slate-900/90` + `backdrop-blur`, axe không xác định được màu nền hiệu
    // dụng và lấy nhầm nền sáng của trang, khiến mọi chữ màu nhạt trong header bị
    // báo fail. Đục hoàn toàn giữ đúng ý đồ thiết kế và cho tỷ lệ ổn định.
    //
    // `flex-wrap` cho phép vùng điều khiển xuống hàng khi hết chỗ (320px @ 200%
    // zoom). Vì vậy CHỈ dùng `min-h-16`, tuyệt đối không thêm `sm:h-16`: chiều
    // cao cố định 64px cắt mất hàng thứ hai, khiến các nút tràn ra ngoài header
    // và đè lên nội dung trang. Đã xảy ra thật trên production.
    <header className="min-h-16 py-1.5 sm:py-0 bg-slate-900 border-b border-slate-800 px-3 sm:px-6 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 sticky top-0 z-20 shadow-sm text-slate-100 no-print">
      {/* Left Area: Mobile Hamburger + Workspace Switcher + Search Input

          `flex-1 min-w-0` là bắt buộc, không phải mỹ thuật: vùng bên phải (nút
          điều khiển) chiếm ~450px, còn vùng này chỉ còn ~180px. Thiếu `min-w-0`
          thì con KHÔNG co lại được và tràn ra ngoài — đã xảy ra thật: nút chuyển
          workspace rộng 214px trong container 179px làm ô tìm kiếm bị bóp còn 70px
          và nút "Brand Kit" CHỒNG LÊN ô tìm kiếm (không bấm được). */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 basis-[45%] sm:basis-auto">
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

        {/* Workspace Switcher. Trước đây bọc trong `hidden sm:block` khiến trên
            điện thoại không có đường vào đổi/tạo workspace (sidebar cũng ẩn ở
            md), nên người dùng mobile bị kẹt ở workspace đầu tiên.
            Giữ nó hiện ở mọi kích thước, nhưng phải cho phép co lại
            (`min-w-0` + `max-w`), nếu không nó giữ nguyên 214px và đẩy các phần
            tử khác ra ngoài. */}
        <div className="min-w-0 max-w-[168px] shrink basis-0 flex-1 sm:basis-auto sm:flex-none">
          <WorkspaceSwitcher onOpenBrandKit={onOpenBrandKit} />
        </div>

        {/* Search Input Form. `flex-1 min-w-0` để nó co lại dần thay vì bị bóp
            về kích thước tối thiểu rồi CHỒNG LÊN phần tử kế bên. Ẩn hoàn toàn
            dưới `md` vì ở tầm kích thước đó ô tìm kiếm không đủ chỗ để dùng
            hữu ích; phím tắt Cmd+K vẫn hoạt động ở mọi màn hình có bàn phím. */}
        <form onSubmit={handleSearchSubmit} role="search" className="relative min-w-0 flex-1 max-w-xs hidden md:block">
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
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-xl text-xs font-medium text-slate-300 hover:text-white transition-all shadow-sm"
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

        {/* User Info & Role Badge.
            Badge vai trò chỉ hiện từ `lg` trở lên. Trước đây hiện từ `sm` và
            chiếm ~100px ở navbar, cộng dồn với các nút khác khiến vùng trái bị
            bóp và chồng lấn. Tên/email bên cạnh vốn đã là `hidden lg:flex`. */}
        {user && (
          <div className="hidden lg:flex items-center gap-2 pl-2 border-l border-slate-800 shrink-0">
            {/* Khối này khai báo lại `bg-slate-900` — cùng màu với header, nên
                giao diện không đổi. Cần thiết vì axe đo tương phản bằng cách dò
                nền của chính khối chứa chữ và các tổ tiên KẾ TIẾP; nó bỏ qua nền
                của `<header>` (đã thử cả `position: static` lẫn đổi tag, kết quả
                vẫn là nền trang `#F8FAFC`), nên chữ nhạt trong header bị báo sai
                là 1.41:1 so với thực tế ~11:1 trên nền slate-900. */}
            <div className="flex flex-col text-right bg-slate-900">
              <span className="text-xs font-semibold text-slate-200 leading-tight">
                {user.full_name}
              </span>
              <span className="text-[10px] text-slate-300 truncate max-w-[120px]">
                {user.email}
              </span>
            </div>
            {getRoleBadge(userRole)}
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
