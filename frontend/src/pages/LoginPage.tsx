import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getApiErrorMessage } from '../services/api';
import {
  Sparkles,
  ShieldCheck,
  BarChart3,
  Layers,
  Eye,
  EyeOff,
  ArrowRight,
  Lock,
  Mail,
  User as UserIcon,
  AlertCircle,
} from 'lucide-react';

export interface LoginPageProps {
  mode?: 'login' | 'register';
  onNavigateToRegister?: () => void;
  onNavigateToLogin?: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  mode = 'login',
  onNavigateToRegister,
  onNavigateToLogin,
}) => {
  const { login, register } = useAuth();
  const [isRegisterMode, setIsRegisterMode] = useState(mode === 'register');

  React.useEffect(() => {
    setIsRegisterMode(mode === 'register');
  }, [mode]);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const role: 'MARKETER' = 'MARKETER';

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isRegisterMode) {
      if (!fullName.trim() || fullName.trim().length < 2) {
        setError('Vui lòng nhập họ và tên hợp lệ (tối thiểu 2 ký tự).');
        return;
      }
      if (password.length < 6) {
        setError('Mật khẩu phải có ít nhất 6 ký tự.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Mật khẩu xác nhận không khớp. Vui lòng kiểm tra lại.');
        return;
      }
    }

    setIsLoading(true);
    try {
      if (isRegisterMode) {
        await register({
          email: email.trim(),
          password,
          full_name: fullName.trim(),
          role,
        });
      } else {
        await login(email.trim(), password);
      }
    } catch (err: any) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setIsRegisterMode(false);
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  const switchMode = (registerMode: boolean) => {
    setIsRegisterMode(registerMode);
    setError(null);
    if (registerMode) {
      onNavigateToRegister?.();
    } else {
      onNavigateToLogin?.();
    }
  };

  const emailInputId = isRegisterMode ? 'register-email' : 'email';
  const passwordInputId = isRegisterMode ? 'register-password' : 'password';

  return (
    <div className="min-h-screen bg-[#F6F5F0] text-[#121316] flex flex-col lg:flex-row font-sans selection:bg-[#D95D39]/20">
      {/* Left Column: Editorial Brand & Architecture Overview */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-1/2 bg-[#121316] text-[#F6F5F0] p-12 xl:p-16 flex-col justify-between relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(#F6F5F0 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#D95D39] flex items-center justify-center text-white font-black text-lg shadow-sm">
            M
          </div>
          <div>
            <span className="text-lg font-extrabold tracking-tight block leading-none">
              MarketFlow AI
            </span>
            <span className="text-[11px] font-mono uppercase tracking-widest text-stone-400">
              Campaign Operations Platform
            </span>
          </div>
        </div>

        <div className="relative z-10 space-y-8 my-auto py-12">
          <div className="space-y-4">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-xs font-semibold text-[#D95D39]">
              <Sparkles className="w-3.5 h-3.5" />
              Quản trị Chiến dịch Tiếp thị Đa kênh
            </span>
            <h1 className="text-3xl xl:text-4xl font-extrabold tracking-tight leading-tight">
              Điều phối chiến dịch, kiểm duyệt nội dung và tối ưu hiệu suất dựa trên dữ liệu thực.
            </h1>
            <p className="text-sm text-stone-400 leading-relaxed max-w-lg">
              Mọi nội dung do AI hỗ trợ đều bám sát Sản phẩm, USP, Tệp khách hàng mục tiêu và quy chuẩn Brand Kit của từng chiến dịch — minh bạch nguồn gốc và kiểm soát chặt chẽ qua quy trình phê duyệt.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 pt-4 border-t border-white/10 max-w-lg">
            <div className="flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 text-[#D95D39]">
                <Layers className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Ngữ cảnh Chiến dịch & Sản phẩm rõ ràng</h2>
                <p className="text-xs text-stone-400 mt-0.5">
                  Kết nối trực tiếp dữ liệu sản phẩm, thông điệp cốt lõi (USP) và ngân sách kênh vào từng bản thảo.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 text-emerald-400">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Phê duyệt HITL & Quét tuân thủ</h2>
                <p className="text-xs text-stone-400 mt-0.5">
                  Kiểm soát từ khóa cấm theo Brand Kit và quy trình duyệt nhiều cấp trước khi xuất bản.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 text-amber-400">
                <BarChart3 className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Phân tích ROAS, Pacing & Chẩn đoán KPI</h2>
                <p className="text-xs text-stone-400 mt-0.5">
                  Theo dõi chi phí thực tế, cảnh báo bão hòa quảng cáo và đề xuất phân bổ ngân sách.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-xs text-stone-500 border-t border-white/10 pt-6">
          <span>© 2026 MarketFlow Enterprise</span>
          <span className="font-mono">RBAC • Multi-Workspace • Audit Log</span>
        </div>
      </div>

      {/* Right Column: Authentication Form */}
      <main className="flex-1 flex items-center justify-center p-6 sm:p-10 lg:p-12">
        <div className="w-full max-w-md bg-white rounded-2xl border border-stone-200/90 shadow-sm p-6 sm:p-8 space-y-6">
          {/* Header */}
          <div className="space-y-1.5">
            <div className="flex lg:hidden items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-lg bg-[#D95D39] flex items-center justify-center text-white font-black text-sm">
                M
              </div>
              <span className="font-extrabold text-base tracking-tight text-[#121316]">
                MarketFlow AI
              </span>
            </div>
            <h2 className="text-2xl font-extrabold tracking-tight text-[#121316]">
              {isRegisterMode ? 'Tạo tài khoản mới' : 'Đăng nhập hệ thống'}
            </h2>
            <p className="text-xs text-stone-500">
              {isRegisterMode
                ? 'Khởi tạo không gian làm việc cho chiến dịch tiếp thị của bạn'
                : 'Truy cập trung tâm quản lý chiến dịch và sáng tạo nội dung'}
            </p>
          </div>

          {/* Mode Switcher Tabs */}
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
              className={`py-2 text-xs font-bold rounded-lg transition-all ${
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
              className={`py-2 text-xs font-bold rounded-lg transition-all ${
                isRegisterMode
                  ? 'bg-white text-[#121316] shadow-xs border border-stone-200/60'
                  : 'text-stone-500 hover:text-[#121316]'
              }`}
            >
              Đăng ký mới
            </button>
          </div>

          {/* Form */}
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            {isRegisterMode && (
              <div className="space-y-1.5">
                <label
                  htmlFor="register-fullname"
                  className="block text-xs font-bold text-stone-700"
                >
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
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-[#121316] transition-colors"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor={emailInputId} className="block text-xs font-bold text-stone-700">
                Địa chỉ Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id={emailInputId}
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  autoComplete="email"
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-[#121316] transition-colors"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor={passwordInputId} className="block text-xs font-bold text-stone-700">
                Mật khẩu
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id={passwordInputId}
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={isRegisterMode ? 'Tối thiểu 6 ký tự' : 'Nhập mật khẩu'}
                  autoComplete={isRegisterMode ? 'new-password' : 'current-password'}
                  className="w-full pl-10 pr-10 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-[#121316] transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 p-1"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {isRegisterMode && (
              <>
                <div className="space-y-1.5">
                  <label
                    htmlFor="confirmPassword"
                    className="block text-xs font-bold text-stone-700"
                  >
                    Xác nhận mật khẩu
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      id="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Nhập lại mật khẩu"
                      autoComplete="new-password"
                      className="w-full pl-10 pr-10 py-2.5 text-sm bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:bg-white focus:border-[#121316] transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                      aria-label={
                        showConfirmPassword ? 'Ẩn mật khẩu xác nhận' : 'Hiện mật khẩu xác nhận'
                      }
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 p-1"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 text-xs text-stone-600 leading-relaxed">
                  <span className="font-bold text-[#121316] block mb-0.5">
                    Phân quyền mặc định: Nhân viên Marketing (Marketer)
                  </span>
                  Tài khoản mới được khởi tạo Không gian làm việc và tự động kết nối với Quản lý (Manager) để phối hợp soạn thảo AI, trình duyệt nội dung và lên lịch đăng bài.
                </div>
              </>
            )}

            {error && (
              <div
                role="alert"
                aria-live="assertive"
                className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-start gap-2"
              >
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-[#121316] hover:bg-stone-800 disabled:opacity-50 text-white rounded-xl text-sm font-bold flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <span>
                {isLoading
                  ? isRegisterMode
                    ? 'Đang khởi tạo...'
                    : 'Đang xác thực...'
                  : isRegisterMode
                  ? 'Hoàn tất Đăng ký'
                  : 'Đăng nhập'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {/* Quick-chips for testing RBAC roles (Quản lý & Nhân viên Marketing) */}
            {!isRegisterMode && (
              <div className="pt-4 border-t border-stone-100 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-stone-400">
                    Tài khoản mẫu phân quyền (Quản lý &amp; Nhân viên Marketing)
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleQuickLogin('manager@gmail.com', 'Manager@123')}
                    className="px-3 py-2 rounded-lg border border-stone-200 hover:border-stone-400 bg-stone-50 hover:bg-stone-100 text-xs font-semibold text-stone-700 transition-colors text-center cursor-pointer"
                  >
                    Quản lý (Manager)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickLogin('marketer@gmail.com', 'Marketer@123')}
                    className="px-3 py-2 rounded-lg border border-stone-200 hover:border-stone-400 bg-stone-50 hover:bg-stone-100 text-xs font-semibold text-stone-700 transition-colors text-center cursor-pointer"
                  >
                    Nhân viên Marketing
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
                    className="text-action font-bold text-[#D95D39] hover:underline"
                  >
                    Đăng nhập
                  </button>
                </>
              ) : (
                <>
                  Chưa có tài khoản?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode(true)}
                    className="text-action font-bold text-[#D95D39] hover:underline"
                  >
                    Đăng ký
                  </button>
                </>
              )}
            </div>
          </form>
        </div>
      </main>
    </div>
  );
};
