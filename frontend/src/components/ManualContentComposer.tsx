import React, { useEffect, useState } from 'react';
import { PencilLine, X, ShieldCheck, AlertTriangle, Loader2, CheckCircle2, Send } from 'lucide-react';
import { contentApi, getApiErrorMessage } from '../services/api';
import { getChannelRegistry, channelPresentation, channelIdByCode } from '../utils/channels';
import { CHANNEL_CODES, type ChannelCode } from '../utils/channels';
import { useToast } from './Toast';
import { useFocusTrap } from '../hooks/useFocusTrap';
import type { ComplianceCheckResponse } from '../types';

/**
 * Trình soạn thảo thủ công — đường tạo nội dung KHÔNG dùng AI.
 *
 * Vì sao cần
 * ----------
 * Trước khi có component này, mọi đường tạo `MarketingContent` trong giao diện
 * đều đi qua AI Studio, AI Drawer hoặc WorkflowCanvas — tức là đều phải có một
 * lời gọi AI thành công trước. Người không dùng được AI (hết quota, provider
 * hỏng, không muốn gửi nội dung khách hàng ra ngoài) không có cách nào tạo bài
 * để đưa vào hàng đợi duyệt.
 *
 * Nguyên tắc sản phẩm của dự án là "AI là tính năng tăng cường không bắt buộc",
 * nên đường thủ công phải là đường NGANG HÀNG, không phải đường dự phòng ẩn.
 * Nó cũng là bằng chứng mã nguồn cho yêu cầu "nhiều người không cần tính năng AI
 * vẫn làm được".
 *
 * Trạng thái tạo luôn là `DRAFT`, không phải `AI_DRAFT`: đây là bài người viết,
 * không phải bài máy sinh. Việc đó cũng làm audit log trung thực.
 *
 * Quét tuân thủ vẫn chạy được vì `ComplianceScanner` là bộ quy tắc tất định đọc
 * từ khóa cấm của Brand Kit — không gọi mô hình ngôn ngữ.
 */

interface ManualContentComposerProps {
  campaignId: number;
  onClose: () => void;
  onCreated?: (contentId: number, submitForReview: boolean) => void;
}

const MIN_TITLE = 3;
const MIN_BODY = 10;

export const ManualContentComposer: React.FC<ManualContentComposerProps> = ({
  campaignId,
  onClose,
  onCreated,
}) => {
  const toast = useToast();
  // Hộp thoại chỉ tồn tại khi được render, nên `isActive` luôn true. Giữ biến
  // riêng để hook focus trap đọc đúng hợp đồng của nó.
  const isActive = true;
  const dialogRef = useFocusTrap<HTMLDivElement>({ isActive, onEscape: onClose });

  const [channelCode, setChannelCode] = useState<ChannelCode>('facebook');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [cta, setCta] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [compliance, setCompliance] = useState<ComplianceCheckResponse | null>(null);
  const [touched, setTouched] = useState(false);

  const channels = getChannelRegistry();
  const channelId = channelIdByCode(channelCode);
  const presentation = channelPresentation(channelCode);

  // Bộ quy tắc định dạng của kênh để người viết biết cần bám theo gì.
  const formatRules = channels.find((c) => c.code === channelCode)?.format_rules ?? null;

  useEffect(() => {
    // Đổi kênh thì điểm tuân thủ cũ không còn ý nghĩa cho nội dung mới.
    setCompliance(null);
  }, [channelCode]);

  const titleError = title.trim().length < MIN_TITLE;
  const bodyError = body.trim().length < MIN_BODY;
  const canSave = !titleError && !bodyError && channelId !== null && !isSaving;

  const handleComplianceCheck = async () => {
    if (titleError || bodyError || channelId === null) return;
    setIsChecking(true);
    try {
      const res = await contentApi.checkCompliance({
        channel: channelCode,
        title: title.trim(),
        body: body.trim(),
        cta: cta.trim(),
      });
      setCompliance(res);
      if (res.status === 'PASSED') {
        toast.success(`Nội dung đạt chuẩn (${res.score}/100).`);
      } else if (res.status === 'WARNING') {
        toast.warning(`Có cảnh báo chính sách (${res.score}/100). Xem chi tiết bên dưới.`);
      } else {
        toast.error(`Vi phạm chính sách (${res.score}/100). Cần sửa trước khi gửi duyệt.`);
      }
    } catch (e) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi kiểm tra tuân thủ');
    } finally {
      setIsChecking(false);
    }
  };

  const handleSave = async (submitForReview: boolean) => {
    if (!canSave || channelId === null) return;
    setTouched(true);

    // Cảnh báo chặn khi quét cho thấy vi phạm mức HIGH. Đây là cùng hàng rào với
    // luồng AI: bài viết vi phạm nghiêm trọng không được gửi duyệt.
    const hasHighViolation = (compliance?.violations ?? []).some((v) => v.severity === 'HIGH');
    if (submitForReview && hasHighViolation) {
      toast.error('Nội dung vi phạm nghiêm trọng (mức HIGH). Sửa lại trước khi gửi duyệt.');
      return;
    }

    setIsSaving(true);
    try {
      const created = await contentApi.create({
        campaign_id: campaignId,
        channel_id: channelId,
        title: title.trim(),
        body: body.trim(),
        cta: cta.trim(),
        // DRAFT chứ không phải AI_DRAFT: bài do con người viết.
        status: 'DRAFT',
      });

      if (submitForReview) {
        await contentApi.submitForReview(created.id);
        toast.success('Đã tạo bài và gửi vào hàng đợi phê duyệt.');
      } else {
        toast.success('Đã lưu bản nháp. Bạn có thể sửa lại bất cứ lúc nào.');
      }
      onCreated?.(created.id, submitForReview);
      onClose();
    } catch (e) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi lưu nội dung');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto">
      {/*
        Lớp phủ không gắn onClick: click ra vùng ngoài KHÔNG đóng hộp thoại.
        Đây là quyết định có chủ đích cho một form soạn thảo — bấm nhầm ra ngoài
        mất toàn bộ nội dung đã viết là lỗi dễ chịu nhất. Hộp thoại đã có nút
        "Đóng" và Escape (qua useFocusTrap).
      */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="manual-composer-title"
        className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl my-8"
      >
        {/* Header: nói rõ đây là đường không dùng AI */}
        <div className="flex items-start justify-between gap-3 p-5 border-b border-slate-200 bg-slate-50 rounded-t-2xl">
          <div>
            <h2 id="manual-composer-title" className="text-base font-bold text-slate-900 flex items-center gap-2">
              <PencilLine className="w-5 h-5 text-indigo-600" />
              Soạn nội dung thủ công
            </h2>
            <p className="text-xs text-slate-600 mt-1">
              Bạn tự viết toàn bộ nội dung. Không có bước sinh nội dung tự động nào, và không có
              dữ liệu nào được gửi tới nhà cung cấp AI.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng trình soạn thảo"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Kênh */}
          <div>
            <label htmlFor="manual-channel" className="block text-xs font-bold text-slate-700 mb-1.5">
              Kênh phân phối
            </label>
            <select
              id="manual-channel"
              value={channelCode}
              onChange={(e) => setChannelCode(e.target.value as ChannelCode)}
              className="w-full px-3 py-2.5 rounded-xl border border-slate-300 bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              {CHANNEL_CODES.map((code) => (
                <option key={code} value={code}>
                  {channelPresentation(code).label}
                </option>
              ))}
            </select>
            {formatRules && (
              <p className="text-[11px] text-slate-500 mt-1.5 flex items-start gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0 mt-px text-slate-400" />
                <span>Quy chuẩn kênh: {formatRules}</span>
              </p>
            )}
          </div>

          {/* Tiêu đề */}
          <div>
            <label htmlFor="manual-title" className="block text-xs font-bold text-slate-700 mb-1.5">
              Tiêu đề <span className="text-red-500">*</span>
            </label>
            <input
              id="manual-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onBlur={() => setTouched(true)}
              maxLength={255}
              placeholder={`Ví dụ: 3 lý do nên chọn ${presentation.label}`}
              aria-invalid={touched && titleError}
              aria-describedby="manual-title-error"
              className="w-full px-3 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            {touched && titleError && (
              <p id="manual-title-error" className="text-[11px] text-red-600 mt-1">
                Tiêu đề cần ít nhất {MIN_TITLE} ký tự.
              </p>
            )}
          </div>

          {/* Nội dung */}
          <div>
            <label htmlFor="manual-body" className="block text-xs font-bold text-slate-700 mb-1.5">
              Nội dung <span className="text-red-500">*</span>
            </label>
            <textarea
              id="manual-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              onBlur={() => setTouched(true)}
              rows={7}
              placeholder="Viết nội dung theo cách của bạn. Giữ nguyên dấu tiếng Việt khi sao chép."
              aria-invalid={touched && bodyError}
              aria-describedby="manual-body-error"
              className="w-full px-3 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-y"
            />
            {touched && bodyError && (
              <p id="manual-body-error" className="text-[11px] text-red-600 mt-1">
                Nội dung cần ít nhất {MIN_BODY} ký tự.
              </p>
            )}
          </div>

          {/* CTA */}
          <div>
            <label htmlFor="manual-cta" className="block text-xs font-bold text-slate-700 mb-1.5">
              Lời kêu gọi hành động (CTA) — không bắt buộc
            </label>
            <input
              id="manual-cta"
              type="text"
              value={cta}
              onChange={(e) => setCta(e.target.value)}
              maxLength={255}
              placeholder="Ví dụ: Nhắn tin ngay để nhận báo giá"
              className="w-full px-3 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Kết quả quét tuân thủ */}
          {compliance && (
            <div
              role="status"
              className={`rounded-xl border p-3 text-xs ${
                compliance.status === 'PASSED'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : compliance.status === 'WARNING'
                    ? 'bg-amber-50 border-amber-200 text-amber-900'
                    : 'bg-rose-50 border-rose-200 text-rose-900'
              }`}
            >
              <p className="font-bold flex items-center gap-1.5">
                {compliance.status === 'PASSED' ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : (
                  <AlertTriangle className="w-4 h-4" />
                )}
                Điểm tuân thủ: {compliance.score}/100 — {compliance.summary}
              </p>
              {(compliance.violations ?? []).length > 0 && (
                <ul className="mt-1.5 space-y-0.5 list-disc pl-4">
                  {compliance.violations.map((v, i) => (
                    <li key={`${v.word ?? v.category}-${i}`}>
                      <strong className="font-semibold">{v.category}</strong>
                      {v.word ? ` — "${v.word}"` : ''}
                      {v.suggestion ? ` · Gợi ý: ${v.suggestion}` : ''}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleComplianceCheck}
            disabled={isChecking || titleError || bodyError || channelId === null}
            className="px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs font-bold text-slate-700 hover:bg-slate-100 flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isChecking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
            Kiểm tra tuân thủ
          </button>

          <span className="text-[11px] text-slate-500 flex items-center gap-1 mr-auto">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            Bộ quét chạy bằng quy tắc cục bộ, không gọi AI.
          </span>

          <button
            type="button"
            onClick={() => handleSave(false)}
            disabled={!canSave}
            className="px-4 py-2 rounded-xl border border-slate-300 bg-white text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Lưu bản nháp
          </button>

          <button
            type="button"
            onClick={() => handleSave(true)}
            disabled={!canSave}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            Lưu và gửi duyệt
          </button>
        </div>
      </div>
    </div>
  );
};