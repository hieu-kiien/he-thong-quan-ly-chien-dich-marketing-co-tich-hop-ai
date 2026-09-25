import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, ArrowRight, ShieldCheck, Mail, Lock, AlertCircle, Loader2 } from 'lucide-react';
import { getApiErrorMessage } from '../services/api';

interface LoginPageProps {
  onNavigateToRegister: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigateToRegister }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Vui lòng nhập đầy đủ email và mật khẩu');
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = (quickEmail: string, quickPass: string) => {
    setEmail(quickEmail);
    setPassword(quickPass);
    setError(null);
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
            Nền tảng Điều phối Tiếp thị Tinh gọn & Quản trị Đa Workspace
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/50">
          <h2 className="text-xl font-bold text-white mb-2">Đăng nhập tài khoản</h2>
          <p className="text-xs text-slate-400 mb-6">
            Nhập thông tin xác thực để truy cập không gian làm việc của bạn
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
                Mật khẩu
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

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang xác thực...</span>
                </>
              ) : (
                <>
                  <span>Đăng nhập hệ thống</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick-chips for testing */}
          <div className="mt-6 pt-5 border-t border-slate-800/80">
            <p className="text-xs font-medium text-slate-400 mb-3 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Chọn nhanh tài khoản kiểm thử chuẩn:
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('manager@ictu.edu.vn', 'Manager@123')}
                className="py-1.5 px-2 bg-slate-800/70 hover:bg-slate-800 hover:border-indigo-500/50 border border-slate-700/60 rounded-lg text-xs font-medium text-slate-200 transition-all text-center"
              >
                Manager
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('marketer@ictu.edu.vn', 'Marketer@123')}
                className="py-1.5 px-2 bg-slate-800/70 hover:bg-slate-800 hover:border-indigo-500/50 border border-slate-700/60 rounded-lg text-xs font-medium text-slate-200 transition-all text-center"
              >
                Marketer
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('approver@ictu.edu.vn', 'Approver@123')}
                className="py-1.5 px-2 bg-slate-800/70 hover:bg-slate-800 hover:border-indigo-500/50 border border-slate-700/60 rounded-lg text-xs font-medium text-slate-200 transition-all text-center"
              >
                Approver
              </button>
            </div>
          </div>
        </div>

        {/* Footer switch to register */}
        <div className="text-center mt-6">
          <p className="text-sm text-slate-400">
            Chưa có tài khoản?{' '}
            <button
              type="button"
              onClick={onNavigateToRegister}
              className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors underline-offset-4 hover:underline"
            >
              Đăng ký tài khoản mới
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
