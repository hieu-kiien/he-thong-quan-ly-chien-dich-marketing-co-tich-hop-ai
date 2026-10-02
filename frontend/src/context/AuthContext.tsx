import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { User, UserRole } from '../types';
import { authApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';

interface AuthContextType {
  user: User | null;
  userRole: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; role?: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const toast = useToast();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const endSession = useCallback(() => {
    authApi.logout();
    setUser(null);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        if (!cancelled) setIsLoading(false);
        return;
      }

      try {
        const userData = await authApi.getMe();
        if (!cancelled) setUser(userData);
      } catch (err: any) {
        if (cancelled) return;
        // KHÔNG được coi là "đã đăng nhập" khi không xác minh được với máy chủ.
        // current_user trong localStorage là dữ liệu tự do, không phải bằng chứng phiên còn hiệu lực.
        // 401/403 = phiên hết hạn/bị thu hồi (về trang đăng nhập là hành vi đúng).
        // Mọi lỗi còn lại (mạng, timeout, 5xx) = KHÔNG xác minh được, cũng phải dứt phiên.
        const status = err?.response?.status;
        const isSessionRejected = status === 401 || status === 403;
        endSession();
        if (!isSessionRejected) {
          toast.warning(
            getApiErrorMessage(err),
            'Không thể xác minh phiên đăng nhập - vui lòng đăng nhập lại'
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    initializeAuth();

    // Interceptor 401 trong lớp api đã dọn token và bắn sự kiện này; nghe để
    // đưa UI về màn hình đăng nhập ngay thay vì để trang hiện tại đứng yên.
    const onUnauthorized = () => endSession();
    window.addEventListener('auth:unauthorized', onUnauthorized);

    return () => {
      cancelled = true;
      window.removeEventListener('auth:unauthorized', onUnauthorized);
    };
  }, [endSession, toast]);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const res = await authApi.login(email, password);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(
    async (data: { email: string; password: string; full_name: string; role?: string }): Promise<void> => {
      setIsLoading(true);
      try {
        await authApi.register(data);
        await authApi.login(data.email, data.password).then((res) => setUser(res.user));
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const logout = useCallback(() => {
    endSession();
  }, [endSession]);

  const value = useMemo<AuthContextType>(
    () => ({
      user,
      userRole: user?.role || null,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
    }),
    [user, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
