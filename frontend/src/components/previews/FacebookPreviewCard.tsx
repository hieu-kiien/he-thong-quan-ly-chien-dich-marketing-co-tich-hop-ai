import React, { useState } from 'react';
import { Globe, MoreHorizontal, ThumbsUp, MessageSquare, Share2, Image as ImageIcon, CheckCircle } from 'lucide-react';
import { ImageAttachmentPicker } from './ImageAttachmentPicker';

export interface FacebookPreviewCardProps {
  brandName?: string;
  brandLogo?: string;
  title?: string;
  headline?: string;
  body?: string;
  primaryText?: string;
  cta?: string;
  hashtags?: string[];
  imageUrl?: string;
  publishedAt?: string;
  isSponsored?: boolean;
  likesCount?: number;
  commentsCount?: number;
  sharesCount?: number;
  onImageChange?: (newUrl: string) => void;
  showImagePicker?: boolean;
  compact?: boolean;
}

export const FacebookPreviewCard: React.FC<FacebookPreviewCardProps> = ({
  brandName = 'MarketFlow AI',
  brandLogo,
  title,
  headline,
  body = '',
  primaryText,
  cta = 'Tìm hiểu thêm',
  hashtags = ['#MarketFlow', '#DigitalMarketing', '#GenAI2026'],
  imageUrl,
  publishedAt = '1 giờ trước',
  isSponsored = true,
  likesCount = 2450,
  commentsCount = 86,
  sharesCount = 24,
  onImageChange,
  compact = false
}) => {
  const [isLiked, setIsLiked] = useState(false);
  const [likeTotal, setLikeTotal] = useState(likesCount);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const toggleLike = () => {
    if (isLiked) {
      setIsLiked(false);
      setLikeTotal(prev => prev - 1);
    } else {
      setIsLiked(true);
      setLikeTotal(prev => prev + 1);
    }
  };

  const effectiveBody = primaryText || body || '';
  const effectiveTitle = headline || title || brandName;
  const shouldTruncate = effectiveBody.length > 200;
  const displayedBody = shouldTruncate && !isExpanded
    ? `${effectiveBody.slice(0, 180)}...`
    : effectiveBody;

  return (
    <div className={`bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden text-slate-900 font-sans transition-all duration-200 hover:shadow-md ${compact ? 'max-w-md' : 'max-w-lg w-full mx-auto'}`}>
      {/* 1. Header bài viết */}
      <div className="p-3.5 flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          {/* Fanpage Avatar */}
          <div className="relative">
            {brandLogo ? (
              <img
                src={brandLogo}
                alt={brandName}
                className="w-10 h-10 rounded-full object-cover border border-slate-200 shadow-2xs"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-2xs">
                {brandName.slice(0, 2).toUpperCase()}
              </div>
            )}
            {/* Facebook small badge indicator */}
            <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-blue-600 rounded-full flex items-center justify-center border-2 border-white">
              <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-1">
              <span className="font-semibold text-slate-900 text-sm hover:underline cursor-pointer">
                {brandName}
              </span>
              {/* Verified Blue Badge */}
              <span className="inline-flex text-[#0866FF]" title="Tài khoản đã xác thực">
                <CheckCircle className="w-3.5 h-3.5 fill-[#0866FF] text-white" />
              </span>
            </div>

            <div className="flex items-center text-[11px] text-slate-500 gap-1 leading-tight mt-0.5">
              {isSponsored ? (
                <>
                  <span className="font-medium text-slate-600">Được tài trợ</span>
                  <span>·</span>
                </>
              ) : (
                <>
                  <span>{publishedAt}</span>
                  <span>·</span>
                </>
              )}
              <Globe className="w-3 h-3 text-slate-500 inline" />
            </div>
          </div>
        </div>

        <button className="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition">
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>

      {/* 2. Nội dung văn bản (Post Body & Hashtags) */}
      <div className="px-3.5 pb-3">
        {title && (
          <h4 className="font-bold text-sm text-slate-900 mb-1.5 leading-snug">
            {title}
          </h4>
        )}
        <div className="text-[13px] text-slate-800 whitespace-pre-line leading-relaxed">
          {displayedBody}
          {shouldTruncate && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="ml-1 text-slate-500 font-semibold hover:underline cursor-pointer focus:outline-none"
            >
              {isExpanded ? ' Thu gọn' : '... Xem thêm'}
            </button>
          )}
        </div>

        {/* Danh sách Hashtags */}
        {hashtags && hashtags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {hashtags.map((tag, i) => (
              <span
                key={i}
                className="text-[#0866FF] hover:underline cursor-pointer text-xs font-normal"
              >
                {tag.startsWith('#') ? tag : `#${tag}`}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 3. Thành phần Thị giác (Banner / Product Image) */}
      <div className="relative group border-t border-slate-100 bg-slate-100">
        {imageUrl ? (
          <div className="relative aspect-video w-full overflow-hidden bg-slate-900">
            <img
              src={imageUrl}
              alt={title || 'Facebook Ad Banner'}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-101"
              onError={(e) => {
                // Fallback nếu link ảnh hỏng
                (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80';
              }}
            />
            {onImageChange && (
              <button
                onClick={() => setIsPickerOpen(!isPickerOpen)}
                className="absolute top-2 right-2 px-2.5 py-1 bg-black/70 hover:bg-black text-white text-xs font-medium rounded-lg opacity-0 group-hover:opacity-100 transition shadow backdrop-blur-xs flex items-center gap-1.5"
              >
                <ImageIcon className="w-3.5 h-3.5" />
                Đổi ảnh
              </button>
            )}
          </div>
        ) : (
          <div
            onClick={() => onImageChange && setIsPickerOpen(true)}
            className="aspect-video w-full flex flex-col items-center justify-center p-6 text-center bg-slate-50 border-y border-dashed border-slate-300 hover:bg-slate-100 transition cursor-pointer"
          >
            <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 mb-2">
              <ImageIcon className="w-5 h-5" />
            </div>
            <p className="text-xs font-semibold text-slate-700">Chưa gắn ảnh banner/sản phẩm</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Bấm vào đây để chọn ảnh mẫu hoặc dán liên kết</p>
          </div>
        )}

        {/* Facebook Snippet Bar bên dưới ảnh */}
        <div className="bg-slate-100 p-3 flex items-center justify-between border-t border-slate-200">
          <div className="min-w-0 pr-3">
            <span className="text-[10px] uppercase font-medium tracking-wide text-slate-500 block truncate">
              MARKETFLOW.AI / TIẾP THỊ ĐA KÊNH
            </span>
            <p className="text-xs font-bold text-slate-900 truncate mt-0.5">
              {effectiveTitle}
            </p>
          </div>
          <button className="px-3.5 py-1.5 bg-slate-200/80 hover:bg-slate-300 text-slate-800 font-semibold text-xs rounded-md shrink-0 transition shadow-2xs border border-slate-300">
            {cta || 'Tìm hiểu thêm'}
          </button>
        </div>
      </div>

      {/* Image Picker Dropdown / Overlay nếu bật */}
      {isPickerOpen && onImageChange && (
        <div className="p-3 border-t border-slate-200 bg-slate-50">
          <ImageAttachmentPicker
            currentImageUrl={imageUrl}
            onSelectImage={(newUrl) => {
              onImageChange(newUrl);
              setIsPickerOpen(false);
            }}
            onClose={() => setIsPickerOpen(false)}
          />
        </div>
      )}

      {/* 4. Thanh Thống kê Tương tác (Engagement Bar) */}
      <div className="px-3.5 py-2 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <div className="flex -space-x-1">
            <div className="w-4 h-4 rounded-full bg-[#0866FF] flex items-center justify-center text-white ring-2 ring-white">
              <ThumbsUp className="w-2.5 h-2.5 fill-white" />
            </div>
            <div className="w-4 h-4 rounded-full bg-[#FA383E] flex items-center justify-center text-white ring-2 ring-white">
              <span className="text-[9px] leading-none">❤️</span>
            </div>
          </div>
          <span className="hover:underline cursor-pointer">{likeTotal.toLocaleString()}</span>
        </div>

        <div className="flex items-center gap-3">
          <span className="hover:underline cursor-pointer">{commentsCount} bình luận</span>
          <span>·</span>
          <span className="hover:underline cursor-pointer">{sharesCount} lượt chia sẻ</span>
        </div>
      </div>

      {/* 5. Thanh 3 Nút Hành động Chuẩn Facebook */}
      <div className="border-t border-slate-200 px-2 py-0.5 flex items-center justify-around text-xs font-semibold text-slate-600">
        <button
          onClick={toggleLike}
          className={`flex-1 py-2 flex items-center justify-center gap-1.5 rounded-lg hover:bg-slate-100 transition ${
            isLiked ? 'text-[#0866FF]' : 'text-slate-600'
          }`}
        >
          <ThumbsUp className={`w-4 h-4 ${isLiked ? 'fill-[#0866FF]' : ''}`} />
          <span>Thích</span>
        </button>

        <button className="flex-1 py-2 flex items-center justify-center gap-1.5 rounded-lg hover:bg-slate-100 transition text-slate-600">
          <MessageSquare className="w-4 h-4" />
          <span>Bình luận</span>
        </button>

        <button className="flex-1 py-2 flex items-center justify-center gap-1.5 rounded-lg hover:bg-slate-100 transition text-slate-600">
          <Share2 className="w-4 h-4" />
          <span>Chia sẻ</span>
        </button>
      </div>
    </div>
  );
};
