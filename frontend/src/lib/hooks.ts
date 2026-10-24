import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { channelsApi, usersApi } from './api/endpoints';
import { useAuth } from './auth';
import { isManager } from './permissions';

export function useDebounced<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

/** Danh sách kênh (dùng chung cho bộ lọc & form). */
export function useChannels(includeInactive = false) {
  return useQuery({
    queryKey: ['channels', { includeInactive }],
    queryFn: () => channelsApi.list(includeInactive),
    staleTime: 5 * 60_000,
  });
}

/**
 * Danh sách người dùng cho bộ lọc "Người phụ trách". `GET /users` chỉ dành cho MANAGER,
 * nên với MARKETER hook trả về rỗng và UI ẩn bộ lọc tương ứng.
 */
export function useUserOptions() {
  const { user } = useAuth();
  const enabled = isManager(user);
  const q = useQuery({
    queryKey: ['users', 'options'],
    queryFn: () => usersApi.list({ page: 1, page_size: 100 }),
    enabled,
    staleTime: 5 * 60_000,
  });
  return { enabled, users: q.data?.items ?? [], isLoading: q.isLoading && enabled };
}

/** Đặt document.title theo trang. */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} · MarketFlow` : 'MarketFlow';
  }, [title]);
}
