import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, Lock, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { ComplianceCheckResponse, ComplianceViolation } from '../types';

interface ComplianceAlertBadgeProps {
  result: ComplianceCheckResponse | null;
  isLoading?: boolean;
  onAutoFix?: (word: string, suggestion: string) => void;
  onAutoFixAll?: () => void;
  className?: string;
}

export const ComplianceAlertBadge: React.FC<ComplianceAlertBadgeProps> = ({
  result,
  isLoading = false,
  onAutoFix,
  onAutoFixAll,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  if (isLoading) {
    return (
      <div className={`p-4 rounded-xl border border-blue-200 bg-blue-50/50 flex items-center gap-3 animate-pulse ${className}`}>
        <div className="w-5 h-5 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
        <span className="text-sm font-medium text-blue-800">
          Đang quét tuân thủ chính sách quảng cáo & an toàn thương hiệu...
        </span>
      </div>
    );
  }

  if (!result) return null;

  const { status, score, can_submit, violations = [] } = result;
  const hasHigh = violations.some(v => v.severity === 'HIGH') || !can_submit;

  const getStatusConfig = () => {
    switch (status) {
      case 'PASSED':
        return {
          bg: 'bg-emerald-50 border-emerald-300 text-emerald-900',
          badgeBg: 'bg-emerald-100 text-emerald-800',
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />,
          title: 'ĐẠT CHUẨN TUÂN THỦ (PASSED)',
          desc: 'Nội dung an toàn, không chứa từ khóa cấm hay vi phạm chính sách quảng cáo.'
        };
      case 'WARNING':
        return {
          bg: 'bg-amber-50 border-amber-300 text-amber-900',
          badgeBg: 'bg-amber-100 text-amber-800',
          icon: <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />,
          title: 'CẢNH BÁO TIẾP THỊ (WARNING)',
          desc: 'Phát hiện từ ngữ nhạy cảm hoặc thổi phồng. Nên tinh chỉnh để tăng hiệu quả phân phối.'
        };
      case 'VIOLATION':
      default:
        return {
          bg: 'bg-rose-50 border-rose-300 text-rose-900',
          badgeBg: 'bg-rose-100 text-rose-800',
          icon: <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />,
          title: 'VI PHẠM CHÍNH SÁCH (VIOLATION)',
          desc: 'Phát hiện vi phạm nghiêm trọng chính sách quảng cáo Meta/TikTok hoặc Brand Kit.'
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={`rounded-xl border transition-all ${config.bg} ${className}`}>
      {/* Header Bar */}
      <div className="p-4 flex items-center justify-between gap-3 cursor-pointer select-none" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center gap-3">
          {config.icon}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-wide">{config.title}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${config.badgeBg}`}>
                {score}/100 Điểm
              </span>
              {!can_submit && (
                <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-rose-600 text-white flex items-center gap-1">
                  <Lock className="w-3 h-3" /> Đã khóa gửi duyệt
                </span>
              )}
            </div>
            <p className="text-xs opacity-90 mt-0.5">{config.desc}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {violations.length > 0 && onAutoFixAll && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onAutoFixAll();
              }}
              className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-sm transition"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Tự động sửa toàn bộ</span>
            </button>
          )}
          <button type="button" className="p-1 rounded-md hover:bg-black/5 text-slate-600">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Violation Details */}
      {isExpanded && violations.length > 0 && (
        <div className="px-4 pb-4 pt-1 border-t border-black/10 space-y-3">
          {/* Submission Block Warning Banner */}
          {hasHigh && (
            <div className="p-3 rounded-lg bg-rose-100 border border-rose-300 text-rose-900 text-xs flex items-start gap-2.5">
              <Lock className="w-4 h-4 text-rose-700 shrink-0 mt-0.5" />
              <div>
                <strong>Chốt chặn kiểm duyệt nghiêm ngặt (Strict Review Gate):</strong>
                <p className="mt-0.5">
                  Bài viết chứa từ vi phạm mức độ <strong>NGHIÊM TRỌNG (HIGH)</strong>. Hệ thống tự động khóa nút Gửi phê duyệt (Submit) cho đến khi các vi phạm này được khắc phục triệt để.
                </p>
              </div>
            </div>
          )}

          {/* List of Flagged Words */}
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              Chi tiết các vi phạm được phát hiện ({violations.length}):
            </div>
            <div className="divide-y divide-black/5 bg-white/70 rounded-lg border border-black/10 overflow-hidden">
              {violations.map((v: ComplianceViolation, idx: number) => {
                const isHigh = v.severity === 'HIGH';
                const isMed = v.severity === 'MEDIUM';

                return (
                  <div key={idx} className="p-3 text-xs flex items-start justify-between gap-3 hover:bg-white transition">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                          "{v.word}"
                        </span>
                        <span className={`px-2 py-0.5 rounded font-semibold text-[10px] ${
                          v.category === 'BRAND_BANNED' 
                            ? 'bg-purple-100 text-purple-800' 
                            : 'bg-blue-100 text-blue-800'
                        }`}>
                          {v.category === 'BRAND_BANNED' ? 'Brand Blacklist' : 'Chính sách Ads'}
                        </span>
                        <span className={`px-2 py-0.5 rounded font-semibold text-[10px] ${
                          isHigh 
                            ? 'bg-rose-100 text-rose-800' 
                            : isMed 
                            ? 'bg-amber-100 text-amber-800' 
                            : 'bg-slate-100 text-slate-800'
                        }`}>
                          Mức {v.severity}
                        </span>
                      </div>
                      <p className="text-slate-700">
                        <span className="text-slate-500 font-medium">Gợi ý sửa:</span> {v.suggestion}
                      </p>
                    </div>

                    {onAutoFix && (
                      <button
                        type="button"
                        onClick={() => onAutoFix(v.word, v.suggestion)}
                        className="shrink-0 text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 font-medium px-2.5 py-1 rounded border border-slate-200 flex items-center gap-1 transition"
                      >
                        <Sparkles className="w-3 h-3 text-indigo-600" />
                        <span>Sửa ngay</span>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
