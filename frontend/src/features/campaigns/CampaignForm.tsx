import { useMemo, useState, type FormEvent } from 'react';
import { cn } from '@/lib/cn';
import { useChannels } from '@/lib/hooks';
import { formatMoney, todayKey } from '@/lib/format';
import { CAMPAIGN_STATUS_LABEL, GOAL_LABEL, options } from '@/lib/labels';
import type { Campaign, CampaignGoal, CampaignInput, CampaignStatus } from '@/lib/types';
import { Button, Callout, FormField, Input, MoneyInput, Select, Skeleton, Textarea, useFormErrors } from '@/components/ui';
import type { ApiError } from '@/lib/api/client';

interface ChannelDraft {
  selected: boolean;
  planned_budget: number | null;
}

interface FormState {
  name: string;
  goal: CampaignGoal | '';
  status: CampaignStatus;
  start_date: string;
  end_date: string;
  budget: number | null;
  objective: string;
  target_audience: string;
  product: string;
  key_message: string;
  channels: Record<number, ChannelDraft>;
}

function initialState(c?: Campaign): FormState {
  const channels: Record<number, ChannelDraft> = {};
  c?.channels.forEach((ch) => (channels[ch.id] = { selected: true, planned_budget: ch.planned_budget }));
  return {
    name: c?.name ?? '',
    goal: c?.goal ?? '',
    status: c?.status ?? 'PLANNED',
    start_date: c?.start_date ?? todayKey(),
    end_date: c?.end_date ?? '',
    budget: c?.budget ?? null,
    objective: c?.objective ?? '',
    target_audience: c?.target_audience ?? '',
    product: c?.product ?? '',
    key_message: c?.key_message ?? '',
    channels,
  };
}

export interface CampaignFormProps {
  campaign?: Campaign;
  submitLabel: string;
  onSubmit: (body: CampaignInput) => Promise<unknown>;
  onCancel: () => void;
  /** id của <form> để nút submit có thể nằm ngoài (vd chân Drawer). */
  formId?: string;
  hideActions?: boolean;
}

/** Form tạo/sửa chiến dịch, dùng cho /campaigns/new và ngăn kéo "Sửa chiến dịch". */
export function CampaignForm({ campaign, submitLabel, onSubmit, onCancel, formId, hideActions }: CampaignFormProps) {
  const channelsQ = useChannels(!!campaign);
  const [s, setS] = useState<FormState>(() => initialState(campaign));
  const [submitting, setSubmitting] = useState(false);
  const { errors, formError, clearField, validate, applyApiError } = useFormErrors();

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setS((prev) => ({ ...prev, [key]: value }));
    clearField(key as string);
  };

  const availableChannels = useMemo(
    () => (channelsQ.data ?? []).filter((c) => c.is_active || s.channels[c.id]?.selected),
    [channelsQ.data, s.channels],
  );

  const selectedIds = Object.entries(s.channels)
    .filter(([, v]) => v.selected)
    .map(([k]) => Number(k));
  const plannedSum = selectedIds.reduce((sum, id) => sum + (s.channels[id]?.planned_budget ?? 0), 0);

  const toggleChannel = (id: number) => {
    setS((prev) => {
      const cur = prev.channels[id] ?? { selected: false, planned_budget: null };
      return { ...prev, channels: { ...prev.channels, [id]: { ...cur, selected: !cur.selected } } };
    });
    clearField('channels');
  };

  const setPlanned = (id: number, v: number | null) => {
    setS((prev) => ({ ...prev, channels: { ...prev.channels, [id]: { selected: true, planned_budget: v } } }));
    clearField('channels');
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string | undefined> = {
      name: !s.name.trim() ? 'Vui lòng nhập tên chiến dịch.' : s.name.length > 200 ? 'Tên tối đa 200 ký tự.' : undefined,
      goal: !s.goal ? 'Vui lòng chọn mục tiêu.' : undefined,
      start_date: !s.start_date ? 'Vui lòng chọn ngày bắt đầu.' : undefined,
      end_date: !s.end_date
        ? 'Vui lòng chọn ngày kết thúc.'
        : s.start_date && s.end_date < s.start_date
          ? 'Ngày kết thúc phải sau hoặc bằng ngày bắt đầu.'
          : undefined,
      budget: s.budget === null ? 'Vui lòng nhập ngân sách (có thể là 0).' : undefined,
      objective: !s.objective.trim() ? 'Vui lòng mô tả mục tiêu cụ thể.' : undefined,
      target_audience: !s.target_audience.trim() ? 'Vui lòng mô tả đối tượng mục tiêu.' : undefined,
      product: !s.product.trim() ? 'Vui lòng nhập sản phẩm/dịch vụ.' : undefined,
      channels:
        selectedIds.length === 0
          ? 'Chọn ít nhất một kênh.'
          : s.budget !== null && plannedSum > s.budget
            ? `Tổng ngân sách theo kênh (${formatMoney(plannedSum)}) vượt ngân sách chiến dịch.`
            : undefined,
    };
    if (validate(errs)) return;
    const body: CampaignInput = {
      name: s.name.trim(),
      goal: s.goal as CampaignGoal,
      objective: s.objective.trim(),
      target_audience: s.target_audience.trim(),
      product: s.product.trim(),
      key_message: s.key_message.trim() || null,
      start_date: s.start_date,
      end_date: s.end_date,
      budget: s.budget ?? 0,
      status: s.status,
      channels: selectedIds.map((id) => ({ channel_id: id, planned_budget: s.channels[id]?.planned_budget ?? null })),
    };
    setSubmitting(true);
    try {
      await onSubmit(body);
    } catch (err) {
      applyApiError(err as ApiError);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form id={formId} onSubmit={submit} noValidate className="space-y-6">
      {formError && <Callout tone="danger">{formError}</Callout>}

      <section className="space-y-4">
        <h3 className="text-sm font-semibold text-fg">Thông tin chung</h3>
        <FormField label="Tên chiến dịch" required error={errors.name}>
          {(p) => (
            <Input {...p} value={s.name} maxLength={200} onChange={(e) => set('name', e.target.value)} placeholder="Ví dụ: Ra mắt cà phê muối mùa thu" />
          )}
        </FormField>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Mục tiêu" required error={errors.goal}>
            {(p) => (
              <Select
                {...p}
                value={s.goal}
                placeholder="Chọn mục tiêu"
                options={options(GOAL_LABEL)}
                onChange={(e) => set('goal', e.target.value as CampaignGoal)}
              />
            )}
          </FormField>
          <FormField label="Trạng thái" error={errors.status}>
            {(p) => (
              <Select
                {...p}
                value={s.status}
                options={options(CAMPAIGN_STATUS_LABEL)}
                onChange={(e) => set('status', e.target.value as CampaignStatus)}
              />
            )}
          </FormField>
          <FormField label="Ngày bắt đầu" required error={errors.start_date}>
            {(p) => <Input {...p} type="date" value={s.start_date} onChange={(e) => set('start_date', e.target.value)} />}
          </FormField>
          <FormField label="Ngày kết thúc" required error={errors.end_date}>
            {(p) => (
              <Input {...p} type="date" value={s.end_date} min={s.start_date || undefined} onChange={(e) => set('end_date', e.target.value)} />
            )}
          </FormField>
          <FormField label="Ngân sách" required error={errors.budget} hint="Đơn vị: đồng (VND)">
            {(p) => <MoneyInput {...p} value={s.budget} onChange={(v) => set('budget', v)} placeholder="0" />}
          </FormField>
        </div>
      </section>

      <section className="space-y-4">
        <h3 className="text-sm font-semibold text-fg">Định hướng</h3>
        <FormField label="Mục tiêu cụ thể" required error={errors.objective} hint="Kết quả mong muốn, đo được nếu có thể.">
          {(p) => <Textarea {...p} rows={3} value={s.objective} onChange={(e) => set('objective', e.target.value)} />}
        </FormField>
        <FormField label="Đối tượng mục tiêu" required error={errors.target_audience}>
          {(p) => <Textarea {...p} rows={2} value={s.target_audience} onChange={(e) => set('target_audience', e.target.value)} />}
        </FormField>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Sản phẩm / dịch vụ" required error={errors.product}>
            {(p) => <Input {...p} value={s.product} onChange={(e) => set('product', e.target.value)} />}
          </FormField>
          <FormField label="Thông điệp chính" error={errors.key_message}>
            {(p) => <Input {...p} value={s.key_message} onChange={(e) => set('key_message', e.target.value)} />}
          </FormField>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold text-fg">
            Kênh triển khai <span className="text-danger" aria-hidden>*</span>
          </h3>
          <p className="text-xs text-fg-subtle tabular">
            Đã phân bổ {formatMoney(plannedSum)}
            {s.budget !== null && ` / ${formatMoney(s.budget)}`}
          </p>
        </div>
        {channelsQ.isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : channelsQ.isError ? (
          <Callout tone="danger">Không tải được danh sách kênh.</Callout>
        ) : availableChannels.length === 0 ? (
          <Callout tone="warning">Chưa có kênh nào đang hoạt động. Quản lý cần tạo kênh trong Cài đặt.</Callout>
        ) : (
          <fieldset
            className={cn('divide-y divide-border rounded-lg border', errors.channels ? 'border-danger' : 'border-border')}
            aria-describedby={errors.channels ? 'channels-err' : undefined}
          >
            <legend className="sr-only">Chọn kênh và ngân sách dự kiến</legend>
            {availableChannels.map((ch) => {
              const d = s.channels[ch.id];
              const checked = !!d?.selected;
              return (
                <div key={ch.id} className="flex flex-wrap items-center gap-3 px-3 py-2.5">
                  <label className="flex min-w-[10rem] flex-1 items-center gap-2.5 text-sm">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleChannel(ch.id)}
                      className="h-4 w-4 rounded accent-[rgb(var(--accent))]"
                    />
                    <span className="text-fg">{ch.name}</span>
                    {!ch.is_active && <span className="text-xs text-fg-subtle">(đã tắt)</span>}
                  </label>
                  <div className="w-full sm:w-52">
                    <MoneyInput
                      aria-label={`Ngân sách dự kiến cho ${ch.name}`}
                      value={d?.planned_budget ?? null}
                      onChange={(v) => setPlanned(ch.id, v)}
                      disabled={!checked}
                      placeholder="Ngân sách dự kiến"
                      className="[&_input]:h-8"
                    />
                  </div>
                </div>
              );
            })}
          </fieldset>
        )}
        {errors.channels && (
          <p id="channels-err" className="text-xs text-danger" role="alert">
            {errors.channels}
          </p>
        )}
      </section>

      {!hideActions && (
        <div className="flex justify-end gap-2 border-t border-border pt-4">
          <Button onClick={onCancel} disabled={submitting}>
            Huỷ
          </Button>
          <Button type="submit" variant="primary" loading={submitting}>
            {submitLabel}
          </Button>
        </div>
      )}
    </form>
  );
}
