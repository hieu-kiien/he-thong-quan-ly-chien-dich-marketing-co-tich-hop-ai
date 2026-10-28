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
  Command,
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
    staleTime: 5 * 60_000,
  });

  const campaigns = campaignsData?.items || [];
  const currentCampaign = campaigns.find((c: CampaignListItem) => c.id === attachedCampaignId);

  // Tự động co giãn chiều cao của textarea (ưu tiên CSS field-sizing: content, fallback JS scrollHeight)
  useEffect(() => {
    if (typeof CSS !== 'undefined' && CSS.supports?.('field-sizing', 'content')) {
      return;
    }
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
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
    let resolved = template;
    if (currentCampaign?.name) {
      resolved = resolved
        .replace(/\[Tên chiến dịch\/sản phẩm\]/g, currentCampaign.name)
        .replace(/\[Tên sản phẩm\]/g, currentCampaign.name)
        .replace(/\[Chương trình\/Sản phẩm mới\]/g, currentCampaign.name);
    }
    onChange(resolved);
    setShowSlashMenu(false);

    // Focus vào textarea và chọn phần placeholder đầu tiên (nếu còn)
    setTimeout(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus();
      const firstBracket = resolved.indexOf('[');
      const closeBracket = resolved.indexOf(']');
      if (firstBracket !== -1 && closeBracket !== -1) {
        el.setSelectionRange(firstBracket, closeBracket + 1);
      } else {
        el.setSelectionRange(resolved.length, resolved.length);
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
    <div className="relative shrink-0 bg-gradient-to-t from-canvas via-canvas/95 to-transparent px-4 pb-3 pt-1.5 sm:px-6">
      <div className="relative mx-auto max-w-3xl">
        {/* Menu popup "/" cho các câu lệnh nhanh */}
        {showSlashMenu && (
          <div
            role="listbox"
            aria-label="Gợi ý câu lệnh nhanh"
            className="absolute bottom-full left-0 mb-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-surface p-1.5 shadow-overlay animate-scale-in z-30"
          >
            <div className="flex items-center justify-between px-2.5 py-1.5 text-[11px] font-semibold text-fg-subtle">
              <span>Mẫu câu lệnh nhanh (Enter để chọn)</span>
              <button
                type="button"
                onClick={() => setShowSlashMenu(false)}
                className="rounded p-0.5 hover:bg-subtle hover:text-fg focus:outline-none"
                aria-label="Đóng menu mẫu"
              >
                <X className="h-3 w-3" aria-hidden />
              </button>
            </div>
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={prompt.id}
                type="button"
                role="option"
                aria-selected={idx === slashSelectedIndex}
                onClick={() => handleApplyTemplate(prompt.template)}
                className={`flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition-colors focus:outline-none ${
                  idx === slashSelectedIndex
                    ? 'bg-ai-soft text-ai-soft-fg font-medium'
                    : 'text-fg hover:bg-subtle'
                }`}
              >
                <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ai" aria-hidden />
                <div className="min-w-0">
                  <div className="font-medium">{prompt.title}</div>
                  <div className="truncate text-[11px] text-fg-muted">{prompt.description}</div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Khung soạn thảo hợp nhất kiểu Claude / Notion AI / Linear */}
        <div className="rounded-2xl border border-border-strong/80 bg-surface shadow-sm transition-all focus-within:border-ai focus-within:shadow-md">
          {/* Vùng nhập văn bản */}
          <div className="px-4 pt-3 pb-1">
            <textarea
              ref={textareaRef}
              rows={1}
              value={value}
              onChange={handleTextChange}
              onKeyDown={handleKeyDown}
              placeholder={
                isStreaming
                  ? 'Trợ lý AI đang tổng hợp và phản hồi...'
                  : 'Nhập yêu cầu cho Trợ lý AI (phân tích số liệu, viết nội dung, tối ưu ngân sách)...'
              }
              disabled={disabled}
              className="auto-grow-textarea max-h-44 min-h-[40px] w-full resize-none border-0 bg-transparent p-0 text-sm leading-relaxed text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-0 focus-visible:outline-none"
            />
          </div>

          {/* Thanh công cụ tích hợp ngay đáy thẻ Composer (1 dòng duy nhất, nút Gửi luôn cố định bên phải) */}
          <div className="flex items-center justify-between gap-2 px-3 pb-2.5 pt-1.5">
            {/* Cụm nút bên trái: Ngữ cảnh chiến dịch + Mẫu lệnh nhanh */}
            <div className="flex min-w-0 flex-1 items-center gap-1.5">
              {currentCampaign ? (
                <span className="inline-flex min-w-0 max-w-[180px] items-center gap-1.5 whitespace-nowrap rounded-lg border border-ai/30 bg-ai-soft px-2.5 py-1 text-xs font-medium text-ai-soft-fg sm:max-w-[240px]">
                  <Megaphone className="h-3 w-3 shrink-0" aria-hidden />
                  <span className="min-w-0 truncate" title={currentCampaign.name}>
                    {currentCampaign.name}
                  </span>
                  <button
                    type="button"
                    onClick={() => onSelectCampaign(null)}
                    className="shrink-0 rounded p-0.5 hover:bg-ai/20 focus:outline-none"
                    title="Gỡ bỏ ngữ cảnh chiến dịch"
                    aria-label="Gỡ bỏ ngữ cảnh"
                  >
                    <X className="h-3 w-3" aria-hidden />
                  </button>
                </span>
              ) : (
                <div className="relative shrink-0">
                  <button
                    type="button"
                    onClick={() => setShowCampaignPicker((prev) => !prev)}
                    className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-subtle/70 px-2.5 py-1 text-xs font-medium text-fg-muted transition-colors hover:border-border-strong hover:bg-subtle hover:text-fg focus:outline-none"
                  >
                    <Megaphone className="h-3 w-3 shrink-0 text-ai" aria-hidden />
                    <span>Gắn chiến dịch</span>
                  </button>

                  {showCampaignPicker && (
                    <div className="absolute bottom-full left-0 z-30 mb-1.5 max-h-56 w-64 overflow-y-auto rounded-xl border border-border bg-surface p-1 shadow-overlay animate-scale-in">
                      <div className="px-2.5 py-1.5 text-[11px] font-semibold text-fg-subtle">
                        Chọn chiến dịch ngữ cảnh
                      </div>
                      {campaigns.length === 0 ? (
                        <div className="px-2.5 py-2 text-xs text-fg-subtle">Chưa có chiến dịch nào</div>
                      ) : (
                        campaigns.map((c: CampaignListItem) => (
                          <button
                            key={c.id}
                            type="button"
                            onClick={() => {
                              onSelectCampaign(c.id);
                              setShowCampaignPicker(false);
                            }}
                            className="flex w-full items-center justify-between truncate rounded-lg px-2.5 py-1.5 text-left text-xs text-fg hover:bg-subtle focus:outline-none"
                          >
                            <span className="truncate">{c.name}</span>
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}

              <button
                type="button"
                onClick={() => setShowSlashMenu((prev) => !prev)}
                className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-lg border border-border bg-subtle/70 px-2 py-1 text-xs text-fg-muted transition-colors hover:border-border-strong hover:bg-subtle hover:text-fg focus:outline-none"
                title="Mở danh sách mẫu câu lệnh nhanh"
              >
                <Command className="h-3 w-3 shrink-0 text-fg-subtle" aria-hidden />
                <span>Mẫu lệnh</span>
              </button>

              {!currentCampaign && !value.trim() && (
                <div className="hidden min-w-0 items-center gap-1 overflow-hidden xl:flex">
                  {QUICK_PROMPTS.slice(0, 2).map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handleApplyTemplate(p.template)}
                      className="shrink-0 whitespace-nowrap rounded-lg px-2 py-1 text-[11px] text-fg-subtle transition-colors hover:bg-subtle hover:text-fg focus:outline-none"
                    >
                      + {p.title}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Cụm nút bên phải: Gợi ý phím tắt + Nút Gửi/Dừng */}
            <div className="flex shrink-0 items-center gap-2">
              <span className="hidden whitespace-nowrap text-[11px] text-fg-subtle sm:inline">
                Enter để gửi
              </span>

              {isStreaming ? (
                <button
                  type="button"
                  onClick={onStop}
                  className="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xl bg-danger px-3 text-xs font-medium text-white shadow-2xs transition-colors hover:bg-danger/90 focus:outline-none"
                  title="Dừng phản hồi"
                  aria-label="Dừng phản hồi"
                >
                  <Square className="h-3 w-3 shrink-0 fill-current" aria-hidden />
                  <span>Dừng</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!value.trim() || disabled}
                  className={`inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xl px-3 text-xs font-medium transition-all focus:outline-none ${
                    value.trim() && !disabled
                      ? 'bg-ai text-ai-fg shadow-2xs hover:bg-ai-hover'
                      : 'cursor-not-allowed bg-subtle text-fg-subtle'
                  }`}
                  title="Gửi câu lệnh (Enter)"
                  aria-label="Gửi câu lệnh"
                >
                  <span>Gửi</span>
                  <ArrowUp className="h-3.5 w-3.5 shrink-0" aria-hidden />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Khuyến cáo ngắn gọn dưới khung soạn (§8) */}
        <p className="mt-1.5 text-center text-[11px] text-fg-subtle">
          Chỉnh sửa từ AI chỉ áp dụng trên bản nháp — bạn luôn kiểm duyệt trước khi xuất bản.
        </p>
      </div>
    </div>
  );
}
