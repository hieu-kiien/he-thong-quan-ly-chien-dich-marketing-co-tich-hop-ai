import React, { useState } from 'react';
import { Mail, Star, Archive, Trash2, Eye, ShieldCheck, ArrowLeft, Printer, Image as ImageIcon, CheckCircle2 } from 'lucide-react';
import { ImageAttachmentPicker } from './ImageAttachmentPicker';

export interface EmailInboxPreviewProps {
  brandName?: string;
  senderEmail?: string;
  recipientEmail?: string;
  subjectOptions?: string[];
  subjectLineA?: string;
  subjectLineB?: string;
  activeSubjectIndex?: number;
  preheader?: string;
  greeting?: string;
  body?: string;
  bodyContent?: string;
  ctaButton?: string;
  ctaUrl?: string;
  psNote?: string;
  imageUrl?: string;
  receivedTime?: string;
  onImageChange?: (newUrl: string) => void;
  showImagePicker?: boolean;
}

export const EmailInboxPreview: React.FC<EmailInboxPreviewProps> = ({
  brandName = 'MarketFlow AI',
  senderEmail = 'contact@marketflow.ai',
  recipientEmail = 'nguyen.van.a@doanhnghiep.vn',
  subjectOptions,
  subjectLineA,
  subjectLineB,
  preheader = 'Đừng bỏ lỡ ưu đãi đặc quyền dành riêng cho khách hàng doanh nghiệp tiên phong...',
  greeting = 'Chào bạn thân mến,',
  body = '',
  bodyContent,
  ctaButton = 'ĐĂNG KÝ TRẢI NGHIỆM MIỄN PHÍ NGAY',
  psNote = 'P.S. Chương trình dùng thử Enterprise 14 ngày chỉ áp dụng cho 50 tài khoản đăng ký đầu tiên.',
  imageUrl,
  receivedTime = '10:45 AM',
  onImageChange
}) => {
  const effectiveSubjectOptions = subjectOptions || [
    subjectLineA || '🔥 [Chỉ 48H] Giải pháp tự động hóa Marketing x3 ROI doanh nghiệp',
    ...(subjectLineB ? [subjectLineB] : ['Bí quyết cắt giảm 40% chi phí quảng cáo với MarketFlow AI'])
  ];
  const effectiveBody = bodyContent || body || '';
  const [viewMode, setViewMode] = useState<'INBOX_ROW' | 'FULL_READER'>('INBOX_ROW');
  const [selectedSubjectIdx, setSelectedSubjectIdx] = useState<number>(0);
  const [isStarred, setIsStarred] = useState(false);
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const activeSubject = effectiveSubjectOptions[selectedSubjectIdx] || effectiveSubjectOptions[0] || 'Thông báo từ MarketFlow AI';

  return (
    <div className="w-full max-w-xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden text-slate-800 font-sans transition-all duration-200 hover:shadow-md">
      {/* Dual Mode Switcher Bar */}
      <div className="bg-slate-100/90 px-4 py-2 border-b border-slate-200 flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 font-semibold text-slate-700">
          <Mail className="w-4 h-4 text-indigo-600" />
          <span>Email Marketing Simulator</span>
        </div>

        {/* View Mode Toggle Buttons */}
        <div className="flex bg-slate-200/80 p-0.5 rounded-lg border border-slate-300/60">
          <button
            onClick={() => setViewMode('INBOX_ROW')}
            className={`px-2.5 py-1 rounded-md font-medium text-[11px] transition ${
              viewMode === 'INBOX_ROW'
                ? 'bg-white text-indigo-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            📋 Hàng Hộp Thư (Inbox)
          </button>
          <button
            onClick={() => setViewMode('FULL_READER')}
            className={`px-2.5 py-1 rounded-md font-medium text-[11px] transition ${
              viewMode === 'FULL_READER'
                ? 'bg-white text-indigo-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            📖 Đọc Thư Chi Tiết (Reader)
          </button>
        </div>
      </div>

      {/* A/B Subject Variant Selector Bar */}
      {effectiveSubjectOptions.length > 1 && (
        <div className="bg-indigo-50/60 px-4 py-1.5 border-b border-indigo-100 flex items-center justify-between text-xs">
          <span className="text-[11px] font-semibold text-indigo-900 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-600"></span>
            A/B Subject Testing:
          </span>
          <div className="flex items-center gap-1.5">
            {effectiveSubjectOptions.map((subj, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedSubjectIdx(idx)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                  selectedSubjectIdx === idx
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-100'
                }`}
              >
                Tiêu đề {String.fromCharCode(65 + idx)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* CHẾ ĐỘ 1: INBOX ROW PREVIEW */}
      {viewMode === 'INBOX_ROW' && (
        <div className="p-3 bg-white hover:bg-slate-50 transition cursor-pointer group">
          <div
            onClick={() => setViewMode('FULL_READER')}
            className="flex items-center gap-3"
          >
            {/* Unread blue dot */}
            <div className="w-2.5 h-2.5 rounded-full bg-blue-600 shrink-0 shadow-xs"></div>

            {/* Checkbox & Star */}
            <div className="flex items-center gap-2 text-slate-400">
              <input
                type="checkbox"
                readOnly
                className="w-3.5 h-3.5 rounded border-slate-300 text-indigo-600 focus:ring-0 cursor-pointer"
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsStarred(!isStarred);
                }}
                className="hover:text-amber-500 transition"
              >
                <Star className={`w-4 h-4 ${isStarred ? 'fill-amber-400 text-amber-400' : ''}`} />
              </button>
            </div>

            {/* Sender Name */}
            <span className="font-bold text-slate-900 text-xs sm:text-sm w-28 sm:w-36 truncate shrink-0">
              {brandName}
            </span>

            {/* Subject Line & Preheader Snippet */}
            <div className="flex-1 min-w-0 flex items-baseline gap-1.5">
              <span className="font-bold text-slate-800 text-xs sm:text-sm truncate">
                {activeSubject}
              </span>
              <span className="text-slate-400 text-xs font-normal truncate hidden sm:inline">
                - {preheader || body.slice(0, 80)}
              </span>
            </div>

            {/* Time & Hover Actions */}
            <div className="shrink-0 flex items-center gap-2">
              <span className="text-xs text-slate-500 font-medium group-hover:hidden">
                {receivedTime}
              </span>
              <div className="hidden group-hover:flex items-center gap-1.5 text-slate-500">
                <button title="Lưu trữ" className="p-1 hover:text-slate-800 rounded">
                  <Archive className="w-3.5 h-3.5" />
                </button>
                <button title="Xóa" className="p-1 hover:text-rose-600 rounded">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                <button title="Mở thư" className="p-1 text-indigo-600 font-bold">
                  <Eye className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          <div className="mt-2 text-center">
            <span className="text-[10px] text-indigo-600 font-medium underline">
              👉 Bấm vào dòng thư để xem chế độ trình đọc đầy đủ (Full Reader)
            </span>
          </div>
        </div>
      )}

      {/* CHẾ ĐỘ 2: FULL NEWSLETTER READER */}
      {viewMode === 'FULL_READER' && (
        <div className="p-5 space-y-5 animate-in fade-in duration-200">
          {/* Reader Top Controls */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <button
              onClick={() => setViewMode('INBOX_ROW')}
              className="text-xs text-slate-600 hover:text-indigo-600 font-medium flex items-center gap-1 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Quay lại danh sách thư
            </button>
            <div className="flex items-center gap-2 text-slate-400">
              <span className="text-[11px] text-emerald-600 font-medium flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <ShieldCheck className="w-3.5 h-3.5" />
                Bảo mật TLS / DKIM Hợp lệ
              </span>
            </div>
          </div>

          {/* Subject Heading */}
          <div>
            <h2 className="text-base sm:text-lg font-black text-slate-900 leading-snug">
              {activeSubject}
            </h2>
            <div className="mt-2 flex items-center justify-between text-xs text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-600 text-white font-bold text-xs flex items-center justify-center">
                  {brandName.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <div className="font-bold text-slate-800 text-xs">
                    {brandName} <span className="font-normal text-slate-500">&lt;{senderEmail}&gt;</span>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Gửi đến: <span className="text-slate-700">{recipientEmail}</span>
                  </div>
                </div>
              </div>
              <span className="text-[11px] font-medium text-slate-400">{receivedTime}</span>
            </div>
          </div>

          {/* Newsletter Header Banner (Ảnh thực tế) */}
          <div className="relative group rounded-xl overflow-hidden border border-slate-200 bg-slate-100">
            {imageUrl ? (
              <div className="relative aspect-[21/9] w-full overflow-hidden bg-slate-900">
                <img
                  src={imageUrl}
                  alt="Email Header Banner"
                  className="w-full h-full object-cover"
                />
                {onImageChange && (
                  <button
                    onClick={() => setIsPickerOpen(!isPickerOpen)}
                    className="absolute top-2 right-2 px-2.5 py-1 bg-black/70 hover:bg-black text-white text-xs font-medium rounded-lg opacity-0 group-hover:opacity-100 transition shadow backdrop-blur-xs flex items-center gap-1.5"
                  >
                    <ImageIcon className="w-3.5 h-3.5" />
                    Đổi ảnh Banner
                  </button>
                )}
              </div>
            ) : (
              <div
                onClick={() => onImageChange && setIsPickerOpen(true)}
                className="py-6 px-4 text-center bg-slate-50 border-dashed border-2 border-slate-200 hover:bg-slate-100 transition cursor-pointer"
              >
                <ImageIcon className="w-6 h-6 text-slate-400 mx-auto mb-1" />
                <p className="text-xs font-semibold text-slate-700">Chưa gắn ảnh banner tiêu đề email</p>
                <p className="text-[10px] text-slate-500">Bấm để chọn banner chất lượng cao</p>
              </div>
            )}
          </div>

          {/* Image Picker Dropdown */}
          {isPickerOpen && onImageChange && (
            <div className="p-3 border border-slate-200 rounded-xl bg-slate-50">
              <ImageAttachmentPicker
                currentImageUrl={imageUrl}
                onSelectImage={(url) => {
                  onImageChange(url);
                  setIsPickerOpen(false);
                }}
                onClose={() => setIsPickerOpen(false)}
              />
            </div>
          )}

          {/* Newsletter Content Body */}
          <div className="space-y-3.5 text-xs sm:text-[13px] text-slate-800 leading-relaxed">
            {/* Lời chào */}
            {greeting && (
              <p className="font-semibold text-slate-900">{greeting}</p>
            )}

            {/* Thân bài */}
            <div className="whitespace-pre-line leading-relaxed text-slate-800">
              {effectiveBody}
            </div>

            {/* Nút Kêu gọi Hành động (CTA Button) */}
            <div className="py-4 text-center">
              <a
                href="#cta"
                onClick={(e) => e.preventDefault()}
                className="inline-block px-6 py-3 bg-gradient-to-r from-indigo-600 via-indigo-700 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold text-xs sm:text-sm rounded-xl shadow-md hover:shadow-lg transition transform hover:-translate-y-0.5 tracking-wide"
              >
                👉 {ctaButton}
              </a>
            </div>

            {/* Tái bút (P.S. Note) */}
            {psNote && (
              <div className="p-3 bg-amber-50/80 rounded-xl border border-amber-200 text-amber-900 text-xs italic">
                {psNote}
              </div>
            )}
          </div>

          {/* Chân trang Email Compliance & Unsubscribe */}
          <div className="pt-4 border-t border-slate-200 text-center space-y-1.5 text-[11px] text-slate-400">
            <p className="text-slate-500 font-medium">
              © 2026 {brandName}. Bảo lưu mọi quyền.
            </p>
            <p>
              Bạn nhận được email này vì đã đăng ký thông tin nhận thông báo từ hệ thống.
            </p>
            <div className="space-x-2 pt-1 text-slate-500">
              <a href="#unsub" onClick={(e) => e.preventDefault()} className="hover:underline">
                Hủy đăng ký nhận thư (Unsubscribe)
              </a>
              <span>·</span>
              <a href="#pref" onClick={(e) => e.preventDefault()} className="hover:underline">
                Tùy chỉnh thông báo
              </a>
              <span>·</span>
              <a href="#policy" onClick={(e) => e.preventDefault()} className="hover:underline">
                Chính sách bảo mật
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
