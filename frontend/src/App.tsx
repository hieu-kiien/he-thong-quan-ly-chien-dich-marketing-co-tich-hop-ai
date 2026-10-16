import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { AIDrawer } from './components/AIDrawer';
import { BrandKitModal } from './components/BrandKitModal';
import { ToastProvider, useToast } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WorkspaceProvider, useWorkspace } from './context/WorkspaceContext';
import { Campaign, MarketingContent } from './types';
import { campaignApi, contentApi, taskApi, getApiErrorMessage, isOfflineDemoEnabled, isBackendConnected } from './services/api';

const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const Campaigns = lazy(() => import('./pages/Campaigns').then(m => ({ default: m.Campaigns })));
const ReviewQueue = lazy(() => import('./pages/ReviewQueue').then(m => ({ default: m.ReviewQueue })));
const WorkflowCanvas = lazy(() => import('./components/WorkflowCanvas').then(m => ({ default: m.WorkflowCanvas })));
const AIStudio = lazy(() => import('./pages/AIStudio').then(m => ({ default: m.AIStudio })));
const MyTasksPage = lazy(() => import('./pages/MyTasksPage').then(m => ({ default: m.MyTasksPage })));
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })));
const MarketingCalendar = lazy(() => import('./components/MarketingCalendar').then(m => ({ default: m.MarketingCalendar })));
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));

const PageFallback: React.FC = () => (
  <div className="flex h-full w-full min-h-[400px] items-center justify-center p-12">
    <div className="flex flex-col items-center gap-3 text-slate-500">
      <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      <span className="text-xs font-semibold">Đang tải phân hệ...</span>
    </div>
  </div>
);


function AppContent() {
  const toast = useToast();
  const { user, userRole, isAuthenticated, isLoading: isAuthLoading, logout } = useAuth();
  const { currentWorkspace } = useWorkspace();

  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [contents, setContents] = useState<MarketingContent[]>([]);
  const [myTasksCount, setMyTasksCount] = useState<number>(0);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [drawerCampaignRequest, setDrawerCampaignRequest] = useState<Campaign | null>(null);
  // Truy vấn tìm kiếm từ ô trên Navbar, truyền xuống Campaigns.
  const [campaignSearch, setCampaignSearch] = useState<string>('');

  const [isAIDrawerOpen, setIsAIDrawerOpen] = useState<boolean>(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [isBrandKitModalOpen, setIsBrandKitModalOpen] = useState<boolean>(false);
  const [isOffline, setIsOffline] = useState<boolean>(typeof navigator !== 'undefined' ? !navigator.onLine : false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      toast.success('Kết nối mạng đã được khôi phục!');
    };
    const handleOffline = () => {
      setIsOffline(true);
      toast.error('Mất kết nối mạng! Vui lòng kiểm tra đường truyền Internet.', 'Ngoại tuyến');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [toast]);

  const loadCampaignsAndContents = useCallback(async (wsId?: number) => {
    try {
      const [cList, ctList, myTasks] = await Promise.all([
        campaignApi.getAll(undefined, undefined, wsId),
        contentApi.getAll(undefined, undefined, wsId),
        taskApi.getMyTasks({ include_completed: false }).catch(() => [])
      ]);
      setCampaigns(cList);
      setContents(ctList);
      setMyTasksCount(myTasks.length);
      if (cList.length > 0) {
        setSelectedCampaign(cList[0]);
      } else {
        setSelectedCampaign(null);
      }
    } catch (e: any) {
      console.error('Lỗi nạp chiến dịch & nội dung:', e);
      toast.error(getApiErrorMessage(e), 'Lỗi tải dữ liệu');
    }
  }, [toast]);

  useEffect(() => {
    if (isAuthenticated) {
      loadCampaignsAndContents(currentWorkspace?.id);
    } else {
      // Reset toàn bộ dữ liệu của người dùng trước khi thoát. Nếu không, sau khi
      // đăng nhập bằng tài khoản khác, UI vẫn hiện tab và danh sách contents
      // của người dùng cũ cho tới lúc refetch hoàn tất.
      setCampaigns([]);
      setContents([]);
      setMyTasksCount(0);
      setSelectedCampaign(null);
      setCurrentTab('dashboard');
      setCampaignSearch('');
    }
  }, [isAuthenticated, currentWorkspace?.id, loadCampaignsAndContents]);

  const handleSearchCampaigns = (query: string) => {
    setCampaignSearch(query);
    setCurrentTab('campaigns');
  };

  const handleOpenWorkflow = (campaign: Campaign) => {
    setSelectedCampaign(campaign);
    setCurrentTab('workflow');
  };

  const handleOpenAI = (campaign: Campaign) => {
    setSelectedCampaign(campaign);
    setIsAIDrawerOpen(true);
  };

  const handleApproveContent = async (id: number) => {
    try {
      await contentApi.approve(id);
      toast.success('Đã phê duyệt bài viết thành công (APPROVED)!');
      loadCampaignsAndContents(currentWorkspace?.id);
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi duyệt bài');
    }
  };

  // Trạng thái đang tải session đăng nhập
  if (isAuthLoading) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#141518] text-white gap-3 font-sans">
        <div className="w-12 h-12 rounded-xl bg-[#D95D39] flex items-center justify-center shadow-sm">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <div className="text-center">
          <h2 className="font-bold text-sm text-slate-100">MarketFlow</h2>
          <p className="text-xs text-slate-400 mt-1 flex items-center justify-center gap-1.5">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Đang xác thực thông tin tài khoản...</span>
          </p>
        </div>
      </div>
    );
  }

  // Nếu chưa đăng nhập: Điều hướng tới LoginPage hoặc RegisterPage
  if (!isAuthenticated) {
    return (
      <div className="relative min-h-screen">
        <Suspense fallback={
          <div className="flex min-h-screen items-center justify-center bg-[#141518]">
            <Loader2 className="h-8 w-8 animate-spin text-[#D95D39]" />
          </div>
        }>
          <LoginPage
            mode={authMode}
            onNavigateToRegister={() => setAuthMode('register')}
            onNavigateToLogin={() => setAuthMode('login')}
          />
        </Suspense>
      </div>
    );
  }

  // Đã đăng nhập: Giao diện chính của ứng dụng
  return (
    <div className="flex h-screen bg-[#F6F5F0] overflow-hidden font-sans">
      {/* Sidebar Navigation (with Mobile Drawer support) */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        currentUser={user}
        onLogout={logout}
        isOpen={isMobileSidebarOpen}
        onClose={() => setIsMobileSidebarOpen(false)}
        tasksCount={myTasksCount}
      />


      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Offline Demo Warning Banner */}
        {isOfflineDemoEnabled() && !isBackendConnected() && (
          <div className="bg-amber-500/15 border-b border-amber-500/30 text-amber-900 dark:text-amber-200 px-4 py-2 text-xs flex items-center justify-between font-medium z-10 no-print shrink-0">
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-ping shrink-0" />
              <span>
                <strong>[CHẾ ĐỘ DEMO CỤC BỘ]</strong> Máy chủ backend hiện chưa kết nối. Hệ thống đang chạy dự phòng với LocalStorage.
              </span>
            </div>
          </div>
        )}

        {/* Offline Network Warning Banner */}
        {isOffline && (
          <div className="bg-rose-600 text-white px-4 py-2 text-xs flex items-center justify-between font-semibold z-50 shrink-0 shadow-md">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-white animate-pulse" />
              <span>Đang ngoại tuyến: Mất kết nối mạng Internet. Các thao tác có thể không được lưu về máy chủ.</span>
            </div>
          </div>
        )}

        <Navbar
          onOpenBrandKit={() => setIsBrandKitModalOpen(true)}
          onOpenAIDrawer={() => {
            if (!selectedCampaign && campaigns.length > 0) {
              setSelectedCampaign(campaigns[0]);
            }
            setIsAIDrawerOpen(true);
          }}
          onToggleSidebar={() => setIsMobileSidebarOpen(prev => !prev)}
          onNavigateTab={(tab) => setCurrentTab(tab)}
          onSearchCampaigns={handleSearchCampaigns}
          pendingReviewsCount={contents.filter(c => c.status === 'IN_REVIEW').length}
          activeCampaignsCount={campaigns.filter(c => c.status === 'ACTIVE').length}
        />

        <main className="flex-1 overflow-y-auto">
          <Suspense fallback={<PageFallback />}>
            {currentTab === 'dashboard' && (
              <Dashboard
                onSelectCampaign={(c) => {
                  setSelectedCampaign(c);
                  setDrawerCampaignRequest(c);
                  setCurrentTab('campaigns');
                }}
                onOpenWorkflow={handleOpenWorkflow}
                onOpenAI={handleOpenAI}
                onNavigateTab={(t) => setCurrentTab(t)}
                userRole={userRole || undefined}
              />
            )}

            {currentTab === 'campaigns' && (
              <Campaigns
                onSelectCampaign={(c) => {
                  setSelectedCampaign(c);
                }}
                onOpenWorkflow={handleOpenWorkflow}
                onOpenAI={handleOpenAI}
                onNavigateTab={(t) => setCurrentTab(t)}
                onRefreshData={() => loadCampaignsAndContents(currentWorkspace?.id)}
                userRole={userRole || undefined}
                initialSearchTerm={campaignSearch}
                searchTermSync={campaignSearch}
                initialDrawerCampaign={drawerCampaignRequest}
                onClearInitialDrawerCampaign={() => setDrawerCampaignRequest(null)}
              />
            )}

            {currentTab === 'calendar' && (
              <div className="p-8 max-w-7xl mx-auto space-y-6">
                <MarketingCalendar
                  campaigns={campaigns}
                  contents={contents}
                  selectedCampaign={selectedCampaign}
                  onSelectCampaign={setSelectedCampaign}
                />
              </div>
            )}

            {currentTab === 'workflow' && (
              <div className="p-8 max-w-7xl mx-auto space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-bold text-[#121316] tracking-tight">Điều phối Chiến dịch & Tiến độ bài viết</h2>
                    <p className="text-xs text-[#5A5E66] mt-1">Theo dõi luồng bài viết theo trạng thái, soạn thảo đa kênh, chẩn đoán hiệu suất và sơ đồ vòng đời chiến dịch.</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={selectedCampaign?.id || ''}
                      onChange={(e) => {
                        const found = campaigns.find(c => c.id === Number(e.target.value));
                        if (found) setSelectedCampaign(found);
                      }}
                      aria-label="Chọn chiến dịch điều phối"
                      className="text-xs bg-white border border-slate-200 rounded-lg px-3 py-2 font-semibold text-slate-700 shadow-sm outline-none"
                    >
                      {campaigns.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <WorkflowCanvas
                  campaign={selectedCampaign}
                  contents={contents}
                  campaigns={campaigns}
                  onSelectCampaign={setSelectedCampaign}
                  onOpenAI={handleOpenAI}
                  onApproveContent={handleApproveContent}
                  onSubmitForReview={() => loadCampaignsAndContents(currentWorkspace?.id)}
                  onRefreshData={() => loadCampaignsAndContents(currentWorkspace?.id)}
                  userRole={userRole || undefined}
                />
              </div>
            )}

            {currentTab === 'my_tasks' && (
              <MyTasksPage
                onNavigateToCampaign={(cId) => {
                  const c = campaigns.find(x => x.id === cId);
                  if (c) {
                    setSelectedCampaign(c);
                    setCurrentTab('workflow');
                  } else {
                    setCurrentTab('campaigns');
                  }
                }}
              />
            )}

            {currentTab === 'reviews' && (
              <ReviewQueue userRole={userRole || undefined} />
            )}


            {currentTab === 'ai_studio' && (
              <AIStudio
                campaigns={campaigns}
                selectedCampaign={selectedCampaign}
                onSelectCampaign={setSelectedCampaign}
                onContentCreated={() => loadCampaignsAndContents(currentWorkspace?.id)}
                onNavigateToReviews={() => setCurrentTab('reviews')}
              />
            )}

            {currentTab === 'settings' && (
              <div className="p-8 max-w-7xl mx-auto">
                <Settings 
                  currentUser={user} 
                  currentWorkspace={currentWorkspace} 
                />
              </div>
            )}
          </Suspense>
        </main>
      </div>

      {/* In-Context AI Slide-over Drawer (Tự động ẩn khi đang ở trang AI Studio toàn màn hình để tránh trùng lặp UI) */}
      <AIDrawer
        isOpen={isAIDrawerOpen && currentTab !== 'ai_studio'}
        onClose={() => setIsAIDrawerOpen(false)}
        campaign={selectedCampaign}
        campaigns={campaigns}
        onSelectCampaign={setSelectedCampaign}
        onContentCreated={() => loadCampaignsAndContents(currentWorkspace?.id)}
      />

      {/* Brand Kit Configuration Modal */}
      <BrandKitModal
        isOpen={isBrandKitModalOpen}
        onClose={() => setIsBrandKitModalOpen(false)}
      />
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider>
          <WorkspaceProvider>
            <AppContent />
          </WorkspaceProvider>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
