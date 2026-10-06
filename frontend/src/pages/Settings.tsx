import React, { useState, useEffect, useCallback } from 'react';
import { KeyRound, ShieldCheck, Zap, CheckCircle2, AlertCircle, Eye, EyeOff, Trash2, ExternalLink, RefreshCw, Loader2, Building2, User, Check, Power } from 'lucide-react';
import { settingsApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { CustomApiKey, AIKeyTestResponse, User as UserType, Workspace } from '../types';

/**
 * Cấu hình hiển thị cho từng nhà cung cấp AI.
 *
 * `keyless: true` nghĩa là provider phục vụ được mà KHÔNG cần API key
 * (Ollama chạy cục bộ, HuggingFace router phục vụ model công khai). Với hai
 * provider này, form không được chặn người dùng khi ô khóa trống — khác với
 * provider có khóa, nơi khóa rỗng là cấu hình chắc chắn không chạy được.
 *
 * Danh sách slug ở đây phải khớp `SUPPORTED_AI_PROVIDERS` của backend
 * (`backend/app/services/ai/providers.py`). Backend cũng có CHECK constraint
 * ở tầng CSDL, nên lệch danh sách sẽ ra HTTP 500 chứ không phải 422.
 */
interface ProviderConfig {
  name: string;
  initials: string;
  initialsColor: string;
  badge: string;
  badgeColor: string;
  desc: string;
  keyLabel: string;
  keyLink: string;
  linkText: string;
  placeholder: string;
  keyless?: boolean;
  models: Array<{ id: string; name: string; badge: string; badgeColor: string; desc: string }>;
}

const PROVIDER_CONFIGS: Record<string, ProviderConfig> = {
  gemini: {
    name: 'Google Gemini',
    initials: 'G',
    initialsColor: 'text-indigo-700',
    badge: 'Chính thức',
    badgeColor: 'bg-emerald-100 text-emerald-800',
    desc: 'Hệ sinh thái Gemini tối ưu tốc độ và chi phí với cửa sổ ngữ cảnh lớn.',
    keyLabel: 'Google Gemini API Key',
    keyLink: 'https://aistudio.google.com/app/apikey',
    linkText: 'Lấy API Key tại Google AI Studio',
    placeholder: 'AIzaSy... (Dán khóa API Google Gemini tại đây)',
    models: [
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
        id: 'gemini-1.5-flash',
        name: 'Gemini 1.5 Flash',
        badge: 'Tiết kiệm',
        badgeColor: 'bg-slate-100 text-slate-700',
        desc: 'Phù hợp các tác vụ tóm tắt ngắn và trích xuất từ khóa đơn giản.'
      }
    ]
  },
  openrouter: {
    name: 'OpenRouter',
    initials: 'OR',
    initialsColor: 'text-purple-700',
    badge: 'Đa mô hình',
    badgeColor: 'bg-purple-100 text-purple-800',
    desc: 'Cổng Gateway kết nối hàng trăm mô hình mã nguồn mở và thương mại.',
    keyLabel: 'OpenRouter API Key',
    keyLink: 'https://openrouter.ai/keys',
    linkText: 'Lấy API Key tại OpenRouter',
    placeholder: 'sk-or-v1-... (Dán khóa API OpenRouter tại đây)',
    models: [
      {
        id: 'meta-llama/llama-3.3-70b-instruct',
        name: 'Llama 3.3 70B',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Mô hình mã nguồn mở hàng đầu, văn phong tiếp thị tự nhiên và sáng tạo.'
      },
      {
        id: 'google/gemini-2.5-flash',
        name: 'Gemini 2.5 Flash (OR)',
        badge: 'Cân bằng',
        badgeColor: 'bg-blue-100 text-blue-700',
        desc: 'Truy cập Gemini qua OpenRouter gateway tốc độ cao.'
      },
      {
        id: 'anthropic/claude-3.5-sonnet',
        name: 'Claude 3.5 Sonnet',
        badge: 'Cao cấp',
        badgeColor: 'bg-amber-100 text-amber-800',
        desc: 'Chất lượng văn phong vượt trội, lý luận sắc bén cho chiến dịch lớn.'
      },
      {
        id: 'openai/gpt-4o-mini',
        name: 'GPT-4o Mini (OR)',
        badge: 'Tiết kiệm',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Nhanh, chi phí siêu rẻ cho việc sinh tiêu đề và hashtag hàng loạt.'
      }
    ]
  },
  openai: {
    name: 'OpenAI',
    initials: 'OA',
    initialsColor: 'text-emerald-700',
    badge: 'Tiêu chuẩn',
    badgeColor: 'bg-blue-100 text-blue-800',
    desc: 'Dòng mô hình GPT và o-series hàng đầu thế giới từ OpenAI.',
    keyLabel: 'OpenAI API Key',
    keyLink: 'https://platform.openai.com/api-keys',
    linkText: 'Lấy API Key tại OpenAI Platform',
    placeholder: 'sk-... (Dán khóa API OpenAI tại đây)',
    models: [
      {
        id: 'gpt-4o',
        name: 'GPT-4o',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Mô hình đa nhiệm thông minh nhất, xuất sắc trong sáng tạo kịch bản video và email.'
      },
      {
        id: 'gpt-4o-mini',
        name: 'GPT-4o Mini',
        badge: 'Tiết kiệm',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Tối ưu độ trễ thấp và chi phí tiết kiệm cho các tác vụ hàng ngày.'
      },
      {
        id: 'gpt-3.5-turbo',
        name: 'GPT-3.5 Turbo',
        badge: 'Cơ bản',
        badgeColor: 'bg-slate-100 text-slate-700',
        desc: 'Mô hình truyền thống ổn định cho việc trích xuất và phân loại nội dung.'
      },
      {
        id: 'o3-mini',
        name: 'o3-mini',
        badge: 'Suy luận',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Chuyên sâu giải toán, lập luận logic và phân tích chỉ số Attribution.'
      }
    ]
  },
  // Endpoint OpenAI-compatible của opencode zen. Danh sách model đầy đủ lấy
  // từ GET {AI_BASE_URL}/models — những model dưới đây chỉ là lựa chọn nhanh,
  // người dùng vẫn gõ được slug bất kỳ (backend chỉ yêu cầu khác rỗng).
  opencode: {
    name: 'OpenCode Zen',
    initials: 'OC',
    initialsColor: 'text-indigo-700',
    badge: 'Không cần credits',
    badgeColor: 'bg-indigo-100 text-indigo-800',
    desc: 'Endpoint OpenAI-compatible của opencode, dùng đúng model opencode đang cấu hình.',
    keyLabel: 'OpenCode API Key',
    keyLink: '',
    linkText: '',
    placeholder: 'sk-... (Dán khóa API từ ~/.config/opencode/opencode.json)',
    models: [
      {
        id: 'space-bunny-free',
        name: 'space-bunny-free',
        badge: 'Mặc định',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Model đang dùng cho backend khi AI_PROVIDER=opencode.'
      },
      {
        id: 'muse-spark-1.3-contributor-free',
        name: 'muse-spark-1.3',
        badge: 'Miễn phí',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Biến thể cộng tác viên, ưu tiên tốc độ cho nội dung ngắn.'
      },
      {
        id: 'claude-sonnet-5-5',
        name: 'claude-sonnet-5-5',
        badge: 'Suy luận sâu',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Phân tích chiến lược dài, thẩm định chất lượng bản nháp.'
      }
    ]
  },
  // Anthropic KHÔNG dùng giao thức OpenAI. Backend có adapter riêng gọi
  // Messages API (`backend/app/services/ai/anthropic_adapter.py`): endpoint
  // /v1/messages, header `x-api-key` + `anthropic-version`, `max_tokens` bắt
  // buộc. Danh sách model dưới đây là lựa chọn nhanh — backend chỉ yêu cầu
  // model bắt đầu bằng "claude".
  anthropic: {
    name: 'Anthropic (Claude)',
    initials: 'AN',
    initialsColor: 'text-orange-700',
    badge: 'Messages API',
    badgeColor: 'bg-orange-100 text-orange-800',
    desc: 'Dòng Claude của Anthropic. Dùng API Messages riêng, không phải giao thức OpenAI.',
    keyLabel: 'Anthropic API Key',
    keyLink: 'https://console.anthropic.com/settings/keys',
    linkText: 'Lấy API Key tại Anthropic Console',
    placeholder: 'sk-ant-... (Dán khóa API Anthropic tại đây)',
    models: [
      {
        id: 'claude-3-5-haiku-latest',
        name: 'Claude 3.5 Haiku',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Nhanh và tiết kiệm nhất trong dòng Claude; phù hợp sinh hàng loạt mẫu quảng cáo.'
      },
      {
        id: 'claude-3-5-sonnet-latest',
        name: 'Claude 3.5 Sonnet',
        badge: 'Cân bằng',
        badgeColor: 'bg-blue-100 text-blue-700',
        desc: 'Văn phong tự nhiên, lý luận sắc bén cho chiến dịch nhiều kênh.'
      },
      {
        id: 'claude-3-opus-latest',
        name: 'Claude 3 Opus',
        badge: 'Chất lượng cao',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Chất lượng văn xuôi cao nhất, đắt hơn; dùng cho bản nháp cần duyệt kỹ.'
      }
    ]
  },
  // HuggingFace router nói đúng giao thức OpenAI (`/v1/chat/completions`).
  // Token là tuỳ chọn: router phục vụ được model công khai không token, chỉ bị
  // giới hạn tần suất.
  huggingface: {
    name: 'Hugging Face',
    initials: 'HF',
    initialsColor: 'text-amber-700',
    badge: 'Mã nguồn mở',
    badgeColor: 'bg-amber-100 text-amber-800',
    desc: 'Router suy luận OpenAI-compatible của Hugging Face; chạy được model công khai không cần token.',
    keyLabel: 'Hugging Face Token (tuỳ chọn)',
    keyLink: 'https://huggingface.co/settings/tokens',
    linkText: 'Lấy token tại Hugging Face',
    placeholder: 'hf_... (Bỏ trống cũng chạy được với model công khai)',
    keyless: true,
    models: [
      {
        id: 'meta-llama/Llama-3.1-8B-Instruct',
        name: 'Llama 3.1 8B Instruct',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Model mã nguồn mở phổ biến nhất; chất lượng ổn với nội dung ngắn.'
      },
      {
        id: 'Qwen/Qwen2.5-72B-Instruct',
        name: 'Qwen 2.5 72B',
        badge: 'Tiếng Việt tốt',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Điểm mạnh về tiếng Việt, phù hợp bản quảng cáo nhiều dấu.'
      },
      {
        id: 'mistralai/Mistral-7B-Instruct-v0.3',
        name: 'Mistral 7B Instruct',
        badge: 'Nhẹ',
        badgeColor: 'bg-slate-100 text-slate-700',
        desc: 'Model nhỏ, chạy nhanh trên máy yếu hoặc suy luận tự phục vụ.'
      }
    ]
  },
  // Ollama: HTTP OpenAI-compatible mặc định http://localhost:11434/v1.
  // Cần `ollama serve` chạy trước và đã `ollama pull <model>`.
  ollama: {
    name: 'Ollama (chạy cục bộ)',
    initials: 'OL',
    initialsColor: 'text-slate-700',
    badge: 'Không cần API key',
    badgeColor: 'bg-emerald-100 text-emerald-800',
    desc: 'Chạy mô hình ngay trên máy của bạn. Không cần khóa, không mất phí, dùng được khi mạng ngoài không ổn định.',
    keyLabel: 'Không cần API Key',
    keyLink: 'https://ollama.com/library',
    linkText: 'Xem các model có sẵn trên Ollama',
    placeholder: 'Không cần khóa — chỉ cần Ollama đang chạy ở máy',
    keyless: true,
    models: [
      {
        id: 'llama3.2',
        name: 'llama3.2',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Model mặc định của hệ thống; chạy được cả trên máy yếu.'
      },
      {
        id: 'qwen2.5:7b',
        name: 'qwen2.5:7b',
        badge: 'Tiếng Việt',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Sinh văn bản tiếng Việt tự nhiên hơn Llama ở cùng kích thước.'
      },
      {
        id: 'mistral',
        name: 'mistral',
        badge: 'Cân bằng',
        badgeColor: 'bg-blue-100 text-blue-700',
        desc: 'Văn phong trực tiếp, hợp với thân bài quảng cáo ngắn.'
      }
    ]
  }
};

type ProviderSlug = 'gemini' | 'openrouter' | 'openai' | 'anthropic' | 'huggingface' | 'ollama' | 'opencode';

interface SettingsProps {
  currentUser?: UserType | null;
  currentWorkspace?: Workspace | null;
}

export const Settings: React.FC<SettingsProps> = ({ currentUser, currentWorkspace }) => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'byok' | 'profile' | 'workspace'>('byok');

  // BYOK Form States
  // Khớp SUPPORTED_AI_PROVIDERS của backend (xem backend/app/services/ai/providers.py).
  // Thiếu một slug ở đây thì tab provider đó không chọn được dù backend đã hỗ trợ.
  const [selectedProvider, setSelectedProvider] = useState<ProviderSlug>('gemini');
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
  const [keysError, setKeysError] = useState<string | null>(null);

  // Active Keys Table States
  const [keysList, setKeysList] = useState<CustomApiKey[]>([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(false);

  const loadKeys = useCallback(async () => {
    setIsLoadingKeys(true);
    setKeysError(null);
    try {
      const keys = await settingsApi.getKeysList(currentWorkspace?.id);
      setKeysList(keys);
    } catch (err) {
      // KHÔNG nuốt lỗi: bảng khóa AI hiển thị "chưa cấu hình khóa nào" khi
      // tải thất bại, tức người dùng tưởng mình thật sự chưa có khóa.
      setKeysError(getApiErrorMessage(err));
    } finally {
      setIsLoadingKeys(false);
    }
  }, [currentWorkspace?.id]);

  // Nạp khóa khi mount và mỗi khi đổi workspace. Phụ thuộc vào `id` chứ không
  // phải cả object workspace: đổi object (mỗi lần load lại danh sách) sẽ khiến
  // effect chạy lại vô ích.
  useEffect(() => {
    void loadKeys();
  }, [loadKeys]);

  /**
 * Provider hiện tại có bắt buộc nhập API key không.
 *
 * Ollama và HuggingFace phục vụ được mà không cần token. Nếu chặn ô khóa rỗng
 * với hai provider đó thì tính năng demo offline (cắm Ollama vào rồi chạy) không
 * bao giờ dùng được qua UI — trong khi backend vẫn hỗ trợ.
 */
const selectedProviderRequiresKey = !PROVIDER_CONFIGS[selectedProvider]?.keyless;

const handleTestConnection = async () => {
    if (selectedProviderRequiresKey && !apiKey.trim()) {
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
        provider: selectedProvider,
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
    if (selectedProviderRequiresKey && !apiKey.trim()) {
      setSaveErrorMessage('API Key không được để trống.');
      return;
    }

    setIsSaving(true);
    setSaveSuccessMessage(null);
    setSaveErrorMessage(null);

    try {
      await settingsApi.saveKey({
        provider: selectedProvider,
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
                Mã hóa Fernet (AES-128-CBC + HMAC-SHA256)
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
                {/* Provider Selection (BYOK Multi-Provider) */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Nhà cung cấp AI (AI Provider)
                  </label>
                  {/* `lg:` chứ không phải `md:` cho 3 cột. Ở viewport 929px (nội dung thực
                      ~617px), `md:grid-cols-3` để lại mỗi thẻ ~69px — hẹp hơn
                      cả tên provider lẫn badge, nên badge tràn ra ngoài thẻ.
                      Ở `lg:` mỗi thẻ đủ chỗ cho icon + tên + badge. */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                    {(Object.keys(PROVIDER_CONFIGS) as Array<keyof typeof PROVIDER_CONFIGS>).map((pKey) => {
                      const p = PROVIDER_CONFIGS[pKey];
                      const isSelected = selectedProvider === pKey;
                      return (
                        // Thẻ chọn nhà cung cấp: dùng <button> gốc + aria-pressed để
                        // hoạt động được bằng chuột lẫn bàn phím.
                        <button
                          key={pKey}
                          type="button"
                          aria-pressed={isSelected}
                          onClick={() => {
                            setSelectedProvider(pKey as ProviderSlug);
                            setSelectedModel(p.models[0].id);
                          }}
                          className={`w-full text-left font-sans p-3.5 rounded-xl border-2 cursor-pointer transition-all flex flex-col justify-between ${
                            isSelected
                              ? 'border-indigo-600 bg-indigo-50/50 shadow-sm'
                              : 'border-slate-200 hover:border-slate-300 bg-white'
                          }`}
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2 mb-2">
                              {/* Tên provider và badge đều cần `shrink-0`: badge
                                  "Đa mô hình" bị vỡ thành "Đa mô / hình" khi thẻ
                                  provider hẹp (bề rộng thực tế ~144px ở viewport
                                  929px sau khi trừ sidebar). */}
                              <div className="flex items-center gap-2 min-w-0">
                                <div className={`w-7 h-7 shrink-0 rounded-lg bg-white border border-slate-200 flex items-center justify-center font-bold text-xs shadow-sm ${p.initialsColor}`}>
                                  {p.initials}
                                </div>
                                <span className="font-bold text-sm text-slate-900 shrink-0">{p.name}</span>
                              </div>
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap ${p.badgeColor}`}>
                                {p.badge}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 leading-snug">{p.desc}</p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Model Selection */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Lựa chọn Mô hình AI ({PROVIDER_CONFIGS[selectedProvider].name} Model)
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {PROVIDER_CONFIGS[selectedProvider].models.map((m) => (
                      // Thẻ chọn mô hình AI: dùng <button> gốc + aria-pressed để chọn được bằng bàn phím.
                      <button
                        key={m.id}
                        type="button"
                        aria-pressed={selectedModel === m.id}
                        onClick={() => setSelectedModel(m.id)}
                        className={`w-full text-left font-sans p-3.5 rounded-xl border-2 cursor-pointer transition-all ${
                          selectedModel === m.id
                            ? 'border-indigo-600 bg-indigo-50/50 shadow-sm'
                            : 'border-slate-200 hover:border-slate-300 bg-white'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 mb-1.5">
                          <span className="font-bold text-sm text-slate-900 min-w-0">{m.name}</span>
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap ${m.badgeColor}`}>
                            {m.badge}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 leading-snug">{m.desc}</p>
                      </button>
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
                      {PROVIDER_CONFIGS[selectedProvider].keyLabel}
                    </label>
                    {/* opencode không có trang "lấy API key" công khai — khoá nằm trong
                        file cấu hình cục bộ. Render link rỗng sẽ tạo <a href="">
                        bấm được nhưng điều hướng về chính trang hiện tại, nên ẩn. */}
                    {PROVIDER_CONFIGS[selectedProvider].keyLink && (
                      <a
                        href={PROVIDER_CONFIGS[selectedProvider].keyLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-indigo-600 hover:text-indigo-700 flex items-center gap-1 font-medium"
                      >
                        {PROVIDER_CONFIGS[selectedProvider].linkText}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                  {/* Provider không cần khoá: ẩn hẳn ô nhập và nút hiện/ẩn khoá.
                      Hiển thị ô nhập rỗng bắt người dùng nhập gì đó vô nghĩa chỉ để
                      hệ thống bỏ qua, đó là thói quen dễ dẫn tới việc dán nhầm khoá
                      của provider khác vào ô này. */}
                  {!selectedProviderRequiresKey ? (
                    <div className="flex items-start gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5">
                      <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-emerald-900">
                          {selectedProvider === 'ollama'
                            ? 'Không cần API Key — chỉ cần Ollama đang chạy'
                            : 'API Key là tuỳ chọn — để trống vẫn dùng được'}
                        </p>
                        <p className="text-xs text-emerald-800 mt-0.5">
                          {selectedProvider === 'ollama'
                            ? 'Hãy chạy `ollama serve` rồi `ollama pull ' + PROVIDER_CONFIGS[selectedProvider].models[0].id + '` trên máy của bạn. Nếu Ollama chạy ở máy khác, đặt biến môi trường MARKETFLOW_OLLAMA_BASE_URL trên backend.'
                            : 'Router của Hugging Face phục vụ được model công khai không cần token, nhưng bị giới hạn tần suất. Điền token để có hạn mức cao hơn.'}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <>
                    <div className="relative">
                      <input
                        type={showKey ? 'text' : 'password'}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={PROVIDER_CONFIGS[selectedProvider].placeholder}
                        className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm pr-12 transition-all shadow-sm"
                      />
                      <button
                        type="button"
                      onClick={() => setShowKey(!showKey)}
                      aria-label={showKey ? "Ẩn khóa API" : "Hiện khóa API"}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
                    >
                      {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                    </>
                  )}
                </div>

                {/* Live Test Connection & Results (FEAT-FE-18) */}
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      disabled={isTesting || (selectedProviderRequiresKey && !apiKey.trim())}
                      onClick={handleTestConnection}
                      className="px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 font-semibold text-sm text-slate-700 flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {isTesting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                          <span>Đang kiểm tra kết nối với {PROVIDER_CONFIGS[selectedProvider].name}...</span>
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
                      disabled={isSaving || (selectedProviderRequiresKey && !apiKey.trim())}
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
                type="button"
                onClick={() => void loadKeys()}
                aria-label="Tải lại danh sách khóa API"
                className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
                title="Tải lại danh sách"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingKeys ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div
              className="overflow-x-auto"
              role="region"
              aria-label="Bảng khóa API đã cấu hình"
              tabIndex={0}
            >
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
                  {keysError ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center">
                        <p className="text-xs font-bold text-rose-700">Không tải được danh sách khóa API</p>
                        <p className="text-[11px] text-rose-600 mt-1">{keysError}</p>
                        <button
                          type="button"
                          onClick={() => void loadKeys()}
                          className="mt-2 px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-[11px] font-bold"
                        >
                          Thử lại
                        </button>
                      </td>
                    </tr>
                  ) : keysList.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-slate-400 text-xs">
                        {isLoadingKeys
                          ? 'Đang tải danh sách khóa…'
                          : 'Chưa có khóa tùy biến nào được lưu. Hệ thống hiện đang sử dụng Khóa Hệ thống hoặc Smart Fallback Engine.'}
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
