import React, { useState, useEffect, useCallback } from 'react';
import { KeyRound, ShieldCheck, Zap, CheckCircle2, AlertCircle, Eye, EyeOff, Trash2, ExternalLink, RefreshCw, Loader2, Building2, User, Check, Power, Route, Plus, Star, ArrowDown, X, UserPlus, Lock, Crown } from 'lucide-react';
import { settingsApi, authApi, workspaceApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { CustomApiKey, AIKeyTestResponse, User as UserType, Workspace, AIModelListResponse, AIChain, AIChainHop, WorkspaceMemberItem } from '../types';

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
    badge: 'Chính thức · Có Free Tier',
    badgeColor: 'bg-emerald-100 text-emerald-800',
    desc: 'Hệ sinh thái Google Gemini (gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash) hoặc tự nhập mã model bất kỳ từ Google AI Studio.',
    keyLabel: 'Google Gemini API Key',
    keyLink: 'https://aistudio.google.com/app/apikey',
    linkText: 'Lấy API Key tại Google AI Studio',
    placeholder: 'AIzaSy... (Dán khóa API Google Gemini tại đây)',
    models: [
      {
        id: 'gemini-2.5-flash',
        name: 'gemini-2.5-flash',
        badge: 'Khuyên dùng · Free Tier',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Mô hình lai suy luận (Hybrid Reasoning) tốc độ cao của Google, hỗ trợ 1M token context & Free Tier.'
      },
      {
        id: 'gemini-2.5-pro',
        name: 'gemini-2.5-pro',
        badge: 'Suy luận chuyên sâu',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Mô hình Pro mạnh nhất cho lập kế hoạch chiến lược, Bác sĩ AI Doctor & phân bổ ngân sách ROAS.'
      },
      {
        id: 'gemini-2.5-flash-lite',
        name: 'gemini-2.5-flash-lite',
        badge: 'Siêu nhẹ · Tiết kiệm',
        badgeColor: 'bg-blue-100 text-blue-700',
        desc: 'Tối ưu chi phí và độ trễ thấp cho các tác vụ sinh biến thể A/B và kiểm duyệt nhanh.'
      },
      {
        id: 'gemini-2.0-flash',
        name: 'gemini-2.0-flash',
        badge: 'Ổn định · Free Tier',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Dòng Flash phổ biến, ổn định cao cho các tác vụ biên tập nội dung hàng ngày.'
      }
    ]
  },
  openrouter: {
    name: 'OpenRouter',
    initials: 'OR',
    initialsColor: 'text-purple-700',
    badge: '300+ Model · Tự nhập ID',
    badgeColor: 'bg-purple-100 text-purple-800',
    desc: 'Gateway hợp nhất hơn 300 mô hình; hỗ trợ tự nhập bất kỳ ID tác giả/tên-model nào hoặc dùng openrouter/free.',
    keyLabel: 'OpenRouter API Key',
    keyLink: 'https://openrouter.ai/keys',
    linkText: 'Lấy API Key tại OpenRouter',
    placeholder: 'sk-or-v1-... (Dán khóa API OpenRouter tại đây)',
    models: [
      {
        id: 'openrouter/free',
        name: 'openrouter/free',
        badge: 'Khuyên dùng · Auto Free',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Bộ định tuyến tự động chọn mô hình :free đang hoạt động tốt nhất trên OpenRouter.'
      },
      {
        id: 'deepseek/deepseek-r1:free',
        name: 'deepseek/deepseek-r1:free',
        badge: 'Miễn phí · Suy luận',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Mô hình suy luận chuỗi tư duy (Reasoning) DeepSeek R1 miễn phí qua OpenRouter.'
      },
      {
        id: 'deepseek/deepseek-chat-v3-0324:free',
        name: 'deepseek/deepseek-chat-v3-0324:free',
        badge: 'Miễn phí · Đa năng',
        badgeColor: 'bg-amber-100 text-amber-800',
        desc: 'DeepSeek V3 0324 miễn phí, văn phong tự nhiên và tốc độ phản hồi nhanh.'
      },
      {
        id: 'meta-llama/llama-3.3-70b-instruct:free',
        name: 'meta-llama/llama-3.3-70b-instruct:free',
        badge: 'Miễn phí · 70B',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Mô hình mở 70B của Meta miễn phí qua cổng OpenRouter.'
      }
    ]
  },
  openai: {
    name: 'OpenAI',
    initials: 'OA',
    initialsColor: 'text-emerald-700',
    badge: 'GPT-4.1 · GPT-4o · o3',
    badgeColor: 'bg-blue-100 text-blue-800',
    desc: 'Hệ sinh thái OpenAI chuẩn thực tế (gpt-4.1, gpt-4o, o3, o4-mini) hoặc tự nhập tên model/fine-tune riêng của bạn.',
    keyLabel: 'OpenAI API Key',
    keyLink: 'https://platform.openai.com/api-keys',
    linkText: 'Lấy API Key tại OpenAI Platform',
    placeholder: 'sk-proj-... (Dán khóa API OpenAI tại đây)',
    models: [
      {
        id: 'gpt-4.1',
        name: 'gpt-4.1',
        badge: 'Khuyên dùng · 1M Context',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Flagship GPT-4.1 của OpenAI: tuân thủ cấu trúc JSON chuẩn xác và biên tập nội dung sắc bén.'
      },
      {
        id: 'gpt-4o',
        name: 'gpt-4o',
        badge: 'Đa phương thức',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Mô hình Omni đa năng, cân bằng tốc độ và chất lượng sáng tạo đa kênh.'
      },
      {
        id: 'o3',
        name: 'o3',
        badge: 'Suy luận sâu',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Mô hình suy luận chuyên sâu cho phân bổ ngân sách ROI/ROAS và chẩn đoán phễu chuyển đổi.'
      },
      {
        id: 'o4-mini',
        name: 'o4-mini',
        badge: 'Suy luận nhanh',
        badgeColor: 'bg-slate-100 text-slate-700',
        desc: 'Mô hình suy luận tốc độ cao, chi phí thấp cho tác nhân MCP tự hành.'
      }
    ]
  },
  anthropic: {
    name: 'Anthropic (Claude)',
    initials: 'AN',
    initialsColor: 'text-orange-700',
    badge: 'Claude 4 & 3.7 Series',
    badgeColor: 'bg-orange-100 text-orange-800',
    desc: 'Dòng Claude Sonnet 4, Opus 4 & 3.7 Sonnet qua Messages API gốc — văn phong tự nhiên, hoặc tự nhập mã model Claude bất kỳ.',
    keyLabel: 'Anthropic API Key',
    keyLink: 'https://console.anthropic.com/settings/keys',
    linkText: 'Lấy API Key tại Anthropic Console',
    placeholder: 'sk-ant-... (Dán khóa API Anthropic tại đây)',
    models: [
      {
        id: 'claude-sonnet-4-0',
        name: 'claude-sonnet-4-0',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Claude Sonnet 4: cân bằng giữa chiều sâu ngôn từ quảng cáo, tốc độ và chi phí.'
      },
      {
        id: 'claude-opus-4-0',
        name: 'claude-opus-4-0',
        badge: 'Flagship Sáng tạo',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Claude Opus 4 cho chiến lược B2B phức tạp, kịch bản đa kênh & thẩm định rủi ro thương hiệu.'
      },
      {
        id: 'claude-3-7-sonnet-latest',
        name: 'claude-3-7-sonnet-latest',
        badge: 'Hybrid Reasoning',
        badgeColor: 'bg-amber-100 text-amber-800',
        desc: 'Claude 3.7 Sonnet hỗ trợ suy luận mở rộng và viết nội dung dài mạch lạc.'
      },
      {
        id: 'claude-3-5-haiku-latest',
        name: 'claude-3-5-haiku-latest',
        badge: 'Siêu tốc',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Phản hồi tức thì cho tóm tắt chỉ số chiến dịch và kiểm duyệt nhanh.'
      }
    ]
  },
  groq: {
    name: 'Groq LPU (Siêu tốc)',
    initials: 'GQ',
    initialsColor: 'text-rose-700',
    badge: 'LPU ~800 tok/s',
    badgeColor: 'bg-rose-100 text-rose-800',
    desc: 'Hạ tầng vi xử lý LPU chuyên biệt cho suy luận AI thời gian thực (Llama 3.3, Llama 4 Scout/Maverick, DeepSeek R1).',
    keyLabel: 'GroqCloud API Key',
    keyLink: 'https://console.groq.com/keys',
    linkText: 'Lấy API Key miễn phí tại GroqCloud Console',
    placeholder: 'gsk_... (Dán khóa API GroqCloud tại đây)',
    models: [
      {
        id: 'llama-3.3-70b-versatile',
        name: 'llama-3.3-70b-versatile',
        badge: 'Khuyên dùng · Ổn định',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Mô hình 70B ổn định nhất trên Groq LPU cho tiếng Việt và cấu trúc JSON.'
      },
      {
        id: 'meta-llama/llama-4-scout-17b-16e-instruct',
        name: 'llama-4-scout-17b-16e',
        badge: 'Llama 4 · Siêu tốc',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Mô hình Llama 4 MoE 16 chuyên gia tốc độ cực cao trên GroqCloud.'
      },
      {
        id: 'meta-llama/llama-4-maverick-17b-128e-instruct',
        name: 'llama-4-maverick-17b-128e',
        badge: 'Llama 4 · 128E',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Kiến trúc Llama 4 MoE 128 chuyên gia chạy trên phần cứng LPU.'
      },
      {
        id: 'deepseek-r1-distill-llama-70b',
        name: 'deepseek-r1-distill-llama-70b',
        badge: 'Suy luận nhanh',
        badgeColor: 'bg-amber-100 text-amber-800',
        desc: 'Suy luận chuỗi tư duy tốc độ cao cho chẩn đoán điểm nghẽn chiến dịch.'
      }
    ]
  },
  xai: {
    name: 'xAI (Grok)',
    initials: 'X',
    initialsColor: 'text-slate-900',
    badge: 'Grok 3 Series',
    badgeColor: 'bg-slate-200 text-slate-900',
    desc: 'Hệ sinh thái Grok của xAI (grok-3, grok-3-mini) hoặc tự nhập bất kỳ mã model xAI nào của bạn.',
    keyLabel: 'xAI (Grok) API Key',
    keyLink: 'https://console.x.ai/',
    linkText: 'Lấy API Key tại xAI Console',
    placeholder: 'xai-... (Dán khóa API xAI Grok tại đây)',
    models: [
      {
        id: 'grok-3',
        name: 'grok-3',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Mô hình chủ lực của xAI: ngôn từ sắc sảo, tối ưu cho hook mạng xã hội và phân tích.'
      },
      {
        id: 'grok-3-mini',
        name: 'grok-3-mini',
        badge: 'Suy luận nhẹ',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Mô hình suy luận nhanh, tiết kiệm chi phí của xAI.'
      },
      {
        id: 'grok-3-fast',
        name: 'grok-3-fast',
        badge: 'Tốc độ cao',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Phản hồi độ trễ thấp cho sinh biến thể nội dung quảng cáo hàng loạt.'
      }
    ]
  },
  huggingface: {
    name: 'Hugging Face',
    initials: 'HF',
    initialsColor: 'text-amber-700',
    badge: 'Open-Weights · Tự nhập repo',
    badgeColor: 'bg-amber-100 text-amber-800',
    desc: 'Router suy luận OpenAI-compatible của Hugging Face; hỗ trợ tự nhập bất kỳ repo ID model mở nào.',
    keyLabel: 'Hugging Face Token (tuỳ chọn)',
    keyLink: 'https://huggingface.co/settings/tokens',
    linkText: 'Lấy token tại Hugging Face',
    placeholder: 'hf_... (Bỏ trống cũng chạy được với model công khai)',
    keyless: true,
    models: [
      {
        id: 'Qwen/Qwen2.5-72B-Instruct',
        name: 'Qwen/Qwen2.5-72B-Instruct',
        badge: 'Khuyên dùng',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Mô hình mở 72B ổn định, mạnh về tiếng Việt và sáng tạo nội dung đa kênh.'
      },
      {
        id: 'deepseek-ai/DeepSeek-R1',
        name: 'deepseek-ai/DeepSeek-R1',
        badge: 'Suy luận sâu',
        badgeColor: 'bg-blue-100 text-blue-700',
        desc: 'Chuyên trị lập kế hoạch ngân sách chiến dịch và phân tích điểm nghẽn chuyển đổi.'
      },
      {
        id: 'deepseek-ai/DeepSeek-V3-0324',
        name: 'deepseek-ai/DeepSeek-V3-0324',
        badge: 'MoE 685B',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Mô hình MoE mã nguồn mở cho viết quảng cáo & phân tích.'
      },
      {
        id: 'meta-llama/Llama-3.3-70B-Instruct',
        name: 'meta-llama/Llama-3.3-70B-Instruct',
        badge: 'Meta 70B',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Dòng Llama 3.3 70B Instruct chuẩn xác của Meta.'
      }
    ]
  },
  ollama: {
    name: 'Ollama (chạy cục bộ)',
    initials: 'OL',
    initialsColor: 'text-slate-700',
    badge: 'Local · Tự nhập tag',
    badgeColor: 'bg-emerald-100 text-emerald-800',
    desc: 'Chạy mô hình mở (qwen3, deepseek-r1, llama3.2, gemma3) ngay trên máy hoặc tự nhập bất kỳ tag Ollama nào bạn đã pull.',
    keyLabel: 'Không cần API Key',
    keyLink: 'https://ollama.com/library',
    linkText: 'Xem thư viện model trên Ollama',
    placeholder: 'Không cần khóa — chỉ cần Ollama đang chạy ở máy',
    keyless: true,
    models: [
      {
        id: 'qwen3:8b',
        name: 'qwen3:8b',
        badge: 'Khuyên dùng · 8GB RAM',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Chạy mượt trên laptop 8GB–16GB RAM, hỗ trợ tiếng Việt tự nhiên.'
      },
      {
        id: 'deepseek-r1:8b',
        name: 'deepseek-r1:8b',
        badge: 'Suy luận cục bộ',
        badgeColor: 'bg-purple-100 text-purple-700',
        desc: 'Mô hình suy luận chuỗi tư duy (Reasoning) chạy hoàn toàn offline.'
      },
      {
        id: 'llama3.2:3b',
        name: 'llama3.2:3b',
        badge: 'Siêu nhẹ',
        badgeColor: 'bg-emerald-100 text-emerald-800',
        desc: 'Mô hình 3B cực nhẹ, phản hồi tức thì trên mọi cấu hình CPU/GPU.'
      },
      {
        id: 'gemma3:12b',
        name: 'gemma3:12b',
        badge: 'Google Gemma 3',
        badgeColor: 'bg-blue-100 text-blue-700',
        desc: 'Thế hệ Gemma 3 của Google chạy trên phần cứng cá nhân.'
      }
    ]
  },
  opencode: {
    name: 'OpenCode Zen',
    initials: 'OC',
    initialsColor: 'text-indigo-700',
    badge: 'Free Tier Mặc định',
    badgeColor: 'bg-indigo-100 text-indigo-800',
    desc: 'Gateway AI miễn phí không cần khóa đang kích hoạt sẵn trên máy chủ; hỗ trợ tự nhập mã model hoặc bấm Lấy model mới nhất.',
    keyLabel: 'OpenCode API Key (tuỳ chọn)',
    keyLink: '',
    linkText: '',
    placeholder: 'sk-... (Để trống để dùng tầng Free mặc định của máy chủ)',
    keyless: true,
    models: [
      {
        id: 'space-bunny-free',
        name: 'space-bunny-free',
        badge: 'Mặc định Live',
        badgeColor: 'bg-indigo-100 text-indigo-700',
        desc: 'Model miễn phí đang kích hoạt mặc định trên máy chủ khi AI_PROVIDER=opencode.'
      }
    ]
  }
};

type ProviderSlug = 'gemini' | 'openrouter' | 'openai' | 'anthropic' | 'groq' | 'xai' | 'huggingface' | 'ollama' | 'opencode';

interface SettingsProps {
  currentUser?: UserType | null;
  currentWorkspace?: Workspace | null;
}

export const Settings: React.FC<SettingsProps> = ({ currentUser, currentWorkspace }) => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'byok' | 'chains' | 'profile' | 'workspace'>('byok');

  // BYOK Form States
  // Khớp SUPPORTED_AI_PROVIDERS của backend (xem backend/app/services/ai/providers.py).
  // Thiếu một slug ở đây thì tab provider đó không chọn được dù backend đã hỗ trợ.
  const [selectedProvider, setSelectedProvider] = useState<ProviderSlug>('gemini');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
  const [scope, setScope] = useState<'workspace' | 'personal'>('workspace');

  // Model nạp động từ nhà cung cấp. Danh sách tĩnh trong PROVIDER_CONFIGS chỉ
  // là gợi ý nhanh; backend `/settings/ai-models` mới là nguồn thật (gọi
  // `{base_url}/models` kiểu OpenAI). Nhờ vậy thêm model mới không cần sửa UI.
  const [liveModels, setLiveModels] = useState<AIModelListResponse | null>(null);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  
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

  // =========================================================================
  // Chuỗi fallback Model (kiểu 9Router)
  // =========================================================================
  const [chains, setChains] = useState<AIChain[]>([]);
  const [isLoadingChains, setIsLoadingChains] = useState(false);
  const [chainsError, setChainsError] = useState<string | null>(null);
  const [isSavingChain, setIsSavingChain] = useState(false);
  const [chainName, setChainName] = useState('');
  const [chainHops, setChainHops] = useState<AIChainHop[]>([{ provider: 'gemini', model: '' }]);

  // Đổi mật khẩu (Workstream E)
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const handlePasswordSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (newPassword !== confirmPassword) {
      setPasswordError('Mật khẩu nhập lại không khớp.');
      return;
    }
    if (newPassword === currentPassword) {
      setPasswordError('Mật khẩu mới phải khác mật khẩu hiện tại.');
      return;
    }
    setIsChangingPassword(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      toast.success('Đổi mật khẩu thành công. Mọi phiên khác đã bị thu hồi.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPasswordError(getApiErrorMessage(err));
    } finally {
      setIsChangingPassword(false);
    }
  }, [currentPassword, newPassword, confirmPassword, toast]);

  // =========================================================================
  // Quản trị Nhân sự & Cấp phát Tài khoản theo Phân quyền (RBAC 2-Tầng)
  // =========================================================================
  const workspaceId = currentWorkspace?.id || 1;
  const isManagerOrAdmin =
    currentUser?.role === 'MANAGER' ||
    currentUser?.role === 'AGENCY_MANAGER' ||
    (currentUser?.role as string) === 'ADMIN' ||
    (currentWorkspace?.owner_id && currentUser?.id === currentWorkspace.owner_id);

  const [members, setMembers] = useState<WorkspaceMemberItem[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [membersError, setMembersError] = useState<string | null>(null);

  const [provFullName, setProvFullName] = useState('');
  const [provEmail, setProvEmail] = useState('');
  const [provPassword, setProvPassword] = useState('');
  const [provRole, setProvRole] = useState<'MANAGER' | 'MARKETER' | 'CLIENT_APPROVER'>('MARKETER');
  const [isProvisioning, setIsProvisioning] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);

  const loadMembers = useCallback(async () => {
    setIsLoadingMembers(true);
    setMembersError(null);
    try {
      const list = await workspaceApi.getMembers(workspaceId);
      setMembers(list);
    } catch (err) {
      setMembersError(getApiErrorMessage(err));
    } finally {
      setIsLoadingMembers(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (activeTab === 'profile' || activeTab === 'workspace') {
      void loadMembers();
    }
  }, [activeTab, loadMembers]);

  const handleProvisionAccount = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!provFullName.trim() || !provEmail.trim() || provPassword.length < 6) {
      toast.error('Điền đầy đủ họ tên, email và mật khẩu tối thiểu 6 ký tự.');
      return;
    }
    setIsProvisioning(true);
    try {
      const res = await workspaceApi.provisionAccount(workspaceId, {
        full_name: provFullName.trim(),
        email: provEmail.trim().toLowerCase(),
        password: provPassword,
        role: provRole,
      });
      toast.success(
        res.created_new_user
          ? `Đã tạo tài khoản ${res.email} với quyền ${provRole}.`
          : `Đã gán quyền ${provRole} cho tài khoản ${res.email}.`,
      );
      setProvFullName('');
      setProvEmail('');
      setProvPassword('');
      setProvRole('MARKETER');
      await loadMembers();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể cấp phát tài khoản');
    } finally {
      setIsProvisioning(false);
    }
  }, [workspaceId, provFullName, provEmail, provPassword, provRole, loadMembers, toast]);

  const handleRoleChange = useCallback(async (member: WorkspaceMemberItem, nextRole: 'MANAGER' | 'MARKETER' | 'CLIENT_APPROVER') => {
    setUpdatingUserId(member.user_id);
    try {
      await workspaceApi.updateMemberRole(workspaceId, member.user_id, nextRole);
      toast.success(`Đã đổi quyền của ${member.full_name} sang ${nextRole}.`);
      await loadMembers();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể đổi vai trò');
    } finally {
      setUpdatingUserId(null);
    }
  }, [workspaceId, loadMembers, toast]);

  const handleRemoveMember = useCallback(async (member: WorkspaceMemberItem) => {
    if (!window.confirm(`Gỡ ${member.full_name} (${member.email}) khỏi Workspace hiện tại?`)) {
      return;
    }
    setUpdatingUserId(member.user_id);
    try {
      await workspaceApi.removeMember(workspaceId, member.user_id);
      toast.success(`Đã gỡ ${member.email} khỏi không gian làm việc.`);
      await loadMembers();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể gỡ thành viên');
    } finally {
      setUpdatingUserId(null);
    }
  }, [workspaceId, loadMembers, toast]);

  const loadChains = useCallback(async () => {
    setIsLoadingChains(true);
    setChainsError(null);
    try {
      setChains(await settingsApi.listChains());
    } catch (err) {
      setChainsError(getApiErrorMessage(err));
    } finally {
      setIsLoadingChains(false);
    }
  }, []);

  useEffect(() => {
    void loadChains();
  }, [loadChains]);

  const handleCreateChain = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const name = chainName.trim();
    if (!name) {
      toast.error('Nhập tên chuỗi trước khi lưu.');
      return;
    }
    // Model để trống là hợp lệ (backend điền model mặc định của provider).
    const hops = chainHops
      .map(h => ({ provider: h.provider, model: h.model.trim() }))
      .filter(h => h.provider);
    if (hops.length === 0) {
      toast.error('Chuỗi cần ít nhất một bước (provider).');
      return;
    }
    setIsSavingChain(true);
    try {
      await settingsApi.createChain({
        name,
        hops,
        workspace_id: currentWorkspace?.id ?? null,
      });
      toast.success(`Đã tạo chuỗi “${name}”.`);
      setChainName('');
      setChainHops([{ provider: 'gemini', model: '' }]);
      await loadChains();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    } finally {
      setIsSavingChain(false);
    }
  }, [chainName, chainHops, currentWorkspace?.id, loadChains, toast]);

  const handleToggleChain = useCallback(async (chain: AIChain) => {
    try {
      await settingsApi.toggleChain(chain.id);
      await loadChains();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    }
  }, [loadChains, toast]);

  const handleSetDefaultChain = useCallback(async (chain: AIChain) => {
    try {
      await settingsApi.setDefaultChain(chain.id);
      toast.success(`“${chain.name}” đã là chuỗi mặc định.`);
      await loadChains();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    }
  }, [loadChains, toast]);

  const handleDeleteChain = useCallback(async (chain: AIChain) => {
    if (!window.confirm(`Xóa chuỗi “${chain.name}”? Các request đang dùng chuỗi này sẽ tự rơi về model đơn.`)) {
      return;
    }
    try {
      await settingsApi.deleteChain(chain.id);
      toast.success(`Đã xóa chuỗi “${chain.name}”.`);
      await loadChains();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    }
  }, [loadChains, toast]);

  /**
   * Hỏi nhà cung cấp xem đang có model nào.
   *
   * Chỉ gọi khi người dùng bấm nút (không tự chạy lúc mở trang): mỗi lần gọi
   * là một request đi ra ngoài, và cần khoá mới có danh sách đầy đủ. Nếu
   * backend không lấy được, nó vẫn trả danh sách dự phòng với
   * `source: "registry"` — UI hiện rõ nguồn đó.
   */
  const handleFetchModels = useCallback(async () => {
    setIsLoadingModels(true);
    try {
      const result = await settingsApi.listModels(selectedProvider);
      setLiveModels(result);
      if (result.default_model) setSelectedModel(result.default_model);
      toast.success(
        result.source === 'live'
          ? `Đã lấy ${result.models.length} model trực tiếp từ ${PROVIDER_CONFIGS[selectedProvider].name}.`
          : 'Nhà cung cấp không cho liệt kê model — dùng danh sách dự phòng.'
      );
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không lấy được danh sách model');
    } finally {
      setIsLoadingModels(false);
    }
  }, [selectedProvider, toast]);

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
          onClick={() => setActiveTab('chains')}
          className={`flex items-center gap-2 px-5 py-3 font-medium text-sm border-b-2 transition-all ${
            activeTab === 'chains'
              ? 'border-indigo-600 text-indigo-600 font-semibold'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
          }`}
        >
          <Route className="w-4 h-4" />
          Chuỗi AI (Fallback)
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

                {/* Model Selection (Free-text Input + Quick Suggestions) */}
                <div>
                  <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
                    <label htmlFor="byok-custom-model-input" className="block text-sm font-semibold text-slate-700">
                      Tên Mô hình AI ({PROVIDER_CONFIGS[selectedProvider].name} — Tự nhập hoặc chọn nhanh)
                    </label>
                    <button
                      type="button"
                      onClick={handleFetchModels}
                      disabled={isLoadingModels}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-60"
                    >
                      {isLoadingModels ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <RefreshCw className="w-3.5 h-3.5" />
                      )}
                      {isLoadingModels ? 'Đang hỏi nhà cung cấp...' : 'Đồng bộ danh sách từ API'}
                    </button>
                  </div>

                  {/* Ô tự nhập tên Model bất kỳ cho nhẹ & linh hoạt tuyệt đối */}
                  <div className="mb-3">
                    <input
                      id="byok-custom-model-input"
                      type="text"
                      list="byok-model-suggestions"
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      placeholder={`Nhập mã model bất kỳ của ${PROVIDER_CONFIGS[selectedProvider].name} (VD: ${PROVIDER_CONFIGS[selectedProvider].models[0]?.id || 'gemini-2.5-flash'})`}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm bg-white shadow-sm"
                    />
                    <datalist id="byok-model-suggestions">
                      {PROVIDER_CONFIGS[selectedProvider].models.map((m) => (
                        <option key={`dl-${m.id}`} value={m.id}>{m.name} — {m.badge}</option>
                      ))}
                      {liveModels && liveModels.provider === selectedProvider && liveModels.models.map((id) => (
                        <option key={`dl-live-${id}`} value={id}>{id}</option>
                      ))}
                    </datalist>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Bạn có thể tự gõ trực tiếp bất kỳ mã model nào (kể cả model mới phát hành hoặc fine-tune riêng), hoặc bấm chọn nhanh gợi ý bên dưới.
                    </p>
                  </div>

                  {liveModels && liveModels.provider === selectedProvider && (
                    <p className="text-xs text-slate-500 mb-2">
                      {liveModels.source === 'live' ? (
                        <>
                          <span className="font-semibold text-emerald-700">Danh sách lấy trực tiếp từ nhà cung cấp</span>
                          {' '}· {liveModels.models.length} model.
                        </>
                      ) : (
                        <>
                          <span className="font-semibold text-amber-700">Nhà cung cấp không cho liệt kê</span>
                          {' '}· đang dùng danh sách dự phòng bên trong hệ thống.
                        </>
                      )}
                      {liveModels.free_tier && liveModels.free_note && (
                        <span className="ml-1 text-indigo-600">Tầng free: {liveModels.free_note}.</span>
                      )}
                    </p>
                  )}

                  {/* Model lấy động: hiển thị TRƯỚC danh sách gợi ý tĩnh. */}
                  {liveModels && liveModels.provider === selectedProvider && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {liveModels.models.slice(0, 24).map((id) => (
                        <button
                          key={`live-${id}`}
                          type="button"
                          aria-pressed={selectedModel === id}
                          onClick={() => setSelectedModel(id)}
                          className={`px-2.5 py-1 rounded-full border text-xs font-mono transition-all ${
                            selectedModel === id
                              ? 'border-indigo-600 bg-indigo-50 text-indigo-800'
                              : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                          }`}
                        >
                          {id}
                        </button>
                      ))}
                    </div>
                  )}

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
                          <span className="font-bold text-sm text-slate-900 min-w-0 font-mono">{m.name}</span>
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
        <div className="space-y-6">
          {/* Card 1: Hồ sơ cá nhân & Đổi mật khẩu */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
            <div className="flex items-center gap-4 pb-6 border-b border-slate-100">
              <div className="w-16 h-16 rounded-2xl bg-[#121316] text-white font-bold text-2xl flex items-center justify-center shadow-sm">
                {currentUser?.full_name ? currentUser.full_name[0].toUpperCase() : 'U'}
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">{currentUser?.full_name || 'Người dùng MarketFlow'}</h2>
                <p className="text-slate-500 text-sm">{currentUser?.email || 'manager@gmail.com'}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="px-2.5 py-0.5 bg-[#FFF3EE] text-[#D95D39] border border-[#F5D0C5] text-xs font-bold rounded-full uppercase">
                    {currentUser?.role || 'MANAGER'}
                  </span>
                  <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-medium rounded-full">
                    {currentUser?.status || 'ACTIVE'}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div className="p-4 bg-[#F6F5F0] rounded-xl border border-slate-200">
                <span className="text-slate-500 text-xs block mb-1">Mã định danh Người dùng</span>
                <span className="font-mono font-bold text-slate-800">#{currentUser?.id || 1}</span>
              </div>
              <div className="p-4 bg-[#F6F5F0] rounded-xl border border-slate-200">
                <span className="text-slate-500 text-xs block mb-1">Cấp độ Quyền hạn hiện tại</span>
                <span className="font-semibold text-slate-800">
                  {isManagerOrAdmin
                    ? 'Quản lý Chiến dịch — Được cấp phát tài khoản & duyệt bài'
                    : currentUser?.role === 'CLIENT_APPROVER'
                      ? 'Khách hàng Duyệt bài — Được phê duyệt / trả bài'
                      : 'Chuyên viên Nội dung — Soạn thảo & gửi duyệt'}
                </span>
              </div>
              <div className="p-4 bg-[#F6F5F0] rounded-xl border border-slate-200">
                <span className="text-slate-500 text-xs block mb-1">Cơ chế Tạo tài khoản (RBAC 2-Tầng)</span>
                <span className="font-semibold text-slate-800">
                  Tự đăng ký = <code className="text-xs bg-white px-1.5 py-0.5 rounded border">MARKETER</code> · Quản lý cấp quyền cao hơn
                </span>
              </div>
            </div>

            {/* Đổi mật khẩu — thu hồi mọi phiên đang mở ở các thiết bị khác */}
            <form
              onSubmit={handlePasswordSubmit}
              className="pt-6 border-t border-slate-100 space-y-4"
            >
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#0F766E]" />
                  Đổi mật khẩu cá nhân
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Sau khi đổi, mọi phiên đăng nhập khác sẽ bị thu hồi và phải đăng nhập lại.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Mật khẩu hiện tại"
                  className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  required
                />
                <input
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Mật khẩu mới (tối thiểu 6 ký tự)"
                  className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  required
                  minLength={6}
                />
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Nhập lại mật khẩu mới"
                  className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  required
                />
              </div>
              {passwordError && (
                <p className="text-xs text-red-600">{passwordError}</p>
              )}
              <button
                type="submit"
                disabled={isChangingPassword}
                className="inline-flex items-center gap-2 px-4 py-2 bg-[#121316] text-white text-sm font-semibold rounded-lg hover:bg-slate-800 disabled:opacity-50"
              >
                {isChangingPassword && <Loader2 className="w-4 h-4 animate-spin" />}
                Cập nhật mật khẩu
              </button>
            </form>
          </div>

          {/* Card 2: Kiến trúc Phân quyền 2-Tầng & Cấp phát Tài khoản Nhân sự */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#F6F5F0]/60">
              <div>
                <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-[#D95D39] mb-1">
                  <Lock className="w-3.5 h-3.5" />
                  Phân quyền Tạo Tài khoản Hợp lý (Zero Privilege Escalation)
                </div>
                <h3 className="text-lg font-bold text-slate-900">
                  Quản trị Nhân sự & Cấp phát Tài khoản theo Vai trò (RBAC)
                </h3>
                <p className="text-xs text-slate-600 mt-1 max-w-3xl leading-relaxed">
                  Để bảo mật hệ thống, người lạ tự đăng ký ngoài trang chủ chỉ nhận quyền <strong>MARKETER (Chuyên viên Nội dung)</strong>.
                  Chỉ <strong>Quản lý chiến dịch (MANAGER)</strong> hoặc <strong>Chủ sở hữu Workspace</strong> mới có quyền tạo tài khoản mới với vai trò
                  <strong> MANAGER</strong>, <strong>CLIENT_APPROVER (Khách hàng duyệt bài)</strong> hoặc nâng/hạ quyền thành viên tại đây.
                </p>
              </div>
              <button
                type="button"
                onClick={() => void loadMembers()}
                className="self-start sm:self-center inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingMembers ? 'animate-spin' : ''}`} />
                Làm mới
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Ma trận 3 vai trò chuẩn */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-4 rounded-xl border border-slate-200 bg-[#F6F5F0]/40">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-[#D95D39]">MANAGER</span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-[#FFF3EE] text-[#D95D39]">Toàn quyền</span>
                  </div>
                  <div className="font-bold text-sm text-slate-900 mb-1">Quản lý Chiến dịch</div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Khởi tạo chiến dịch, phân bổ ngân sách, cấu hình khóa AI BYOK, phê duyệt bài viết và cấp phát tài khoản nhân sự.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-[#F6F5F0]/40">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-[#0F766E]">MARKETER</span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-teal-50 text-[#0F766E]">Mặc định khi tự đăng ký</span>
                  </div>
                  <div className="font-bold text-sm text-slate-900 mb-1">Chuyên viên Nội dung</div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Sử dụng Xưởng AI đa kênh, kiểm tra mùi AI & chính sách quảng cáo, soạn bản nháp và gửi vào hàng đợi chờ duyệt.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-[#F6F5F0]/40">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-800">CLIENT_APPROVER</span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800">Do Quản lý cấp</span>
                  </div>
                  <div className="font-bold text-sm text-slate-900 mb-1">Khách hàng Duyệt bài</div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Kiểm tra chất lượng bài viết, đối chiếu quy tắc thương hiệu, bấm Duyệt xuất bản hoặc Yêu cầu chỉnh sửa.
                  </p>
                </div>
              </div>

              {/* Form tạo tài khoản mới — chỉ hiển thị thao tác cho MANAGER / ADMIN / Owner */}
              {isManagerOrAdmin ? (
                <form
                  onSubmit={handleProvisionAccount}
                  className="p-5 rounded-xl border border-slate-200 bg-[#F6F5F0]/70 space-y-4"
                >
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <UserPlus className="w-4 h-4 text-[#D95D39]" />
                      <h4 className="text-sm font-bold text-slate-900">
                        Cấp phát Tài khoản Mới hoặc Gán Quyền theo Email
                      </h4>
                    </div>
                    <span className="text-[11px] text-slate-500">
                      Tài khoản tạo tại đây đăng nhập được ngay lập tức tại màn hình Đăng nhập
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Họ và tên nhân sự</label>
                      <input
                        type="text"
                        value={provFullName}
                        onChange={(e) => setProvFullName(e.target.value)}
                        placeholder="VD: Nguyễn Minh Anh"
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Email đăng nhập</label>
                      <input
                        type="email"
                        value={provEmail}
                        onChange={(e) => setProvEmail(e.target.value)}
                        placeholder="minhanh@company.vn"
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Mật khẩu khởi tạo</label>
                      <input
                        type="password"
                        value={provPassword}
                        onChange={(e) => setProvPassword(e.target.value)}
                        placeholder="Tối thiểu 6 ký tự"
                        minLength={6}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Vai trò phân quyền (Role)</label>
                      <select
                        value={provRole}
                        onChange={(e) => setProvRole(e.target.value as 'MANAGER' | 'MARKETER' | 'CLIENT_APPROVER')}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900"
                      >
                        <option value="MARKETER">MARKETER — Chuyên viên Nội dung</option>
                        <option value="CLIENT_APPROVER">CLIENT_APPROVER — Khách hàng Duyệt bài</option>
                        <option value="MANAGER">MANAGER — Quản lý Chiến dịch</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center justify-between flex-wrap gap-3 pt-1">
                    <p className="text-xs text-slate-500">
                      Mẹo: Nếu email đã tồn tại trong hệ thống, thao tác này sẽ tự động cập nhật vai trò mới và thêm vào Workspace hiện tại.
                    </p>
                    <button
                      type="submit"
                      disabled={isProvisioning}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#D95D39] hover:bg-[#C04E2C] text-white text-sm font-semibold transition-colors disabled:opacity-50 shadow-sm"
                    >
                      {isProvisioning ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                      Tạo Tài Khoản & Gán Quyền
                    </button>
                  </div>
                </form>
              ) : (
                <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/70 text-xs text-amber-900 flex items-center gap-2.5">
                  <Lock className="w-4 h-4 text-amber-700 shrink-0" />
                  <span>
                    Bạn đang đăng nhập với vai trò <strong>{currentUser?.role}</strong>. Chỉ tài khoản <strong>MANAGER</strong> hoặc Chủ sở hữu Workspace mới có quyền tạo tài khoản mới và thay đổi phân quyền nhân sự.
                  </span>
                </div>
              )}

              {/* Bảng danh sách thành viên trong Workspace */}
              {membersError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{membersError}</span>
                </div>
              )}

              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[#F6F5F0] text-slate-600 uppercase text-[11px] font-bold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Nhân sự</th>
                      <th className="px-4 py-3">Email đăng nhập</th>
                      <th className="px-4 py-3">Vai trò hiện tại</th>
                      <th className="px-4 py-3">Trạng thái</th>
                      <th className="px-4 py-3 text-right">Điều chỉnh Phân quyền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {isLoadingMembers && members.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-xs text-slate-400">
                          Đang tải danh sách nhân sự Workspace...
                        </td>
                      </tr>
                    ) : members.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-xs text-slate-400">
                          Chưa có thành viên nào trong danh sách.
                        </td>
                      </tr>
                    ) : (
                      members.map((m) => {
                        const effectiveRole =
                          m.system_role === 'MANAGER' || m.workspace_role === 'AGENCY_MANAGER'
                            ? 'MANAGER'
                            : m.system_role === 'CLIENT_APPROVER' || m.workspace_role === 'CLIENT_APPROVER'
                              ? 'CLIENT_APPROVER'
                              : 'MARKETER';
                        return (
                          <tr key={`${m.user_id}-${m.id}`} className="hover:bg-slate-50/70 transition-colors">
                            <td className="px-4 py-3.5 font-semibold text-slate-900 flex items-center gap-2.5">
                              <div className="w-8 h-8 rounded-lg bg-slate-900 text-white text-xs font-bold flex items-center justify-center shrink-0">
                                {(m.full_name || m.email || 'U')[0].toUpperCase()}
                              </div>
                              <div>
                                <div className="flex items-center gap-1.5">
                                  <span>{m.full_name}</span>
                                  {m.is_owner && (
                                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold">
                                      <Crown className="w-3 h-3" />
                                      Owner
                                    </span>
                                  )}
                                </div>
                                <span className="text-[11px] text-slate-400 font-normal">ID #{m.user_id}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3.5 font-mono text-xs text-slate-700">{m.email}</td>
                            <td className="px-4 py-3.5">
                              <span
                                className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                                  effectiveRole === 'MANAGER'
                                    ? 'bg-[#FFF3EE] text-[#D95D39] border border-[#F5D0C5]'
                                    : effectiveRole === 'CLIENT_APPROVER'
                                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                                      : 'bg-teal-50 text-[#0F766E] border border-teal-200'
                                }`}
                              >
                                {effectiveRole}
                              </span>
                            </td>
                            <td className="px-4 py-3.5">
                              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-medium rounded-full">
                                {m.status || 'ACTIVE'}
                              </span>
                            </td>
                            <td className="px-4 py-3.5 text-right">
                              {isManagerOrAdmin && !m.is_owner ? (
                                <div className="inline-flex items-center gap-2">
                                  <select
                                    aria-label={`Đổi vai trò của ${m.email}`}
                                    disabled={updatingUserId === m.user_id}
                                    value={effectiveRole}
                                    onChange={(e) =>
                                      void handleRoleChange(
                                        m,
                                        e.target.value as 'MANAGER' | 'MARKETER' | 'CLIENT_APPROVER',
                                      )
                                    }
                                    className="px-2.5 py-1 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900"
                                  >
                                    <option value="MARKETER">MARKETER</option>
                                    <option value="CLIENT_APPROVER">CLIENT_APPROVER</option>
                                    <option value="MANAGER">MANAGER</option>
                                  </select>
                                  <button
                                    type="button"
                                    disabled={updatingUserId === m.user_id}
                                    onClick={() => void handleRemoveMember(m)}
                                    className="p-1.5 rounded-lg border border-rose-200 text-rose-600 hover:bg-rose-50 transition-colors"
                                    title="Gỡ khỏi Workspace"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <span className="text-xs text-slate-400">
                                  {m.is_owner ? 'Chủ sở hữu cố định' : 'Chỉ xem'}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Workspace */}
      {activeTab === 'workspace' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center justify-between pb-6 border-b border-slate-100">
            <div>
              <span className="text-xs font-bold text-[#D95D39] uppercase tracking-wider block mb-1">
                Không gian làm việc hiện tại
              </span>
              <h2 className="text-xl font-bold text-slate-900">{currentWorkspace?.name || 'Default Agency Workspace'}</h2>
              <p className="text-slate-500 text-sm mt-0.5">{currentWorkspace?.description || 'Không gian làm việc điều phối chiến dịch tiếp thị'}</p>
            </div>
            <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full">
              {currentWorkspace?.status || 'ACTIVE'}
            </span>
          </div>

          <div className="p-4 bg-[#F6F5F0] rounded-xl border border-slate-200 text-sm space-y-2">
            <div className="font-bold text-slate-800 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-[#0F766E]" />
              Cách ly Dữ liệu Đa khách hàng (Multi-Tenancy Isolation)
            </div>
            <p className="text-slate-600 text-xs leading-relaxed">
              Mỗi Workspace sở hữu Tờ giấy Quy tắc Thương hiệu (Brand Kit), Chiến dịch, Hàng đợi Duyệt bài và Khóa AI BYOK tách biệt hoàn toàn.
              Để thêm nhân sự hoặc cấp phát tài khoản mới cho Workspace này, chuyển sang tab{' '}
              <button
                type="button"
                onClick={() => setActiveTab('profile')}
                className="font-bold text-[#D95D39] underline hover:opacity-80"
              >
                Hồ sơ & Phân quyền RBAC
              </button>
              .
            </p>
          </div>
        </div>
      )}

      {/* Tab: Chuỗi AI (Fallback kiểu 9Router) */}
      {activeTab === 'chains' && (
        <div className="space-y-6">
          {/* Giải thích cơ chế */}
          <div className="bg-slate-900 text-slate-200 p-5 rounded-2xl border border-slate-800 text-xs space-y-2">
            <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
              <Route className="w-4 h-4 text-indigo-400" />
              Chuỗi Fallback Model (kiểu 9Router)
            </div>
            <p className="text-slate-300 leading-relaxed">
              Một chuỗi là danh sách có thứ tự các bước <strong>(nhà cung cấp, model)</strong>. Khi gọi AI,
              hệ thống thử lần lượt từng bước: bước nào lỗi (hết hạn mức, sai cấu trúc, sự cố mạng) thì chuyển
              bước kế tiếp. Chỉ khi <strong>hết chuỗi</strong> mới rơi về nội dung Smart Fallback mẫu.
              Chuỗi đặt làm <strong>mặc định</strong> được dùng tự động cho mọi request trong phạm vi của nó
              (workspace hoặc cá nhân) khi không truyền chuỗi tường minh.
            </p>
          </div>

          {/* Form tạo chuỗi */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-900">Tạo chuỗi mới</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Chọn thứ tự nhà cung cấp — model để trống sẽ dùng model mặc định của nhà cung cấp đó.
              </p>
            </div>
            <form onSubmit={handleCreateChain} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Tên chuỗi</label>
                <input
                  type="text"
                  value={chainName}
                  onChange={e => setChainName(e.target.value)}
                  maxLength={100}
                  placeholder="VD: Chuỗi Vip (Gemini -> OpenAI -> OpenRouter)"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-semibold text-slate-700">Các bước (thứ tự ưu tiên)</label>
                {chainHops.map((hop, idx) => (
                  <div key={idx} className="flex items-center gap-2 flex-wrap">
                    <span className="w-7 h-7 shrink-0 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <select
                      value={hop.provider}
                      onChange={e => {
                        const next = [...chainHops];
                        next[idx] = { ...hop, provider: e.target.value };
                        setChainHops(next);
                      }}
                      className="px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      {Object.entries(PROVIDER_CONFIGS).map(([slug, cfg]) => (
                        <option key={slug} value={slug}>{cfg.name}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      value={hop.model}
                      onChange={e => {
                        const next = [...chainHops];
                        next[idx] = { ...hop, model: e.target.value };
                        setChainHops(next);
                      }}
                      placeholder={`Model (để trống = mặc định của ${hop.provider})`}
                      className="flex-1 min-w-[220px] px-3 py-2 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    {chainHops.length > 1 && (
                      <button
                        type="button"
                        onClick={() => setChainHops(chainHops.filter((_, i) => i !== idx))}
                        className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        title="Bỏ bước này"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setChainHops([...chainHops, { provider: 'openai', model: '' }])}
                  disabled={chainHops.length >= 10}
                  className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Thêm bước (tối đa 10)
                </button>
              </div>

              <button
                type="submit"
                disabled={isSavingChain}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {isSavingChain ? <Loader2 className="w-4 h-4 animate-spin" /> : <Route className="w-4 h-4" />}
                Lưu chuỗi
              </button>
            </form>
          </div>

          {/* Danh sách chuỗi */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Danh sách chuỗi</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Chuỗi mặc định (ngôi sao) được dùng tự động khi request không chọn chuỗi.
                </p>
              </div>
              <button
                onClick={() => void loadChains()}
                className="p-2 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                title="Tải lại"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingChains ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {chainsError && (
              <div className="mx-6 mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {chainsError}
              </div>
            )}

            {isLoadingChains && chains.length === 0 ? (
              <div className="p-10 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Đang tải danh sách chuỗi...
              </div>
            ) : !isLoadingChains && chains.length === 0 && !chainsError ? (
              <div className="p-10 text-center text-slate-400 text-sm">
                Chưa có chuỗi nào. Tạo chuỗi đầu tiên ở phía trên để bắt đầu failover đa nhà cung cấp.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {chains.map(chain => (
                  <div key={chain.id} className="p-5 flex items-start gap-4 flex-wrap">
                    <div className="flex-1 min-w-[260px] space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-slate-900">{chain.name}</span>
                        {chain.is_default && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold uppercase tracking-wide">
                            <Star className="w-3 h-3 fill-current" />
                            Mặc định
                          </span>
                        )}
                        {!chain.is_active && (
                          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold uppercase tracking-wide">
                            Đang tắt
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold uppercase tracking-wide">
                          {chain.scope === 'workspace' ? 'Workspace' : 'Cá nhân'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {chain.hops.map((hop, idx) => (
                          <React.Fragment key={`${chain.id}-hop-${idx}`}>
                            {idx > 0 && <ArrowDown className="w-3.5 h-3.5 text-slate-300 rotate-[-90deg]" />}
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
                              <span className="font-bold text-slate-400">{idx + 1}.</span>
                              {hop.provider}
                              <span className="text-slate-400">/</span>
                              <code className="text-[11px]">{hop.model}</code>
                            </span>
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {!chain.is_default && chain.is_active && (
                        <button
                          onClick={() => void handleSetDefaultChain(chain)}
                          className="p-2 rounded-lg text-slate-400 hover:text-amber-600 hover:bg-amber-50 transition-colors"
                          title="Đặt làm chuỗi mặc định"
                        >
                          <Star className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => void handleToggleChain(chain)}
                        className={`p-2 rounded-lg transition-colors ${
                          chain.is_active
                            ? 'text-emerald-600 hover:bg-emerald-50'
                            : 'text-slate-400 hover:bg-slate-50'
                        }`}
                        title={chain.is_active ? 'Tắt chuỗi' : 'Bật chuỗi'}
                      >
                        <Power className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => void handleDeleteChain(chain)}
                        className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        title="Xóa chuỗi"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
