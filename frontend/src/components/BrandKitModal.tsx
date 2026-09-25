import React, { useState, useEffect } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { useAuth } from '../context/AuthContext';
import { X, Palette, Sparkles, Plus, AlertCircle, CheckCircle2, Loader2, ShieldAlert } from 'lucide-react';
import { BrandKit } from '../types';

interface BrandKitModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const TONE_PRESETS = [
  'Chuyên nghiệp, hiện đại, tin cậy',
  'Trẻ trung, năng động, bắt trend',
  'Sang trọng, đẳng cấp, tối giản',
  'Gần gũi, ấm áp, truyền cảm hứng',
  'Hài hước, dí dỏm, kích thích tương tác'
];

export const BrandKitModal: React.FC<BrandKitModalProps> = ({ isOpen, onClose }) => {
  const { currentWorkspace, brandKit, updateBrandKit } = useWorkspace();
  const { userRole } = useAuth();

  const isEditable = userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER';

  const [brandName, setBrandName] = useState('');
  const [usp, setUsp] = useState('');
  const [toneOfVoice, setToneOfVoice] = useState('');
  const [bannedKeywords, setBannedKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (brandKit) {
      setBrandName(brandKit.brand_name || '');
      setUsp(brandKit.usp || '');
      setToneOfVoice(brandKit.tone_of_voice || 'Chuyên nghiệp, hiện đại, tin cậy');
      setBannedKeywords(brandKit.banned_keywords || []);
    } else if (currentWorkspace) {
      setBrandName(currentWorkspace.name);
      setUsp('');
      setToneOfVoice('Chuyên nghiệp, hiện đại, tin cậy');
      setBannedKeywords([]);
    }
    setFeedback(null);
  }, [brandKit, currentWorkspace, isOpen]);

  if (!isOpen) return null;

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
        banned_keywords: bannedKeywords
      });
      setFeedback({ type: 'success', message: 'Cập nhật Brand Kit thành công!' });
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err: any) {
      setFeedback({ type: 'error', message: err?.message || 'Lỗi khi lưu Brand Kit' });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl shadow-black/80 flex flex-col max-h-[90vh] overflow-hidden text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400">
              <Palette className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Brand Kit Thương Hiệu</h3>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-medium">
                  {currentWorkspace?.name}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Định vị USP, giọng văn chuẩn và bộ từ khóa cấm kỵ áp dụng cho toàn bộ AI Studio & Guardrail
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Permission Notice if Read-Only */}
        {!isEditable && (
          <div className="px-6 py-2.5 bg-amber-500/10 border-b border-amber-500/20 flex items-center gap-2 text-amber-300 text-xs">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            <span>Chế độ Chỉ xem (Read-only): Chỉ Quản lý Agency mới có quyền chỉnh sửa bộ quy tắc Brand Kit.</span>
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
            {feedback.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Brand Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Tên thương hiệu (Brand Name)
            </label>
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              disabled={!isEditable}
              placeholder="VD: VinFast, ICTU Education..."
              className="w-full bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 disabled:opacity-60 transition-all"
              required
            />
          </div>

          {/* USP */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Lợi thế bán hàng độc nhất (USP / Positioning Statement)
            </label>
            <textarea
              value={usp}
              onChange={(e) => setUsp(e.target.value)}
              disabled={!isEditable}
              rows={3}
              placeholder="Mô tả giá trị cốt lõi, thế mạnh vượt trội mà thương hiệu cam kết mang lại..."
              className="w-full bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 disabled:opacity-60 transition-all resize-none"
            />
          </div>

          {/* Tone of Voice */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Giọng văn chuẩn (Tone of Voice)
            </label>
            <input
              type="text"
              value={toneOfVoice}
              onChange={(e) => setToneOfVoice(e.target.value)}
              disabled={!isEditable}
              placeholder="VD: Chuyên nghiệp, hiện đại, tin cậy..."
              className="w-full bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 disabled:opacity-60 transition-all mb-2"
              required
            />
            {isEditable && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {TONE_PRESETS.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setToneOfVoice(preset)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition-all"
                  >
                    {preset}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Blacklist / Banned Keywords */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Danh sách từ khóa cấm kỵ (Banned Keywords Blacklist)
              </label>
              <span className="text-[11px] text-slate-400">
                {bannedKeywords.length} từ khóa
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Hệ thống Guardrail sẽ tự động rà quét và chặn gửi duyệt nếu bài viết vi phạm các từ khóa này.
            </p>

            {/* Keyword Input */}
            {isEditable && (
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddKeyword();
                    }
                  }}
                  placeholder="Nhập từ khóa cấm kỵ (VD: cam kết 100%, lừa đảo)..."
                  className="flex-1 bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-rose-500 transition-all"
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
            <div className="p-3 bg-slate-950/50 border border-slate-800/80 rounded-xl min-h-[80px] flex flex-wrap gap-2">
              {bannedKeywords.length === 0 ? (
                <span className="text-xs text-slate-500 italic m-auto">
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
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/90 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            Đóng
          </button>
          {isEditable && (
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-violet-600/30 disabled:opacity-50 transition-all"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang lưu...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Lưu Brand Kit</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
