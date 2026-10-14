import React from 'react';
import { LoginPage } from './LoginPage';

interface RegisterPageProps {
  onNavigateToLogin: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onNavigateToLogin }) => {
  return <LoginPage initialMode="register" onNavigateToLogin={onNavigateToLogin} />;
};
