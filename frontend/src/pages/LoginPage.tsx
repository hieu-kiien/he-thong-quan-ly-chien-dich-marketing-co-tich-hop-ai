import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getApiErrorMessage, isOfflineDemoEnabled } from '../services/api';
import { startHalloweenScene } from '../features/halloween-login';
import '../features/halloween-login/halloween.css';

interface LoginPageProps {
  mode?: 'login' | 'register';
  initialMode?: 'login' | 'register';
  onNavigateToRegister?: () => void;
  onNavigateToLogin?: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  mode,
  initialMode = 'login',
  onNavigateToRegister,
  onNavigateToLogin,
}) => {
  const { login, register } = useAuth();
  const [internalMode, setInternalMode] = useState<'login' | 'register'>(mode ?? initialMode);
  const activeMode = mode ?? internalMode;
  const isRegister = activeMode === 'register';

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [statusNote, setStatusNote] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recentRegistered, setRecentRegistered] = useState<{ email: string; full_name: string } | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('mf_recent_registered_user');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.email) {
          setRecentRegistered(parsed);
        }
      }
      const prefill = sessionStorage.getItem('mf_prefill_email');
      if (prefill) {
        setEmail(prefill);
        sessionStorage.removeItem('mf_prefill_email');
      }
    } catch {
      // ignore storage errors
    }
    const teardown = startHalloweenScene();
    return teardown;
  }, []);

  const switchMode = (nextMode: 'login' | 'register') => {
    if (nextMode === activeMode) return;
    setError(null);
    setStatusNote(null);
    setInternalMode(nextMode);
    if (nextMode === 'register') {
      onNavigateToRegister?.();
    } else {
      onNavigateToLogin?.();
    }
  };

  const handleQuickLogin = (quickEmail: string, quickPass: string) => {
    setEmail(quickEmail);
    setPassword(quickPass);
    setError(null);
    setStatusNote(null);
  };

  const handleFillRecentAccount = () => {
    if (!recentRegistered) return;
    setEmail(recentRegistered.email);
    setError(null);
    setStatusNote(`Đã điền email vừa đăng ký (${recentRegistered.full_name}). Vui lòng nhập mật khẩu của bạn.`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isRegister) {
      const cleanName = fullName.trim();
      const cleanEmail = email.trim();
      if (!cleanName || !cleanEmail || !password) {
        setError('Vui lòng điền đầy đủ họ tên, email và mật khẩu');
        return;
      }
      if (password.length < 6) {
        setError('Mật khẩu phải chứa tối thiểu 6 ký tự');
        return;
      }
      if (confirmPassword && password !== confirmPassword) {
        setError('Mật khẩu nhập lại không khớp');
        return;
      }
      setError(null);
      setStatusNote(null);
      setIsLoading(true);
      try {
        try {
          const record = { email: cleanEmail, full_name: cleanName };
          localStorage.setItem('mf_recent_registered_user', JSON.stringify(record));
          sessionStorage.setItem('mf_prefill_email', cleanEmail);
          setRecentRegistered(record);
        } catch {
          // ignore storage errors
        }
        await register({
          full_name: cleanName,
          email: cleanEmail,
          password,
          role: 'MARKETER',
        });
      } catch (err: any) {
        setError(getApiErrorMessage(err));
      } finally {
        setIsLoading(false);
      }
      return;
    }

    if (!email || !password) {
      setError('Vui lòng nhập đầy đủ email và mật khẩu');
      return;
    }

    setError(null);
    setStatusNote(null);
    setIsLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const showQuickLogin = isOfflineDemoEnabled();

  return (
    <div className="halloween-login-root">
      {/* Cảnh nền full màn hình */}
      <div className="landscape-scene page-landscape" aria-hidden="true">
        <img className="scene-land scene-day" src="/halloween/images/background-day.svg" alt="" />
        <img className="scene-land scene-night" src="/halloween/images/background-night.svg" alt="" />
        <div className="sky-flight" aria-hidden="true">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <span key={n} className={`sky-bat bat-${n}`}>
              <span className="flyer-facing">
                <span data-svg="images/bat.svg" aria-hidden="true" />
              </span>
            </span>
          ))}
          <span className="sky-witch">
            <span className="flyer-facing">
              <img src="/halloween/images/witch.svg" alt="" width={3600} height={3400} draggable={false} />
            </span>
          </span>
        </div>
      </div>

      <div className="login-shell">
        <div className="halloween-vines" id="halloween-vines" aria-hidden="true" />
        <main className="login-card" aria-labelledby="login-title">
          <section className="scene-panel" aria-labelledby="welcome-title">
            <div className="landscape-scene" aria-hidden="true">
              <div className="scene-sky-objects">
                <div className="scene-sun" />
                <div className="scene-moon" />
              </div>
              <img className="scene-land scene-day" src="/halloween/images/panel-day.svg" alt="" />
              <img className="scene-land scene-night" src="/halloween/images/panel-night.svg" alt="" />
              <div className="sky-flight" aria-hidden="true">
                {[1, 2, 3].map((n) => (
                  <span key={n} className={`sky-bat bat-${n}`}>
                    <span className="flyer-facing">
                      <span data-svg="images/bat.svg" aria-hidden="true" />
                    </span>
                  </span>
                ))}
              </div>
            </div>
            <div className="summit-stage" aria-hidden="true" />
            <button className="theme-toggle" id="theme-toggle" type="button" aria-pressed="false" aria-label="Bật đêm Halloween">
              <span className="theme-toggle-thumb" aria-hidden="true" />
              <span data-svg="images/icon-sun.svg" aria-hidden="true" />
              <span data-svg="images/icon-moon.svg" aria-hidden="true" />
            </button>
            <div className="scene-copy scene-copy-animated">
              <h2 id="welcome-title">{isRegister ? 'Tạo không gian mới' : 'Không gian của bạn'}</h2>
              <p>
                {isRegister
                  ? 'Khởi tạo tài khoản Chuyên viên kèm Không gian làm việc và Tờ giấy Quy tắc Thương hiệu ngay sau 1 bước.'
                  : 'Đăng nhập để điều phối chiến dịch, kiểm duyệt nội dung và theo dõi số liệu thực đo tại một nơi.'}
              </p>
            </div>
          </section>

          <section className="form-panel">
            <form className="login-form" id="login-form" onSubmit={handleSubmit}>
              <div
                className={`auth-mode-switch ${isRegister ? 'is-register-mode' : ''}`}
                role="tablist"
                aria-label="Chế độ xác thực"
              >
                <span className="auth-mode-pill" aria-hidden="true" />
                <button
                  type="button"
                  role="tab"
                  aria-selected={!isRegister}
                  className={!isRegister ? 'is-active' : ''}
                  onClick={() => switchMode('login')}
                >
                  Đăng nhập
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={isRegister}
                  className={isRegister ? 'is-active' : ''}
                  onClick={() => switchMode('register')}
                >
                  Đăng ký tài khoản
                </button>
              </div>

              <div className="auth-title-stage">
                <h1 id="login-title">{isRegister ? 'Đăng ký tài khoản' : 'Đăng nhập'}</h1>
              </div>

              {!isRegister && recentRegistered && (
                <button
                  type="button"
                  className="recent-registered-chip"
                  onClick={handleFillRecentAccount}
                  title="Điền nhanh email tài khoản bạn vừa đăng ký"
                >
                  <span>
                    Vừa đăng ký: <strong>{recentRegistered.full_name}</strong> ({recentRegistered.email})
                  </span>
                  <span>Điền →</span>
                </button>
              )}

              {/* Trường Họ và tên: mở mượt khi ở chế độ Đăng ký */}
              <div className={`auth-expandable ${isRegister ? 'is-open' : ''}`} aria-hidden={!isRegister}>
                <div className="auth-expandable-inner">
                  <div className="field">
                    <label className="sr-only" htmlFor="register-fullname">
                      Họ và tên
                    </label>
                    <input
                      id="register-fullname"
                      name="fullName"
                      type="text"
                      placeholder="Họ và tên (VD: Nguyễn Văn A)"
                      autoComplete="name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      disabled={!isRegister}
                      tabIndex={isRegister ? 0 : -1}
                      required={isRegister}
                    />
                  </div>
                </div>
              </div>

              <div className="field">
                <label className="sr-only" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder={isRegister ? 'Địa chỉ Email (VD: ban@congty.vn)' : 'Email'}
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <div className="email-owl" id="email-owl" aria-hidden="true">
                  <span data-svg="images/owl.svg" aria-hidden="true" />
                </div>
              </div>

              <div className="field password">
                <label className="sr-only" htmlFor="password">
                  Mật khẩu
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  placeholder={isRegister ? 'Mật khẩu (tối thiểu 6 ký tự)' : 'Mật khẩu'}
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  className="eye"
                  id="show-password"
                  type="button"
                  aria-label="Hiện mật khẩu"
                  aria-pressed="false"
                  aria-controls="password"
                >
                  <img src="/halloween/images/icon-eye.svg" alt="" width={18} height={18} />
                </button>
              </div>

              {/* Trường Xác nhận mật khẩu & Quyền tài khoản: mở mượt khi ở chế độ Đăng ký */}
              <div className={`auth-expandable ${isRegister ? 'is-open' : ''}`} aria-hidden={!isRegister}>
                <div className="auth-expandable-inner">
                  <div className="field password">
                    <label className="sr-only" htmlFor="confirmPassword">
                      Xác nhận mật khẩu
                    </label>
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type="password"
                      placeholder="Nhập lại mật khẩu xác nhận"
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={!isRegister}
                      tabIndex={isRegister ? 0 : -1}
                    />
                  </div>

                  <div className="register-role-badge">
                    <strong>Phân quyền tài khoản chuẩn bảo mật (2 tầng)</strong>
                    <span>
                      • <b>Tự đăng ký công khai:</b> Cấp quyền <b>Chuyên viên (Marketer)</b> + Không gian làm việc riêng (chống tự ý nâng đặc quyền).
                      <br />
                      • <b>Cấp quyền Quản lý / Duyệt bài:</b> Do Quản trị viên tạo hoặc nâng quyền tại mục <i>Cài đặt → Nhân sự &amp; Phân quyền</i>.
                    </span>
                  </div>
                </div>
              </div>

              {error && (
                <p className="status status-error" id="status" role="alert">
                  {error}
                </p>
              )}

              {statusNote && !error && (
                <p className="status" role="status">
                  {statusNote}
                </p>
              )}

              <p className={error || statusNote ? 'sr-only' : 'status'} role="status" aria-live="polite">
                {isLoading ? (isRegister ? 'Đang khởi tạo tài khoản & Workspace...' : 'Đang xác thực...') : ''}
              </p>

              <button className="submit" type="submit" disabled={isLoading}>
                <span>
                  {isLoading
                    ? isRegister
                      ? 'Đang khởi tạo...'
                      : 'Đang xác thực...'
                    : isRegister
                    ? 'Hoàn tất Đăng ký & Vào Hệ thống'
                    : 'Đăng nhập'}
                </span>{' '}
                <img src="/halloween/images/icon-arrow.svg" alt="" width={17} height={17} />
              </button>

              {!isRegister && showQuickLogin && (
                <div className="quick-login">
                  <p>Chọn nhanh tài khoản kiểm thử:</p>
                  <div className="quick-login-grid">
                    <button type="button" onClick={() => handleQuickLogin('manager@gmail.com', 'Manager@123')}>
                      Manager
                    </button>
                    <button type="button" onClick={() => handleQuickLogin('marketer@gmail.com', 'Marketer@123')}>
                      Marketer
                    </button>
                    <button type="button" onClick={() => handleQuickLogin('approver@gmail.com', 'Approver@123')}>
                      Approver
                    </button>
                  </div>
                </div>
              )}

              <p className="signup-row">
                <span>{isRegister ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'}</span>{' '}
                <button
                  className="text-action"
                  type="button"
                  onClick={() => switchMode(isRegister ? 'login' : 'register')}
                >
                  {isRegister ? 'Đăng nhập ngay' : 'Đăng ký'}
                </button>
              </p>
            </form>
          </section>
        </main>
      </div>

      <canvas id="halloween-spider" aria-hidden="true" />
      <div className="flash-beam" id="flash-beam" aria-hidden="true" />
      <div className="password-reveal" id="password-reveal" aria-hidden="true">
        <span id="reveal-text" />
      </div>
      <div className="flashlight" id="flashlight" aria-hidden="true">
        <img src="/halloween/images/flashlight.svg" alt="" width={33} height={33} />
      </div>
    </div>
  );
};
