import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, ArrowRight, UserPlus, Mail, Lock, User as UserIcon, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { getApiErrorMessage } from '../services/api';

interface RegisterPageProps {
  onNavigateToLogin: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onNavigateToLogin }) => {
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'MARKETER' | 'AGENCY_MANAGER' | 'CLIENT_APPROVER'>('MARKETER');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !email || !password) {
      setError('Vui lòng điền đầy đủ tất cả các trường thông tin');
      return;
    }
    if (password.length < 6) {
      setError('Mật khẩu phải chứa tối thiểu 6 ký tự');
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      await register({
        full_name: fullName,
        email,
        password,
        role,
      });
    } catch (err: any) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 relative overflow-hidden font-sans text-slate-100">
      {/* Background Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-gradient-to-tr from-indigo-600/20 via-violet-600/20 to-pink-500/10 blur-[120px] pointer-events-none rounded-full" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-500 via-indigo-600 to-violet-600 shadow-xl shadow-indigo-500/20 mb-4 border border-indigo-400/30">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
            MarketFlow AI
          </h1>
          <p className="text-sm text-slate-400 mt-2">
            Khởi tạo Workspace & Thiết lập Brand Kit cho Thương hiệu của bạn
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/50">
          <h2 className="text-xl font-bold text-white mb-2">Đăng ký tài khoản</h2>
          <p className="text-xs text-slate-400 mb-6">
            Hệ thống sẽ tự động khởi tạo Không gian làm việc và Brand Kit riêng biệt
          </p>

          {error && (
            <div className="mb-5 p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-2.5 text-rose-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Họ và tên
              </label>
              <div className="relative">
                <UserIcon className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Nguyễn Văn A"
                  className="w-full bg-slate-950/60 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Email doanh nghiệp
              </label>
              <div className="relative">
                <Mail className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@agency.com"
                  className="w-full bg-slate-950/60 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Mật khẩu (Tối thiểu 6 ký tự)
              </label>
              <div className="relative">
                <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950/60 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Vai trò chính của bạn
              </label>
              <div className="space-y-2">
                <label className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${role === 'AGENCY_MANAGER' ? 'bg-indigo-600/10 border-indigo-500/80 text-white' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-300'}`}>
                  <input
                    type="radio"
                    name="role"
                    value="AGENCY_MANAGER"
                    checked={role === 'AGENCY_MANAGER'}
                    onChange={() => setRole('AGENCY_MANAGER')}
                    className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <div className="text-xs font-bold text-slate-100">Quản lý Agency (Agency Manager)</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Toàn quyền tạo Workspace, duyệt bài, cấu hình Brand Kit và quản lý thành viên.</div>
                  </div>
                </label>

                <label className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${role === 'MARKETER' ? 'bg-indigo-600/10 border-indigo-500/80 text-white' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-300'}`}>
                  <input
                    type="radio"
                    name="role"
                    value="MARKETER"
                    checked={role === 'MARKETER'}
                    onChange={() => setRole('MARKETER')}
                    className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <div className="text-xs font-bold text-slate-100">Chuyên viên Tiếp thị (Marketer / Creator)</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Tạo chiến dịch, sáng tạo nội dung AI, chỉnh sửa bản nháp và nộp duyệt.</div>
                  </div>
                </label>

                <label className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${role === 'CLIENT_APPROVER' ? 'bg-indigo-600/10 border-indigo-500/80 text-white' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-300'}`}>
                  <input
                    type="radio"
                    name="role"
                    value="CLIENT_APPROVER"
                    checked={role === 'CLIENT_APPROVER'}
                    onChange={() => setRole('CLIENT_APPROVER')}
                    className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <div className="text-xs font-bold text-slate-100">Đại diện Khách hàng (Client Approver)</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Kiểm tra Social Preview, thẩm định tiêu chuẩn thương hiệu và phê duyệt xuất bản.</div>
                  </div>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-3 py-3 px-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang khởi tạo tài khoản & Workspace...</span>
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  <span>Đăng ký & Bắt đầu ngay</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer switch to login */}
        <div className="text-center mt-6">
          <p className="text-sm text-slate-400">
            Đã có tài khoản?{' '}
            <button
              type="button"
              onClick={onNavigateToLogin}
              className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors underline-offset-4 hover:underline"
            >
              Đăng nhập ngay
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
