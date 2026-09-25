import React, { useState } from 'react';
import { FileSpreadsheet, Printer, Copy, Check, Sparkles } from 'lucide-react';
import { MarketingContent } from '../types';
import { exportCampaignContentsToCSV, printCampaignPlan } from '../utils/exportUtils';
import { copyToClipboardWithFormatting } from '../utils/copyUtils';

export interface ExportActionsProps {
  campaignName?: string;
  contents: MarketingContent[];
  className?: string;
}

export const ExportActions: React.FC<ExportActionsProps> = ({
  campaignName = 'Kế Hoạch Marketing Đa Kênh',
  contents,
  className = ''
}) => {
  const [copiedAll, setCopiedAll] = useState(false);

  const handleExportCSV = () => {
    exportCampaignContentsToCSV(campaignName, contents);
  };

  const handlePrint = () => {
    printCampaignPlan(contents, campaignName);
  };

  const handleCopyAllContents = async () => {
    if (!contents || contents.length === 0) {
      alert('Không có nội dung để sao chép.');
      return;
    }

    const textBlocks = contents.map((c, idx) => {
      const channel = c.channel?.name || (c.channel_id === 1 ? 'Facebook' : c.channel_id === 4 ? 'TikTok' : 'Email');
      return `========================================\n[ BÀI VIẾT #${idx + 1} - ${channel.toUpperCase()} ]\nTIÊU ĐỀ: ${c.title}\n\nNỘI DUNG:\n${c.body}\n${c.cta ? `\n👉 CTA: ${c.cta}` : ''}${c.image_url ? `\n🖼️ ẢNH: ${c.image_url}` : ''}\nTRẠNG THÁI: ${c.status}`;
    });

    const fullExportText = `📋 KẾ HOẠCH CHIẾN DỊCH: ${campaignName.toUpperCase()}\nTổng số nội dung: ${contents.length}\nNgày tạo: ${new Date().toLocaleDateString('vi-VN')}\n\n${textBlocks.join('\n\n')}`;

    const ok = await copyToClipboardWithFormatting(fullExportText);
    if (ok) {
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2500);
    }
  };

  return (
    <div className={`flex flex-wrap items-center gap-2 p-2 bg-slate-50/90 rounded-xl border border-slate-200/80 shadow-2xs no-print export-actions ${className}`}>
      <span className="text-xs font-semibold text-slate-600 px-2 flex items-center gap-1.5 hidden sm:inline-flex">
        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
        Công cụ thao tác:
      </span>

      {/* Nút 1-Click Copy toàn bộ */}
      <button
        onClick={handleCopyAllContents}
        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 border shadow-2xs ${
          copiedAll
            ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
            : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200 hover:text-indigo-600'
        }`}
      >
        {copiedAll ? (
          <>
            <Check className="w-3.5 h-3.5 text-emerald-600" />
            <span className="font-semibold text-emerald-600">Đã copy toàn bộ!</span>
          </>
        ) : (
          <>
            <Copy className="w-3.5 h-3.5 text-slate-500" />
            <span>Copy format chuẩn</span>
          </>
        )}
      </button>

      {/* Nút Xuất Excel (.csv) */}
      <button
        onClick={handleExportCSV}
        className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 border border-slate-200 hover:border-emerald-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow-2xs"
      >
        <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
        <span>Xuất Excel (.csv BOM)</span>
      </button>

      {/* Nút In / Xuất PDF */}
      <button
        onClick={handlePrint}
        className="px-3 py-1.5 bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 border border-slate-200 hover:border-indigo-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow-2xs"
      >
        <Printer className="w-3.5 h-3.5 text-indigo-600" />
        <span>In / Lưu PDF</span>
      </button>
    </div>
  );
};
