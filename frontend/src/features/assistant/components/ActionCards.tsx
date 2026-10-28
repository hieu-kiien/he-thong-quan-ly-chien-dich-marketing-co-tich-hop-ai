import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Layers,
  Megaphone,
  Radio,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { formatDate, formatMoney, formatRelative, fromDateTimeLocal, toDateTimeLocal } from '@/lib/format';
import {
  AI_ACTION_STATUS_LABEL,
  AI_ACTION_STATUS_TONE,
  CAMPAIGN_STATUS_LABEL,
  CHANNEL_LABEL,
  CONTENT_TYPE_LABEL,
  GOAL_LABEL,
} from '@/lib/labels';
import type {
  AiAction,
  CampaignGoal,
  CampaignStatus,
  ChannelCode,
  ContentType,
} from '@/lib/types';
import { Badge, Button, Input, Select, Textarea } from '@/components/ui';
import type { DraftItemEditable } from '../types';

interface ActionCardProps {
  action: AiAction;
  onConfirm: (actionId: number, editedArgs: Record<string, unknown>) => Promise<void>;
  onReject: (actionId: number) => Promise<void>;
  highlighted?: boolean;
}

const CHANNEL_CHAR_HINTS: Partial<Record<ChannelCode, number>> = {
  FACEBOOK: 2000,
  INSTAGRAM: 2200,
  TIKTOK: 300,
  ZALO_OA: 500,
  GOOGLE_ADS: 90,
};

/**
 * Thẻ hiển thị và chỉnh sửa cho công cụ propose_content_drafts.
 */
function ActionCardDrafts({
  action,
  onConfirm,
  onReject,
  highlighted,
}: ActionCardProps) {
  const isProposed = action.status === 'PROPOSED';
  const initialItems: DraftItemEditable[] = Array.isArray(action.args_json?.items)
    ? (action.args_json.items as Array<Record<string, unknown>>).map((it) => ({
        campaign_id: (it.campaign_id as number) ?? null,
        channel_code: (it.channel_code as ChannelCode) || 'FACEBOOK',
        content_type: (it.content_type as ContentType) || 'SOCIAL_POST',
        title: String(it.title || ''),
        body: String(it.body || ''),
        cta: it.cta ? String(it.cta) : '',
        submit_mode: (it.submit_mode as 'PENDING_REVIEW' | 'DRAFT') || 'PENDING_REVIEW',
      }))
    : [];

  const [items, setItems] = useState<DraftItemEditable[]>(initialItems);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateItem = (index: number, patch: Partial<DraftItemEditable>) => {
    setItems((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], ...patch };
      return copy;
    });
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(action.id, {
        items: items.map((it) => ({
          campaign_id: it.campaign_id,
          channel_code: it.channel_code,
          content_type: it.content_type,
          title: it.title,
          body: it.body,
          cta: it.cta || undefined,
          status: it.submit_mode, // PENDING_REVIEW hoặc DRAFT
        })),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await onReject(action.id);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Trích xuất id bài viết đã tạo từ result_json
  const createdContentIds: number[] = Array.isArray(action.result_json?.content_ids)
    ? (action.result_json.content_ids as number[])
    : Array.isArray(action.result_json?.contents)
      ? (action.result_json.contents as Array<{ id: number }>).map((c) => c.id)
      : action.result_json?.content_id
        ? [action.result_json.content_id as number]
        : [];

  return (
    <div
      id={`action-${action.id}`}
      className={cn(
        'rounded-lg border border-border bg-surface p-4 transition-all shadow-xs',
        highlighted && 'ring-2 ring-accent border-accent',
      )}
    >
      {/* Header thẻ */}
      <div className="flex items-start justify-between gap-2 border-b border-border/70 pb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-accent" aria-hidden />
            <h3 className="text-xs font-semibold text-fg">
              {action.summary || 'Đề xuất bản nháp nội dung'}
            </h3>
          </div>
          <div className="mt-1 text-[11px] text-fg-subtle">
            Tạo lúc {formatRelative(action.created_at)}
          </div>
        </div>

        <Badge tone={AI_ACTION_STATUS_TONE[action.status]}>
          {AI_ACTION_STATUS_LABEL[action.status]}
        </Badge>
      </div>

      {/* Danh sách các bản nháp */}
      <div className="mt-3 space-y-4">
        {items.map((draft, idx) => {
          const charHint = CHANNEL_CHAR_HINTS[draft.channel_code];
          const charCount = draft.body.length;

          return (
            <div
              key={idx}
              className="rounded-md border border-border/80 bg-subtle/50 p-3 text-xs"
            >
              <div className="mb-2.5 flex flex-wrap items-center justify-between gap-1.5">
                <div className="flex items-center gap-1.5">
                  <Badge tone="accent">
                    {CHANNEL_LABEL[draft.channel_code] || draft.channel_code}
                  </Badge>
                  <span className="text-[11px] text-fg-subtle">
                    {CONTENT_TYPE_LABEL[draft.content_type] || draft.content_type}
                  </span>
                </div>

                {isProposed && (
                  <div className="flex items-center gap-1 text-[11px]">
                    <label className="flex items-center gap-1 cursor-pointer">
                      <input
                        type="radio"
                        name={`mode-${action.id}-${idx}`}
                        checked={draft.submit_mode === 'PENDING_REVIEW'}
                        onChange={() => updateItem(idx, { submit_mode: 'PENDING_REVIEW' })}
                        className="text-accent focus:ring-accent"
                      />
                      <span>Gửi duyệt</span>
                    </label>
                    <label className="ml-2 flex items-center gap-1 cursor-pointer">
                      <input
                        type="radio"
                        name={`mode-${action.id}-${idx}`}
                        checked={draft.submit_mode === 'DRAFT'}
                        onChange={() => updateItem(idx, { submit_mode: 'DRAFT' })}
                        className="text-accent focus:ring-accent"
                      />
                      <span>Lưu nháp</span>
                    </label>
                  </div>
                )}
              </div>

              {isProposed ? (
                <div className="space-y-2.5">
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                      Tiêu đề bài viết
                    </label>
                    <Input
                      value={draft.title}
                      onChange={(e) => updateItem(idx, { title: e.target.value })}
                      placeholder="Nhập tiêu đề..."
                      className="text-xs"
                    />
                  </div>

                  <div>
                    <div className="mb-1 flex items-center justify-between text-[11px]">
                      <label className="font-medium text-fg-subtle">Nội dung</label>
                      <span
                        className={cn(
                          'text-[10px]',
                          charHint && charCount > charHint ? 'text-warning font-semibold' : 'text-fg-subtle',
                        )}
                      >
                        {charCount} ký tự {charHint ? `/ gợi ý < ${charHint}` : ''}
                      </span>
                    </div>
                    <Textarea
                      rows={4}
                      value={draft.body}
                      onChange={(e) => updateItem(idx, { body: e.target.value })}
                      placeholder="Nội dung bài viết..."
                      className="text-xs"
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                      Lời kêu gọi hành động (CTA)
                    </label>
                    <Input
                      value={draft.cta || ''}
                      onChange={(e) => updateItem(idx, { cta: e.target.value })}
                      placeholder="VD: Nhắn tin ngay, Đặt hàng..."
                      className="text-xs"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-1.5 text-xs text-fg">
                  <div className="font-semibold text-fg">{draft.title}</div>
                  <div className="whitespace-pre-wrap rounded bg-surface/70 p-2 text-fg-muted">
                    {draft.body}
                  </div>
                  {draft.cta && (
                    <div className="text-[11px] text-fg-subtle">
                      <span className="font-medium">CTA:</span> {draft.cta}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Trạng thái sau thực thi */}
      {action.status === 'EXECUTED' && (
        <div className="mt-3 rounded-md bg-success-soft p-2.5 text-xs text-success-soft-fg">
          <div className="flex items-center gap-1.5 font-medium">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            <span>Đã tạo nội dung thành công vào hệ thống.</span>
          </div>
          {createdContentIds.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {createdContentIds.map((cid) => (
                <Link
                  key={cid}
                  to={`/contents/${cid}`}
                  className="inline-flex items-center gap-1 rounded border border-success/40 bg-surface px-2 py-1 text-[11px] font-medium text-fg hover:border-accent hover:text-accent"
                >
                  <span>Xem nội dung #{cid}</span>
                  <ExternalLink className="h-3 w-3" aria-hidden />
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {action.status === 'FAILED' && (
        <div className="mt-3 flex items-start gap-2 rounded-md bg-danger-soft p-2.5 text-xs text-danger-soft-fg">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden />
          <div>
            <div className="font-medium">Thực thi đề xuất thất bại</div>
            <div className="mt-0.5 text-[11px] text-fg-muted">
              {action.error || 'Đã có lỗi xảy ra trong quá trình xác nhận đề xuất.'}
            </div>
          </div>
        </div>
      )}

      {action.status === 'REJECTED' && (
        <div className="mt-3 flex items-center gap-1.5 text-xs text-fg-subtle italic">
          <XCircle className="h-3.5 w-3.5" aria-hidden />
          <span>Đề xuất này đã được bỏ qua.</span>
        </div>
      )}

      {/* Nút hành động Xác nhận / Bỏ qua */}
      {isProposed && (
        <div className="mt-4 border-t border-border/70 pt-3">
          <p className="mb-2.5 text-[11px] leading-relaxed text-fg-subtle">
            Chỉnh sửa chỉ áp dụng trên bản nháp khi bạn bấm <strong className="font-medium text-fg-muted">Xác nhận</strong>. Bạn có thể sửa trực tiếp các ô trên hoặc hoàn tác bất kỳ lúc nào.
          </p>
          <div className="flex items-center justify-end gap-2">
            <Button
              size="sm"
              variant="secondary"
              loading={isSubmitting}
              onClick={handleReject}
            >
              Bỏ qua
            </Button>
            <Button
              size="sm"
              variant="primary"
              loading={isSubmitting}
              onClick={handleConfirm}
            >
              <Check className="mr-1 h-3.5 w-3.5" aria-hidden />
              Áp dụng gợi ý
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Thẻ hiển thị đề xuất tạo mới hoặc cập nhật chiến dịch: propose_campaign / propose_campaign_update
 */
function ActionCardCampaign({
  action,
  onConfirm,
  onReject,
  highlighted,
}: ActionCardProps) {
  const isProposed = action.status === 'PROPOSED';
  const args = action.args_json || {};
  // propose_campaign_update chỉ chứa các trường AI muốn đổi; trường trống nghĩa là GIỮ NGUYÊN
  const isUpdate = action.tool.replace(/^marketflow_/, '') === 'propose_campaign_update';

  const original = {
    name: args.name == null ? '' : String(args.name),
    goal: args.goal == null ? '' : String(args.goal),
    status: args.status == null ? '' : String(args.status),
    objective: args.objective == null ? '' : String(args.objective),
    target_audience: args.target_audience == null ? '' : String(args.target_audience),
    product: args.product == null ? '' : String(args.product),
    key_message: args.key_message == null ? '' : String(args.key_message),
    start_date: args.start_date == null ? '' : String(args.start_date),
    end_date: args.end_date == null ? '' : String(args.end_date),
    budget: args.budget == null ? '' : String(args.budget),
  };

  const [form, setForm] = useState({
    ...original,
    goal: (original.goal || (isUpdate ? '' : 'AWARENESS')) as CampaignGoal | '',
    status: (original.status || '') as CampaignStatus | '',
  });
  const [showUnchanged, setShowUnchanged] = useState(!isUpdate);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const hasProposedValue = (key: keyof typeof original) => original[key] !== '';
  const proposedFieldCount = (Object.keys(original) as (keyof typeof original)[]).filter(hasProposedValue).length;
  // Nếu vì lý do nào đó isUpdate không có trường đơn lẻ nào (vd chỉ đổi channels), hoặc người dùng mở rộng
  const shouldShowField = (key: keyof typeof original) =>
    !isUpdate || showUnchanged || hasProposedValue(key) || proposedFieldCount === 0;

  const proposedChannels = Array.isArray(args.channels)
    ? (args.channels as Array<{ code?: string; channel_code?: string; planned_budget?: number }>)
    : [];

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      // Chỉ gửi các trường người dùng đã SỬA so với đề xuất; phần còn lại backend lấy từ đề xuất gốc
      const override: Record<string, unknown> = {};
      (Object.keys(original) as (keyof typeof original)[]).forEach((key) => {
        if (String(form[key]) === original[key]) return;
        if (key === 'budget') {
          if (form.budget !== '') override.budget = Number(form.budget);
        } else if (form[key] !== '') {
          override[key] = form[key];
        }
      });
      await onConfirm(action.id, override);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await onReject(action.id);
    } finally {
      setIsSubmitting(false);
    }
  };

  const createdCampaignId =
    (action.result_json?.campaign_id as number) ||
    (action.result_json?.id as number) ||
    (args.campaign_id as number | undefined);

  return (
    <div
      id={`action-${action.id}`}
      className={cn(
        'rounded-lg border border-border bg-surface p-4 transition-all shadow-xs',
        highlighted && 'ring-2 ring-accent border-accent',
      )}
    >
      <div className="flex items-start justify-between gap-2 border-b border-border/70 pb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Megaphone className="h-4 w-4 text-accent" aria-hidden />
            <h3 className="text-xs font-semibold text-fg">
              {action.summary || (isUpdate ? 'Đề xuất chỉnh sửa chiến dịch' : 'Đề xuất tạo chiến dịch mới')}
            </h3>
          </div>
          <div className="mt-1 flex items-center gap-2 text-[11px] text-fg-subtle">
            <span>Tạo lúc {formatRelative(action.created_at)}</span>
            {isUpdate && args.campaign_id != null && (
              <span className="rounded bg-subtle px-1.5 py-0.5 font-mono text-[10px] font-medium text-fg-muted">
                Chiến dịch #{String(args.campaign_id)}
              </span>
            )}
          </div>
        </div>

        <Badge tone={AI_ACTION_STATUS_TONE[action.status]}>
          {AI_ACTION_STATUS_LABEL[action.status]}
        </Badge>
      </div>

      <div className="mt-3 space-y-2.5 text-xs">
        {isProposed ? (
          <>
            {shouldShowField('name') && (
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-[11px] font-medium text-fg-subtle">Tên chiến dịch</label>
                  {isUpdate && hasProposedValue('name') && (
                    <span className="text-[10px] font-medium text-ai">Đề xuất đổi</span>
                  )}
                </div>
                <Input
                  value={form.name}
                  placeholder={isUpdate ? '(giữ nguyên tên hiện tại)' : 'Nhập tên chiến dịch...'}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="text-xs"
                />
              </div>
            )}

            {(shouldShowField('goal') || shouldShowField('budget')) && (
              <div className="grid grid-cols-2 gap-2">
                {shouldShowField('goal') && (
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                      Mục tiêu tổng quát
                    </label>
                    <Select
                      value={form.goal}
                      onChange={(e) => setForm({ ...form, goal: e.target.value as CampaignGoal | '' })}
                      options={[
                        ...(isUpdate ? [{ value: '', label: '(giữ nguyên)' }] : []),
                        { value: 'AWARENESS', label: GOAL_LABEL.AWARENESS },
                        { value: 'TRAFFIC', label: GOAL_LABEL.TRAFFIC },
                        { value: 'LEADS', label: GOAL_LABEL.LEADS },
                        { value: 'SALES', label: GOAL_LABEL.SALES },
                      ]}
                      className="text-xs"
                    />
                  </div>
                )}

                {shouldShowField('budget') && (
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                      Ngân sách (VND)
                    </label>
                    <Input
                      type="number"
                      value={form.budget}
                      placeholder={isUpdate ? '(giữ nguyên)' : undefined}
                      onChange={(e) => setForm({ ...form, budget: e.target.value })}
                      className="text-xs tabular-nums"
                    />
                  </div>
                )}
              </div>
            )}

            {isUpdate && shouldShowField('status') && (
              <div>
                <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                  Trạng thái chiến dịch
                </label>
                <Select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value as CampaignStatus | '' })}
                  options={[
                    { value: '', label: '(giữ nguyên)' },
                    { value: 'PLANNED', label: CAMPAIGN_STATUS_LABEL.PLANNED },
                    { value: 'ACTIVE', label: CAMPAIGN_STATUS_LABEL.ACTIVE },
                    { value: 'PAUSED', label: CAMPAIGN_STATUS_LABEL.PAUSED },
                    { value: 'COMPLETED', label: CAMPAIGN_STATUS_LABEL.COMPLETED },
                    { value: 'CANCELLED', label: CAMPAIGN_STATUS_LABEL.CANCELLED },
                  ]}
                  className="text-xs"
                />
              </div>
            )}

            {shouldShowField('product') && (
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-[11px] font-medium text-fg-subtle">Sản phẩm / Dịch vụ</label>
                  {isUpdate && hasProposedValue('product') && (
                    <span className="text-[10px] font-medium text-ai">Đề xuất đổi</span>
                  )}
                </div>
                <Input
                  value={form.product}
                  placeholder={isUpdate ? '(giữ nguyên)' : 'Tên sản phẩm hoặc dịch vụ...'}
                  onChange={(e) => setForm({ ...form, product: e.target.value })}
                  className="text-xs"
                />
              </div>
            )}

            {shouldShowField('key_message') && (
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-[11px] font-medium text-fg-subtle">Thông điệp chính (Key Message)</label>
                  {isUpdate && hasProposedValue('key_message') && (
                    <span className="text-[10px] font-medium text-ai">Đề xuất đổi</span>
                  )}
                </div>
                <Textarea
                  rows={2}
                  value={form.key_message}
                  placeholder={isUpdate ? '(giữ nguyên thông điệp hiện tại)' : 'Thông điệp xuyên suốt chiến dịch...'}
                  onChange={(e) => setForm({ ...form, key_message: e.target.value })}
                  className="text-xs"
                />
              </div>
            )}

            {shouldShowField('target_audience') && (
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-[11px] font-medium text-fg-subtle">Đối tượng mục tiêu</label>
                  {isUpdate && hasProposedValue('target_audience') && (
                    <span className="text-[10px] font-medium text-ai">Đề xuất đổi</span>
                  )}
                </div>
                <Textarea
                  rows={3}
                  value={form.target_audience}
                  placeholder={isUpdate ? '(giữ nguyên đối tượng hiện tại)' : 'Chân dung khách hàng mục tiêu...'}
                  onChange={(e) => setForm({ ...form, target_audience: e.target.value })}
                  className="text-xs"
                />
              </div>
            )}

            {shouldShowField('objective') && (
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-[11px] font-medium text-fg-subtle">Mục tiêu chi tiết (KPI)</label>
                  {isUpdate && hasProposedValue('objective') && (
                    <span className="text-[10px] font-medium text-ai">Đề xuất đổi</span>
                  )}
                </div>
                <Textarea
                  rows={2}
                  value={form.objective}
                  placeholder={isUpdate ? '(giữ nguyên mục tiêu chi tiết)' : 'KPI cụ thể cần đạt...'}
                  onChange={(e) => setForm({ ...form, objective: e.target.value })}
                  className="text-xs"
                />
              </div>
            )}

            {(shouldShowField('start_date') || shouldShowField('end_date')) && (
              <div className="grid grid-cols-2 gap-2">
                {shouldShowField('start_date') && (
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                      Ngày bắt đầu
                    </label>
                    <Input
                      type="date"
                      value={form.start_date}
                      onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                      className="text-xs tabular-nums"
                    />
                  </div>
                )}
                {shouldShowField('end_date') && (
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                      Ngày kết thúc
                    </label>
                    <Input
                      type="date"
                      value={form.end_date}
                      onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                      className="text-xs tabular-nums"
                    />
                  </div>
                )}
              </div>
            )}

            {proposedChannels.length > 0 && (
              <div className="rounded-md border border-border/80 bg-subtle/40 p-2.5">
                <div className="mb-1.5 text-[11px] font-medium text-fg-subtle">
                  Phân bổ kênh tiếp thị đề xuất
                </div>
                <div className="space-y-1">
                  {proposedChannels.map((ch, idx) => {
                    const code = (ch.code || ch.channel_code || '') as ChannelCode;
                    return (
                      <div key={idx} className="flex items-center justify-between text-xs">
                        <span className="font-medium text-fg">{CHANNEL_LABEL[code] || code}</span>
                        <span className="font-mono text-fg-muted tabular-nums">
                          {ch.planned_budget != null ? formatMoney(Number(ch.planned_budget)) : '—'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {isUpdate && proposedFieldCount > 0 && proposedFieldCount < Object.keys(original).length && (
              <button
                type="button"
                onClick={() => setShowUnchanged((v) => !v)}
                className="inline-flex items-center gap-1 pt-1 text-[11px] font-medium text-accent hover:underline"
              >
                {showUnchanged ? (
                  <>
                    <ChevronUp className="h-3.5 w-3.5" aria-hidden />
                    <span>Thu gọn các trường đang giữ nguyên</span>
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3.5 w-3.5" aria-hidden />
                    <span>Chỉnh sửa thêm các trường khác (đang giữ nguyên)</span>
                  </>
                )}
              </button>
            )}
          </>
        ) : (
          <div className="space-y-2 text-xs text-fg">
            {form.name && <div className="font-semibold text-fg">{form.name}</div>}
            {(form.goal || form.budget !== '' || form.status) && (
              <div className="text-fg-muted">
                {form.goal ? `Mục tiêu: ${GOAL_LABEL[form.goal]}` : ''}
                {form.goal && form.budget !== '' ? ' • ' : ''}
                {form.budget !== '' ? `Ngân sách: ${formatMoney(Number(form.budget))}` : ''}
                {form.status ? ` • Trạng thái: ${CAMPAIGN_STATUS_LABEL[form.status] || form.status}` : ''}
              </div>
            )}
            {form.product && (
              <div className="text-fg-muted">
                <span className="font-medium text-fg-subtle">Sản phẩm:</span> {form.product}
              </div>
            )}
            {form.key_message && (
              <div className="rounded bg-subtle/60 p-2 text-fg-muted">
                <span className="block text-[11px] font-medium text-fg-subtle">Thông điệp chính:</span>
                {form.key_message}
              </div>
            )}
            {form.target_audience && (
              <div className="rounded bg-subtle/60 p-2 text-fg-muted">
                <span className="block text-[11px] font-medium text-fg-subtle">Đối tượng mục tiêu:</span>
                {form.target_audience}
              </div>
            )}
            {form.objective && (
              <div className="rounded bg-subtle/60 p-2 text-fg-muted">
                <span className="block text-[11px] font-medium text-fg-subtle">Mục tiêu chi tiết:</span>
                {form.objective}
              </div>
            )}
            {(form.start_date || form.end_date) && (
              <div className="text-[11px] text-fg-subtle tabular-nums">
                Thời gian: {form.start_date ? formatDate(form.start_date) : '—'} -{' '}
                {form.end_date ? formatDate(form.end_date) : '—'}
              </div>
            )}
          </div>
        )}
      </div>

      {action.status === 'EXECUTED' && (
        <div className="mt-3 rounded-md bg-success-soft p-2.5 text-xs text-success-soft-fg">
          <div className="flex items-center gap-1.5 font-medium">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            <span>{isUpdate ? 'Đã cập nhật chiến dịch thành công.' : 'Đã tạo chiến dịch thành công.'}</span>
          </div>
          {createdCampaignId && (
            <div className="mt-2">
              <Link
                to={`/campaigns/${createdCampaignId}`}
                className="inline-flex items-center gap-1 rounded border border-success/40 bg-surface px-2.5 py-1 text-[11px] font-medium text-fg hover:border-accent hover:text-accent"
              >
                <span>Xem chi tiết chiến dịch #{createdCampaignId}</span>
                <ExternalLink className="h-3 w-3" aria-hidden />
              </Link>
            </div>
          )}
        </div>
      )}

      {action.status === 'FAILED' && (
        <div className="mt-3 rounded-md bg-danger-soft p-2.5 text-xs text-danger-soft-fg">
          {action.error || (isUpdate ? 'Cập nhật chiến dịch thất bại.' : 'Tạo chiến dịch thất bại.')}
        </div>
      )}

      {isProposed && (
        <div className="mt-4 border-t border-border/70 pt-3">
          <p className="mb-2.5 text-[11px] leading-relaxed text-fg-subtle">
            Chỉnh sửa chỉ áp dụng khi bạn bấm <strong className="font-medium text-fg-muted">Áp dụng gợi ý</strong>. Các trường giữ nguyên sẽ không bị ghi đè.
          </p>
          <div className="flex items-center justify-end gap-2">
            <Button size="sm" variant="secondary" loading={isSubmitting} onClick={handleReject}>
              Bỏ qua
            </Button>
            <Button size="sm" variant="primary" loading={isSubmitting} onClick={handleConfirm}>
              <Check className="mr-1 h-3.5 w-3.5" aria-hidden />
              Áp dụng gợi ý
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Thẻ hiển thị đề xuất lịch đăng bài: propose_schedule
 */
function ActionCardSchedule({
  action,
  onConfirm,
  onReject,
  highlighted,
}: ActionCardProps) {
  const isProposed = action.status === 'PROPOSED';
  const args = action.args_json || {};

  // Hiển thị và sửa theo giờ Việt Nam; gửi lên kèm múi giờ +07:00 (tránh lệch 7 tiếng)
  const [scheduledAt, setScheduledAt] = useState(toDateTimeLocal(String(args.scheduled_at || '')));
  const [note, setNote] = useState(String(args.note || ''));
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(action.id, {
        content_id: args.content_id,
        scheduled_at: scheduledAt ? fromDateTimeLocal(scheduledAt) : undefined,
        note: note || undefined,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await onReject(action.id);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      id={`action-${action.id}`}
      className={cn(
        'rounded-lg border border-border bg-surface p-4 transition-all shadow-xs',
        highlighted && 'ring-2 ring-accent border-accent',
      )}
    >
      <div className="flex items-start justify-between gap-2 border-b border-border/70 pb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-accent" aria-hidden />
            <h3 className="text-xs font-semibold text-fg">
              {action.summary || 'Đề xuất lịch đăng bài'}
            </h3>
          </div>
          <div className="mt-1 text-[11px] text-fg-subtle">
            Tạo lúc {formatRelative(action.created_at)}
          </div>
        </div>

        <Badge tone={AI_ACTION_STATUS_TONE[action.status]}>
          {AI_ACTION_STATUS_LABEL[action.status]}
        </Badge>
      </div>

      <div className="mt-3 space-y-2 text-xs">
        {isProposed ? (
          <>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                Thời điểm đăng bài (giờ Việt Nam)
              </label>
              <Input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                className="text-xs"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-fg-subtle">
                Ghi chú thêm
              </label>
              <Input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Ghi chú phân công hoặc thời điểm..."
                className="text-xs"
              />
            </div>
          </>
        ) : (
          <div className="text-fg-muted">
            Thời điểm: {scheduledAt} {note ? `• Ghi chú: ${note}` : ''}
          </div>
        )}
      </div>

      {action.status === 'EXECUTED' && (
        <div className="mt-3 rounded-md bg-success-soft p-2.5 text-xs text-success-soft-fg">
          <div className="flex items-center gap-1.5 font-medium">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            <span>Đã lên lịch đăng bài thành công.</span>
          </div>
          <div className="mt-2">
            <Link
              to="/calendar"
              className="inline-flex items-center gap-1 rounded border border-success/40 bg-surface px-2.5 py-1 text-[11px] font-medium text-fg hover:border-accent hover:text-accent"
            >
              <span>Xem trên lịch xuất bản</span>
              <ExternalLink className="h-3 w-3" aria-hidden />
            </Link>
          </div>
        </div>
      )}

      {isProposed && (
        <div className="mt-4 border-t border-border/70 pt-3">
          <p className="mb-2.5 text-[11px] leading-relaxed text-fg-subtle">
            Chỉnh sửa chỉ áp dụng khi bạn bấm <strong className="font-medium text-fg-muted">Áp dụng gợi ý</strong>. Bạn có thể huỷ lịch bất kỳ lúc nào.
          </p>
          <div className="flex items-center justify-end gap-2">
            <Button size="sm" variant="secondary" loading={isSubmitting} onClick={handleReject}>
              Bỏ qua
            </Button>
            <Button size="sm" variant="primary" loading={isSubmitting} onClick={handleConfirm}>
              <Check className="mr-1 h-3.5 w-3.5" aria-hidden />
              Áp dụng gợi ý
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Thẻ hiển thị đề xuất cập nhật số liệu tiếp thị: propose_metrics
 */
function ActionCardMetrics({
  action,
  onConfirm,
  onReject,
  highlighted,
}: ActionCardProps) {
  const isProposed = action.status === 'PROPOSED';
  const initialRows = Array.isArray(action.args_json?.rows)
    ? (action.args_json.rows as Array<Record<string, unknown>>)
    : [];

  const [rows, setRows] = useState(initialRows);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateRow = (index: number, patch: Partial<Record<string, unknown>>) => {
    setRows((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], ...patch };
      return copy;
    });
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(action.id, { rows });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await onReject(action.id);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      id={`action-${action.id}`}
      className={cn(
        'rounded-lg border border-border bg-surface p-4 transition-all shadow-xs',
        highlighted && 'ring-2 ring-accent border-accent',
      )}
    >
      <div className="flex items-start justify-between gap-2 border-b border-border/70 pb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Radio className="h-4 w-4 text-accent" aria-hidden />
            <h3 className="text-xs font-semibold text-fg">
              {action.summary || 'Đề xuất ghi nhận số liệu'}
            </h3>
          </div>
          <div className="mt-1 text-[11px] text-fg-subtle">
            Tạo lúc {formatRelative(action.created_at)}
          </div>
        </div>

        <Badge tone={AI_ACTION_STATUS_TONE[action.status]}>
          {AI_ACTION_STATUS_LABEL[action.status]}
        </Badge>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border text-fg-subtle">
              <th className="py-1 pr-2">Ngày</th>
              <th className="py-1 px-2">Kênh</th>
              <th className="py-1 px-2">Lượt xem</th>
              <th className="py-1 px-2">Nhấp</th>
              <th className="py-1 px-2">Chuyển đổi</th>
              <th className="py-1 pl-2">Chi phí</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-border/50 text-fg">
                <td className="py-1.5 pr-2">{formatDate(r.metric_date as string)}</td>
                <td className="py-1.5 px-2">{String(r.channel_code)}</td>
                <td className="py-1.5 px-2">
                  {isProposed ? (
                    <input
                      type="number"
                      value={Number(r.views || 0)}
                      onChange={(e) => updateRow(i, { views: Number(e.target.value) || 0 })}
                      className="w-16 rounded border border-border bg-surface px-1 py-0.5 text-xs text-fg"
                    />
                  ) : (
                    Number(r.views || 0)
                  )}
                </td>
                <td className="py-1.5 px-2">
                  {isProposed ? (
                    <input
                      type="number"
                      value={Number(r.clicks || 0)}
                      onChange={(e) => updateRow(i, { clicks: Number(e.target.value) || 0 })}
                      className="w-16 rounded border border-border bg-surface px-1 py-0.5 text-xs text-fg"
                    />
                  ) : (
                    Number(r.clicks || 0)
                  )}
                </td>
                <td className="py-1.5 px-2">
                  {isProposed ? (
                    <input
                      type="number"
                      value={Number(r.conversions || 0)}
                      onChange={(e) => updateRow(i, { conversions: Number(e.target.value) || 0 })}
                      className="w-16 rounded border border-border bg-surface px-1 py-0.5 text-xs text-fg"
                    />
                  ) : (
                    Number(r.conversions || 0)
                  )}
                </td>
                <td className="py-1.5 pl-2">
                  {isProposed ? (
                    <input
                      type="number"
                      value={Number(r.cost || 0)}
                      onChange={(e) => updateRow(i, { cost: Number(e.target.value) || 0 })}
                      className="w-20 rounded border border-border bg-surface px-1 py-0.5 text-xs text-fg"
                    />
                  ) : (
                    formatMoney(Number(r.cost || 0))
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {action.status === 'EXECUTED' && (
        <div className="mt-3 rounded-md bg-success-soft p-2.5 text-xs text-success-soft-fg">
          <CheckCircle2 className="inline mr-1 h-3.5 w-3.5" />
          <span>Đã ghi nhận các số liệu vào hệ thống.</span>
        </div>
      )}

      {isProposed && (
        <div className="mt-4 border-t border-border/70 pt-3">
          <p className="mb-2.5 text-[11px] leading-relaxed text-fg-subtle">
            Chỉnh sửa chỉ áp dụng khi bạn bấm <strong className="font-medium text-fg-muted">Áp dụng gợi ý</strong>. Bạn có thể huỷ lịch bất kỳ lúc nào.
          </p>
          <div className="flex items-center justify-end gap-2">
            <Button size="sm" variant="secondary" loading={isSubmitting} onClick={handleReject}>
              Bỏ qua
            </Button>
            <Button size="sm" variant="primary" loading={isSubmitting} onClick={handleConfirm}>
              <Check className="mr-1 h-3.5 w-3.5" aria-hidden />
              Áp dụng gợi ý
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Thẻ fallback cho các công cụ khác hoặc cập nhật chiến dịch.
 */
function ActionCardGeneric({
  action,
  onConfirm,
  onReject,
  highlighted,
}: ActionCardProps) {
  const isProposed = action.status === 'PROPOSED';
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(action.id, action.args_json);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await onReject(action.id);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      id={`action-${action.id}`}
      className={cn(
        'rounded-lg border border-border bg-surface p-4 transition-all shadow-xs',
        highlighted && 'ring-2 ring-accent border-accent',
      )}
    >
      <div className="flex items-start justify-between gap-2 border-b border-border/70 pb-3">
        <div className="min-w-0">
          <h3 className="text-xs font-semibold text-fg">
            {action.summary || action.tool}
          </h3>
          <div className="mt-1 text-[11px] text-fg-subtle">
            Tạo lúc {formatRelative(action.created_at)}
          </div>
        </div>

        <Badge tone={AI_ACTION_STATUS_TONE[action.status]}>
          {AI_ACTION_STATUS_LABEL[action.status]}
        </Badge>
      </div>

      <div className="mt-3">
        <pre className="max-h-48 overflow-x-auto rounded border border-border bg-subtle p-2 font-mono text-[11px] text-fg">
          {JSON.stringify(action.args_json, null, 2)}
        </pre>
      </div>

      {isProposed && (
        <div className="mt-4 border-t border-border/70 pt-3">
          <p className="mb-2.5 text-[11px] leading-relaxed text-fg-subtle">
            Chỉnh sửa chỉ áp dụng khi bạn bấm <strong className="font-medium text-fg-muted">Áp dụng gợi ý</strong>. Bạn có thể huỷ lịch bất kỳ lúc nào.
          </p>
          <div className="flex items-center justify-end gap-2">
            <Button size="sm" variant="secondary" loading={isSubmitting} onClick={handleReject}>
              Bỏ qua
            </Button>
            <Button size="sm" variant="primary" loading={isSubmitting} onClick={handleConfirm}>
              <Check className="mr-1 h-3.5 w-3.5" aria-hidden />
              Áp dụng gợi ý
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Điều phối thẻ hành động thích hợp dựa trên tên tool.
 */
export function ActionCardRouter(props: ActionCardProps) {
  return (
    <>
      <ActionCardByTool {...props} />
      {/* Xác nhận thất bại do dữ liệu (vd sai ngày): đề xuất vẫn ở trạng thái chờ để sửa và thử lại */}
      {props.action.status === 'PROPOSED' && props.action.error && (
        <div role="alert" className="-mt-1 mb-2 rounded-md bg-danger-soft p-2.5 text-xs text-danger-soft-fg">
          Lần xác nhận trước chưa thực hiện được: {props.action.error}. Hãy chỉnh lại thông tin rồi xác nhận lần nữa.
        </div>
      )}
    </>
  );
}

function ActionCardByTool(props: ActionCardProps) {
  const cleanTool = props.action.tool.replace(/^marketflow_/, '');

  switch (cleanTool) {
    case 'propose_content_drafts':
      return <ActionCardDrafts {...props} />;
    case 'propose_campaign':
    case 'propose_campaign_update':
      return <ActionCardCampaign {...props} />;
    case 'propose_schedule':
      return <ActionCardSchedule {...props} />;
    case 'propose_metrics':
      return <ActionCardMetrics {...props} />;
    default:
      return <ActionCardGeneric {...props} />;
  }
}
