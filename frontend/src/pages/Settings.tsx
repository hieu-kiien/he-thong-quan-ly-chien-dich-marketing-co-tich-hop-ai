import React, { useState, useEffect } from 'react';
import { 
  KeyRound, ShieldCheck, Zap, CheckCircle2, AlertCircle, Eye, EyeOff, 
  Trash2, ExternalLink, RefreshCw, Loader2, Sparkles, Building2, User, 
  Check, Power, ShieldAlert, Cpu, ArrowRight
} from 'lucide-react';
import { settingsApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { CustomApiKey, AIKeyTestResponse, User as UserType, Workspace } from '../types';

interface SettingsProps {
  currentUser?: UserType | null;
  currentWorkspace?: Workspace | null;
}

export const Settings: React.FC<SettingsProps> = ({ currentUser, currentWorkspace }) => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'byok' | 'profile' | 'workspace'>('byok');

  // BYOK Form States
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
  const [scope, setScope] = useState<'workspace' | 'personal'>('workspace');
  
  // Test Connection States
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<AIKeyTestResponse | null>(null);

  // Saving States
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);

  // Active Keys Table States
  const [keysList, setKeysList] = useState<CustomApiKey[]>([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(false);

  // Load keys on mount and when workspace changes
  useEffect(() => {
    loadKeys();
  }, [currentWorkspace]);

  const loadKeys = async () => {
    setIsLoadingKeys(true);
    try {
      const keys = await settingsApi.getKeysList(currentWorkspace?.id);
      setKeysList(keys);
    } catch (err) {
      console.error('Lỗi khi tải danh sách khóa AI:', err);
    } finally {
      setIsLoadingKeys(false);
    }
  };

  const handleTestConnection = async () => {
    if (!apiKey.trim()) {
      setTestResult({
        success: false,
        latency_ms: 0,
        message: 'Vui lòng nhập API Key trước khi kiểm tra kết nối.',
        error: 'EMPTY_KEY'
      });
      return;
    }

    setIsTesting(true);
    setTestResult(null);
    setSaveSuccessMessage(null);
    setSaveErrorMessage(null);

    try {
      const res = await settingsApi.testConnection({
        provider: 'gemini',
        api_key: apiKey.trim(),
        model: selectedModel
      });
      setTestResult(res);
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || 'Không thể kết nối đến máy chủ.';
      setTestResult({
        success: false,
        latency_ms: 0,
        message: typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg),
        error: 'NETWORK_ERROR'
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setSaveErrorMessage('API Key không được để trống.');
      return;
    }

    setIsSaving(true);
    setSaveSuccessMessage(null);
    setSaveErrorMessage(null);

    try {
      await settingsApi.saveKey({
        provider: 'gemini',
        api_key: apiKey.trim(),
        model: selectedModel,
        workspace_id: scope === 'workspace' ? (currentWorkspace?.id || 1) : null,
        scope: scope,
        is_active: true
      });

      setSaveSuccessMessage('Khóa API đã được mã hóa Fernet AES-128 và lưu trữ thành công!');
      setApiKey('');
      setTestResult(null);
      await loadKeys();
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || 'Lỗi khi lưu trữ khóa API.';
      setSaveErrorMessage(typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteKey = async (keyId?: number) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa/vô hiệu hóa khóa AI này? Hệ thống sẽ tự động hoàn nguyên về cấu hình mặc định.')) {
      return;
    }

    try {
      if (keyId) {
        await settingsApi.deleteKeyById(keyId);
      } else {
        await settingsApi.deleteKey(currentWorkspace?.id);
      }
      toast.success('Đã xóa cấu hình khóa AI thành công!');
      await loadKeys();
    } catch (err: any) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi xóa khóa AI');
    }
  };

  const handleToggleActive = async (keyId?: number) => {
    if (!keyId) return;
    try {
      const updated = await settingsApi.toggleKey(keyId);
      toast.success(`Đã ${updated.is_active ? 'bật kích hoạt' : 'tạm dừng'} khóa AI thành công!`);
      await loadKeys();
    } catch (err: any) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi đổi trạng thái khóa AI');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Top Banner Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden border border-slate-800">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-500/20 via-transparent to-transparent pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-1 bg-indigo-500/20 text-indigo-300 text-xs font-semibold rounded-full border border-indigo-400/30 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                Mã hóa AES-256 Vault / Fernet Kích hoạt
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Trung tâm Cài đặt & Quản trị Doanh nghiệp
            </h1>
            <p className="text-slate-400 text-sm mt-1 max-w-2xl">
              Cấu hình khóa AI tùy biến (Bring Your Own Key - BYOK), thông số kỹ thuật, hồ sơ tổ chức và chính sách bảo mật đa tầng.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 gap-2">
        <button
          onClick={() => setActiveTab('byok')}
          className={`flex items-center gap-2 px-5 py-3 font-medium text-sm border-b-2 transition-all ${
            activeTab === 'byok'
              ? 'border-indigo-600 text-indigo-600 font-semibold'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
          }`}
        >
          <KeyRound className="w-4 h-4" />
          Khóa AI Doanh nghiệp (BYOK Vault)
        </button>
        <button
          onClick={() => setActiveTab('profile')}
          className={`flex items-center gap-2 px-5 py-3 font-medium text-sm border-b-2 transition-all ${
            activeTab === 'profile'
              ? 'border-indigo-600 text-indigo-600 font-semibold'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
          }`}
        >
          <User className="w-4 h-4" />
          Hồ sơ & Phân quyền RBAC
        </button>
        <button
          onClick={() => setActiveTab('workspace')}
          className={`flex items-center gap-2 px-5 py-3 font-medium text-sm border-b-2 transition-all ${
            activeTab === 'workspace'
              ? 'border-indigo-600 text-indigo-600 font-semibold'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
          }`}
        >
          <Building2 className="w-4 h-4" />
          Không gian làm việc (Workspace)
        </button>
      </div>

      {/* Tab 1: BYOK Vault */}
      {activeTab === 'byok' && (
        <div className="space-y-6">
          {/* Card 1: Configuration Form */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Cấu hình Khóa API Riêng (Bring Your Own Key - BYOK)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Sử dụng quota và mô hình Google Gemini của riêng bạn với cơ chế mã hóa nghỉ an toàn tuyệt đối.
                  </p>
                </div>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Security Callout */}
              <div className="bg-slate-900 text-slate-200 p-4 rounded-xl text-xs space-y-2 border border-slate-800">
                <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Bảo mật Chuẩn Doanh nghiệp (Enterprise Cryptographic Vault)
                </div>
                <p className="text-slate-300 leading-relaxed">
                  Khóa API của bạn được mã hóa đối xứng ngay khi gửi lên máy chủ (<strong>AES-128-CBC + HMAC-SHA256 / Fernet</strong>) với salt độc quyền dẫn xuất từ Secret Key. 
                  Hệ thống <strong>tuyệt đối không lưu trữ plaintext</strong> và chỉ giải mã trên bộ nhớ RAM tạm thời khi thực thi tác vụ AI.
                </p>
              </div>

              <form onSubmit={handleSaveKey} className="space-y-6">
                {/* Provider Selection */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Nhà cung cấp AI (AI Provider)
                  </label>
                  <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center font-bold text-indigo-600 text-xs shadow-sm">
                        G
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900 flex items-center gap-2">
                          Google Gemini AI Studio
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-semibold rounded-full">
                            Chính thức & Độc quyền
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">
                          Tuân thủ chính sách bảo mật doanh nghiệp MarketFlow AI (Không hỗ trợ Claude hoặc GPT).
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Model Selection */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Lựa chọn Mô hình AI (Gemini Model)
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {[
                      {
                        id: 'gemini-2.5-flash',
                        name: 'Gemini 2.5 Flash',
                        badge: 'Khuyên dùng',
                        badgeColor: 'bg-indigo-100 text-indigo-700',
                        desc: 'Tốc độ cực nhanh (~120ms), tối ưu sáng tạo đa kênh Facebook, TikTok, Email.'
                      },
                      {
                        id: 'gemini-2.5-pro',
                        name: 'Gemini 2.5 Pro',
                        badge: 'Chuyên sâu',
                        badgeColor: 'bg-purple-100 text-purple-700',
                        desc: 'Suy luận chiến lược phức tạp, tối ưu cho phân tích Bác sĩ AI Doctor.'
                      },
                      {
                        id: 'gemini-2.0-flash',
                        name: 'Gemini 2.0 Flash',
                        badge: 'Cân bằng',
                        badgeColor: 'bg-blue-100 text-blue-700',
                        desc: 'Cân đối giữa tốc độ phản hồi và chi phí vận hành hàng ngày.'
                      },
                      {
                        id: 'gemini-flash-lite',
                        name: 'Gemini Flash Lite',
                        badge: 'Tiết kiệm',
                        badgeColor: 'bg-slate-100 text-slate-700',
                        desc: 'Phù hợp các tác vụ tóm tắt ngắn và trích xuất từ khóa đơn giản.'
                      }
                    ].map((m) => (
                      <div
                        key={m.id}
                        onClick={() => setSelectedModel(m.id)}
                        className={`p-3.5 rounded-xl border-2 cursor-pointer transition-all ${
                          selectedModel === m.id
                            ? 'border-indigo-600 bg-indigo-50/50 shadow-sm'
                            : 'border-slate-200 hover:border-slate-300 bg-white'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-bold text-sm text-slate-900">{m.name}</span>
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${m.badgeColor}`}>
                            {m.badge}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 leading-snug">{m.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Scope Selection */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Phạm vi Áp dụng (Key Scope)
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label
                      className={`p-3.5 rounded-xl border-2 flex items-start gap-3 cursor-pointer transition-all ${
                        scope === 'workspace'
                          ? 'border-indigo-600 bg-indigo-50/40'
                          : 'border-slate-200 hover:border-slate-300 bg-white'
                      }`}
                    >
                      <input
                        type="radio"
                        name="scope"
                        checked={scope === 'workspace'}
                        onChange={() => setScope('workspace')}
                        className="mt-1 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div>
                        <div className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                          <Building2 className="w-4 h-4 text-indigo-600" />
                          Cấp Không gian làm việc (Workspace Level)
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Áp dụng cho toàn bộ Marketers và Quản lý trong <strong>{currentWorkspace?.name || 'Workspace hiện tại'}</strong>.
                        </p>
                      </div>
                    </label>

                    <label
                      className={`p-3.5 rounded-xl border-2 flex items-start gap-3 cursor-pointer transition-all ${
                        scope === 'personal'
                          ? 'border-indigo-600 bg-indigo-50/40'
                          : 'border-slate-200 hover:border-slate-300 bg-white'
                      }`}
                    >
                      <input
                        type="radio"
                        name="scope"
                        checked={scope === 'personal'}
                        onChange={() => setScope('personal')}
                        className="mt-1 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div>
                        <div className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                          <User className="w-4 h-4 text-purple-600" />
                          Cấp Cá nhân (Personal Key)
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Chỉ áp dụng riêng cho tài khoản của bạn (ưu tiên khi bạn thực thi tác vụ AI).
                        </p>
                      </div>
                    </label>
                  </div>
                </div>

                {/* API Key Input Field */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-sm font-semibold text-slate-700">
                      Google Gemini API Key
                    </label>
                    <a
                      href="https://aistudio.google.com/app/apikey"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-600 hover:text-indigo-700 flex items-center gap-1 font-medium"
                    >
                      Lấy API Key tại Google AI Studio
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                  <div className="relative">
                    <input
                      type={showKey ? 'text' : 'password'}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="AIzaSy... (Dán khóa API Google Gemini tại đây)"
                      className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm pr-12 transition-all shadow-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
                    >
                      {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Live Test Connection & Results (FEAT-FE-18) */}
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      disabled={isTesting || !apiKey.trim()}
                      onClick={handleTestConnection}
                      className="px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 font-semibold text-sm text-slate-700 flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {isTesting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                          <span>Đang kiểm tra kết nối với Gemini AI...</span>
                        </>
                      ) : (
                        <>
                          <Zap className="w-4 h-4 text-amber-500" />
                          <span>Kiểm tra kết nối trực tiếp (Live Test)</span>
                        </>
                      )}
                    </button>

                    <button
                      type="submit"
                      disabled={isSaving || !apiKey.trim()}
                      className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm flex items-center gap-2 transition-all shadow-md hover:shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Đang mã hóa & lưu...</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4" />
                          <span>Lưu Cấu Hình Khóa AI</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Test Feedback Badges */}
                  {testResult && (
                    <div
                      className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
                        testResult.success
                          ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                          : 'bg-rose-50 border-rose-200 text-rose-900'
                      }`}
                    >
                      {testResult.success ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="space-y-1">
                        <div className="font-bold text-sm flex items-center gap-2">
                          {testResult.success ? (
                            <>
                              <span>Kết nối thành công ({testResult.latency_ms}ms)</span>
                              <span className="text-xs font-normal px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full">
                                Mô hình: {testResult.model || selectedModel}
                              </span>
                            </>
                          ) : (
                            <span>Kiểm tra kết nối thất bại</span>
                          )}
                        </div>
                        <p className="text-xs leading-relaxed opacity-90">{testResult.message}</p>
                      </div>
                    </div>
                  )}

                  {/* Save Alerts */}
                  {saveSuccessMessage && (
                    <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-medium flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      {saveSuccessMessage}
                    </div>
                  )}
                  {saveErrorMessage && (
                    <div className="p-3.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-medium flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-600" />
                      {saveErrorMessage}
                    </div>
                  )}
                </div>
              </form>
            </div>
          </div>

          {/* Card 2: Active Keys Vault Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Danh sách Khóa AI Doanh nghiệp Đang Kích hoạt
                </h3>
                <p className="text-xs text-slate-500">
                  Khóa được bảo vệ bằng mặt nạ hiển thị (Masked Key) chống quay lén hoặc chụp màn hình.
                </p>
              </div>
              <button
                onClick={loadKeys}
                className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
                title="Tải lại danh sách"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingKeys ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 uppercase text-[11px] font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3.5">Khóa API (Masked)</th>
                    <th className="px-6 py-3.5">Nhà cung cấp</th>
                    <th className="px-6 py-3.5">Mô hình AI</th>
                    <th className="px-6 py-3.5">Phạm vi</th>
                    <th className="px-6 py-3.5">Trạng thái</th>
                    <th className="px-6 py-3.5 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {keysList.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-slate-400 text-xs">
                        Chưa có khóa tùy biến nào được lưu. Hệ thống hiện đang sử dụng Khóa Hệ thống hoặc Smart Fallback Engine.
                      </td>
                    </tr>
                  ) : (
                    keysList.map((k) => (
                      <tr key={k.id || Math.random()} className="hover:bg-slate-50/60 transition-colors">
                        <td className="px-6 py-4 font-mono font-bold text-slate-800 text-xs flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-500" />
                          {k.masked_key || 'AIzaSy...****'}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded-md uppercase">
                            {k.provider}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs font-medium text-slate-700">
                          {k.model}
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-600">
                          {k.workspace_id ? (
                            <span className="flex items-center gap-1 text-indigo-600 font-medium">
                              <Building2 className="w-3.5 h-3.5" />
                              Workspace
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-purple-600 font-medium">
                              <User className="w-3.5 h-3.5" />
                              Cá nhân
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${
                              k.is_active
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {k.is_active ? 'Đang hoạt động' : 'Tạm dừng'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right space-x-2">
                          <button
                            onClick={() => handleToggleActive(k.id)}
                            className="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-medium hover:bg-slate-100 text-slate-700 transition-colors"
                            title={k.is_active ? 'Tạm dừng sử dụng khóa' : 'Kích hoạt khóa'}
                          >
                            <Power className="w-3.5 h-3.5 inline mr-1" />
                            {k.is_active ? 'Tắt' : 'Bật'}
                          </button>
                          <button
                            onClick={() => handleDeleteKey(k.id)}
                            className="px-2.5 py-1 rounded-lg border border-rose-200 text-xs font-medium text-rose-600 hover:bg-rose-50 transition-colors"
                            title="Xóa khóa khỏi két"
                          >
                            <Trash2 className="w-3.5 h-3.5 inline mr-1" />
                            Xóa
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Profile & RBAC */}
      {activeTab === 'profile' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center gap-4 pb-6 border-b border-slate-100">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600 text-white font-bold text-2xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              {currentUser?.full_name ? currentUser.full_name[0].toUpperCase() : 'U'}
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">{currentUser?.full_name || 'Người dùng MarketFlow'}</h2>
              <p className="text-slate-500 text-sm">{currentUser?.email || 'manager@agency.com'}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2.5 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full uppercase">
                  {currentUser?.role || 'MANAGER'}
                </span>
                <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-medium rounded-full">
                  {currentUser?.status || 'ACTIVE'}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-slate-500 text-xs block mb-1">Mã định danh Người dùng</span>
              <span className="font-mono font-bold text-slate-800">{currentUser?.id || 1}</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-slate-500 text-xs block mb-1">Quyền hạn Quản trị</span>
              <span className="font-semibold text-slate-800">
                {currentUser?.role === 'MANAGER' || currentUser?.role === 'AGENCY_MANAGER' 
                  ? 'Toàn quyền Phê duyệt & Cấu hình BYOK' 
                  : 'Sáng tạo Nội dung & Yêu cầu duyệt'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Workspace */}
      {activeTab === 'workspace' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center justify-between pb-6 border-b border-slate-100">
            <div>
              <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider block mb-1">
                Không gian làm việc hiện tại
              </span>
              <h2 className="text-xl font-bold text-slate-900">{currentWorkspace?.name || 'Default Agency Workspace'}</h2>
              <p className="text-slate-500 text-sm mt-0.5">{currentWorkspace?.description || 'Không gian làm việc điều phối chiến dịch tiếp thị tổng lực'}</p>
            </div>
            <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full">
              {currentWorkspace?.status || 'ACTIVE'}
            </span>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-sm space-y-2">
            <div className="font-bold text-slate-800 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-indigo-600" />
              Cách ly Dữ liệu Đa khách hàng (Multi-Tenancy Isolation)
            </div>
            <p className="text-slate-600 text-xs leading-relaxed">
              Mỗi Workspace sở hữu Brand Kit, Chiến dịch, Hàng đợi Duyệt bài và Khóa AI BYOK tách biệt hoàn toàn. 
              Các thành viên chỉ có thể truy xuất dữ liệu thuộc Workspace được phân quyền.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
