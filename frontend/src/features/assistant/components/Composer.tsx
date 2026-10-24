import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowUp,
  Megaphone,
  Sparkles,
  Square,
  X,
} from 'lucide-react';
import { campaignsApi } from '@/lib/api/endpoints';
import type { CampaignListItem } from '@/lib/types';
import { QUICK_PROMPTS } from '../types';

interface ComposerProps {
  value: string;
  onChange: (val: string) => void;
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  attachedCampaignId?: number | null;
  onSelectCampaign: (campaignId: number | null) => void;
  disabled?: boolean;
}

export function Composer({
  value,
  onChange,
  onSend,
  onStop,
  isStreaming,
  attachedCampaignId,
  onSelectCampaign,
  disabled = false,
}: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showSlashMenu, setShowSlashMenu] = useState(false);
  const [slashSelectedIndex, setSlashSelectedIndex] = useState(0);
  const [showCampaignPicker, setShowCampaignPicker] = useState(false);

  // Lấy danh sách chiến dịch để chọn ngữ cảnh
  const { data: campaignsData } = useQuery({
    queryKey: ['campaigns', 'list-select'],
    queryFn: () => campaignsApi.list({ page_size: 100 }),
    staleTime: 60_000,
  });

  const campaigns = campaignsData?.items || [];
  const currentCampaign = campaigns.find((c: CampaignListItem) => c.id === attachedCampaignId);

  // Tự động co giãn chiều cao của textarea (tối đa 192px)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 192)}px`;
  }, [value]);

  const handleTextChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    onChange(val);

    // Kích hoạt menu lệnh nhanh khi gõ ký tự "/" ở đầu dòng hoặc chuỗi
    if (val === '/' || val.endsWith(' /')) {
      setShowSlashMenu(true);
      setSlashSelectedIndex(0);
    } else if (showSlashMenu && !val.includes('/')) {
      setShowSlashMenu(false);
    }
  };

  const handleApplyTemplate = (template: string) => {
    onChange(template);
    setShowSlashMenu(false);

    // Focus vào textarea và chọn phần placeholder đầu tiên
    setTimeout(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus();
      const firstBracket = template.indexOf('[');
      const closeBracket = template.indexOf(']');
      if (firstBracket !== -1 && closeBracket !== -1) {
        el.setSelectionRange(firstBracket, closeBracket + 1);
      }
    }, 50);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSlashMenu) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSlashSelectedIndex((prev) => (prev + 1) % QUICK_PROMPTS.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSlashSelectedIndex(
          (prev) => (prev - 1 + QUICK_PROMPTS.length) % QUICK_PROMPTS.length,
        );
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        handleApplyTemplate(QUICK_PROMPTS[slashSelectedIndex].template);
        return;
      }
      if (e.key === 'Escape') {
        setShowSlashMenu(false);
        return;
      }
    }

    // Nhấn Enter để gửi (Shift + Enter để xuống dòng)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) return;
      if (value.trim()) {
        onSend(value);
      }
    }
  };

  const handleSubmit = () => {
    if (isStreaming) {
      onStop();
      return;
    }
    if (value.trim()) {
      onSend(value);
    }
  };

  return (
    <div className="relative border-t border-border bg-surface px-4 py-3 sm:px-6">
      {/* Menu popup "/" cho các câu lệnh nhanh */}
      {showSlashMenu && (
        <div
          role="listbox"
          aria-label="Gợi ý câu lệnh nhanh"
          className="absolute bottom-full left-4 mb-2 w-80 max-w-[calc(100vw-2rem)] rounded-lg border border-border bg-surface p-1 shadow-overlay animate-scale-in"
        >
          <div className="px-2.5 py-1.5 text-[11px] font-semibold text-fg-subtle">
            Mẫu prompt nhanh (nhấn Enter để chọn)
          </div>
          {QUICK_PROMPTS.map((prompt, idx) => (
            <button
              key={prompt.id}
              type="button"
              role="option"
              aria-selected={idx === slashSelectedIndex}
              onClick={() => handleApplyTemplate(prompt.template)}
              className={`flex w-full items-start gap-2 rounded-md px-2.5 py-2 text-left text-xs transition-colors ${
                idx === slashSelectedIndex
                  ? 'bg-accent/10 text-accent font-medium'
                  : 'text-fg hover:bg-subtle'
              }`}
            >
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" aria-hidden />
              <div className="min-w-0">
                <div className="font-medium">{prompt.title}</div>
                <div className="truncate text-[11px] text-fg-muted">{prompt.description}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="mx-auto max-w-3xl">
        {/* Thanh công cụ nhỏ phía trên: Ngữ cảnh chiến dịch + Gợi ý nhanh */}
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          {/* Chip ngữ cảnh chiến dịch */}
          <div className="relative flex items-center gap-1.5">
            {currentCampaign ? (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-accent/30 bg-accent-soft px-2.5 py-1 text-xs text-accent-soft-fg">
                <Megaphone className="h-3 w-3 shrink-0" aria-hidden />
                <span className="max-w-[180px] truncate font-medium sm:max-w-[260px]">
                  Ngữ cảnh: {currentCampaign.name}
                </span>
                <button
                  type="button"
                  onClick={() => onSelectCampaign(null)}
                  className="rounded p-0.5 hover:bg-accent/20 focus:outline-none"
                  title="Gỡ bỏ ngữ cảnh chiến dịch"
                  aria-label="Gỡ bỏ ngữ cảnh"
                >
                  <X className="h-3 w-3" aria-hidden />
                </button>
              </span>
            ) : (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowCampaignPicker((prev) => !prev)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-subtle px-2.5 py-1 text-xs text-fg-muted hover:border-border-strong hover:text-fg focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
                >
                  <Megaphone className="h-3 w-3" aria-hidden />
                  <span>Gắn chiến dịch</span>
                </button>

                {showCampaignPicker && (
                  <div className="absolute bottom-full left-0 mb-1 max-h-56 w-64 overflow-y-auto rounded-md border border-border bg-surface p-1 shadow-overlay animate-scale-in z-20">
                    <div className="px-2 py-1 text-[11px] font-semibold text-fg-subtle">
                      Chọn chiến dịch ngữ cảnh
                    </div>
                    {campaigns.length === 0 ? (
                      <div className="px-2 py-2 text-xs text-fg-subtle">Chưa có chiến dịch nào</div>
                    ) : (
                      campaigns.map((c: CampaignListItem) => (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => {
                            onSelectCampaign(c.id);
                            setShowCampaignPicker(false);
                          }}
                          className="flex w-full items-center justify-between truncate rounded px-2 py-1.5 text-left text-xs text-fg hover:bg-subtle"
                        >
                          <span className="truncate">{c.name}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Dải chip gợi ý nhanh (có thể bấm để điền mẫu) */}
          <div className="hidden items-center gap-1.5 sm:flex">
            <span className="text-[11px] text-fg-subtle">{'Gõ "/" hoặc chọn nhanh:'}</span>
            {QUICK_PROMPTS.slice(0, 2).map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => handleApplyTemplate(p.template)}
                className="rounded-md border border-border bg-subtle px-2 py-0.5 text-[11px] text-fg-muted hover:bg-muted/50 hover:text-fg"
              >
                {p.title}
              </button>
            ))}
          </div>
        </div>

        {/* Khung soạn thảo tin nhắn */}
        <div className="relative flex items-end rounded-xl border border-border bg-surface shadow-xs transition-colors focus-within:border-accent focus-within:ring-1 focus-within:ring-accent">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder={
              isStreaming
                ? 'Trợ lý AI đang phản hồi...'
                : 'Nhập câu hỏi hoặc yêu cầu cho Trợ lý AI (Shift + Enter để xuống dòng, gõ / để mở mẫu)...'
            }
            disabled={disabled}
            className="max-h-48 min-h-[44px] flex-1 resize-none bg-transparent px-3.5 py-2.5 text-sm leading-relaxed text-fg placeholder:text-fg-subtle focus:outline-none"
          />

          <div className="flex shrink-0 items-center p-1.5">
            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-danger text-white transition-colors hover:bg-danger-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-danger"
                title="Dừng phản hồi"
                aria-label="Dừng phản hồi"
              >
                <Square className="h-3.5 w-3.5 fill-current" aria-hidden />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!value.trim() || disabled}
                className={`inline-flex h-8 w-8 items-center justify-center rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                  value.trim() && !disabled
                    ? 'bg-accent text-accent-fg hover:bg-accent-hover'
                    : 'cursor-not-allowed bg-subtle text-fg-subtle'
                }`}
                title="Gửi câu lệnh"
                aria-label="Gửi câu lệnh"
              >
                <ArrowUp className="h-4 w-4" aria-hidden />
              </button>
            )}
          </div>
        </div>

        {/* Khuyến cáo bắt buộc dưới khung soạn (§8) */}
        <p className="mt-1.5 text-center text-[11px] text-fg-subtle">
          Nội dung do AI tạo cần được kiểm tra và duyệt trước khi sử dụng.
        </p>
      </div>
    </div>
  );
}
