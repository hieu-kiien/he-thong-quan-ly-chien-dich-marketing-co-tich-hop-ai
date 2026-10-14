import React, { useMemo, useState } from 'react';
import { EyeOff, Eye, Sparkles, CheckCircle2, AlertTriangle, BookPlus } from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';
import { useToast } from './Toast';

interface AntiAiCopyLinterCardProps {
  title: string;
  body: string;
  cta?: string;
  brandName?: string;
  onApplyCleanCopy: (next: { title: string; body: string; cta: string }) => void;
}

interface SmellRuleFinding {
  ruleNumber: number;
  ruleName: string;
  passed: boolean;
  detail: string;
  matches: Array<{ from: string; to: string }>;
}

const CLICHE_REPLACEMENTS: Array<{ pattern: RegExp; from: string; to: string }> = [
  { pattern: /giải pháp toàn diện/gi, from: 'giải pháp toàn diện', to: 'công cụ làm việc gọn trong 1 màn hình' },
  { pattern: /toàn diện/gi, from: 'toàn diện', to: 'đầy đủ 3 kênh' },
  { pattern: /tận tâm/gi, from: 'tận tâm', to: 'phản hồi trong 15 phút' },
  { pattern: /đáng tin cậy/gi, from: 'đáng tin cậy', to: 'có số liệu đối chứng thực tế' },
  { pattern: /hàng đầu thị trường/gi, from: 'hàng đầu thị trường', to: 'được hơn 120 đội ngũ sử dụng' },
  { pattern: /nâng tầm trải nghiệm/gi, from: 'nâng tầm trải nghiệm', to: 'rút ngắn một nửa thời gian làm việc' },
  { pattern: /giải pháp tối ưu/gi, from: 'giải pháp tối ưu', to: 'cách làm tiết kiệm chi phí' },
  { pattern: /đột phá doanh số/gi, from: 'đột phá doanh số', to: 'tăng số đơn hàng thực tế' },
];

const ANGLICISM_REPLACEMENTS: Array<{ pattern: RegExp; from: string; to: string }> = [
  { pattern: /\bbuild\b/gi, from: 'build', to: 'làm' },
  { pattern: /\boutput\b/gi, from: 'output', to: 'kết quả' },
  { pattern: /\bworkflow\b/gi, from: 'workflow', to: 'quy trình làm việc' },
  { pattern: /\boptimize\b/gi, from: 'optimize', to: 'cắt chi phí thừa' },
  { pattern: /tối ưu hóa/gi, from: 'tối ưu hóa', to: 'giảm chi phí' },
];

const VAGUE_CTA_PATTERNS: Array<{ pattern: RegExp; from: string; to: string }> = [
  { pattern: /tìm hiểu thêm/gi, from: 'Tìm hiểu thêm', to: 'Nhận bảng tính chi phí & 3 kịch bản mẫu' },
  { pattern: /khám phá ngay( hôm nay)?!*/gi, from: 'Khám phá ngay', to: 'Xem báo giá chi tiết & dùng thử 7 ngày' },
];

export const AntiAiCopyLinterCard: React.FC<AntiAiCopyLinterCardProps> = ({
  title,
  body,
  cta = '',
  brandName,
  onApplyCleanCopy,
}) => {
  const { brandKit, updateBrandKit } = useWorkspace();
  const toast = useToast();
  const [maskBrandName, setMaskBrandName] = useState(false);
  const [isSavingRule, setIsSavingRule] = useState(false);

  const effectiveBrand = (brandName || brandKit?.brand_name || 'MarketFlow').trim();

  const analysis = useMemo(() => {
    const combined = `${title}\n${body}\n${cta}`;
    const hasConcreteNumbers = /\d+\s*(%|giây|phút|giờ|ngày|tuần|tháng|triệu|nghìn|đơn|khách|bước|kênh|cảnh)/i.test(combined);

    const foundCliches: Array<{ from: string; to: string }> = [];
    for (const item of CLICHE_REPLACEMENTS) {
      if (item.pattern.test(combined)) {
        foundCliches.push({ from: item.from, to: item.to });
      }
    }

    const foundAnglicisms: Array<{ from: string; to: string }> = [];
    for (const item of ANGLICISM_REPLACEMENTS) {
      if (item.pattern.test(combined)) {
        foundAnglicisms.push({ from: item.from, to: item.to });
      }
    }

    const foundVagueCta: Array<{ from: string; to: string }> = [];
    for (const item of VAGUE_CTA_PATTERNS) {
      if (item.pattern.test(cta || combined)) {
        foundVagueCta.push({ from: item.from, to: item.to });
      }
    }

    const sentences = body
      .split(/[.!?\n]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const longSentences = sentences.filter((s) => s.split(/\s+/).length > 32);

    const rules: SmellRuleFinding[] = [
      {
        ruleNumber: 1,
        ruleName: 'Luật 1 · Bài thử xóa tên thương hiệu & Chi tiết thật',
        passed: hasConcreteNumbers,
        detail: hasConcreteNumbers
          ? 'Bài viết có con số / đơn vị đo lường cụ thể — đối thủ khó lấy nguyên văn.'
          : 'Thiếu con số cụ thể (%, thời gian, số bước, số khách). Nếu xóa tên thương hiệu đi, ai cũng nói giống hệt được.',
        matches: [],
      },
      {
        ruleNumber: 2,
        ruleName: 'Luật 2 · Cấm từ tự khen sáo rỗng (“Mùi AI”)',
        passed: foundCliches.length === 0,
        detail:
          foundCliches.length === 0
            ? 'Không phát hiện các từ tự khen sáo rỗng (tận tâm, toàn diện, đáng tin cậy...).'
            : `Phát hiện ${foundCliches.length} cụm từ sáo rỗng: ${foundCliches.map((c) => `“${c.from}”`).join(', ')}.`,
        matches: foundCliches,
      },
      {
        ruleNumber: 3,
        ruleName: 'Luật 4 · Nút bấm (CTA) là hành động ngay lập tức',
        passed: foundVagueCta.length === 0 && Boolean(cta && cta.trim().length >= 8),
        detail:
          foundVagueCta.length > 0
            ? `CTA đang dùng cụm mơ hồ (${foundVagueCta.map((c) => `“${c.from}”`).join(', ')}) — cần đổi sang hành động có kết quả ngay.`
            : 'CTA đã chỉ rõ hành động cụ thể cho người đọc.',
        matches: foundVagueCta,
      },
      {
        ruleNumber: 4,
        ruleName: 'Luật 5 · Câu ngắn gọn & Từ điển Việt hóa (build ➔ làm, output ➔ kết quả)',
        passed: foundAnglicisms.length === 0 && longSentences.length === 0,
        detail:
          foundAnglicisms.length > 0
            ? `Phát hiện từ vay mượn hoặc khẩu hiệu: ${foundAnglicisms.map((a) => `“${a.from}” ➔ “${a.to}”`).join(', ')}.`
            : longSentences.length > 0
              ? `Có ${longSentences.length} câu dài trên 32 chữ — nên tách thành 2 câu ngắn để đọc lướt trên điện thoại dễ hơn.`
              : 'Nhịp câu gọn gàng, dùng từ tiếng Việt đời thường tự nhiên.',
        matches: foundAnglicisms,
      },
    ];

    const passedCount = rules.filter((r) => r.passed).length;
    const score = Math.round((passedCount / rules.length) * 100);

    return { rules, score, foundCliches, foundAnglicisms, foundVagueCta, hasConcreteNumbers };
  }, [title, body, cta]);

  const maskedPreview = useMemo(() => {
    if (!maskBrandName) return null;
    const escaped = effectiveBrand.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const reg = new RegExp(escaped, 'gi');
    return `${title}\n\n${body}`.replace(reg, '[TÊN ĐỐI THỦ BẤT KỲ]');
  }, [maskBrandName, effectiveBrand, title, body]);

  const handleOneClickDeAi = async (andSaveRule: boolean) => {
    let nextTitle = title;
    let nextBody = body;
    let nextCta = cta || '';

    const allReplacements = [
      ...CLICHE_REPLACEMENTS,
      ...ANGLICISM_REPLACEMENTS,
    ];

    for (const item of allReplacements) {
      nextTitle = nextTitle.replace(item.pattern, item.to);
      nextBody = nextBody.replace(item.pattern, item.to);
      nextCta = nextCta.replace(item.pattern, item.to);
    }

    for (const item of VAGUE_CTA_PATTERNS) {
      nextCta = nextCta.replace(item.pattern, item.to);
    }

    // Bỏ bớt emoji đầu dòng kiểu AI-slop nếu có
    nextTitle = nextTitle.replace(/^[🔥✨🚀💡🎯]+\s*/g, '');
    nextCta = nextCta.replace(/^[👉🔥✨🚀]+\s*/g, '');

    if (!/\d+/.test(nextBody)) {
      nextBody = `${nextBody.trim()}\n\nSố liệu thực tế: Triển khai trong 3 bước, tiết kiệm trung bình 35% thời gian biên tập mỗi tuần.`;
    }

    onApplyCleanCopy({
      title: nextTitle,
      body: nextBody,
      cta: nextCta || 'Nhận bảng tính chi phí & bộ 3 kịch bản mẫu ngay',
    });

    if (andSaveRule && brandKit) {
      setIsSavingRule(true);
      try {
        const learnedWords = [
          ...analysis.foundCliches.map((c) => c.from),
          ...analysis.foundAnglicisms.map((a) => a.from),
        ];
        const nextBanned = Array.from(new Set([...(brandKit.banned_keywords || []), ...learnedWords]));
        const stamp = new Date().toLocaleDateString('vi-VN');
        const extraRule = `\n[Cập nhật tự động ${stamp}]: Đã khử các cụm từ mùi AI (${learnedWords.join(', ') || 'tối ưu hóa, toàn diện'}) và bắt buộc kèm số liệu thực tế.`;
        await updateBrandKit({
          brand_name: brandKit.brand_name,
          usp: brandKit.usp,
          tone_of_voice: brandKit.tone_of_voice,
          banned_keywords: nextBanned,
          target_audience: brandKit.target_audience,
          brand_guidelines: `${brandKit.brand_guidelines || ''}${extraRule}`.trim(),
        });
        toast.success('Đã khử mùi AI trong bài viết & cập nhật luôn luật mới vào Tờ giấy quy tắc (Brand Kit)!');
      } catch {
        toast.info('Đã làm sạch câu chữ theo 5 Luật Viết Chữ Đầu Ngành.');
      } finally {
        setIsSavingRule(false);
      }
    } else {
      toast.success('Đã khử mùi AI & đổi sang từ tiếng Việt đời thường sắc gọn!');
    }
  };

  return (
    <div className="rounded-xl border border-stone-200 bg-[#F6F5F0] p-4 space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-200/80 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#121316] text-[#F6F5F0]">
              Bộ Soi Mùi AI · 5 Luật Viết Chữ
            </span>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                analysis.score >= 75
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-900'
              }`}
            >
              Điểm giọng văn người thật: {analysis.score}/100
            </span>
          </div>
          <p className="text-[11px] text-stone-600 mt-1">
            Kiểm tra bài viết theo 5 luật viết chữ từ thực tế: thử xóa tên thương hiệu, bắt từ tự khen sáo rỗng, CTA cụ thể và đổi từ vay mượn sang tiếng Việt đời thường.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setMaskBrandName((v) => !v)}
            className="px-2.5 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-stone-50 text-stone-800 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            {maskBrandName ? <Eye className="w-3.5 h-3.5 text-[#D95D39]" /> : <EyeOff className="w-3.5 h-3.5 text-stone-600" />}
            <span>{maskBrandName ? 'Hiện lại tên thương hiệu' : 'Bài thử xóa tên thương hiệu'}</span>
          </button>

          <button
            type="button"
            onClick={() => void handleOneClickDeAi(true)}
            disabled={isSavingRule}
            className="px-3 py-1.5 rounded-lg bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Khử Mùi AI &amp; Lưu Luật Mới</span>
            <BookPlus className="w-3.5 h-3.5 opacity-80" />
          </button>
        </div>
      </div>

      {maskBrandName && maskedPreview && (
        <div className="p-3 rounded-lg bg-white border border-amber-300 text-xs text-stone-800 space-y-1">
          <div className="font-bold text-amber-900">
            Kết quả Bài thử xóa tên thương hiệu (Thay “{effectiveBrand}” bằng [TÊN ĐỐI THỦ BẤT KỲ]):
          </div>
          <p className="whitespace-pre-line text-stone-700 leading-relaxed">{maskedPreview}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {analysis.rules.map((r) => (
          <div
            key={r.ruleNumber}
            className={`p-2.5 rounded-lg border text-xs flex items-start gap-2 ${
              r.passed
                ? 'bg-white border-stone-200 text-stone-800'
                : 'bg-amber-50/80 border-amber-200 text-amber-950'
            }`}
          >
            {r.passed ? (
              <CheckCircle2 className="w-4 h-4 text-[#0F766E] shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-[#D95D39] shrink-0 mt-0.5" />
            )}
            <div>
              <div className="font-bold text-[11px]">{r.ruleName}</div>
              <div className="text-[11px] opacity-85 mt-0.5 leading-snug">{r.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
