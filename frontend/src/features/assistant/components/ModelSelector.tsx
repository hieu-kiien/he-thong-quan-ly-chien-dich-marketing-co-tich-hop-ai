import { useEffect, useState } from 'react';
import { Check, ChevronDown, Cpu, Sparkles, Zap } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Popover } from '@/components/ui';

export interface AiModelOption {
  id: string;
  label: string;
  shortLabel: string;
  provider: string;
  badge: string;
  description: string;
  group: 'auto' | 'opencode' | 'groq' | 'nvidia' | 'google';
}

export const AI_PROVIDER_PILLS = [
  { id: 'opencode', name: 'OpenCode Free' },
  { id: 'groq', name: 'Qwen / Groq' },
  { id: 'nvidia', name: 'NVIDIA NIM' },
  { id: 'google', name: 'Google Gemini' },
  { id: 'openrouter', name: 'OpenRouter' },
] as const;

export const AI_MODEL_OPTIONS: AiModelOption[] = [
  {
    id: '',
    label: 'Tự động điều phối đa mô hình',
    shortLabel: 'Tự động (Đa mô hình)',
    provider: '5 nền tảng',
    badge: 'Khuyên dùng',
    description: 'Ưu tiên OpenCode Zen mới nhất; tự động chuyển sang Groq, NVIDIA NIM, Gemini trong 0ms khi chạm giới hạn.',
    group: 'auto',
  },
  {
    id: 'opencode/deepseek-v4.1-flash-free',
    label: 'DeepSeek V4.1 Flash',
    shortLabel: 'DeepSeek V4.1 Flash',
    provider: 'OpenCode Free',
    badge: 'Ưu tiên #1',
    description: 'Thế hệ V4.1 mới nhất trên OpenCode Zen — lập luận chiến lược & phân tích số liệu sắc bén.',
    group: 'opencode',
  },
  {
    id: 'opencode/glm-5.3-flash-free',
    label: 'GLM 5.3 Flash',
    shortLabel: 'GLM 5.3 Flash',
    provider: 'OpenCode Free',
    badge: 'Mới nhất',
    description: 'Thế hệ GLM 5.3 — tối ưu văn phong tiếng Việt, cấu trúc nội dung & kế hoạch marketing.',
    group: 'opencode',
  },
  {
    id: 'opencode/mimo-v2.6-flash-free',
    label: 'Xiaomi MiMo V2.6 Flash',
    shortLabel: 'MiMo V2.6 Flash',
    provider: 'OpenCode Free',
    badge: 'Nhanh',
    description: 'Mô hình MiMo V2.6 tốc độ cao cho các tác vụ tra cứu công cụ và soạn thảo nhanh.',
    group: 'opencode',
  },
  {
    id: 'groq/openai/gpt-oss-120b',
    label: 'GPT-OSS 120B (Groq LPU)',
    shortLabel: 'GPT-OSS 120B',
    provider: 'Groq LPU',
    badge: '~2.8s • 120B',
    description: 'Đại mô hình 120 tỷ tham số chạy trên phần cứng Groq LPU — thông minh vượt trội, phản hồi tức thì.',
    group: 'groq',
  },
  {
    id: 'groq/qwen/qwen3.8-27b',
    label: 'Qwen 3.8 27B',
    shortLabel: 'Qwen 3.8 27B',
    provider: 'Qwen / Groq',
    badge: 'Qwen 3.8',
    description: 'Thế hệ Qwen 3.8 mới nhất — tiếng Việt tự nhiên, lập kế hoạch và viết bài quảng cáo mượt mà.',
    group: 'groq',
  },
  {
    id: 'groq/openai/gpt-oss-20b',
    label: 'GPT-OSS 20B (Groq LPU)',
    shortLabel: 'GPT-OSS 20B',
    provider: 'Groq LPU',
    badge: 'Siêu tốc',
    description: 'Phiên bản 20B tối ưu độ trễ thấp cho hội thoại tương tác liên tục.',
    group: 'groq',
  },
  {
    id: 'openrouter/nvidia/nemotron-3.5-super-vl:free',
    label: 'NVIDIA Nemotron 3.5 Super VL',
    shortLabel: 'Nemotron 3.5 Super',
    provider: 'NVIDIA NIM',
    badge: 'Nemotron 3.5',
    description: 'Mô hình NVIDIA Nemotron 3.5 Super chuyên sâu phân tích dữ liệu KPI và tối ưu ngân sách.',
    group: 'nvidia',
  },
  {
    id: 'openrouter/nvidia/nemotron-3-ultra-550b-a55b:free',
    label: 'NVIDIA Nemotron 3 Ultra 550B',
    shortLabel: 'Nemotron Ultra 550B',
    provider: 'NVIDIA NIM',
    badge: '550B MoE',
    description: 'Kiến trúc MoE 550 tỷ tham số của NVIDIA cho bài toán hoạch định chiến dịch phức tạp.',
    group: 'nvidia',
  },
  {
    id: 'openrouter/nvidia/nemotron-3.5-lightning:free',
    label: 'NVIDIA Nemotron 3.5 Lightning',
    shortLabel: 'Nemotron 3.5 Lightning',
    provider: 'NVIDIA NIM',
    badge: 'Tốc độ cao',
    description: 'Phiên bản Lightning tối ưu tốc độ sinh văn bản của dòng Nemotron 3.5.',
    group: 'nvidia',
  },
  {
    id: 'openrouter/thinkingmachines/inkling:free',
    label: 'ThinkingMachines Inkling',
    shortLabel: 'TM Inkling',
    provider: 'OpenRouter',
    badge: 'Sáng tạo',
    description: 'Mô hình chuyên sâu sáng tạo thông điệp thương hiệu & nội dung đa kênh.',
    group: 'nvidia',
  },
  {
    id: 'openrouter/thinkingmachines/inkling-small:free',
    label: 'ThinkingMachines Inkling Small',
    shortLabel: 'TM Inkling Small',
    provider: 'OpenRouter',
    badge: 'Gọn nhẹ',
    description: 'Phiên bản gọn nhẹ, phản hồi nhanh trên hạ tầng OpenRouter Free.',
    group: 'nvidia',
  },
  {
    id: 'google/gemini-3.5-flash-lite',
    label: 'Google Gemini 3.5 Flash Lite',
    shortLabel: 'Gemini 3.5 Flash',
    provider: 'Google Gemini',
    badge: 'Gemini 3.5',
    description: 'Mô hình Gemini 3.5 thế hệ mới của Google, hỗ trợ ngữ cảnh dài và đa ngôn ngữ.',
    group: 'google',
  },
  {
    id: 'google/gemini-3.1-flash-lite',
    label: 'Google Gemini 3.1 Flash Lite',
    shortLabel: 'Gemini 3.1 Flash',
    provider: 'Google Gemini',
    badge: 'Ổn định',
    description: 'Mô hình dự phòng ổn định trên hạ tầng Google AI Studio.',
    group: 'google',
  },
];

const MODEL_STORAGE_KEY = 'mf.ai.selected_model';
let currentSelectedModel: string = (() => {
  try {
    return localStorage.getItem(MODEL_STORAGE_KEY) || '';
  } catch {
    return '';
  }
})();

const modelListeners = new Set<() => void>();

export function getSelectedAiModel(): string {
  return currentSelectedModel;
}

export function setSelectedAiModel(modelId: string): void {
  currentSelectedModel = modelId;
  try {
    if (modelId) {
      localStorage.setItem(MODEL_STORAGE_KEY, modelId);
    } else {
      localStorage.removeItem(MODEL_STORAGE_KEY);
    }
  } catch {
    // Bỏ qua nếu trình duyệt chặn localStorage
  }
  modelListeners.forEach((fn) => fn());
}

export function useSelectedAiModel() {
  const [, setTick] = useState(0);
  useEffect(() => {
    const fn = () => setTick((t) => t + 1);
    modelListeners.add(fn);
    return () => {
      modelListeners.delete(fn);
    };
  }, []);
  const selected = AI_MODEL_OPTIONS.find((m) => m.id === currentSelectedModel) ?? AI_MODEL_OPTIONS[0];
  return {
    selectedModelId: currentSelectedModel,
    selectedModel: selected,
    setSelectedModelId: setSelectedAiModel,
  };
}

const GROUP_LABELS: Record<AiModelOption['group'], string> = {
  auto: 'Điều phối thông minh',
  opencode: 'OpenCode Free (Ưu tiên số 1 • Thế hệ mới nhất)',
  groq: 'Qwen & OpenAI OSS trên Groq LPU (Tốc độ ~2.8s)',
  nvidia: 'NVIDIA NIM & OpenRouter Free (Siêu mô hình)',
  google: 'Google Gemini (Dự phòng ổn định)',
};

export function ModelSelector({ compact = false }: { compact?: boolean }) {
  const { selectedModelId, selectedModel, setSelectedModelId } = useSelectedAiModel();

  const groups: AiModelOption['group'][] = ['auto', 'opencode', 'groq', 'nvidia', 'google'];

  return (
    <Popover
      label="Chọn mô hình AI"
      className="w-[22rem] p-0 sm:w-[25rem]"
      trigger={(props) => (
        <button
          type="button"
          {...props}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-lg border border-border bg-subtle/60 px-2.5 py-1 text-xs font-medium text-fg transition-colors hover:border-border-strong hover:bg-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
            compact && 'px-2 py-1 text-[11px]',
          )}
          title={`Mô hình đang chọn: ${selectedModel.label} (${selectedModel.provider})`}
        >
          <Cpu className="h-3.5 w-3.5 shrink-0 text-ai" aria-hidden />
          <span className="max-w-[130px] truncate sm:max-w-[165px]">{selectedModel.shortLabel}</span>
          <span className="hidden rounded bg-ai-soft px-1.5 py-0.5 text-[10px] font-semibold text-ai md:inline">
            {selectedModel.provider}
          </span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-fg-subtle" aria-hidden />
        </button>
      )}
    >
      {(close) => (
        <div className="flex max-h-[28rem] flex-col overflow-hidden">
          {/* Header: FREE FOREVER • 5 NỀN TẢNG */}
          <div className="border-b border-border bg-subtle/50 px-3.5 py-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-success" aria-hidden />
                <span className="text-[11px] font-bold tracking-wider text-success uppercase">
                  Miễn phí vĩnh viễn
                </span>
                <span className="text-xs text-fg-subtle">•</span>
                <span className="text-xs font-medium text-fg-muted">5 nhà cung cấp (13 mô hình)</span>
              </div>
              <Sparkles className="h-3.5 w-3.5 text-ai" aria-hidden />
            </div>

            <div className="mt-2 flex flex-wrap gap-1.5">
              {AI_PROVIDER_PILLS.map((p) => (
                <span
                  key={p.id}
                  className="inline-flex items-center rounded-md border border-border bg-surface px-2 py-0.5 text-[11px] font-medium text-fg-muted shadow-2xs"
                >
                  {p.name}
                </span>
              ))}
            </div>
          </div>

          {/* Danh sách lựa chọn mô hình */}
          <div className="flex-1 overflow-y-auto p-2 space-y-3">
            {groups.map((grp) => {
              const items = AI_MODEL_OPTIONS.filter((m) => m.group === grp);
              return (
                <div key={grp}>
                  <p className="px-2 pb-1 text-[10px] font-bold tracking-wider text-fg-subtle uppercase">
                    {GROUP_LABELS[grp]}
                  </p>
                  <div className="space-y-1">
                    {items.map((item) => {
                      const active = item.id === selectedModelId;
                      return (
                        <button
                          key={item.id || 'auto'}
                          type="button"
                          onClick={() => {
                            setSelectedModelId(item.id);
                            close();
                          }}
                          className={cn(
                            'flex w-full items-start justify-between gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors',
                            active
                              ? 'bg-accent-soft/70 text-fg ring-1 ring-accent/30'
                              : 'hover:bg-subtle text-fg',
                          )}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-xs font-semibold text-fg">{item.label}</span>
                              <span className="rounded bg-subtle px-1.5 py-0.5 text-[10px] font-medium text-fg-muted">
                                {item.badge}
                              </span>
                            </div>
                            <p className="mt-0.5 text-[11px] leading-snug text-fg-muted">
                              {item.description}
                            </p>
                          </div>
                          <div className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                            {active ? (
                              <Check className="h-4 w-4 text-accent" aria-hidden />
                            ) : item.group === 'opencode' || item.group === 'groq' ? (
                              <Zap className="h-3.5 w-3.5 text-fg-subtle/60" aria-hidden />
                            ) : null}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Popover>
  );
}
