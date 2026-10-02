import React, { useState, useRef, useEffect } from 'react';
import { FileSpreadsheet, Printer, Copy, Check, Sparkles } from 'lucide-react';
import { MarketingContent } from '../types';
import { exportCampaignContentsToCSV, printCampaignPlan } from '../utils/exportUtils';
import { copyToClipboardWithFormatting } from '../utils/copyUtils';
import { channelNameById } from '../utils/channels';
import { formatDateVN } from '../utils/format';
import { useToast } from './Toast';

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
  const toast = useToast();
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
    };
  }, []);

  const handleExportCSV = () => {
    exportCampaignContentsToCSV(campaignName, contents);
  };

  const handlePrint = () => {
    printCampaignPlan(contents, campaignName);
  };

  const handleCopyAllContents = async () => {
    if (!contents || contents.length === 0) {
      // alert() native chặn toàn bộ luồng UI, lệch với hệ Toast của ứng dụng.
      toast.warning('Không có nội dung để sao chép');
      return;
    }

    const textBlocks = contents.map((c, idx) => {
      const channel = c.channel?.name || channelNameById(c.channel_id);
      return `========================================\n[ BÀI VIẾT #${idx + 1} - ${channel.toUpperCase()} ]\nTIÊU ĐỀ: ${c.title}\n\nNỘI DUNG:\n${c.body}\n${c.cta ? `\n👉 CTA: ${c.cta}` : ''}${c.image_url ? `\n🖼️ ẢNH: ${c.image_url}` : ''}\nTRẠNG THÁI: ${c.status}`;
    });

    const fullExportText = `📋 KẾ HOẠCH CHIẾN DỊCH: ${campaignName.toUpperCase()}\nTổng số nội dung: ${contents.length}\nNgày tạo: ${formatDateVN(new Date())}\n\n${textBlocks.join('\n\n')}`;

    const ok = await copyToClipboardWithFormatting(fullExportText);
    if (ok) {
      setCopiedAll(true);
      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
      resetTimerRef.current = setTimeout(() => setCopiedAll(false), 2500);
    } else {
      // Promise của clipboard có thể reject (HTTP, quyền bị chặn, trình duyệt cũ).
      // Không được báo "Đã copy" khi thực tế chưa copy được gì.
      toast.error('Trình duyệt từ chối ghi vào clipboard', 'Không sao chép được nội dung');
    }
  };

  return (
    <div className={`flex flex-wrap items-center gap-2 p-2 bg-slate-50/90 rounded-xl border border-slate-200/80 shadow no-print export-actions ${className}`}>
      <span className="text-xs font-semibold text-slate-600 px-2 flex items-center gap-1.5 hidden sm:inline-flex">
        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
        Công cụ thao tác:
      </span>

      {/* Nút 1-Click Copy toàn bộ */}
      <button
        onClick={handleCopyAllContents}
        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 border shadow ${
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
        className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 border border-slate-200 hover:border-emerald-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow"
      >
        <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
        <span>Xuất Excel (.csv BOM)</span>
      </button>

      {/* Nút In / Xuất PDF */}
      <button
        onClick={handlePrint}
        className="px-3 py-1.5 bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 border border-slate-200 hover:border-indigo-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow"
      >
        <Printer className="w-3.5 h-3.5 text-indigo-600" />
        <span>In / Lưu PDF</span>
      </button>
    </div>
  );
};
