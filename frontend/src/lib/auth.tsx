import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { authApi } from './api/endpoints';
import { getToken, onUnauthorized, setToken } from './api/client';
import type { LoginRequest, RegisterRequest, User } from './types';

interface AuthState {
  user: User | null;
  /** true khi đang xác minh token đã lưu lúc mở ứng dụng. */
  loading: boolean;
  login: (body: LoginRequest) => Promise<User>;
  register: (body: RegisterRequest) => Promise<User>;
  logout: () => Promise<void>;
  /** Cập nhật user hiện tại sau khi sửa hồ sơ. */
  setUser: (user: User) => void;
  /** Lý do lần đăng xuất gần nhất (hết phiên), hiển thị ở trang đăng nhập. */
  sessionExpired: boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => !!getToken());
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    if (!getToken()) return;
    let cancelled = false;
    authApi
      .me()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        if (!cancelled) {
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(
    () =>
      onUnauthorized(() => {
        setUser(null);
        setSessionExpired(true);
        queryClient.clear();
      }),
    [queryClient],
  );

  const login = useCallback(
    async (body: LoginRequest) => {
      const res = await authApi.login(body);
      setToken(res.access_token);
      queryClient.clear();
      setSessionExpired(false);
      setUser(res.user);
      return res.user;
    },
    [queryClient],
  );

  const register = useCallback(
    async (body: RegisterRequest) => {
      const res = await authApi.register(body);
      setToken(res.access_token);
      queryClient.clear();
      setSessionExpired(false);
      setUser(res.user);
      return res.user;
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* token có thể đã hết hạn — vẫn đăng xuất phía trình duyệt */
    }
    setToken(null);
    setUser(null);
    setSessionExpired(false);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthState>(
    () => ({ user, loading, login, register, logout, setUser, sessionExpired }),
    [user, loading, login, register, logout, sessionExpired],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth phải nằm trong AuthProvider');
  return ctx;
}

/** User hiện tại, chỉ dùng bên trong route đã đăng nhập. */
export function useCurrentUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error('Chưa đăng nhập');
  return user;
}
