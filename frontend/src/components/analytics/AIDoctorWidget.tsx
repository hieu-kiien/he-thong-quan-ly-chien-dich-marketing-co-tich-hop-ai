import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Stethoscope, Sparkles, AlertTriangle, Zap, TrendingUp, RefreshCw, ArrowUpRight, PauseCircle, Wand2, Check, AlertCircle, Info } from 'lucide-react';
import { AIDoctorReport, AIDoctorRecommendation } from '../../types';
import { campaignApi } from '../../services/api';
import { useToast } from '../Toast';

export interface AIDoctorWidgetProps {
  campaignId?: number;
  initialReport?: AIDoctorReport | null;
  compact?: boolean;
  onOpenAIStudio?: () => void;
  className?: string;
}

export const AIDoctorWidget: React.FC<AIDoctorWidgetProps> = ({
  campaignId,
  initialReport,
  compact = false,
  onOpenAIStudio,
  className = ''
}) => {
  const toast = useToast();
  const [report, setReport] = useState<AIDoctorReport | null>(initialReport || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [appliedActions, setAppliedActions] = useState<Record<number, boolean>>({});
  const [isFallback, setIsFallback] = useState<boolean>(false);

  const loadDiagnosis = useCallback(async (cid: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await campaignApi.getAIDoctor(cid);
      setReport(data);
      setIsFallback(false);
    } catch (e) {
      // Không rơi về mock trong production — số liệu giả không được trình bày như thật.
      setReport(null);
      setIsFallback(false);
      setError('Không lấy được báo cáo Bác sĩ AI. Vui lòng thử lại sau.');
      toast.error('Không thể tải chẩn đoán AI cho chiến dịch này.');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (initialReport) {
      setReport(initialReport);
      setIsFallback(false);
      setError(null);
    } else if (campaignId) {
      loadDiagnosis(campaignId);
    } else {
      // Không có campaign và không có report ban đầu: không hiển thị số giả.
      setReport(null);
      setIsFallback(false);
      setError('Chọn một chiến dịch để xem chẩn đoán của Bác sĩ AI.');
    }
  }, [campaignId, initialReport, loadDiagnosis]);

  const handleApplyAction = async (index: number, rec: AIDoctorRecommendation) => {
    if (rec.action === 'OPTIMIZE') {
      setAppliedActions(prev => ({ ...prev, [index]: true }));
      toast.info('Đã mở AI Studio để tinh chỉnh thông điệp quảng cáo.');
      if (onOpenAIStudio) {
        onOpenAIStudio();
      }
      return;
    }

    if (!campaignId) {
      setAppliedActions(prev => ({ ...prev, [index]: true }));
      return;
    }

    try {
      const currentCamp = await campaignApi.getById(campaignId);
      const currentBudget = Number(currentCamp.budget) || 0;
      if (rec.action === 'SCALE') {
        const nextBudget = currentBudget > 0 ? Math.round(currentBudget * 1.15) : 10000000;
        await campaignApi.update(campaignId, { budget: nextBudget });
        setAppliedActions(prev => ({ ...prev, [index]: true }));
        toast.success(
          `Đã tăng 15% ngân sách chiến dịch lên ${nextBudget.toLocaleString('vi-VN')} đ theo khuyến nghị SCALE.`
        );
      } else if (rec.action === 'PAUSE') {
        await campaignApi.update(campaignId, { status: 'PAUSED' });
        setAppliedActions(prev => ({ ...prev, [index]: true }));
        toast.warning(`Đã chuyển trạng thái chiến dịch "${currentCamp.name}" sang Tạm dừng (PAUSED).`);
      } else if (rec.action === 'REDUCE') {
        const nextBudget = Math.max(1000000, Math.round(currentBudget * 0.85));
        await campaignApi.update(campaignId, { budget: nextBudget });
        setAppliedActions(prev => ({ ...prev, [index]: true }));
        toast.warning(
          `Đã giảm 15% ngân sách chiến dịch xuống ${nextBudget.toLocaleString('vi-VN')} đ để cắt lỗ.`
        );
      }
    } catch {
      toast.error('Không thể cập nhật ngân sách / trạng thái chiến dịch.');
    }
  };

  const isDemoMode = useMemo(() => {
    if (!report) return false;
    if (isFallback) return true;
    if (report.is_sparse_data) return true;
    const analyzed = report.metrics_analyzed;
    if (analyzed) {
      const conv = Number(analyzed.total_conversions) || 0;
      const cost = Number(analyzed.total_cost) || 0;
      if (conv === 0 || cost === 0) return true;
    }
    return false;
  }, [report, isFallback]);

  // Status mapping
  const getStatusBadge = (status: string, scoreVal: number) => {
    if (status === 'HEALTHY' || scoreVal >= 75) {
      return {
        text: 'Khỏe Mạnh (HEALTHY)',
        badge: 'bg-emerald-50 text-emerald-800 border border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300',
        color: '#047857',
        stroke: 'stroke-emerald-600',
        desc: 'Chiến dịch tăng trưởng tích cực, sẵn sàng tăng ngân sách'
      };
    }
    if (status === 'NEEDS_ATTENTION' || scoreVal >= 45) {
      return {
        text: 'Cần Chú Ý (NEEDS_ATTENTION)',
        badge: 'bg-amber-50 text-amber-900 border border-amber-300 dark:bg-amber-950/40 dark:text-amber-300',
        color: '#B45309',
        stroke: 'stroke-amber-600',
        desc: 'Phát hiện điểm nghẽn hiệu suất cần tối ưu hóa'
      };
    }
    return {
      text: 'Nguy Kịch (CRITICAL)',
      badge: 'bg-rose-50 text-rose-900 border border-rose-300 dark:bg-rose-950/40 dark:text-rose-300',
      color: '#BE123C',
      stroke: 'stroke-rose-600',
      desc: 'Báo động đỏ: Nguy cơ lãng phí ngân sách hoặc lỗ vốn'
    };
  };

  if (!report) {
    return (
      <div className={`bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm ${className}`}>
        <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
            <Stethoscope className="w-6 h-6 text-slate-400" />
          </div>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {error || 'Chưa có báo cáo chẩn đoán cho chiến dịch này.'}
          </p>
          {campaignId && (
            <button
              type="button"
              onClick={() => loadDiagnosis(campaignId)}
              disabled={loading}
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Đang khám…' : 'Thử lại'}</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  const statusInfo = getStatusBadge(report.health_status, report.health_score);
  const bottlenecks = report.key_bottlenecks || report.bottlenecks || [];
  const recommendations = report.recommendations || [];

  const score = report.health_score;

  // SVG Circular Gauge calculation
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className={`bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6 ${className}`}>
      
      {/* 1. Header & Re-diagnose Trigger */}
      {/* Widget này xuất hiện ở hai nơi với bề rộng rất khác nhau: cột ~305px của
          Dashboard và toàn bộ bề rộng trong PerformanceTab. Breakpoint theo
          viewport không phân biệt được hai trường hợp đó — nên `compact`
          quyết định bố cục thay vì `sm:`/`lg:`. */}
      <div className={`flex ${compact ? 'flex-col' : 'flex-col lg:flex-row'} items-center justify-between gap-3 pb-5 border-b border-slate-100 dark:border-slate-800`}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-[#121316] text-white flex items-center justify-center shrink-0">
            <Stethoscope className="w-5 h-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-bold text-[#121316] dark:text-white">
                Đánh giá hiệu quả chiến dịch
              </h3>
              
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#ECFDF5] text-[#15803D] border border-[#A7F3D0]">
                Đối soát thực tế
              </span>

              {isDemoMode && (
                <span 
                  role="status"
                  aria-label="Chưa phát sinh chi phí"
                  className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] text-[11px] font-bold"
                >
                  <AlertCircle className="w-3.5 h-3.5 text-[#B45309] shrink-0" aria-hidden="true" />
                  <span>Chưa phát sinh chi phí</span>
                </span>
              )}
            </div>
            <p className="text-xs text-[#5A5E66] dark:text-slate-400 mt-0.5">
              Chấm điểm chi phí — doanh thu và gợi ý điều chỉnh hạn mức theo ROAS
            </p>
          </div>
        </div>

        {campaignId && (
          <button
            type="button"
            onClick={() => loadDiagnosis(campaignId)}
            disabled={loading}
            className="px-3.5 py-2 bg-[#FAF9F5] hover:bg-[#EFECE6] border border-[#E4E2DD] text-[#121316] rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 shrink-0 self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#D95D39]' : ''}`} />
            <span>{loading ? 'Đang tính toán...' : 'Tính toán lại'}</span>
          </button>
        )}
      </div>

      {isDemoMode && (
        <div 
          role="status"
          className="p-3.5 bg-[#FFFBEB] border border-[#FDE68A] rounded-lg text-xs text-[#B45309] flex items-start gap-2.5"
        >
          <Info className="w-4 h-4 text-[#B45309] shrink-0 mt-0.5" aria-hidden="true" />
          <div className="leading-relaxed">
            <span className="font-bold">Chiến dịch chưa phát sinh chi phí quảng cáo:</span>{' '}
            <span>
              Chiến dịch hiện có chi phí hoặc đơn hàng bằng 0. Hãy đồng bộ từ Tài khoản Quảng cáo (Meta BM, TikTok BC, Google MCC) hoặc nhập báo cáo CSV để hệ thống chấm điểm trên số liệu thực tế.
            </span>
          </div>
        </div>
      )}

      {/* 2. Health Score Meter & Diagnostic Summary */}
      <div className={`grid grid-cols-1 ${compact ? '' : 'lg:grid-cols-12'} gap-5 items-center bg-[#FAF9F5] dark:bg-slate-800/40 p-5 rounded-xl border border-[#E4E2DD] dark:border-slate-800`}>
        
        {/* Circular Gauge Meter */}
        <div className={`${compact ? '' : 'lg:col-span-4'} flex items-center gap-4 justify-center ${compact ? '' : 'lg:justify-start'} min-w-0`}>
          <div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
            <svg 
              className="w-full h-full transform -rotate-90" 
              viewBox="0 0 96 96"
              role="img"
              aria-label={`Điểm sức khỏe chiến dịch: ${score} trên 100 điểm`}
            >
              <circle
                cx="48"
                cy="48"
                r={radius}
                className="stroke-slate-200 dark:stroke-slate-700"
                strokeWidth="7"
                fill="transparent"
              />
              <circle
                cx="48"
                cy="48"
                r={radius}
                className={`${statusInfo.stroke} transition-all duration-1000 ease-out`}
                strokeWidth="7"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center text-center">
              <span className="text-2xl font-black text-slate-900 dark:text-white leading-none">
                {score}
              </span>
              {/* KHÔNG dùng `uppercase` ở đây: nó biến chữ "đ" trong "điểm"
                  thành "Đ", nên vòng tròn hiển thị "/ 100Đ" và trông như lỗi
                  chính tả. Chữ thường vẫn đọc rõ ở cỡ 10px đã in đậm. */}
              <span className="text-[10px] font-bold text-slate-600 dark:text-slate-400 mt-0.5">/ 100đ</span>
            </div>
          </div>

          <div className="space-y-1">
            <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border ${statusInfo.badge}`}>
              {statusInfo.text}
            </span>
            <div className="text-[11px] font-medium text-slate-600 dark:text-slate-400 leading-tight">
              {statusInfo.desc}
            </div>
          </div>
        </div>

        {/* Diagnostic Narrative */}
        <div className={`${compact ? '' : 'lg:col-span-8'} space-y-1.5 min-w-0 ${compact ? '' : 'lg:border-l lg:border-slate-200 dark:lg:border-slate-800 lg:pl-5'}`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-700 dark:text-indigo-400" />
            <span>Tóm tắt Chẩn đoán Cấp Quản lý</span>
          </span>
          <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
            {report.diagnosis_summary}
          </p>
        </div>
      </div>

      {/* 3. Root Causes & Key Bottlenecks */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-500" />
            <span>Điểm Nghẽn Hiệu Suất Phát Hiện ({bottlenecks.length})</span>
          </h4>
          <span className="text-[11px] text-slate-600 dark:text-slate-400">Thẩm định theo thời gian thực</span>
        </div>

        <div className="space-y-2">
          {bottlenecks.map((item, idx) => {
            const isHigh = item.toLowerCase().includes('roas') && (item.includes('< 1.0') || item.includes('lỗ') || item.includes('thâm hụt'));
            const isMedium = item.toLowerCase().includes('ctr') || item.toLowerCase().includes('cvr');

            return (
              <div 
                key={idx}
                className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 rounded-xl p-3 flex items-start gap-3 text-xs"
              >
                <span className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 font-bold text-[10px] ${
                  isHigh 
                    ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-200' 
                    : isMedium 
                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-200' 
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-200'
                }`}>
                  {isHigh ? '!' : idx + 1}
                </span>
                <div className="flex-1 text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
                  {item}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Actionable Strategic Prescriptions */}
      <div className="space-y-3 pt-2 border-t border-slate-100 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-indigo-700 dark:text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
            <Zap className="w-4 h-4 text-indigo-700 dark:text-indigo-400" />
            <span>Đơn Thuốc Chiến Lược & Hành Động 1-Click ({recommendations.length})</span>
          </h4>
          <span className="text-[11px] text-emerald-700 dark:text-emerald-400 font-bold">
            {isDemoMode ? 'Định Hướng Mẫu' : '100% Căn Cứ Số Liệu Thật'}
          </span>
        </div>

        {/* Xem `compact`: ở Dashboard mỗi thẻ chỉ còn ~89px nên badge "SCALE" +
            tên kênh bị tràn; ở PerformanceTab thì 3 cột vẫn vừa. */}
        <div className={`grid grid-cols-1 ${compact ? '' : 'lg:grid-cols-3'} gap-4`}>
          {recommendations.map((rec, idx) => {
            const isApplied = appliedActions[idx];
            const isScale = rec.action === 'SCALE';
            const isOptimize = rec.action === 'OPTIMIZE';

            const cardBorder = isScale
              ? 'border-emerald-200 dark:border-emerald-900 bg-emerald-50/40 dark:bg-emerald-950/20'
              : isOptimize
              ? 'border-indigo-200 dark:border-indigo-900 bg-indigo-50/40 dark:bg-indigo-950/20'
              : 'border-rose-200 dark:border-rose-900 bg-rose-50/40 dark:bg-rose-950/20';

            const actionBadge = isScale
              ? 'bg-emerald-100 text-emerald-800'
              : isOptimize
              ? 'bg-indigo-100 text-indigo-800'
              : 'bg-rose-100 text-rose-800';

            return (
              <div 
                key={idx}
                className={`rounded-xl border p-4.5 space-y-3 flex flex-col justify-between transition-all hover:shadow-md min-w-0 ${cardBorder}`}
              >
                <div className="space-y-2 min-w-0">
                  {/* `flex-wrap`: badge hành động + tên kênh không đứng cạnh
                      nhau được trong thẻ hẹp. */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${actionBadge}`}>
                      {rec.action}
                    </span>
                    {rec.channel && (
                      <span className="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-400 uppercase">
                        {rec.channel}
                      </span>
                    )}
                  </div>

                  <h5 className="font-bold text-xs text-slate-900 dark:text-white leading-snug">
                    {rec.title || rec.reason}
                  </h5>

                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                    {rec.suggestion || rec.description || rec.reason}
                  </p>
                </div>

                <div className="space-y-2.5 pt-2">
                  {rec.impact && (
                    <div className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                      <TrendingUp className="w-3.5 h-3.5" />
                      <span>{rec.impact}</span>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => handleApplyAction(idx, rec)}
                    disabled={isApplied}
                    className={`w-full py-2 px-3 rounded-lg text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-1.5 active:scale-95 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      isApplied
                        ? 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400 cursor-default'
                        : isScale
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20 focus:ring-emerald-500'
                        : isOptimize
                        ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20 focus:ring-indigo-500'
                        : 'bg-rose-600 hover:bg-rose-700 text-white shadow-rose-600/20 focus:ring-rose-500'
                    }`}
                  >
                    {isApplied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Đã Áp Dụng Đơn Thuốc</span>
                      </>
                    ) : isScale ? (
                      <>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                        <span>Tăng ngân sách ngay</span>
                      </>
                    ) : isOptimize ? (
                      <>
                        <Wand2 className="w-3.5 h-3.5" />
                        <span>Mở AI Studio tối ưu</span>
                      </>
                    ) : (
                      <>
                        <PauseCircle className="w-3.5 h-3.5" />
                        <span>Tạm dừng kênh lỗ</span>
                      </>
                    )}
                  </button>
                </div>

              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
};
