import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import { authApi } from '../services/api';

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
        // Nếu lỗi 401/403, phiên đăng nhập đã hết hạn
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          authApi.logout();
          setUser(null);
        } else {
          // Lỗi mạng hoặc server offline, đọc thông tin lưu tạm từ localStorage
          const cachedUser = authApi.getCurrentUser();
          if (cachedUser) {
            setUser(cachedUser);
          } else {
            authApi.logout();
            setUser(null);
          }
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
