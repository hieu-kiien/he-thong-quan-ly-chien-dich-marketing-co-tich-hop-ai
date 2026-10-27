/**
 * Quy tắc mật khẩu giống backend (`validate_password_strength`): tối thiểu 8 ký tự, có cả chữ và số.
 * Kiểm tra ở client chỉ để báo lỗi sớm; backend vẫn là nơi quyết định.
 */
export function passwordProblem(password: string): string | null {
  if (password.length < 8) return 'Mật khẩu tối thiểu 8 ký tự.';
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return 'Mật khẩu cần có cả chữ và số.';
  return null;
}
