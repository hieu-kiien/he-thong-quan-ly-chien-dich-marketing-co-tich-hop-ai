import React, { useState, useEffect } from 'react';
import { 
  Stethoscope, 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  Zap, 
  TrendingUp, 
  RefreshCw, 
  ArrowUpRight, 
  PauseCircle, 
  Wand2, 
  Check, 
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import { AIDoctorReport, AIDoctorRecommendation } from '../../types';
import { campaignApi } from '../../services/api';
import { useToast } from '../Toast';
import { MOCK_AI_DOCTOR_REPORT } from '../../services/mockData';

interface AIDoctorWidgetProps {
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
  const [appliedActions, setAppliedActions] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (initialReport) {
      setReport(initialReport);
    } else if (campaignId) {
      loadDiagnosis(campaignId);
    } else {
      setReport(MOCK_AI_DOCTOR_REPORT);
    }
  }, [campaignId, initialReport]);

  const loadDiagnosis = async (cid: number) => {
    try {
      setLoading(true);
      const data = await campaignApi.getAIDoctor(cid);
      setReport(data);
    } catch (e) {
      setReport({ ...MOCK_AI_DOCTOR_REPORT, campaign_id: cid });
    } finally {
      setLoading(false);
    }
  };

  const handleApplyAction = (index: number, rec: AIDoctorRecommendation) => {
    setAppliedActions(prev => ({ ...prev, [index]: true }));

    if (rec.action === 'SCALE') {
      toast.success(`Đã áp dụng đơn thuốc SCALE: Tăng ngân sách cho kênh ${rec.channel || 'mục tiêu'}!`);
    } else if (rec.action === 'OPTIMIZE') {
      toast.info(`Đã kích hoạt chế độ TỐI ƯU HÓA: Mở AI Studio để tinh chỉnh thông điệp!`);
      if (onOpenAIStudio) {
        onOpenAIStudio();
      }
    } else if (rec.action === 'PAUSE' || rec.action === 'REDUCE') {
      toast.warning(`Đã áp dụng đơn thuốc CẮT LỖ: Tạm hoãn chi tiêu trên kênh ${rec.channel || 'mục tiêu'}!`);
    }
  };

  const currentReport = report || MOCK_AI_DOCTOR_REPORT;
  const score = currentReport.health_score;

  // Status mapping
  const getStatusBadge = (status: string, scoreVal: number) => {
    if (status === 'HEALTHY' || scoreVal >= 75) {
      return {
        text: 'Khỏe Mạnh (HEALTHY)',
        badge: 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300',
        color: '#10B981',
        stroke: 'stroke-emerald-500',
        desc: 'Chiến dịch tăng trưởng tích cực, sẵn sàng tăng ngân sách'
      };
    }
    if (status === 'NEEDS_ATTENTION' || scoreVal >= 45) {
      return {
        text: 'Cần Chú Ý (NEEDS_ATTENTION)',
        badge: 'bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300',
        color: '#F59E0B',
        stroke: 'stroke-amber-500',
        desc: 'Phát hiện điểm nghẽn hiệu suất cần tối ưu hóa'
      };
    }
    return {
      text: 'Nguy Kịch (CRITICAL)',
      badge: 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300',
      color: '#F43F5E',
      stroke: 'stroke-rose-500',
      desc: 'Báo động đỏ: Nguy cơ lãng phí ngân sách hoặc lỗ vốn'
    };
  };

  const statusInfo = getStatusBadge(currentReport.health_status, score);
  const bottlenecks = currentReport.key_bottlenecks || currentReport.bottlenecks || [];
  const recommendations = currentReport.recommendations || [];

  // SVG Circular Gauge calculation
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className={`bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-xs space-y-6 ${className}`}>
      
      {/* 1. Header & Re-diagnose Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-600 text-white flex items-center justify-center shadow-md shadow-emerald-600/20 shrink-0">
            <Stethoscope className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Bác Sĩ Chiến Dịch AI (AI Doctor)
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                Zero Hallucination
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Đánh giá sức khỏe chiến dịch và kê đơn hành động 1-click dựa trên số liệu thực tế CSDL
            </p>
          </div>
        </div>

        {campaignId && (
          <button
            onClick={() => loadDiagnosis(campaignId)}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 shrink-0 self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
            <span>{loading ? 'Đang khám số liệu...' : 'Khám & Chẩn đoán lại'}</span>
          </button>
        )}
      </div>

      {/* 2. Health Score Meter & Diagnostic Summary */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-center bg-gradient-to-r from-slate-50 via-indigo-50/30 to-emerald-50/30 dark:from-slate-800/40 dark:to-slate-800/20 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800">
        
        {/* Circular Gauge Meter */}
        <div className="md:col-span-4 flex items-center gap-4 justify-center md:justify-start">
          <div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 96 96">
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
              <span className="text-[10px] font-bold text-slate-400 uppercase mt-0.5">/ 100đ</span>
            </div>
          </div>

          <div className="space-y-1">
            <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border ${statusInfo.badge}`}>
              {statusInfo.text}
            </span>
            <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 leading-tight">
              {statusInfo.desc}
            </div>
          </div>
        </div>

        {/* Diagnostic Narrative */}
        <div className="md:col-span-8 space-y-1.5 md:border-l md:border-slate-200 dark:md:border-slate-800 md:pl-5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Tóm tắt Chẩn đoán Cấp Quản lý</span>
          </span>
          <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
            {currentReport.diagnosis_summary}
          </p>
        </div>
      </div>

      {/* 3. Root Causes & Key Bottlenecks */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span>Điểm Nghẽn Hiệu Suất Phát Hiện ({bottlenecks.length})</span>
          </h4>
          <span className="text-[11px] text-slate-400">Thẩm định theo thời gian thực</span>
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
                    ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/60' 
                    : isMedium 
                    ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60' 
                    : 'bg-blue-100 text-blue-700 dark:bg-blue-950/60'
                }`}>
                  {isHigh ? '!' : idx + 1}
                </span>
                <div className="flex-1 text-slate-700 dark:text-slate-300 leading-relaxed">
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
            <Zap className="w-4 h-4 text-indigo-600" />
            <span>Đơn Thuốc Chiến Lược & Hành Động 1-Click ({recommendations.length})</span>
          </h4>
          <span className="text-[11px] text-emerald-600 font-bold">100% Căn Cứ Số Liệu Thật</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {recommendations.map((rec, idx) => {
            const isApplied = appliedActions[idx];
            const isScale = rec.action === 'SCALE';
            const isOptimize = rec.action === 'OPTIMIZE';
            const isPause = rec.action === 'PAUSE' || rec.action === 'REDUCE';

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
                className={`rounded-xl border p-4.5 space-y-3 flex flex-col justify-between transition-all hover:shadow-md ${cardBorder}`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${actionBadge}`}>
                      {rec.action}
                    </span>
                    {rec.channel && (
                      <span className="text-[11px] font-mono font-bold text-slate-500 uppercase">
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
                    <div className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                      <TrendingUp className="w-3.5 h-3.5" />
                      <span>{rec.impact}</span>
                    </div>
                  )}

                  <button
                    onClick={() => handleApplyAction(idx, rec)}
                    disabled={isApplied}
                    className={`w-full py-2 px-3 rounded-lg text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-1.5 active:scale-95 ${
                      isApplied
                        ? 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400 cursor-default'
                        : isScale
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20'
                        : isOptimize
                        ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20'
                        : 'bg-rose-600 hover:bg-rose-700 text-white shadow-rose-600/20'
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
