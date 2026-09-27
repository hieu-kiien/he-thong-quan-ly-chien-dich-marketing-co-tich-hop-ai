import React, { useState, useEffect, useCallback } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Campaigns } from './pages/Campaigns';
import { ReviewQueue } from './pages/ReviewQueue';
import { WorkflowCanvas } from './components/WorkflowCanvas';
import { AIDrawer } from './components/AIDrawer';
import { AIStudio } from './pages/AIStudio';
import { Settings } from './pages/Settings';
import { MarketingCalendar } from './components/MarketingCalendar';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { BrandKitModal } from './components/BrandKitModal';
import { ServerAwakeningIndicator } from './components/ServerAwakeningIndicator';
import { ToastProvider, useToast } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WorkspaceProvider, useWorkspace } from './context/WorkspaceContext';
import { Campaign, MarketingContent } from './types';
import { campaignApi, contentApi, getApiErrorMessage, isOfflineDemoEnabled, isBackendConnected } from './services/api';

function AppContent() {
  const toast = useToast();
  const { user, userRole, isAuthenticated, isLoading: isAuthLoading, logout } = useAuth();
  const { currentWorkspace } = useWorkspace();

  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [contents, setContents] = useState<MarketingContent[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
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
      const [cList, ctList] = await Promise.all([
        campaignApi.getAll(undefined, undefined, wsId),
        contentApi.getAll(undefined, undefined, wsId)
      ]);
      setCampaigns(cList);
      setContents(ctList);
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
    }
  }, [isAuthenticated, currentWorkspace, loadCampaignsAndContents]);

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
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-slate-950 text-white gap-3 font-sans">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 animate-pulse">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <div className="text-center">
          <h2 className="font-bold text-sm text-slate-100">MarketFlow AI</h2>
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
        {isOfflineDemoEnabled() && !isBackendConnected() && (
          <div className="bg-amber-500/20 border-b border-amber-500/40 text-amber-200 px-4 py-2 text-xs text-center font-semibold sticky top-0 z-50">
            <strong>[CHẾ ĐỘ DEMO OFFLINE]</strong> Hệ thống đang chạy giả lập offline với LocalStorage. Bạn có thể sử dụng email demo để trải nghiệm.
          </div>
        )}
        {authMode === 'register' ? (
          <RegisterPage onNavigateToLogin={() => setAuthMode('login')} />
        ) : (
          <LoginPage onNavigateToRegister={() => setAuthMode('register')} />
        )}
      </div>
    );
  }

  // Đã đăng nhập: Giao diện chính của ứng dụng
  return (
    <div className="flex h-screen bg-[#F8FAFC] overflow-hidden font-sans">
      {/* Sidebar Navigation (with Mobile Drawer support) */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        currentUser={user}
        onLogout={logout}
        isOpen={isMobileSidebarOpen}
        onClose={() => setIsMobileSidebarOpen(false)}
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
          pendingReviewsCount={contents.filter(c => c.status === 'IN_REVIEW').length}
          activeCampaignsCount={campaigns.filter(c => c.status === 'ACTIVE').length}
        />

        <main className="flex-1 overflow-y-auto">
          {currentTab === 'dashboard' && (
            <Dashboard
              onSelectCampaign={(c) => {
                setSelectedCampaign(c);
                setCurrentTab('workflow');
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
                setCurrentTab('workflow');
              }}
              onOpenWorkflow={handleOpenWorkflow}
              onOpenAI={handleOpenAI}
              onNavigateTab={(t) => setCurrentTab(t)}
              onRefreshData={() => loadCampaignsAndContents(currentWorkspace?.id)}
              userRole={userRole || undefined}
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
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight">Trung tâm Điều phối Chiến dịch & Pipeline</h2>
                  <p className="text-xs text-slate-500 mt-1">Không gian điều phối chiến dịch toàn diện: Quản lý Pipeline nội dung, AI Copilot đa kênh, Bác sĩ AI chẩn đoán và Sơ đồ vòng đời.</p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={selectedCampaign?.id || ''}
                    onChange={(e) => {
                      const found = campaigns.find(c => c.id === Number(e.target.value));
                      if (found) setSelectedCampaign(found);
                    }}
                    aria-label="Chọn chiến dịch điều phối"
                    className="text-xs bg-white border border-slate-200 rounded-lg px-3 py-2 font-semibold text-slate-700 shadow-xs outline-hidden"
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
        </main>
      </div>

      {/* In-Context AI Slide-over Drawer */}
      <AIDrawer
        isOpen={isAIDrawerOpen}
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
        <ServerAwakeningIndicator />
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
