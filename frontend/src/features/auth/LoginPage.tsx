import { useEffect, useState, type FormEvent } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Bot,
  Eye,
  EyeOff,
  Layers,
  Lock,
  Mail,
  ShieldCheck,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { useDocumentTitle } from '@/lib/hooks';
import { toApiError } from '@/lib/api/client';

export default function LoginPage() {
  const { login, register, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();

  const [isRegisterMode, setIsRegisterMode] = useState(
    () => location.pathname === '/register' || params.get('mode') === 'register',
  );

  useEffect(() => {
    setIsRegisterMode(location.pathname === '/register' || params.get('mode') === 'register');
  }, [location.pathname, params]);

  useDocumentTitle(isRegisterMode ? 'Đăng ký tài khoản' : 'Đăng nhập');

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState<{
    full_name?: string;
    email?: string;
    password?: string;
    confirm_password?: string;
  }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const switchMode = (registerMode: boolean) => {
    setIsRegisterMode(registerMode);
    setErrors({});
    setFormError(null);
    const next = params.get('next');
    const query = next ? `?next=${encodeURIComponent(next)}` : '';
    navigate(registerMode ? `/register${query}` : `/login${query}`, { replace: true });
  };

  const handleQuickFill = (demoEmail: string, demoPass: string) => {
    if (isRegisterMode) {
      setIsRegisterMode(false);
    }
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrors({});
    setFormError(null);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const nextErrors: typeof errors = {};
    const trimmedEmail = email.trim().toLowerCase();
    const trimmedName = fullName.trim();

    if (isRegisterMode) {
      if (!trimmedName || trimmedName.length < 2) {
        nextErrors.full_name = 'Vui lòng nhập họ và tên hợp lệ (tối thiểu 2 ký tự).';
      }
    }

    if (!trimmedEmail) {
      nextErrors.email = 'Vui lòng nhập email.';
    } else if (!/^\S+@\S+\.\S+$/.test(trimmedEmail)) {
      nextErrors.email = 'Email không hợp lệ.';
    }

    if (!password) {
      nextErrors.password = 'Vui lòng nhập mật khẩu.';
    } else if (isRegisterMode) {
      if (password.length < 8) {
        nextErrors.password = 'Mật khẩu tối thiểu 8 ký tự.';
      } else if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
        nextErrors.password = 'Mật khẩu phải có cả chữ và số.';
      }
      if (password !== confirmPassword) {
        nextErrors.confirm_password = 'Mật khẩu xác nhận không khớp.';
      }
    }

    setErrors(nextErrors);
    setFormError(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      if (isRegisterMode) {
        await register({
          email: trimmedEmail,
          full_name: trimmedName,
          password,
        });
      } else {
        await login({ email: trimmedEmail, password });
      }
      const target = params.get('next');
      navigate(target && target.startsWith('/') && !target.startsWith('//') ? target : '/', {
        replace: true,
      });
    } catch (err) {
      const apiErr = toApiError(err);
      setErrors({
        full_name: apiErr.fields.full_name,
        email: apiErr.fields.email,
        password: apiErr.fields.password,
      });
      setFormError(apiErr.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F6F5F0] text-[#121316] flex flex-col lg:flex-row font-sans selection:bg-teal-700/20">
      {/* Cột trái: Giới thiệu nền tảng & kiến trúc hệ thống */}
      <aside className="hidden lg:flex lg:w-5/12 xl:w-1/2 bg-[#121316] text-[#F6F5F0] p-12 xl:p-16 flex-col justify-between relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(#F6F5F0 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white font-black text-lg shadow-sm">
            M
          </div>
          <div>
            <span className="text-lg font-extrabold tracking-tight block leading-none">
              MarketFlow
            </span>
            <span className="text-[11px] font-mono uppercase tracking-widest text-stone-400">
              Hệ thống quản lý chiến dịch marketing
            </span>
          </div>
        </div>

        <div className="relative z-10 space-y-8 my-auto py-12">
          <div className="space-y-4">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-xs font-semibold text-teal-400">
              <Bot className="w-3.5 h-3.5" />
              Quản trị Chiến dịch Đa kênh &amp; Trợ lý AI
            </span>
            <h2 className="text-3xl xl:text-4xl font-extrabold tracking-tight leading-tight">
              Điều phối chiến dịch, kiểm duyệt nội dung và làm việc cùng AI trên dữ liệu thực.
            </h2>
            <p className="text-sm text-stone-400 leading-relaxed max-w-lg">
              Mọi nội dung và đề xuất từ Trợ lý AI đều bám sát sản phẩm, thông điệp cốt lõi, khách hàng mục tiêu và quy chuẩn thương hiệu của từng chiến dịch — kiểm soát chặt chẽ qua xác nhận của con người.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 pt-4 border-t border-white/10 max-w-lg">
            <div className="flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 text-teal-400">
                <Layers className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">
                  Ngữ cảnh Chiến dịch &amp; Phân bổ ngân sách kênh
                </h3>
                <p className="text-xs text-stone-400 mt-0.5">
                  Quản lý mục tiêu, ngân sách từng kênh, bản thảo nội dung và lịch đăng trên một luồng thống nhất.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 text-emerald-400">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">
                  Trợ lý AI theo phiên chat &amp; Phê duyệt hai bước
                </h3>
                <p className="text-xs text-stone-400 mt-0.5">
                  AI đọc dữ liệu thực của dự án, kiểm tra từ cấm theo hồ sơ thương hiệu và tạo thẻ đề xuất để bạn xác nhận trước khi lưu.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 text-amber-400">
                <BarChart3 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">
                  Báo cáo hiệu suất thực tế (CTR, CVR, CPC, CPA)
                </h3>
                <p className="text-xs text-stone-400 mt-0.5">
                  Nhập chỉ số theo ngày hoặc tải file CSV có bước đối soát trước khi ghi nhận vào hệ thống.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-xs text-stone-500 border-t border-white/10 pt-6">
          <span>© 2026 MarketFlow · Học phần AIA331</span>
          <span className="font-mono">Phân quyền RBAC • Trợ lý AI • Kiểm duyệt nội dung</span>
        </div>
      </aside>

      {/* Cột phải: Form Đăng nhập & Đăng ký */}
      <main className="flex-1 flex items-center justify-center p-6 sm:p-10 lg:p-12">
        <div className="w-full max-w-md bg-white rounded-2xl border border-stone-200/90 shadow-sm p-6 sm:p-8 space-y-6">
          {/* Header */}
          <div className="space-y-1.5">
            <div className="flex lg:hidden items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white font-black text-sm">
                M
              </div>
              <span className="font-extrabold text-base tracking-tight text-[#121316]">
                MarketFlow
              </span>
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-[#121316]">
              {isRegisterMode ? 'Đăng ký tài khoản mới' : 'Đăng nhập hệ thống'}
            </h1>
            <p className="text-xs text-stone-500">
              {isRegisterMode
                ? 'Tạo tài khoản Quản lý Marketing để thiết lập thương hiệu, khởi tạo chiến dịch và cấp tài khoản cho nhân viên'
                : 'Truy cập hệ thống quản lý chiến dịch, nội dung và Trợ lý AI'}
            </p>
          </div>

          {/* Chuyển chế độ Đăng nhập / Đăng ký */}
          <div
            role="tablist"
            aria-label="Chọn chế độ xác thực"
            className="grid grid-cols-2 p-1 bg-stone-100 rounded-xl border border-stone-200/80"
          >
            <button
              type="button"
              role="tab"
              aria-selected={!isRegisterMode}
              onClick={() => switchMode(false)}
              className={`py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                !isRegisterMode
                  ? 'bg-white text-[#121316] shadow-xs border border-stone-200/60'
                  : 'text-stone-500 hover:text-[#121316]'
              }`}
            >
              Đăng nhập
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={isRegisterMode}
              onClick={() => switchMode(true)}
              className={`py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                isRegisterMode
                  ? 'bg-white text-[#121316] shadow-xs border border-stone-200/60'
                  : 'text-stone-500 hover:text-[#121316]'
              }`}
            >
              Đăng ký mới
            </button>
          </div>

          {sessionExpired && !formError && (
            <div
              role="status"
              className="p-3 rounded-xl bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium"
            >
              Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.
            </div>
          )}

          {formError && (
            <div
              role="alert"
              aria-live="assertive"
              className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-start gap-2"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            {isRegisterMode && (
              <div className="space-y-1.5">
                <label htmlFor="register-fullname" className="block text-xs font-bold text-stone-700">
                  Họ và tên đầy đủ
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    id="register-fullname"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Nguyễn Văn A"
                    autoComplete="name"
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-teal-700 transition-colors"
                  />
                </div>
                {errors.full_name && (
                  <p className="text-xs text-rose-600 font-medium">{errors.full_name}</p>
                )}
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="auth-email" className="block text-xs font-bold text-stone-700">
                Địa chỉ Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="auth-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ten@marketflow.vn"
                  autoComplete="username"
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-teal-700 transition-colors"
                />
              </div>
              {errors.email && <p className="text-xs text-rose-600 font-medium">{errors.email}</p>}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="auth-password" className="block text-xs font-bold text-stone-700">
                Mật khẩu
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="auth-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={isRegisterMode ? 'Tối thiểu 8 ký tự (có chữ và số)' : 'Nhập mật khẩu'}
                  autoComplete={isRegisterMode ? 'new-password' : 'current-password'}
                  className="w-full pl-10 pr-10 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-teal-700 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 p-1 cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-rose-600 font-medium">{errors.password}</p>
              )}
            </div>

            {isRegisterMode && (
              <>
                <div className="space-y-1.5">
                  <label
                    htmlFor="auth-confirm-password"
                    className="block text-xs font-bold text-stone-700"
                  >
                    Xác nhận mật khẩu
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      id="auth-confirm-password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Nhập lại mật khẩu"
                      autoComplete="new-password"
                      className="w-full pl-10 pr-10 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-teal-700 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                      aria-label={
                        showConfirmPassword ? 'Ẩn mật khẩu xác nhận' : 'Hiện mật khẩu xác nhận'
                      }
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 p-1 cursor-pointer"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  {errors.confirm_password && (
                    <p className="text-xs text-rose-600 font-medium">{errors.confirm_password}</p>
                  )}
                </div>

                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 text-xs text-stone-600 leading-relaxed">
                  <span className="font-bold text-[#121316] block mb-0.5">
                    Vai trò mặc định: Quản lý Marketing (Manager)
                  </span>
                  Tài khoản đăng ký mới được cấp quyền Quản lý để thiết lập hồ sơ thương hiệu, khởi tạo chiến dịch và trực tiếp tạo tài khoản cho Nhân viên Marketing trong mục Cài đặt → Người dùng.
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-xl text-sm font-bold flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <span>
                {submitting
                  ? isRegisterMode
                    ? 'Đang tạo tài khoản...'
                    : 'Đang xác thực...'
                  : isRegisterMode
                    ? 'Hoàn tất Đăng ký'
                    : 'Đăng nhập'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {/* Nút điền nhanh tài khoản mẫu để test */}
            {!isRegisterMode && (
              <div className="pt-4 border-t border-stone-100 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-stone-400">
                    Tài khoản mẫu có sẵn (Bấm để điền nhanh)
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleQuickFill('manager@marketflow.vn', 'Manager@123')}
                    className="px-3 py-2 rounded-xl border border-stone-200 hover:border-teal-600 bg-stone-50 hover:bg-teal-50/40 text-left transition-colors cursor-pointer"
                  >
                    <span className="block text-xs font-bold text-stone-800">
                      Quản lý (Manager)
                    </span>
                    <span className="block text-[11px] font-mono text-stone-500 truncate">
                      manager@marketflow.vn
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickFill('marketer@marketflow.vn', 'Marketer@123')}
                    className="px-3 py-2 rounded-xl border border-stone-200 hover:border-teal-600 bg-stone-50 hover:bg-teal-50/40 text-left transition-colors cursor-pointer"
                  >
                    <span className="block text-xs font-bold text-stone-800">
                      Nhân viên Marketing
                    </span>
                    <span className="block text-[11px] font-mono text-stone-500 truncate">
                      marketer@marketflow.vn
                    </span>
                  </button>
                </div>
              </div>
            )}

            <div className="text-center text-xs text-stone-500 pt-1">
              {isRegisterMode ? (
                <>
                  Đã có tài khoản?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode(false)}
                    className="font-bold text-teal-700 hover:underline cursor-pointer"
                  >
                    Đăng nhập ngay
                  </button>
                </>
              ) : (
                <>
                  Chưa có tài khoản?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode(true)}
                    className="font-bold text-teal-700 hover:underline cursor-pointer"
                  >
                    Đăng ký tài khoản mới
                  </button>
                </>
              )}
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
