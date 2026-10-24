import { useCallback, useState } from 'react';
import { toApiError } from '@/lib/api/client';

export type FieldErrors = Record<string, string | undefined>;

/**
 * Quản lý lỗi form: lỗi kiểm tra phía client + lỗi 422 `fields` từ backend (CONTRACT §4).
 * `formError` là thông báo chung (hiển thị dạng Callout ở đầu/cuối form).
 */
export function useFormErrors() {
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);

  const clearField = useCallback((field: string) => {
    setErrors((e) => (e[field] ? { ...e, [field]: undefined } : e));
  }, []);

  const reset = useCallback(() => {
    setErrors({});
    setFormError(null);
  }, []);

  /** Đặt lỗi phía client; trả về true nếu có lỗi. */
  const validate = useCallback((next: FieldErrors): boolean => {
    const clean: FieldErrors = {};
    for (const [k, v] of Object.entries(next)) if (v) clean[k] = v;
    setErrors(clean);
    setFormError(Object.keys(clean).length ? 'Vui lòng kiểm tra các trường được đánh dấu.' : null);
    return Object.keys(clean).length > 0;
  }, []);

  /**
   * Hiển thị lỗi từ API. Nếu có `fields` → gắn vào từng trường (bỏ tiền tố `body.`).
   * Trả về ApiError để nơi gọi xử lý thêm (vd mã 409).
   */
  const applyApiError = useCallback((err: unknown) => {
    const apiErr = toApiError(err);
    const mapped: FieldErrors = {};
    for (const [k, v] of Object.entries(apiErr.fields)) mapped[k.replace(/^body\./, '')] = v;
    setErrors(mapped);
    setFormError(apiErr.message);
    return apiErr;
  }, []);

  return { errors, formError, setFormError, clearField, reset, validate, applyApiError };
}
