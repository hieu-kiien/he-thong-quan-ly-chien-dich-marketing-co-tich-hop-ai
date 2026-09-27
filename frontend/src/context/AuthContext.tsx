import React, { createContext, useContext, useState, useEffect } from 'react';
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
  // ToastProvider bao ngoài AuthProvider trong App.tsx; showToast dùng useCallback nên
  // tham chiếu ổn định, nên việc dùng trong effect khởi tạo (chạy đúng một lần) là an toàn.
  const toast = useToast();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const userData = await authApi.getMe();
        setUser(userData);
      } catch (err: any) {
        // KHÔNG được coi là "đã đăng nhập" khi không xác minh được với máy chủ.
        // current_user trong localStorage là dữ liệu tự do, không phải bằng chứng phiên còn hiệu lực.
        // Trước đây lỗi mạng rơi vào nhánh else và đọc chính dữ liệu đó: ai cũng có thể tự dựng
        // app shell đã đăng nhập trên máy mình. Giờ: không xác minh được thì dứt phiên, hết quyền.
        // 401/403 = phiên hết hạn/bị thu hồi (về trang đăng nhập là hành vi đúng).
        // Mọi lỗi còn lại (mạng, timeout, 5xx) = KHÔNG xác minh được, cũng phải dứt phiên.
        const status = err?.response?.status;
        const isSessionRejected = status === 401 || status === 403;
        authApi.logout();
        setUser(null);
        if (!isSessionRejected) {
          // Thông báo chuẩn, dùng lại helper sẵn có của lớp api thay vì tự phức tạp.
          toast.warning(
            getApiErrorMessage(err),
            'Không thể xác minh phiên đăng nhập - vui lòng đăng nhập lại'
          );
        }
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const res = await authApi.login(email, password);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { email: string; password: string; full_name: string; role?: string }): Promise<void> => {
    setIsLoading(true);
    try {
      await authApi.register(data);
      // Tự động đăng nhập sau khi đăng ký thành công
      await login(data.email, data.password);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        userRole: user?.role || null,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
