import React, { useState, useRef } from 'react';
import {
  Upload,
  FileSpreadsheet,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  X,
  Database,
  Layers,
  Check,
  PlusCircle,
  ShieldCheck,
} from 'lucide-react';
import { Campaign, SmartImportAnalysis, SmartImportCommitResult } from '../types';
import { metricsApi } from '../services/api';

interface GlobalCsvImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  campaigns?: Campaign[];
  workspaceId?: number;
  onSuccess?: (result: SmartImportCommitResult) => void;
}

const COLUMN_LABELS: Record<string, string> = {
  report_date: 'Ngày báo cáo',
  campaign_name: 'Tên / Mã Chiến dịch',
  channel: 'Kênh quảng cáo',
  views: 'Hiển thị (Impressions)',
  clicks: 'Lượt nhấp (Clicks)',
  conversions: 'Chuyển đổi (Đơn hàng)',
  cost: 'Chi phí (VND)',
  revenue: 'Doanh thu (VND)',
};

export const GlobalCsvImportModal: React.FC<GlobalCsvImportModalProps> = ({
  isOpen,
  onClose,
  campaigns = [],
  workspaceId,
  onSuccess,
}) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [csvText, setCsvText] = useState<string>('');
  const [fileName, setFileName] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isCommitting, setIsCommitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<SmartImportAnalysis | null>(null);
  const [commitResult, setCommitResult] = useState<SmartImportCommitResult | null>(null);
  const [autoCreateCampaigns, setAutoCreateCampaigns] = useState<boolean>(true);
  const [replaceSeedData, setReplaceSeedData] = useState<boolean>(true);
  const [customCampaignMap, setCustomCampaignMap] = useState<Record<string, number>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  if (!isOpen) return null;

  const buildSampleMultiCampaignCsv = (): string => {
    const activeNames = campaigns.slice(0, 3).map(c => c.name);
    const camp1 = activeNames[0] || 'Chiến dịch Ra mắt Sản phẩm AI Q4';
    const camp2 = activeNames[1] || 'Chiến dịch Retargeting Giỏ hàng Bỏ quên';
    const camp3 = activeNames[2] || 'Chiến dịch Mega Sale Đa Kênh 11.11';
    const campNew = 'Chiến dịch TikTok Shop Flash Sale Mới (Auto-Discovery)';

    const today = new Date();
    const fmtDate = (daysAgo: number) => {
      const d = new Date(today);
      d.setDate(d.getDate() - daysAgo);
      return d.toISOString().slice(0, 10);
    };

    const rows = [
      'Date,Campaign Name,Platform,Impressions,Clicks,Conversions,Spend (VND),Revenue (VND)',
      `${fmtDate(3)},"${camp1}",Facebook,48500,1420,68,6500000,24800000`,
      `${fmtDate(2)},"${camp1}",TikTok,62000,2150,94,7200000,31500000`,
      `${fmtDate(1)},"${camp1}",Facebook,51200,1680,79,6800000,28900000`,
      `${fmtDate(3)},"${camp2}",Facebook,29400,980,52,4100000,18600000`,
      `${fmtDate(2)},"${camp2}",Email,15800,1120,74,1200000,19400000`,
      `${fmtDate(1)},"${camp3}",TikTok,84000,3120,135,11500000,46200000`,
      `${fmtDate(1)},"${camp3}",Facebook,43000,1390,61,5900000,21300000`,
      `${fmtDate(1)},"${campNew}",TikTok,71500,2640,118,8900000,36800000`,
    ];
    return rows.join('\n');
  };

  const handleLoadSampleAndAnalyze = async () => {
    const sample = buildSampleMultiCampaignCsv();
    setCsvText(sample);
    setFileName('meta_tiktok_master_report_sample.csv');
    setErrorMsg(null);
    await runAnalyze(sample);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setErrorMsg(null);
    const reader = new FileReader();
    reader.onload = ev => {
      const content = String(ev.target?.result || '');
      setCsvText(content);
    };
    reader.readAsText(file, 'utf-8');
  };

  const runAnalyze = async (rawContent?: string) => {
    const contentToUse = (rawContent ?? csvText).trim();
    if (!contentToUse) {
      setErrorMsg('Vui lòng tải lên file CSV hoặc bấm nút nạp dữ liệu mẫu Đa Chiến dịch.');
      return;
    }
    setIsAnalyzing(true);
    setErrorMsg(null);
    try {
      const res = await metricsApi.analyzeSmartImport({
        csv_content: contentToUse,
        workspace_id: workspaceId,
      });
      setAnalysis(res);
      const initialMap: Record<string, number> = {};
      for (const m of res.campaign_matches || []) {
        if (m.matched_campaign_id) {
          initialMap[m.csv_campaign_name] = m.matched_campaign_id;
        }
      }
      setCustomCampaignMap(initialMap);
      setStep(2);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Không thể phân tích cấu trúc CSV.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCommit = async () => {
    if (!csvText.trim() || !analysis) return;
    setIsCommitting(true);
    setErrorMsg(null);
    try {
      const res = await metricsApi.commitSmartImport({
        csv_content: csvText,
        column_mapping: analysis.column_mapping,
        campaign_mapping: customCampaignMap,
        auto_create_campaigns: autoCreateCampaigns,
        replace_seed_data: replaceSeedData,
        workspace_id: workspaceId,
      });
      setCommitResult(res);
      if (onSuccess) {
        onSuccess(res);
      }
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Lỗi khi nạp dữ liệu hàng loạt.');
    } finally {
      setIsCommitting(false);
    }
  };

  const resetAndClose = () => {
    setStep(1);
    setAnalysis(null);
    setCommitResult(null);
    setErrorMsg(null);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto"
      data-testid="global-csv-import-modal"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 bg-[#121316] text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold tracking-tight">
                  Nhập báo cáo quảng cáo đa chiến dịch (CSV / TSV)
                </h3>
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-white/10 text-white/90 rounded border border-white/15">
                  Tự động nhận cột
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                Tự động nhận diện cột xuất từ Meta Ads, TikTok Ads, Google Ads và gộp vào từng chiến dịch.
              </p>
            </div>
          </div>
          <button
            onClick={resetAndClose}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            title="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="px-6 py-3 bg-[#FAF9F5] border-b border-[#E4E2DD] flex items-center justify-between text-xs font-semibold">
          <div className="flex items-center gap-6">
            <div className={`flex items-center gap-2 ${step === 1 ? 'text-[#121316]' : 'text-[#15803D]'}`}>
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  step === 1 ? 'bg-[#121316] text-white' : 'bg-[#ECFDF5] text-[#15803D]'
                }`}
              >
                {step > 1 ? <Check className="w-3.5 h-3.5" /> : '1'}
              </span>
              <span>Bước 1: Chọn tệp báo cáo CSV</span>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-300" />
            <div className={`flex items-center gap-2 ${step === 2 ? 'text-[#121316]' : 'text-slate-400'}`}>
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  step === 2 ? 'bg-[#121316] text-white' : 'bg-slate-200 text-slate-500'
                }`}
              >
                2
              </span>
              <span>Bước 2: Kiểm tra ánh xạ cột & lưu vào chiến dịch</span>
            </div>
          </div>
          {fileName && (
            <span className="px-2.5 py-1 rounded-md bg-white text-[#121316] border border-[#E4E2DD] font-mono text-[11px]">
              {fileName}
            </span>
          )}
        </div>

        {/* Body */}
        <div className="p-6 max-h-[72vh] overflow-y-auto space-y-5">
          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
              <div className="flex-1 font-medium">{errorMsg}</div>
            </div>
          )}

          {commitResult ? (
            <div className="p-6 rounded-2xl bg-emerald-50/70 border border-emerald-200 text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div>
                <h4 className="text-lg font-bold text-slate-900">
                  Đồng bộ Báo cáo Đa Chiến dịch Thành công!
                </h4>
                <p className="text-xs text-slate-600 mt-1">
                  {commitResult.message || 'Toàn bộ số liệu hiệu suất thực tế đã được ghi nhận vào hệ thống.'}
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3 max-w-lg mx-auto pt-2">
                <div className="p-3 rounded-xl bg-white border border-emerald-200">
                  <div className="text-[11px] text-slate-500">Dòng dữ liệu đã nạp</div>
                  <div className="text-lg font-extrabold font-mono tabular-nums text-slate-900 mt-0.5">
                    {commitResult.imported_rows}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-white border border-emerald-200">
                  <div className="text-[11px] text-slate-500">Chiến dịch cập nhật</div>
                  <div className="text-lg font-extrabold font-mono tabular-nums text-[#121316] mt-0.5">
                    {commitResult.updated_campaigns_count}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-white border border-emerald-200">
                  <div className="text-[11px] text-slate-500">Chiến dịch tạo mới</div>
                  <div className="text-lg font-extrabold font-mono tabular-nums text-emerald-600 mt-0.5">
                    +{commitResult.created_campaigns_count}
                  </div>
                </div>
              </div>
              <div className="pt-3">
                <button
                  onClick={resetAndClose}
                  className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-sm transition-all"
                  data-testid="global-csv-close-after-success"
                >
                  Hoàn tất & Xem Bảng Điều Khiển
                </button>
              </div>
            </div>
          ) : step === 1 ? (
            <div className="space-y-4">
              {/* Quick Template Banner */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E4E2DD] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-[#121316]">
                    <Sparkles className="w-4 h-4 text-[#D95D39]" />
                    <span>Nạp biểu mẫu báo cáo chuẩn Meta Ads & TikTok Ads</span>
                  </div>
                  <p className="text-[11px] text-[#5A5E66]">
                    Nạp cấu trúc tệp CSV xuất từ trình quản lý quảng cáo gồm nhiều chiến dịch và kênh để kiểm tra ánh xạ cột.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleLoadSampleAndAnalyze}
                  disabled={isAnalyzing}
                  data-testid="global-csv-load-sample-btn"
                  className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-bold transition-all disabled:opacity-50"
                >
                  {isAnalyzing ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  Tải dữ liệu mẫu Đa Chiến dịch chuẩn Meta/TikTok Ads
                </button>
              </div>

              {/* Upload Dropzone */}
              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                className="border-2 border-dashed border-slate-300 hover:border-indigo-400 bg-slate-50/70 hover:bg-indigo-50/30 rounded-2xl p-6 text-center cursor-pointer transition-all"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="w-11 h-11 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-center mx-auto mb-2.5 text-indigo-600">
                  <Upload className="w-5 h-5" />
                </div>
                <p className="text-xs font-bold text-slate-800">
                  Kéo thả file <span className="text-indigo-600">.CSV</span> từ trình quản lý quảng cáo hoặc bấm để chọn file
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Hỗ trợ xuất thô từ Facebook Ads Manager, TikTok Ads, Google Ads (Tự động nhận diện tiếng Việt & tiếng Anh)
                </p>
              </div>

              {/* Raw CSV Textarea */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-bold text-slate-700">
                    Hoặc dán trực tiếp dữ liệu CSV đa chiến dịch tại đây:
                  </label>
                  <button
                    type="button"
                    onClick={() => setCsvText(buildSampleMultiCampaignCsv())}
                    className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    Điền mẫu CSV vào ô bên dưới
                  </button>
                </div>
                <textarea
                  rows={7}
                  value={csvText}
                  onChange={e => setCsvText(e.target.value)}
                  placeholder="Date,Campaign Name,Platform,Impressions,Clicks,Conversions,Spend (VND),Revenue (VND)&#10;2026-10-14,Chiến dịch Ra mắt Q4,Facebook,48500,1420,68,6500000,24800000"
                  data-testid="global-csv-textarea"
                  className="w-full rounded-xl border border-slate-300 bg-slate-900 text-emerald-300 font-mono text-xs p-3.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          ) : (
            analysis && (
              <div className="space-y-5">
                {/* Summary KPI Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-[11px] text-slate-500 font-medium">Tổng dòng hợp lệ</div>
                    <div className="text-base font-extrabold text-slate-900 mt-0.5">
                      {analysis.total_rows} dòng
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-[11px] text-slate-500 font-medium">Chiến dịch phát hiện</div>
                    <div className="text-base font-extrabold text-indigo-600 mt-0.5">
                      {analysis.campaign_matches.length} chiến dịch
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-[11px] text-slate-500 font-medium">Tổng Chi tiêu (Spend)</div>
                    <div className="text-base font-extrabold text-slate-900 mt-0.5">
                      {(analysis.summary?.total_cost || 0).toLocaleString('vi-VN')} ₫
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-[11px] text-slate-500 font-medium">Tổng Doanh thu</div>
                    <div className="text-base font-extrabold text-emerald-600 mt-0.5">
                      {(analysis.summary?.total_revenue || 0).toLocaleString('vi-VN')} ₫
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-indigo-50/70 border border-indigo-200">
                    <div className="text-[11px] text-indigo-700 font-semibold">ROAS Trung bình</div>
                    <div className="text-base font-extrabold text-indigo-700 mt-0.5">
                      {analysis.summary?.estimated_roas || 0}x
                    </div>
                  </div>
                </div>

                {/* AI Auto-Mapped Columns */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                      <Database className="w-4 h-4 text-indigo-600" />
                      <span>Ánh xạ cột tự động (AI Schema Detection)</span>
                    </div>
                    <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                      Đã khớp {Object.keys(analysis.column_mapping || {}).length}/8 trường chuẩn
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {Object.entries(COLUMN_LABELS).map(([fieldKey, label]) => {
                      const mappedCol = analysis.column_mapping?.[fieldKey];
                      return (
                        <div
                          key={fieldKey}
                          className="p-2 rounded-lg bg-white border border-slate-200 flex flex-col justify-between"
                        >
                          <span className="text-[10px] font-semibold text-slate-500">{label}</span>
                          <span className="text-xs font-bold text-slate-900 font-mono truncate mt-0.5">
                            {mappedCol || 'Tự động suy luận'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Campaign Matching Table */}
                <div className="rounded-xl border border-slate-200 overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-100 border-b border-slate-200 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                      <Layers className="w-4 h-4 text-indigo-600" />
                      <span>Bảng Khớp Chiến Dịch Tự Động ({analysis.campaign_matches.length} chiến dịch)</span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] font-semibold">
                      <span className="text-emerald-700">
                        ● Đã khớp sẵn: {analysis.matched_count}
                      </span>
                      <span className="text-amber-700">
                        ● Chiến dịch mới phát hiện: {analysis.unmatched_count}
                      </span>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-50 text-slate-500 border-b border-slate-200 text-[11px] uppercase">
                          <th className="py-2.5 px-3 font-semibold">Tên Chiến dịch trong CSV</th>
                          <th className="py-2.5 px-3 font-semibold">Kênh</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Số dòng</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Chi tiêu</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Doanh thu</th>
                          <th className="py-2.5 px-3 font-semibold">Đích ánh xạ trong Hệ thống</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {analysis.campaign_matches.map((m, idx) => {
                          const selectedId = customCampaignMap[m.csv_campaign_name] ?? m.matched_campaign_id ?? 0;
                          return (
                            <tr key={idx} className="hover:bg-slate-50/80">
                              <td className="py-2.5 px-3 font-bold text-slate-900">
                                {m.csv_campaign_name}
                              </td>
                              <td className="py-2.5 px-3">
                                <div className="flex flex-wrap gap-1">
                                  {(m.channels || []).map((ch, cIdx) => (
                                    <span
                                      key={cIdx}
                                      className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-semibold text-[10px]"
                                    >
                                      {ch}
                                    </span>
                                  ))}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                                {m.row_count}
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-800">
                                {(m.total_cost || 0).toLocaleString('vi-VN')} ₫
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-600">
                                {(m.total_revenue || 0).toLocaleString('vi-VN')} ₫
                              </td>
                              <td className="py-2.5 px-3">
                                {campaigns.length > 0 ? (
                                  <select
                                    value={selectedId}
                                    onChange={e => {
                                      const val = Number(e.target.value);
                                      setCustomCampaignMap(prev => {
                                        const next = { ...prev };
                                        if (val > 0) next[m.csv_campaign_name] = val;
                                        else delete next[m.csv_campaign_name];
                                        return next;
                                      });
                                    }}
                                    className={`w-full rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${
                                      selectedId > 0
                                        ? 'border-emerald-300 bg-emerald-50/60 text-emerald-900'
                                        : 'border-amber-300 bg-amber-50/60 text-amber-900'
                                    }`}
                                  >
                                    <option value={0}>
                                      Tự động khởi tạo chiến dịch mới
                                    </option>
                                    {campaigns.map(c => (
                                      <option key={c.id} value={c.id}>
                                        Khớp: #{c.id} — {c.name}
                                      </option>
                                    ))}
                                  </select>
                                ) : selectedId > 0 ? (
                                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-semibold">
                                    <Check className="w-3 h-3" /> {m.matched_campaign_name || `Chiến dịch #${selectedId}`}
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[11px] font-semibold">
                                    <PlusCircle className="w-3 h-3" /> Sẽ tạo chiến dịch mới
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Smart Options Checkboxes */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <label className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200 cursor-pointer hover:border-indigo-300 transition-colors">
                    <input
                      type="checkbox"
                      checked={autoCreateCampaigns}
                      onChange={e => setAutoCreateCampaigns(e.target.checked)}
                      className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-800">
                        Tự động khởi tạo chiến dịch mới nếu chưa có
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Các chiến dịch phát hiện mới trong CSV sẽ được tạo tự động với trạng thái ACTIVE và ngân sách ước tính.
                      </div>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200 cursor-pointer hover:border-indigo-300 transition-colors">
                    <input
                      type="checkbox"
                      checked={replaceSeedData}
                      onChange={e => setReplaceSeedData(e.target.checked)}
                      className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                        <span>Thay thế dữ liệu mẫu (Seed) bằng số liệu thực</span>
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Xóa bỏ các dòng số liệu khởi tạo mẫu (`seed`) của chiến dịch được nạp để báo cáo phản ánh 100% số đo thật.
                      </div>
                    </div>
                  </label>
                </div>
              </div>
            )
          )}
        </div>

        {/* Footer */}
        {!commitResult && (
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
            {step === 2 ? (
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-4 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700"
              >
                ← Quay lại chỉnh sửa CSV
              </button>
            ) : (
              <div className="text-[11px] text-slate-500">
                Mẹo: Bạn có thể gộp báo cáo của cả tháng từ nhiều tài khoản quảng cáo vào chung 1 file.
              </div>
            )}

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={resetAndClose}
                className="px-4 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-600"
              >
                Hủy
              </button>
              {step === 1 ? (
                <button
                  type="button"
                  onClick={() => runAnalyze()}
                  disabled={isAnalyzing || !csvText.trim()}
                  data-testid="global-csv-analyze-btn"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-sm transition-all disabled:opacity-50"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Đang phân tích cấu trúc...</span>
                    </>
                  ) : (
                    <>
                      <span>Phân tích & Khớp Chiến dịch</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleCommit}
                  disabled={isCommitting}
                  data-testid="global-csv-commit-btn"
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50"
                >
                  {isCommitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Đang nạp hàng loạt...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Xác nhận Nạp Hàng Loạt ({analysis?.total_rows || 0} dòng)</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
