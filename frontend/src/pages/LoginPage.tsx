import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getApiErrorMessage, isOfflineDemoEnabled } from '../services/api';
import { startHalloweenScene } from '../features/halloween-login';
import '../features/halloween-login/halloween.css';

interface LoginPageProps {
  onNavigateToRegister: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigateToRegister }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const teardown = startHalloweenScene();
    return teardown;
  }, []);

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

  // Khoi nhanh chon tai khoan seed KHONG duoc render o moi truong.
  //
  // Ly do: Vite bake bien moi truong vao bundle tai `npm run build`. Neu khoi nay
  // luon hien thi, mat khau seed ("Manager@123"...) bien mot chuoi ro trong
  // JavaScript gui toi trinh duyet cua moi nguoi dung that. Chi nen bat o moi
  // trien khai co du lieu mau cuc bo (VITE_ENABLE_OFFLINE_DEMO=true).
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
            <div className="scene-copy">
              <h2 id="welcome-title">Không gian của bạn</h2>
              <p>
                Đăng nhập để điều phối chiến dịch marketing, phê duyệt nội dung AI và theo dõi hiệu quả
                từ một nơi duy nhất.
              </p>
            </div>
          </section>

          <section className="form-panel">
            <form className="login-form" id="login-form" onSubmit={handleSubmit}>
              <h1 id="login-title">Đăng nhập</h1>
              <div className="field">
                <label className="sr-only" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="Email"
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
                  placeholder="Mật khẩu"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button className="eye" id="show-password" type="button" aria-label="Hiện mật khẩu" aria-pressed="false" aria-controls="password">
                  <img src="/halloween/images/icon-eye.svg" alt="" width={18} height={18} />
                </button>
              </div>

              {error && (
                <p className="status status-error" id="status" role="alert">
                  {error}
                </p>
              )}

              {/* Trạng thái chờ: giữ nguyên vùng aria-live để người dùng biết đang xử lý. */}
              <p className={error ? 'sr-only' : 'status'} role="status" aria-live="polite">
                {isLoading ? 'Đang xác thực...' : ''}
              </p>

              <button className="submit" type="submit" disabled={isLoading}>
                <span>{isLoading ? 'Đang xác thực...' : 'Đăng nhập'}</span>{' '}
                <img src="/halloween/images/icon-arrow.svg" alt="" width={17} height={17} />
              </button>
              <p className="signup-row">
                <span>Bạn chưa có tài khoản?</span>{' '}
                <button className="text-action" type="button" onClick={onNavigateToRegister}>
                  Đăng ký
                </button>
              </p>

              {showQuickLogin && (
                <div className="quick-login">
                  <p>Chọn nhanh tài khoản kiểm thử:</p>
                  <div className="quick-login-grid">
                    <button type="button" onClick={() => { setEmail('manager@gmail.com'); setPassword('Manager@123'); }}>
                      Manager
                    </button>
                    <button type="button" onClick={() => { setEmail('marketer@gmail.com'); setPassword('Marketer@123'); }}>
                      Marketer
                    </button>
                    <button type="button" onClick={() => { setEmail('approver@gmail.com'); setPassword('Approver@123'); }}>
                      Approver
                    </button>
                  </div>
                </div>
              )}
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
