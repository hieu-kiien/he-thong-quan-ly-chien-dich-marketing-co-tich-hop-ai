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
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { BrandKitModal } from './components/BrandKitModal';
import { ToastProvider, useToast } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WorkspaceProvider, useWorkspace } from './context/WorkspaceContext';
import { Campaign, MarketingContent } from './types';
import { campaignApi, contentApi, getApiErrorMessage } from './services/api';

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
    } catch (e) {
      console.error('Lỗi nạp chiến dịch & nội dung:', e);
    }
  }, []);

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
    if (authMode === 'register') {
      return <RegisterPage onNavigateToLogin={() => setAuthMode('login')} />;
    }
    return <LoginPage onNavigateToRegister={() => setAuthMode('register')} />;
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
        <Navbar
          onOpenBrandKit={() => setIsBrandKitModalOpen(true)}
          onOpenAIDrawer={() => {
            if (!selectedCampaign && campaigns.length > 0) {
              setSelectedCampaign(campaigns[0]);
            }
            setIsAIDrawerOpen(true);
          }}
          onToggleSidebar={() => setIsMobileSidebarOpen(prev => !prev)}
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
              userRole={userRole || undefined}
            />
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
