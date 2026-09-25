import React, { useState } from 'react';
import { Image as ImageIcon, Link as LinkIcon, Check, X, Sparkles, Trash2 } from 'lucide-react';

interface ImagePreset {
  id: string;
  title: string;
  category: string;
  url: string;
  thumb: string;
}

const PRESET_IMAGES: ImagePreset[] = [
  {
    id: 'ai-lab',
    title: 'Phòng Thí Nghiệm AI & Dữ Liệu',
    category: 'Công nghệ & AI',
    url: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80',
    thumb: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=300&auto=format&fit=crop&q=80'
  },
  {
    id: 'saas-growth',
    title: 'Tăng Trưởng Doanh Thu SaaS',
    category: 'Doanh nghiệp',
    url: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&auto=format&fit=crop&q=80',
    thumb: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=300&auto=format&fit=crop&q=80'
  },
  {
    id: 'modern-workspace',
    title: 'Không Gian Sáng Tạo Agency',
    category: 'Doanh nghiệp',
    url: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&auto=format&fit=crop&q=80',
    thumb: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=300&auto=format&fit=crop&q=80'
  },
  {
    id: 'neon-cyber',
    title: 'Hiệu Ứng Sóng Số Neon',
    category: 'Sáng tạo số',
    url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80',
    thumb: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=300&auto=format&fit=crop&q=80'
  },
  {
    id: 'team-collaboration',
    title: 'Hội Thảo Chiến Lược Marketing',
    category: 'Đào tạo & Sự kiện',
    url: 'https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1200&auto=format&fit=crop&q=80',
    thumb: 'https://images.unsplash.com/photo-1557804506-669a67965ba0?w=300&auto=format&fit=crop&q=80'
  },
  {
    id: 'analytics-dashboard',
    title: 'Biểu Đồ Đo Lường Hiệu Quả',
    category: 'Công nghệ & AI',
    url: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&auto=format&fit=crop&q=80',
    thumb: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=300&auto=format&fit=crop&q=80'
  }
];

export interface ImageAttachmentPickerProps {
  currentImageUrl?: string;
  onSelectImage: (newUrl: string) => void;
  onClose?: () => void;
}

export const ImageAttachmentPicker: React.FC<ImageAttachmentPickerProps> = ({
  currentImageUrl,
  onSelectImage,
  onClose
}) => {
  const [customUrl, setCustomUrl] = useState(currentImageUrl || '');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  const categories = ['ALL', 'Công nghệ & AI', 'Doanh nghiệp', 'Sáng tạo số', 'Đào tạo & Sự kiện'];

  const filteredPresets = selectedCategory === 'ALL'
    ? PRESET_IMAGES
    : PRESET_IMAGES.filter(p => p.category === selectedCategory);

  const handleApplyCustom = () => {
    if (customUrl.trim()) {
      onSelectImage(customUrl.trim());
      if (onClose) onClose();
    }
  };

  const handleClearImage = () => {
    setCustomUrl('');
    onSelectImage('');
    if (onClose) onClose();
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden text-slate-800 animate-in fade-in zoom-in-95 duration-200">
      {/* Modal / Card Header */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 px-5 py-4 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-sm">
            <ImageIcon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Gắn Ảnh Sản Phẩm / Banner Thực Tế</h3>
            <p className="text-xs text-slate-500">Hiển thị sắc nét trên toàn bộ các kênh Social Preview</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="p-5 space-y-5">
        {/* Custom URL Input */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
            <LinkIcon className="w-3.5 h-3.5 text-indigo-600" />
            Dán đường dẫn URL hình ảnh tùy chọn
          </label>
          <div className="flex gap-2">
            <input
              type="url"
              placeholder="https://images.unsplash.com/... hoặc link ảnh CDN công ty"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              className="flex-1 px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50 focus:bg-white transition"
            />
            <button
              onClick={handleApplyCustom}
              disabled={!customUrl.trim()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-medium transition shadow-sm flex items-center gap-1 shrink-0"
            >
              <Check className="w-3.5 h-3.5" />
              Áp dụng
            </button>
            {currentImageUrl && (
              <button
                onClick={handleClearImage}
                title="Gỡ ảnh khỏi bài viết"
                className="px-3 py-2 border border-rose-200 text-rose-600 hover:bg-rose-50 rounded-xl text-xs font-medium transition flex items-center gap-1 shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Gỡ ảnh
              </button>
            )}
          </div>
        </div>

        {/* Preset Gallery */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Hoặc chọn nhanh từ thư viện ảnh bản quyền Unsplash
            </span>
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition ${
                  selectedCategory === cat
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat === 'ALL' ? 'Tất cả' : cat}
              </button>
            ))}
          </div>

          {/* Image Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 max-h-56 overflow-y-auto pr-1">
            {filteredPresets.map((preset) => {
              const isSelected = currentImageUrl === preset.url;
              return (
                <div
                  key={preset.id}
                  onClick={() => {
                    setCustomUrl(preset.url);
                    onSelectImage(preset.url);
                    if (onClose) onClose();
                  }}
                  className={`group relative rounded-xl overflow-hidden border-2 cursor-pointer transition transform hover:-translate-y-0.5 shadow-xs ${
                    isSelected
                      ? 'border-indigo-600 ring-2 ring-indigo-200'
                      : 'border-slate-200 hover:border-indigo-400'
                  }`}
                >
                  <img
                    src={preset.thumb}
                    alt={preset.title}
                    className="w-full h-20 object-cover group-hover:scale-105 transition duration-300"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent p-1.5 flex flex-col justify-end">
                    <p className="text-[10px] text-white font-medium truncate">{preset.title}</p>
                  </div>
                  {isSelected && (
                    <div className="absolute top-1 right-1 w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center shadow">
                      <Check className="w-3 h-3" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
