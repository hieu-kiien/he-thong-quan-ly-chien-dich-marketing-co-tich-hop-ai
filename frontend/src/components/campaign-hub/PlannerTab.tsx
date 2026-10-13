import React, { useState } from 'react';
import {
  Sparkles,
  AlertTriangle,
  Coins,
  Target,
  ListTodo,
  Loader2,
  CheckCircle2,
  ShieldAlert,
  Info
} from 'lucide-react';
import { AIPlanResponse, Campaign, PlanApplyResponse, TaskPriority, TaskType } from '../../types';
import { aiApi, campaignApi, getApiErrorMessage } from '../../services/api';
import { formatVND, formatNumber, formatDateVN, addDaysLocalISO } from '../../utils/format';
import { useToast } from '../Toast';
import { useAuth } from '../../context/AuthContext';

interface PlannerTabProps {
  campaign: Campaign | null;
  userRole?: string | null;
  /** Gọi lại khi áp dụng thành công để Canvas/App nạp lại task + phân bổ + KPI. */
  onApplied?: () => void;
}

const newIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `plan-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
};

const TASK_TYPE_LABEL: Record<TaskType, string> = {
  CONTENT: 'Nội dung',
  DESIGN: 'Thiết kế',
  VIDEO: 'Video',
  ADS: 'Quảng cáo',
  RESEARCH: 'Nghiên cứu',
  OTHER: 'Khác'
};

const PRIORITY_STYLE: Record<TaskPriority, string> = {
  URGENT: 'bg-rose-100 text-rose-700 border-rose-200',
  HIGH: 'bg-amber-100 text-amber-700 border-amber-200',
  MEDIUM: 'bg-blue-100 text-blue-700 border-blue-200',
  LOW: 'bg-slate-100 text-slate-600 border-slate-200'
};

const formatKpiValue = (value: number, unit: string): string => {
  const u = (unit || '').toLowerCase();
  if (u === 'vnd') return formatVND(value);
  if (u === 'percent') return `${formatNumber(value)}%`;
  if (u === 'ratio') return `${formatNumber(value)}x`;
  return formatNumber(value);
};

const AiEstimateBadge: React.FC = () => (
  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 whitespace-nowrap">
    Ước tính AI
  </span>
);

export const PlannerTab: React.FC<PlannerTabProps> = ({
  campaign,
  userRole,
  onApplied
}) => {
  const toast = useToast();
  const { user } = useAuth();

  const [plan, setPlan] = useState<AIPlanResponse | null>(null);
  const [loadingPlan, setLoadingPlan] = useState<boolean>(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applying, setApplying] = useState<boolean>(false);
  const [applied, setApplied] = useState<PlanApplyResponse | null>(null);
  // Khoá idempotency sinh MỚI mỗi khi có kế hoạch mới; giữ nguyên qua các lần
  // retry cùng kế hoạch (mạng lỗi server có thể đã ghi) và đổi mới khi 409.
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() => newIdempotencyKey());

  if (!campaign) {
    return (
      <div className="bg-white p-8 rounded-xl border border-slate-200 shadow text-center text-sm text-slate-500">
        Chọn một chiến dịch để dùng Trợ Lý Hoạch Định AI.
      </div>
    );
  }

  const isManagerRole = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER' || userRole === 'ADMIN';
  const isOwner = !!user && campaign.owner_id === user.id;
  const canApply = isManagerRole || isOwner;

  const totalPlanned = plan
    ? plan.budget_split.reduce((sum, item) => sum + (Number(item.planned_amount) || 0), 0)
    : 0;
  const campaignBudget = Number(campaign.budget) || 0;
  const exceedsBudget = !!plan && totalPlanned > campaignBudget + 0.009;

  const handleGenerate = async () => {
    try {
      setLoadingPlan(true);
      setApplyError(null);
      setApplied(null);
      const generated = await aiApi.generatePlan(campaign.id);
      setPlan(generated);
      setIdempotencyKey(newIdempotencyKey());
    } catch (e: any) {
      const msg = getApiErrorMessage(e);
      setApplyError(msg);
      toast.error(msg, 'Lỗi sinh kế hoạch AI');
    } finally {
      setLoadingPlan(false);
    }
  };

  const handleApply = async () => {
    if (!plan || applying || applied) return;
    try {
      setApplying(true);
      setApplyError(null);
      const res = await campaignApi.applyPlan(campaign.id, {
        budget_split: plan.budget_split,
        kpi_targets: plan.kpi_targets,
        tasks: plan.tasks,
        idempotency_key: idempotencyKey
      });
      setApplied(res);
      if (res.deduplicated) {
        toast.success('Kế hoạch này đã được áp dụng trước đó — không ghi trùng lần hai.', 'Đã áp dụng (bỏ qua lặp)');
      } else {
        toast.success(
          `Tạo ${res.tasks_created} task${res.tasks_skipped ? `, bỏ qua ${res.tasks_skipped} trùng` : ''} + phân bổ ngân sách & KPI mục tiêu.`,
          'Áp dụng kế hoạch thành công'
        );
      }
      if (onApplied) onApplied();
    } catch (e: any) {
      const msg = getApiErrorMessage(e);
      setApplyError(msg);
      toast.error(msg, 'Lỗi áp dụng kế hoạch');
      // 409 = khoá tái sử dụng với kế hoạch khác: đổi khoá để lần áp dụng
      // tiếp theo là một lần ghi mới thay vì bị chặn lại.
      if (e?.response?.status === 409) setIdempotencyKey(newIdempotencyKey());
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header + hành động chính */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-violet-600" />
            Trợ Lý Hoạch Định AI (Planner)
          </span>
          <p className="text-[11px] text-slate-500 mt-1">
            Sinh kế hoạch phân bổ ngân sách, KPI mục tiêu và danh sách task theo thời gian chiến dịch
            {' '}(từ {formatDateVN(campaign.start_date)} đến {formatDateVN(campaign.end_date)}).
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loadingPlan}
          className="px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 disabled:opacity-60 text-white text-xs font-bold flex items-center gap-2 whitespace-nowrap transition-colors shadow"
        >
          {loadingPlan ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Đang sinh kế hoạch...</>
          ) : (
            <><Sparkles className="w-4 h-4" /> {plan ? 'Sinh kế hoạch mới' : 'Sinh kế hoạch AI'}</>
          )}
        </button>
      </div>

      {plan?.is_fallback && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 p-3.5 rounded-xl text-xs font-medium flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>
            Kế hoạch này là <strong>template dự phòng</strong> (mô hình AI không khả dụng / chưa cấu hình key),
            không phải nội dung do mô hình sinh. Kiểm tra kỹ trước khi áp dụng.
          </span>
        </div>
      )}

      {!plan && !loadingPlan && (
        <div className="bg-white p-10 rounded-xl border border-slate-200 shadow-sm text-center">
          <Sparkles className="w-8 h-8 text-violet-400 mx-auto mb-3" />
          <p className="text-sm font-bold text-slate-700">Chưa có kế hoạch nào</p>
          <p className="text-xs text-slate-500 mt-1">
            Bấm <strong>“Sinh kế hoạch AI”</strong> để nhận đề xuất phân bổ ngân sách, KPI và task —
            rồi xem lại và bấm Áp dụng.
          </p>
        </div>
      )}

      {plan && (
        <>
          {/* Tóm tắt */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-[11px] font-bold text-violet-700 uppercase tracking-wider flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" /> Tóm tắt kế hoạch
            </span>
            <p className="text-sm text-slate-700 mt-2 leading-relaxed">{plan.summary}</p>
            <div className="flex flex-wrap items-center gap-2 mt-3 text-[10px] text-slate-500">
              <span className="px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 font-medium">
                Model: {plan.model_used}
              </span>
              <span className="px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 font-medium">
                Prompt: {plan.prompt_version}
              </span>
            </div>
            {plan.warnings.length > 0 && (
              <ul className="mt-3 space-y-1">
                {plan.warnings.map((w, i) => (
                  <li key={i} className="text-[11px] text-amber-700 flex items-start gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {w}
                  </li>
                ))}
              </ul>
            )}
            {plan.assumptions.length > 0 && (
              <ul className="mt-2 space-y-1">
                {plan.assumptions.map((a, i) => (
                  <li key={i} className="text-[11px] text-slate-500 flex items-start gap-1.5">
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-slate-400 shrink-0" /> {a}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Phân bổ ngân sách */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <Coins className="w-3.5 h-3.5" /> Phân Bổ Ngân Sách Theo Kênh
            </span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
                    <th className="py-2 pr-3 font-bold">Kênh</th>
                    <th className="py-2 pr-3 font-bold text-right">Số Tiền Đề Xuất</th>
                    <th className="py-2 pr-3 font-bold">Lý Do</th>
                    <th className="py-2 font-bold">Nhãn</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.budget_split.map((item, i) => (
                    <tr key={`${item.channel_code}-${i}`} className="border-b border-slate-50">
                      <td className="py-2.5 pr-3 font-bold text-slate-800">{item.channel_code}</td>
                      <td className="py-2.5 pr-3 text-right font-mono font-semibold text-slate-900">
                        {formatVND(item.planned_amount)}
                      </td>
                      <td className="py-2.5 pr-3 text-slate-500 max-w-md">{item.rationale || '—'}</td>
                      <td className="py-2.5">{item.is_ai_estimate ? <AiEstimateBadge /> : null}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td className="py-2.5 pr-3 font-bold text-slate-700">Tổng đề xuất</td>
                    <td className={`py-2.5 pr-3 text-right font-mono font-extrabold ${exceedsBudget ? 'text-rose-600' : 'text-teal-700'}`}>
                      {formatVND(totalPlanned)}
                    </td>
                    <td className="py-2.5 pr-3 text-slate-500" colSpan={2}>
                      Ngân sách chiến dịch: <strong className={exceedsBudget ? 'text-rose-600' : 'text-slate-700'}>{formatVND(campaignBudget)}</strong>
                      {exceedsBudget && (
                        <span className="ml-2 text-rose-600 font-bold">— tổng đề xuất VƯỢNG ngân sách, backend sẽ từ chối</span>
                      )}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* KPI mục tiêu */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <Target className="w-3.5 h-3.5" /> KPI Mục Tiêu
            </span>
            {plan.kpi_targets.length === 0 ? (
              <p className="text-xs text-slate-500">
                Kế hoạch không kèm KPI (chiến dịch chưa có mục tiêu thật — AI không bịa con số).
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
                      <th className="py-2 pr-3 font-bold">Chỉ Tiêu</th>
                      <th className="py-2 pr-3 font-bold text-right">Mục Tiêu</th>
                      <th className="py-2 font-bold">Nhãn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plan.kpi_targets.map((k, i) => (
                      <tr key={`${k.metric_name}-${i}`} className="border-b border-slate-50">
                        <td className="py-2.5 pr-3 font-bold text-slate-800">{k.metric_name}</td>
                        <td className="py-2.5 pr-3 text-right font-mono font-semibold text-slate-900">
                          {formatKpiValue(k.target_value, k.unit)}
                        </td>
                        <td className="py-2.5">{k.is_ai_estimate ? <AiEstimateBadge /> : null}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Task đề xuất */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-[11px] font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <ListTodo className="w-3.5 h-3.5" /> Task Đề Xuất ({plan.tasks.length})
            </span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
                    <th className="py-2 pr-3 font-bold">Task</th>
                    <th className="py-2 pr-3 font-bold">Loại</th>
                    <th className="py-2 pr-3 font-bold">Ưu Tiên</th>
                    <th className="py-2 pr-3 font-bold">Hạn (dự kiến)</th>
                    <th className="py-2 font-bold">Mô Tả</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.tasks.map((t, i) => (
                    <tr key={`${t.title}-${i}`} className="border-b border-slate-50">
                      <td className="py-2.5 pr-3 font-bold text-slate-800">{t.title}</td>
                      <td className="py-2.5 pr-3 text-slate-600">{TASK_TYPE_LABEL[t.task_type] || t.task_type}</td>
                      <td className="py-2.5 pr-3">
                        <span className={`px-1.5 py-0.5 rounded border text-[10px] font-bold ${PRIORITY_STYLE[t.priority] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                          {t.priority}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 font-mono text-slate-700">
                        {formatDateVN(addDaysLocalISO(campaign.start_date, t.due_offset_days))}
                        <span className="text-slate-400 font-sans"> (+{t.due_offset_days}d)</span>
                      </td>
                      <td className="py-2.5 text-slate-500 max-w-xs">{t.description || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Áp dụng */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
            {applied ? (
              <div className="flex items-start gap-2.5 bg-emerald-50 border border-emerald-200 text-emerald-800 p-3.5 rounded-xl text-xs font-medium">
                <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                <span>
                  Kế hoạch <strong>đã được áp dụng</strong> vào chiến dịch
                  {applied.deduplicated ? ' (trùng khoá idempotency — không ghi lại)' : ''}:
                  {' '}{applied.budget_allocations.length} dòng phân bổ, {applied.kpi_targets.length} KPI,
                  {' '}{applied.tasks_created} task mới{applied.tasks_skipped ? `, ${applied.tasks_skipped} bỏ qua trùng` : ''}.
                  {' '}Bấm “Sinh kế hoạch mới” để tạo một kế hoạch khác.
                </span>
              </div>
            ) : (
              <>
                {!canApply && (
                  <div className="flex items-start gap-2.5 bg-slate-50 border border-slate-200 text-slate-600 p-3 rounded-xl text-xs">
                    <ShieldAlert className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>Chỉ <strong>chủ sở hữu chiến dịch</strong> hoặc <strong>quản lý</strong> mới được áp dụng kế hoạch.</span>
                  </div>
                )}
                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <button
                    onClick={handleApply}
                    disabled={!canApply || applying || exceedsBudget}
                    className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold flex items-center gap-2 whitespace-nowrap transition-colors shadow"
                    title={exceedsBudget ? 'Tổng phân bổ vượt ngân sách — backend sẽ trả 400' : undefined}
                  >
                    {applying ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Đang áp dụng...</>
                    ) : (
                      <><CheckCircle2 className="w-4 h-4" /> Áp dụng kế hoạch vào chiến dịch</>
                    )}
                  </button>
                  <span className="text-[11px] text-slate-500">
                    Ghi phân bổ ngân sách + KPI mục tiêu + {plan.tasks.length} task
                    (hạn tính từ ngày bắt đầu). Áp dụng lại cùng kế hoạch sẽ được bỏ qua nhờ khoá idempotency.
                  </span>
                </div>
              </>
            )}
            {applyError && (
              <div className="flex items-start gap-2.5 bg-rose-50 border border-rose-200 text-rose-700 p-3 rounded-xl text-xs font-medium">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{applyError}</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
