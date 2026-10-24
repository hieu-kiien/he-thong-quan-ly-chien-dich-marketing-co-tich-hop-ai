import { useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/lib/auth';
import { useDocumentTitle } from '@/lib/hooks';
import { toApiError } from '@/lib/api/client';
import { Button, Callout, FormField, Input } from '@/components/ui';
import { Logo } from '@/app/layout/Sidebar';

/** Gợi ý chỉ có khi chạy dev; bản build production loại bỏ hoàn toàn nhánh này. */
const DEV_HINT = import.meta.env.DEV ? import.meta.env.VITE_DEV_LOGIN_HINT : undefined;

export default function LoginPage() {
  useDocumentTitle('Đăng nhập');
  const { login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const next: typeof errors = {};
    if (!email.trim()) next.email = 'Vui lòng nhập email.';
    else if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = 'Email không hợp lệ.';
    if (!password) next.password = 'Vui lòng nhập mật khẩu.';
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length) return;
    setSubmitting(true);
    try {
      await login({ email: email.trim().toLowerCase(), password });
      const target = params.get('next');
      navigate(target && target.startsWith('/') && !target.startsWith('//') ? target : '/', { replace: true });
    } catch (err) {
      const apiErr = toApiError(err);
      setErrors({ email: apiErr.fields.email, password: apiErr.fields.password });
      setFormError(apiErr.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <div className="rounded-lg border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-fg">Đăng nhập</h1>
          <p className="mt-1 text-sm text-fg-muted">Quản lý chiến dịch, nội dung và lịch đăng của nhóm marketing.</p>

          {sessionExpired && !formError && (
            <Callout tone="info" className="mt-4">
              Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.
            </Callout>
          )}
          {formError && (
            <Callout tone="danger" className="mt-4">
              {formError}
            </Callout>
          )}

          <form className="mt-5 space-y-4" onSubmit={onSubmit} noValidate>
            <FormField label="Email" error={errors.email} required>
              {(p) => (
                <Input
                  {...p}
                  type="email"
                  autoComplete="username"
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ten@congty.vn"
                />
              )}
            </FormField>
            <FormField label="Mật khẩu" error={errors.password} required>
              {(p) => (
                <Input
                  {...p}
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              )}
            </FormField>
            <Button type="submit" variant="primary" className="w-full" loading={submitting}>
              Đăng nhập
            </Button>
          </form>
          {DEV_HINT && <p className="mt-4 rounded-md bg-subtle px-3 py-2 text-xs text-fg-muted">{DEV_HINT}</p>}
        </div>
        <p className="mt-6 text-center text-xs text-fg-subtle">MarketFlow · Hệ thống quản lý chiến dịch marketing</p>
      </div>
    </div>
  );
}
