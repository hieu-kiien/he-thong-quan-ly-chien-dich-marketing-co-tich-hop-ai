import React, { useState, useEffect } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { useAuth } from '../context/AuthContext';
import { X, Palette, Plus, AlertCircle, CheckCircle2, Loader2, ShieldAlert, Type, Sparkles, BookOpen, Eye } from 'lucide-react';
import { useFocusTrap } from '../hooks/useFocusTrap';

interface BrandKitModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const TONE_PRESETS = [
  'Thẳng vào số liệu, câu ngắn gọn, dùng từ đời thường (làm, kết quả, đơn thật)',
  'Chuyên nghiệp, sắc gọn như biên tập viên tạp chí kinh doanh',
  'Gần gũi, thực tế như người làm nghề chia sẻ kinh nghiệm thật',
  'Sang trọng, tiết chế, nói bằng chất liệu và nguồn gốc cụ thể',
  'Trẻ trung, nhịp nhanh, mở bài bằng tình huống đời thực'
];

const PERSONA_PRESETS = [
  'Chủ shop thời trang & mỹ phẩm 25–36 tuổi, tự chạy ads ngân sách 15–50 triệu/tháng, cần biết chi phí trên mỗi đơn thật thay vì lý thuyết.',
  'Trưởng phòng Marketing tại SME Việt Nam, quản lý nhóm 3–8 người, áp lực KPI doanh thu hàng tuần và ghét báo cáo màu mè.',
  'Người đi làm văn phòng 24–35 tuổi tại Hà Nội & TP.HCM, bận rộn, đọc lướt trên điện thoại trong 5 giây và chỉ tin vào đánh giá có tên tuổi thật.'
];

const REFERO_LAYOUT_SYSTEMS = [
  {
    id: 'editorial',
    name: 'Hệ 1A · Tạp chí Biên tập (Editorial Studio)',
    desc: 'Tiêu đề căn trái sắc nét, tương phản rõ, đường kẻ mảnh 1px, khoảng nghỉ rộng (28–32% diện tích).'
  },
  {
    id: 'swiss-grid',
    name: 'Hệ 1B · Bảng Số liệu Thực dụng (Swiss Data Grid)',
    desc: 'Chia ô lưới vuông vức, chữ số thẳng hàng (tabular-nums), ưu tiên mật độ thông tin và bảng biểu.'
  },
  {
    id: 'warm-craft',
    name: 'Hệ 1C · Xưởng Thủ công Ấm áp (Warm Craft)',
    desc: 'Bố cục bất đối xứng có chủ đích, bo góc vừa phải 12px, nhấn mạnh hình ảnh thật và câu chuyện sản phẩm.'
  }
];

const REFERO_COLOR_SYSTEMS = [
  {
    id: 'paper-terracotta',
    name: 'Hệ 2A · Giấy Ấm & Đỏ Gạch (Khuyên dùng — Khử mùi tím AI)',
    bg: '#F6F5F0',
    text: '#121316',
    accent: '#D95D39',
    secondary: '#0F766E',
    radius: '12px'
  },
  {
    id: 'obsidian-amber',
    name: 'Hệ 2B · Đá Đen & Hổ Phách (Tương phản mạnh)',
    bg: '#141518',
    text: '#F4F3EF',
    accent: '#E07A5F',
    secondary: '#2A9D8F',
    radius: '8px'
  },
  {
    id: 'forest-sand',
    name: 'Hệ 2C · Xanh Rừng Sâu & Cát Mịn (Điềm tĩnh, bền vững)',
    bg: '#F4F1EA',
    text: '#1B2A24',
    accent: '#2A6F4E',
    secondary: '#B45309',
    radius: '10px'
  }
];

const VIETNAMESE_FONT_PAIRS = [
  {
    id: 'be-vietnam',
    name: 'Be Vietnam Pro (Chuẩn dấu tiếng Việt hiện đại)',
    cssFamily: "'Be Vietnam Pro', 'Inter', system-ui, sans-serif",
    note: 'Thiết kế riêng cho hệ dấu tiếng Việt, không bao giờ nhảy nét ở chữ ẫ, ệ, ữ, ở, ặ.'
  },
  {
    id: 'plus-jakarta',
    name: 'Plus Jakarta Sans + Inter (Editorial Sắc nét)',
    cssFamily: "'Plus Jakarta Sans', 'Inter', system-ui, sans-serif",
    note: 'Hình học gọn gàng, rất hợp tiêu đề báo cáo và thẻ chỉ số KPI.'
  },
  {
    id: 'serif-editorial',
    name: 'Georgia / Noto Serif + Sans (Báo chí cổ điển)',
    cssFamily: "Georgia, 'Times New Roman', serif",
    note: 'Tạo cảm giác bài viết chuyên sâu, khác biệt hoàn toàn với giao diện SaaS đại trà.'
  }
];

const DEFAULT_5_COPY_RULES = `5 LUẬT VIẾT CHỮ ĐẦU NGÀNH (KHỬ MÙI AI):
1. Bài thử xóa tên thương hiệu: Che tên thương hiệu đi, nếu gắn tên đối thủ vào mà câu văn vẫn đúng nghĩa là viết quá chung chung -> phải viết lại bằng con số và chi tiết thật.
2. Cấm từ tự khen sáo rỗng: Tuyệt đối không dùng "tận tâm", "toàn diện", "đáng tin cậy", "hàng đầu", "giải pháp tối ưu".
3. Lời khen phải có tên bên thứ 3: Mọi nhận định tốt phải đi kèm số liệu đo được hoặc tên khách hàng/đối tác cụ thể.
4. Nút bấm (CTA) là hành động ngay lập tức: Dùng "Nhận bảng tính chi phí", "Tải kịch bản mẫu", "Xem báo giá 3 gói" — CẤM dùng "Tìm hiểu thêm".
5. Câu ngắn, từ tiếng Việt đời thường: Đổi từ nửa Anh nửa Việt sang từ thật (build -> làm, output -> kết quả, optimize -> cắt chi phí thừa).`;

const AI_SLOP_CLICHES = [
  'tận tâm',
  'toàn diện',
  'đáng tin cậy',
  'giải pháp tối ưu',
  'tìm hiểu thêm',
  'chắc chắn 100%',
  'cam kết 100%'
];

export const BrandKitModal: React.FC<BrandKitModalProps> = ({ isOpen, onClose }) => {
  const { currentWorkspace, brandKit, updateBrandKit } = useWorkspace();
  const { userRole } = useAuth();

  const isEditable = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER';

  const modalRef = useFocusTrap<HTMLDivElement>({
    isActive: isOpen,
    onEscape: onClose,
  });

  const [brandName, setBrandName] = useState('');
  const [usp, setUsp] = useState('');
  const [toneOfVoice, setToneOfVoice] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [brandGuidelines, setBrandGuidelines] = useState('');
  const [bannedKeywords, setBannedKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [selectedFontId, setSelectedFontId] = useState('be-vietnam');
  const [selectedLayoutId, setSelectedLayoutId] = useState('editorial');
  const [selectedColorId, setSelectedColorId] = useState('paper-terracotta');
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (brandKit) {
      setBrandName(brandKit.brand_name || '');
      setUsp(brandKit.usp || '');
      setToneOfVoice(brandKit.tone_of_voice || TONE_PRESETS[0]);
      setBannedKeywords(brandKit.banned_keywords || []);
      setTargetAudience(brandKit.target_audience || PERSONA_PRESETS[0]);
      setBrandGuidelines(brandKit.brand_guidelines || DEFAULT_5_COPY_RULES);
    } else if (currentWorkspace) {
      setBrandName(currentWorkspace.name);
      setUsp('');
      setToneOfVoice(TONE_PRESETS[0]);
      setBannedKeywords([]);
      setTargetAudience(PERSONA_PRESETS[0]);
      setBrandGuidelines(DEFAULT_5_COPY_RULES);
    }
    setFeedback(null);
  }, [brandKit, currentWorkspace, isOpen]);

  if (!isOpen) return null;

  const activeFont = VIETNAMESE_FONT_PAIRS.find((f) => f.id === selectedFontId) || VIETNAMESE_FONT_PAIRS[0];
  const activeColor = REFERO_COLOR_SYSTEMS.find((c) => c.id === selectedColorId) || REFERO_COLOR_SYSTEMS[0];
  const activeLayout = REFERO_LAYOUT_SYSTEMS.find((l) => l.id === selectedLayoutId) || REFERO_LAYOUT_SYSTEMS[0];

  const handleAddKeyword = () => {
    const trimmed = newKeyword.trim();
    if (!trimmed) return;
    if (bannedKeywords.includes(trimmed)) {
      setFeedback({ type: 'error', message: `Từ khóa "${trimmed}" đã có trong danh sách cấm` });
      return;
    }
    setBannedKeywords([...bannedKeywords, trimmed]);
    setNewKeyword('');
    setFeedback(null);
  };

  const handleAddAllAiSlopCliches = () => {
    if (!isEditable) return;
    const merged = Array.from(new Set([...bannedKeywords, ...AI_SLOP_CLICHES]));
    setBannedKeywords(merged);
    setFeedback({
      type: 'success',
      message: 'Đã nạp bộ từ sáo rỗng "Mùi AI" (tận tâm, toàn diện, đáng tin cậy, tìm hiểu thêm...) vào danh sách chặn.'
    });
  };

  const handleApplyReferoRecipeToGuidelines = () => {
    if (!isEditable) return;
    const recipeHeader = `[CÔNG THỨC 2 HỆ THAM CHIẾU REFERO]:
- ${activeLayout.name}: ${activeLayout.desc}
- ${activeColor.name}: Nền ${activeColor.bg} · Chữ ${activeColor.text} · Nhấn ${activeColor.accent} & ${activeColor.secondary} · Bo góc ${activeColor.radius}
- Font chữ đã qua Bài kiểm tra 5 chữ tiếng Việt (ẫ, ệ, ữ, ở, ặ): ${activeFont.name}`;

    const baseRules = brandGuidelines.includes('5 LUẬT VIẾT CHỮ') ? DEFAULT_5_COPY_RULES : brandGuidelines;
    setBrandGuidelines(`${recipeHeader}\n\n${baseRules}`);
    setFeedback({
      type: 'success',
      message: 'Đã ghép Công thức 2 Hệ Tham Chiếu + Font Tiếng Việt + 5 Luật Viết Chữ vào Tờ giấy quy tắc!'
    });
  };

  const handleRemoveKeyword = (indexToRemove: number) => {
    if (!isEditable) return;
    setBannedKeywords(bannedKeywords.filter((_, idx) => idx !== indexToRemove));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isEditable) return;

    setIsSaving(true);
    setFeedback(null);
    try {
      await updateBrandKit({
        brand_name: brandName,
        usp,
        tone_of_voice: toneOfVoice,
        banned_keywords: bannedKeywords,
        target_audience: targetAudience,
        brand_guidelines: brandGuidelines,
      });
      setFeedback({ type: 'success', message: 'Đã lưu Tờ Giấy Quy Tắc Thiết Kế & Giọng Văn (Brand Kit) thành công!' });
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setFeedback({ type: 'error', message: err?.message || 'Lỗi khi lưu Brand Kit' });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="brand-kit-modal-title"
        className="w-full max-w-4xl bg-[#141518] border border-stone-800 rounded-2xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden text-stone-100"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-stone-800 bg-[#18191D]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#D95D39]/20 border border-[#D95D39]/40 flex items-center justify-center text-[#F08A6C]">
              <Palette className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 id="brand-kit-modal-title" className="text-base font-bold text-white">
                  Tờ Giấy Quy Tắc Thiết Kế & Giọng Văn (Brand Kit Khử Mùi AI)
                </h3>
                <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-stone-800 text-stone-300 font-medium border border-stone-700">
                  {currentWorkspace?.name}
                </span>
              </div>
              <p className="text-xs text-stone-400 mt-0.5">
                Thay thế câu lệnh mơ hồ bằng chân dung người thật, bảng màu Hex cụ thể, bài test 5 chữ tiếng Việt và 5 luật viết chữ đầu ngành.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng modal Brand Kit"
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-100 hover:bg-stone-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Permission Notice if Read-Only */}
        {!isEditable && (
          <div className="px-6 py-2.5 bg-amber-500/10 border-b border-amber-500/20 flex items-center gap-2 text-amber-300 text-xs">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            <span>Chế độ Chỉ xem (Read-only): Chỉ Quản lý Chiến dịch (MANAGER) mới có quyền chỉnh sửa Tờ giấy quy tắc này.</span>
          </div>
        )}

        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`mx-6 mt-4 p-3 rounded-xl flex items-center gap-2 text-xs font-medium ${
              feedback.type === 'success'
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
            }`}
          >
            {feedback.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Phần 1: Tên Thương hiệu + USP cụ thể */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="brand-kit-name" className="block text-xs font-semibold text-stone-300 uppercase tracking-wider mb-2">
                1. Tên thương hiệu (Brand Name)
              </label>
              <input
                id="brand-kit-name"
                type="text"
                data-autofocus="true"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                readOnly={!isEditable}
                placeholder="VD: Highland Roastery, Techcombank, Coolmate..."
                className="w-full bg-stone-950 border border-stone-800 rounded-xl px-4 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:outline-none focus:border-[#D95D39] disabled:opacity-60 transition-all"
                required
              />
            </div>

            <div>
              <label htmlFor="brand-kit-tone" className="block text-xs font-semibold text-stone-300 uppercase tracking-wider mb-2">
                2. Giọng văn chủ đạo (Tone of Voice)
              </label>
              <input
                id="brand-kit-tone"
                type="text"
                value={toneOfVoice}
                onChange={(e) => setToneOfVoice(e.target.value)}
                readOnly={!isEditable}
                placeholder="VD: Câu ngắn gọn, nói thẳng bằng số liệu thật..."
                className="w-full bg-stone-950 border border-stone-800 rounded-xl px-4 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:outline-none focus:border-[#D95D39] disabled:opacity-60 transition-all"
                required
              />
            </div>
          </div>

          {isEditable && (
            <div className="flex flex-wrap gap-1.5 -mt-3">
              {TONE_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setToneOfVoice(preset)}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-stone-900 hover:bg-stone-800 text-stone-300 border border-stone-800 transition-all"
                >
                  {preset}
                </button>
              ))}
            </div>
          )}

          {/* USP */}
          <div>
            <label htmlFor="brand-kit-usp" className="block text-xs font-semibold text-stone-300 uppercase tracking-wider mb-1.5">
              3. Điểm khác biệt có số liệu / bằng chứng thật (USP — Vượt bài thử xóa tên thương hiệu)
            </label>
            <p className="text-[11px] text-stone-400 mb-2">
              Đừng viết chung chung như “chất lượng hàng đầu, dịch vụ tận tâm”. Hãy ghi con số, thời gian, cơ chế hoặc cam kết mà đối thủ không thể chép nguyên xi.
            </p>
            <textarea
              id="brand-kit-usp"
              value={usp}
              onChange={(e) => setUsp(e.target.value)}
              readOnly={!isEditable}
              rows={2}
              placeholder="VD: Đồng bộ chiến dịch 3 kênh trong 90 giây, tự động chặn 100% từ khóa vi phạm chính sách Meta/TikTok trước khi chạy quảng cáo..."
              className="w-full bg-stone-950 border border-stone-800 rounded-xl px-4 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:outline-none focus:border-[#D95D39] disabled:opacity-60 transition-all resize-none"
            />
          </div>

          {/* Chân dung người dùng cụ thể trong 1 câu (Từ Video: "Tả khách hàng trong 1 câu cụ thể") */}
          <div className="p-4 rounded-xl bg-stone-900/90 border border-stone-800 space-y-2.5">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <label htmlFor="brand-kit-audience" className="text-xs font-bold text-[#F08A6C] uppercase tracking-wider flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5" />
                4. Chân dung người đọc trong 1 câu cụ thể (Không viết mơ hồ)
              </label>
              <span className="text-[11px] text-stone-400">Giúp AI chọn đúng từ vựng & nhịp câu của người thật</span>
            </div>
            <textarea
              id="brand-kit-audience"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              readOnly={!isEditable}
              rows={2}
              placeholder="Tả rõ 1 người thật: Họ làm nghề gì, bao nhiêu tuổi, đang đau đầu vì con số nào, đọc bài ở đâu..."
              className="w-full bg-stone-950 border border-stone-800 rounded-xl px-3.5 py-2 text-xs text-stone-100 placeholder-stone-500 focus:outline-none focus:border-[#D95D39]"
            />
            {isEditable && (
              <div className="flex flex-wrap gap-1.5">
                {PERSONA_PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setTargetAudience(p)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-stone-950 hover:bg-stone-800 text-stone-300 border border-stone-800 transition-colors text-left"
                  >
                    Mẫu #{idx + 1}: {p.slice(0, 58)}...
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Phần 5: Công thức 2 Hệ Tham Chiếu Refero + Bài Kiểm Tra 5 Giây 5 Chữ Tiếng Việt */}
          <div className="p-4 rounded-xl bg-stone-900/90 border border-stone-800 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h4 className="text-xs font-bold text-teal-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Type className="w-3.5 h-3.5" />
                  5. Công Thức 2 Hệ Tham Chiếu & Bài Test 5 Giây Chữ Tiếng Việt (ẫ · ệ · ữ · ở · ặ)
                </h4>
                <p className="text-[11px] text-stone-400 mt-0.5">
                  Lấy cách dàn chữ của Hệ 1 + Bảng màu Hex của Hệ 2, đồng thời soi 5 chữ cái có dấu phức tạp nhất để chống lỗi nhảy font (fallback glyph mismatch).
                </p>
              </div>
              {isEditable && (
                <button
                  type="button"
                  onClick={handleApplyReferoRecipeToGuidelines}
                  className="px-3 py-1.5 rounded-lg bg-[#D95D39]/20 hover:bg-[#D95D39]/30 text-[#F08A6C] border border-[#D95D39]/40 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Ghi công thức này vào Tờ giấy quy tắc
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-stone-300 mb-1">
                  Hệ 1 · Chọn Cách dàn chữ & Bố cục (Layout Reference)
                </label>
                <select
                  value={selectedLayoutId}
                  onChange={(e) => setSelectedLayoutId(e.target.value)}
                  disabled={!isEditable}
                  className="w-full bg-stone-950 border border-stone-800 rounded-lg px-3 py-2 text-xs text-stone-100 focus:outline-none focus:border-[#D95D39]"
                >
                  {REFERO_LAYOUT_SYSTEMS.map((l) => (
                    <option key={l.id} value={l.id}>{l.name}</option>
                  ))}
                </select>
                <p className="text-[11px] text-stone-400 mt-1">{activeLayout.desc}</p>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-stone-300 mb-1">
                  Hệ 2 · Chọn Bảng màu Hex cụ thể (Không dùng Tím-Xanh AI mặc định)
                </label>
                <select
                  value={selectedColorId}
                  onChange={(e) => setSelectedColorId(e.target.value)}
                  disabled={!isEditable}
                  className="w-full bg-stone-950 border border-stone-800 rounded-lg px-3 py-2 text-xs text-stone-100 focus:outline-none focus:border-[#D95D39]"
                >
                  {REFERO_COLOR_SYSTEMS.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <div className="flex items-center gap-2 mt-1.5 text-[11px] font-mono text-stone-300">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-950 border border-stone-800">
                    <span className="w-2.5 h-2.5 rounded-full border border-stone-600" style={{ backgroundColor: activeColor.bg }} />
                    Nền {activeColor.bg}
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-950 border border-stone-800">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: activeColor.accent }} />
                    Nhấn {activeColor.accent}
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-950 border border-stone-800">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: activeColor.secondary }} />
                    Phụ {activeColor.secondary}
                  </span>
                </div>
              </div>
            </div>

            {/* Kính lúp soi 5 chữ cái tiếng Việt (ẫ, ệ, ữ, ở, ặ) */}
            <div className="p-3.5 rounded-xl bg-stone-950 border border-stone-800 space-y-2.5">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="text-[11px] font-bold text-stone-300">
                  Bài Kiểm Tra 5 Giây — Soi 5 Chữ Tiếng Việt Có Dấu Phức Tạp Nhất:
                </span>
                <div className="flex gap-1.5 flex-wrap">
                  {VIETNAMESE_FONT_PAIRS.map((f) => (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setSelectedFontId(f.id)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-all ${
                        selectedFontId === f.id
                          ? 'bg-[#D95D39]/20 border-[#D95D39] text-[#F08A6C]'
                          : 'bg-stone-900 border-stone-800 text-stone-400 hover:text-stone-200'
                      }`}
                    >
                      {f.name.split('(')[0].trim()}
                    </button>
                  ))}
                </div>
              </div>

              <div
                className="p-3 rounded-lg border border-stone-800/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                style={{
                  backgroundColor: activeColor.bg,
                  color: activeColor.text,
                  fontFamily: activeFont.cssFamily,
                  borderRadius: activeColor.radius
                }}
              >
                <div className="flex items-center gap-3">
                  {['ẫ', 'ệ', 'ữ', 'ở', 'ặ'].map((ch) => (
                    <div
                      key={ch}
                      className="w-11 h-11 rounded-lg flex flex-col items-center justify-center border font-bold text-xl shadow-sm"
                      style={{
                        borderColor: activeColor.accent,
                        backgroundColor: activeColor.bg === '#141518' ? '#1E2025' : '#FFFFFF',
                        color: activeColor.text
                      }}
                    >
                      <span>{ch}</span>
                    </div>
                  ))}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold tracking-tight">
                    Mẫu thử: “Những mẫu thiết kế chuẩn mực giữ trọn dấu tiếng Việt sắc nét ở mọi cỡ chữ.”
                  </div>
                  <div className="text-[11px] opacity-75 mt-0.5">
                    {activeFont.note}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Phần 6: 5 Luật Viết Chữ Đầu Ngành & Quy tắc Thiết kế (Lưu trong brand_guidelines) */}
          <div>
            <div className="flex items-center justify-between mb-1.5 flex-wrap gap-2">
              <label htmlFor="brand-kit-guidelines" className="text-xs font-semibold text-stone-300 uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-[#F08A6C]" />
                6. Tờ Giấy 5 Luật Viết Chữ Đầu Ngành & Từ Điển Việt Hóa (Tự động bơm vào AI Studio)
              </label>
              {isEditable && (
                <button
                  type="button"
                  onClick={() => setBrandGuidelines(DEFAULT_5_COPY_RULES)}
                  className="text-[11px] text-teal-400 hover:underline font-medium"
                >
                  Khôi phục 5 Luật Viết Chữ chuẩn
                </button>
              )}
            </div>
            <textarea
              id="brand-kit-guidelines"
              value={brandGuidelines}
              onChange={(e) => setBrandGuidelines(e.target.value)}
              readOnly={!isEditable}
              rows={6}
              className="w-full bg-stone-950 border border-stone-800 rounded-xl px-4 py-3 text-xs font-mono text-stone-200 leading-relaxed focus:outline-none focus:border-[#D95D39]"
            />
          </div>

          {/* Phần 7: Blacklist / Banned Keywords */}
          <div>
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <label htmlFor="brandkit-new-keyword" className="block text-xs font-semibold text-stone-300 uppercase tracking-wider">
                7. Danh sách Từ khóa Cấm & Từ Sáo Rỗng “Mùi AI” (Banned Keywords Blacklist)
              </label>
              <div className="flex items-center gap-2">
                {isEditable && (
                  <button
                    type="button"
                    onClick={handleAddAllAiSlopCliches}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 font-semibold transition-colors"
                  >
                    + Nạp nhanh bộ từ sáo rỗng AI (tận tâm, toàn diện, tìm hiểu thêm...)
                  </button>
                )}
                <span className="text-[11px] text-stone-400">
                  {bannedKeywords.length} từ khóa
                </span>
              </div>
            </div>
            <p className="text-[11px] text-stone-400 mb-3">
              Hệ thống Guardrail sẽ tự động rà quét và chặn gửi duyệt nếu bài viết vi phạm các từ khóa hoặc từ sáo rỗng này.
            </p>

            {/* Keyword Input */}
            {isEditable && (
              <div className="flex gap-2 mb-3">
                <input
                  id="brandkit-new-keyword"
                  type="text"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddKeyword();
                    }
                  }}
                  placeholder="Nhập từ khóa cấm hoặc từ sáo rỗng AI (VD: tận tâm, toàn diện, cam kết 100%)..."
                  className="flex-1 bg-stone-950 border border-stone-800 rounded-xl px-4 py-2 text-xs text-stone-100 placeholder-stone-500 focus:outline-none focus:border-rose-500 transition-all"
                />
                <button
                  type="button"
                  onClick={handleAddKeyword}
                  disabled={!newKeyword.trim()}
                  className="px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 rounded-xl text-xs font-semibold flex items-center gap-1.5 disabled:opacity-40 transition-all"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Thêm</span>
                </button>
              </div>
            )}

            {/* Tags Cloud */}
            <div className="p-3 bg-stone-950/80 border border-stone-800 rounded-xl min-h-[72px] flex flex-wrap gap-2">
              {bannedKeywords.length === 0 ? (
                <span className="text-xs text-stone-500 italic m-auto">
                  Chưa có từ khóa cấm kỵ nào được cấu hình cho thương hiệu này
                </span>
              ) : (
                bannedKeywords.map((kw, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium"
                  >
                    <span>{kw}</span>
                    {isEditable && (
                      <button
                        type="button"
                        onClick={() => handleRemoveKeyword(index)}
                        aria-label={`Xóa từ khóa ${kw}`}
                        className="hover:text-rose-100 hover:bg-rose-500/30 rounded p-0.5 transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </span>
                ))
              )}
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-stone-800 bg-[#18191D] flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-stone-300 hover:text-white hover:bg-stone-800 transition-colors"
          >
            Đóng
          </button>
          {isEditable && (
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="px-5 py-2 rounded-xl bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-[#D95D39]/25 disabled:opacity-50 transition-all"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang lưu...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Lưu Tờ Giấy Quy Tắc (Brand Kit)</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

