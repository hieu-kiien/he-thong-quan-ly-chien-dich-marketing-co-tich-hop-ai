import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getApiErrorMessage } from '../services/api';
import { startHalloweenScene } from '../features/halloween-login';
import '../features/halloween-login/halloween.css';

interface RegisterPageProps {
  onNavigateToLogin: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onNavigateToLogin }) => {
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const teardown = startHalloweenScene();
    return teardown;
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
    setIsLoading(true);
    try {
      try {
        localStorage.setItem(
          'mf_recent_registered_user',
          JSON.stringify({ email: cleanEmail, full_name: cleanName })
        );
        sessionStorage.setItem('mf_prefill_email', cleanEmail);
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
  };

  return (
    <div className="halloween-login-root">
      {/* Cảnh nền full màn hình đồng bộ với trang Đăng nhập */}
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
        <main className="login-card" aria-labelledby="register-title">
          <section className="scene-panel" aria-labelledby="welcome-register-title">
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
            <button
              className="theme-toggle"
              id="theme-toggle"
              type="button"
              aria-pressed="false"
              aria-label="Bật đêm Halloween"
            >
              <span className="theme-toggle-thumb" aria-hidden="true" />
              <span data-svg="images/icon-sun.svg" aria-hidden="true" />
              <span data-svg="images/icon-moon.svg" aria-hidden="true" />
            </button>
            <div className="scene-copy">
              <h2 id="welcome-register-title">Khởi tạo Workspace AI</h2>
              <p>
                Tự động cấp phát Không gian làm việc riêng, Brand Kit thương hiệu và quyền truy cập
                AI Copilot đa kênh ngay sau khi đăng ký.
              </p>
            </div>
          </section>

          <section className="form-panel is-register">
            <form className="login-form register-form" id="register-form" onSubmit={handleSubmit}>
              <div className="auth-mode-switch" role="tablist" aria-label="Chế độ xác thực">
                <button type="button" role="tab" aria-selected="false" onClick={onNavigateToLogin}>
                  Đăng nhập
                </button>
                <button type="button" role="tab" aria-selected="true" className="is-active">
                  Đăng ký tài khoản
                </button>
              </div>

              <h1 id="register-title">Đăng ký tài khoản</h1>

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
                  required
                />
              </div>

              <div className="field">
                <label className="sr-only" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="Địa chỉ Email (VD: ban@congty.vn)"
                  autoComplete="email"
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
                  placeholder="Mật khẩu (tối thiểu 6 ký tự)"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
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
                />
              </div>

              <div className="register-role-badge">
                <strong>✦ Quyền hạn mặc định: Marketer &amp; Chủ sở hữu Workspace</strong>
                <span>
                  Tự động khởi tạo Workspace cá nhân + Brand Kit AI. Sau khi đăng ký sẽ tự động đăng nhập
                  và liên kết trực tiếp với trang Đăng nhập.
                </span>
              </div>

              {error && (
                <p className="status status-error" id="status" role="alert">
                  {error}
                </p>
              )}

              <p className={error ? 'sr-only' : 'status'} role="status" aria-live="polite">
                {isLoading ? 'Đang khởi tạo tài khoản & Workspace...' : ''}
              </p>

              <button className="submit" type="submit" disabled={isLoading}>
                <span>{isLoading ? 'Đang khởi tạo...' : 'Hoàn tất Đăng ký & Vào Hệ thống'}</span>{' '}
                <img src="/halloween/images/icon-arrow.svg" alt="" width={17} height={17} />
              </button>

              <p className="signup-row">
                <span>Đã có tài khoản?</span>{' '}
                <button className="text-action" type="button" onClick={onNavigateToLogin}>
                  Đăng nhập ngay
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
