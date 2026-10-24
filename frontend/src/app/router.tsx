import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { isManager } from '@/lib/permissions';
import { EmptyState, Spinner } from '@/components/ui';
import { AppLayout } from './layout/AppLayout';
import { NotFoundPage, RouteErrorPage } from './ErrorPages';

const LoginPage = lazy(() => import('@/features/auth/LoginPage'));
const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage'));
const CampaignsPage = lazy(() => import('@/features/campaigns/CampaignsPage'));
const CampaignCreatePage = lazy(() => import('@/features/campaigns/CampaignCreatePage'));
const CampaignDetailPage = lazy(() => import('@/features/campaigns/CampaignDetailPage'));
const ContentsPage = lazy(() => import('@/features/contents/ContentsPage'));
const ContentDetailPage = lazy(() => import('@/features/contents/ContentDetailPage'));
const ReviewsPage = lazy(() => import('@/features/reviews/ReviewsPage'));
const CalendarPage = lazy(() => import('@/features/calendar/CalendarPage'));
const AssistantPage = lazy(() => import('@/features/assistant/AssistantPage'));
const SettingsPage = lazy(() => import('@/features/settings/SettingsPage'));

function FullScreenLoader() {
  return (
    <div className="flex h-screen items-center justify-center bg-canvas">
      <Spinner label="Đang tải MarketFlow" />
    </div>
  );
}

function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenLoader />;
  if (!user) {
    const next = location.pathname + location.search;
    return <Navigate to={next && next !== '/' ? `/login?next=${encodeURIComponent(next)}` : '/login'} replace />;
  }
  return <AppLayout />;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function RequireManager({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!isManager(user)) {
    return (
      <EmptyState
        icon={<ShieldAlert />}
        title="Bạn không có quyền truy cập trang này"
        description="Trang này chỉ dành cho vai trò Quản lý."
        className="mt-16"
      />
    );
  }
  return <>{children}</>;
}

const page = (node: ReactNode) => <Suspense fallback={<Spinner className="py-24" />}>{node}</Suspense>;

export const router = createBrowserRouter([
  {
    path: '/login',
    errorElement: <RouteErrorPage />,
    element: (
      <GuestOnly>
        <Suspense fallback={<FullScreenLoader />}>
          <LoginPage />
        </Suspense>
      </GuestOnly>
    ),
  },
  {
    path: '/register',
    errorElement: <RouteErrorPage />,
    element: (
      <GuestOnly>
        <Suspense fallback={<FullScreenLoader />}>
          <LoginPage />
        </Suspense>
      </GuestOnly>
    ),
  },
  {
    path: '/',
    element: <RequireAuth />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: page(<DashboardPage />) },
      { path: 'campaigns', element: page(<CampaignsPage />) },
      { path: 'campaigns/new', element: page(<CampaignCreatePage />) },
      { path: 'campaigns/:id', element: page(<CampaignDetailPage />) },
      { path: 'contents', element: page(<ContentsPage />) },
      { path: 'contents/:id', element: page(<ContentDetailPage />) },
      { path: 'reviews', element: page(<RequireManager><ReviewsPage /></RequireManager>) },
      { path: 'calendar', element: page(<CalendarPage />) },
      {
        path: 'assistant',
        element: <Outlet />,
        children: [
          { index: true, element: page(<AssistantPage />) },
          { path: ':threadId', element: page(<AssistantPage />) },
        ],
      },
      { path: 'settings', element: page(<SettingsPage />) },
      { path: 'settings/:section', element: page(<SettingsPage />) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
