import React, { useState, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Campaigns } from './pages/Campaigns';
import { ReviewQueue } from './pages/ReviewQueue';
import { WorkflowCanvas } from './components/WorkflowCanvas';
import { AIDrawer } from './components/AIDrawer';
import { AIStudio } from './pages/AIStudio';
import { ToastProvider, useToast } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Campaign, MarketingContent, User } from './types';
import { authApi, campaignApi, contentApi, getApiErrorMessage } from './services/api';

function AppContent() {
  const toast = useToast();
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [contents, setContents] = useState<MarketingContent[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [isAIDrawerOpen, setIsAIDrawerOpen] = useState<boolean>(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [isAuthReady, setIsAuthReady] = useState<boolean>(false);

  // Khởi tạo đăng nhập tự động tài khoản Manager để demo mượt mà
  useEffect(() => {
    initAuthAndData();
  }, []);

  const initAuthAndData = async () => {
    try {
      // Đăng nhập mặc định Manager
      const authRes = await authApi.login('manager@ictu.edu.vn', 'Manager@123');
      setCurrentUser(authRes.user);
      await loadCampaignsAndContents();
    } catch (e) {
      console.error('Lỗi khởi tạo đăng nhập:', e);
      toast.warning('Chưa kết nối được tới Backend API (127.0.0.1:8000). Vui lòng kiểm tra dịch vụ backend.');
    } finally {
      setIsAuthReady(true);
    }
  };

  const loadCampaignsAndContents = async () => {
    try {
      const [cList, ctList] = await Promise.all([
        campaignApi.getAll(),
        contentApi.getAll()
      ]);
      setCampaigns(cList);
      setContents(ctList);
      if (cList.length > 0) {
        setSelectedCampaign(cList[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSwitchRole = async (role: 'MANAGER' | 'MARKETER') => {
    try {
      if (role === 'MANAGER') {
        const res = await authApi.login('manager@ictu.edu.vn', 'Manager@123');
        setCurrentUser(res.user);
        toast.success('Đã chuyển sang vai trò Quản lý (Manager)');
      } else {
        const res = await authApi.login('marketer@ictu.edu.vn', 'Marketer@123');
        setCurrentUser(res.user);
        toast.success('Đã chuyển sang vai trò Nhân viên (Marketer)');
      }
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi chuyển vai trò');
    }
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
      loadCampaignsAndContents();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi duyệt bài');
    }
  };

  if (!isAuthReady) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-slate-900 text-white gap-3 font-['Plus_Jakarta_Sans',sans-serif]">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 animate-pulse">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <div className="text-center">
          <h2 className="font-bold text-sm text-slate-100">MarketFlow AI</h2>
          <p className="text-xs text-slate-400 mt-0.5">Đang thiết lập phiên làm việc và bảo mật API...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#F8FAFC] overflow-hidden font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Sidebar Navigation (with Mobile Drawer support) */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        currentUser={currentUser}
        onLogout={() => handleSwitchRole('MARKETER')}
        isOpen={isMobileSidebarOpen}
        onClose={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          currentUser={currentUser}
          onSwitchRole={handleSwitchRole}
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
              userRole={currentUser?.role}
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
              userRole={currentUser?.role}
            />
          )}

          {currentTab === 'workflow' && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight">Sơ đồ Luồng Chiến dịch</h2>
                  <p className="text-xs text-slate-500 mt-1">Trực quan hóa luồng công việc dạng Node theo chuẩn Klaviyo / Braze Canvas.</p>
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
                onOpenAI={handleOpenAI}
                onApproveContent={handleApproveContent}
                onSubmitForReview={() => loadCampaignsAndContents()}
                userRole={currentUser?.role}
              />
            </div>
          )}

          {currentTab === 'reviews' && (
            <ReviewQueue userRole={currentUser?.role} />
          )}

          {currentTab === 'ai_studio' && (
            <AIStudio
              campaigns={campaigns}
              selectedCampaign={selectedCampaign}
              onSelectCampaign={setSelectedCampaign}
              onContentCreated={loadCampaignsAndContents}
              onNavigateToReviews={() => setCurrentTab('reviews')}
            />
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
        onContentCreated={loadCampaignsAndContents}
      />
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
