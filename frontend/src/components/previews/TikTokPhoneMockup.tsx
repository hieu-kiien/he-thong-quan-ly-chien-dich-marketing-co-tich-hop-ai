import React, { useState } from 'react';
import { Heart, MessageSquare, Bookmark, Share2, Music, Plus, Check, Sparkles, Image as ImageIcon, Video } from 'lucide-react';
import { ImageAttachmentPicker } from './ImageAttachmentPicker';

export interface TikTokSceneItem {
  scene_number?: number;
  scene?: number;
  scene_name?: string;
  title?: string;
  visual?: string;
  visual_action?: string;
  voiceover?: string;
  voiceover_script?: string;
  audio?: string;
  duration_seconds?: number | string;
}

export interface TikTokPhoneMockupProps {
  hook3s: string;
  scenes?: TikTokSceneItem[];
  suggestedAudio?: string;
  soundRecommendation?: string;
  brandName?: string;
  brandLogo?: string;
  caption?: string;
  hashtags?: string[];
  imageUrl?: string;
  onImageChange?: (newUrl: string) => void;
  showImagePicker?: boolean;
}

export const TikTokPhoneMockup: React.FC<TikTokPhoneMockupProps> = ({
  hook3s,
  scenes = [],
  suggestedAudio,
  soundRecommendation,
  brandName = 'marketflow_ai',
  brandLogo,
  caption,
  hashtags = ['#MarketingAI', '#TikTokGrowth', '#ViralScript', '#MarketFlow'],
  imageUrl,
  onImageChange
}) => {
  const effectiveAudio = soundRecommendation || suggestedAudio || 'Âm thanh gốc - MarketFlow Trending Beats 2026';
  const [activeSceneIndex, setActiveSceneIndex] = useState<number>(0);
  const [isLiked, setIsLiked] = useState(false);
  const [isFollowed, setIsFollowed] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  // Ánh xạ danh sách phân cảnh truyền vào (nếu có)
  const mappedScenes = (scenes || []).map((s, idx) => ({
    title: s.title || s.scene_name || (s.scene ? `Cảnh ${s.scene}` : (s.scene_number ? `Cảnh ${s.scene_number}` : `Cảnh ${idx + 1}`)),
    visual: s.visual_action || s.visual || 'Chuyển cảnh mượt mà minh họa kịch bản',
    voiceover: s.voiceover_script || s.voiceover || 'Khám phá giải pháp tự động hóa thông minh.',
    audio: s.audio
  }));

  const hasHookInScenes = mappedScenes.some(s => 
    s.title.toLowerCase().includes('hook') || s.title.toLowerCase().includes('mở đầu')
  );

  // Danh sách các phân cảnh tổng thể (Ưu tiên 100% scenes truyền vào khi có length > 0)
  const allScenes: { title: string; visual: string; voiceover: string; audio?: string }[] =
    scenes && scenes.length > 0
      ? (hasHookInScenes || !hook3s
          ? mappedScenes
          : [
              {
                title: 'Hook 3s',
                visual: 'Quay cận cảnh biểu cảm ngạc nhiên trước màn hình số liệu tăng trưởng vọt',
                voiceover: hook3s,
                audio: 'Tiếng ding hiệu ứng pop-up bất ngờ'
              },
              ...mappedScenes
            ])
      : [
          {
            title: 'Hook 3s',
            visual: 'Quay cận cảnh biểu cảm ngạc nhiên trước màn hình số liệu tăng trưởng vọt',
            voiceover: hook3s || 'Dừng lại 3 giây! Bí mật tăng trưởng doanh số 2026 mà Agency giấu bạn.',
            audio: 'Tiếng ding hiệu ứng pop-up bất ngờ'
          },
          {
            title: 'Cảnh 1',
            visual: 'Màn hình hiển thị dashboard AI phân tích số liệu đa kênh',
            voiceover: 'Mọi chiến dịch được kiểm soát chỉ trong 1 màn hình duy nhất.',
            audio: 'Nhạc nền tăng dần tốc độ'
          },
          {
            title: 'Cảnh 2',
            visual: 'Nhân vật mỉm cười bấm nút xuất bản kế hoạch hoàn tất',
            voiceover: 'Tiết kiệm 80% thời gian sáng tạo nội dung mỗi ngày.',
            audio: 'Âm thanh hoàn thành nhiệm vụ'
          },
          {
            title: 'CTA',
            visual: 'Mũi tên chỉ vào link bio kèm mã ưu đãi độc quyền',
            voiceover: 'Bấm ngay link bio để nhận bản dùng thử Enterprise miễn phí!',
            audio: 'Hiệu ứng click chuột sống động'
          }
        ];

  const currentScene = allScenes[activeSceneIndex] || allScenes[0];

  return (
    <div className="flex flex-col items-center">
      {/* 1. KHUNG THIẾT BỊ ĐIỆN THOẠI 9:16 */}
      <div className="relative w-full max-w-[320px] aspect-[9/16] bg-slate-950 rounded-[44px] p-2.5 shadow-2xl ring-1 ring-slate-800 border-[6px] border-slate-900 select-none overflow-hidden flex flex-col justify-between">
        {/* Nền Video (Ảnh thật hoặc Cyberpunk Gradient) */}
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="TikTok Background"
            className="absolute inset-0 w-full h-full object-cover opacity-75 transition-opacity duration-300"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-950 via-slate-900 to-black opacity-95"></div>
        )}

        {/* Lớp phủ tối điện ảnh (Vignette & Gradient Shadow) */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/25 to-black/60 pointer-events-none z-10"></div>

        {/* TOP HARDWARE: Dynamic Island & Status Bar */}
        <div className="relative z-20 pt-1 px-4">
          <div className="flex items-center justify-between text-[11px] text-white/90 font-semibold px-2 mb-1.5">
            <span>9:41</span>
            {/* Dynamic Island Capsule */}
            <div className="w-20 h-4 bg-black rounded-full flex items-center justify-end pr-2 ring-1 ring-white/10">
              <span className="w-2 h-2 rounded-full bg-blue-900/60 border border-blue-400/40"></span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-[10px]">5G</span>
              <div className="w-4 h-2 border border-white/80 rounded-xs p-0.5 flex items-center">
                <div className="w-2.5 h-full bg-white rounded-2xs"></div>
              </div>
            </div>
          </div>

          {/* TikTok Segmented Progress Bars */}
          <div className="flex items-center gap-1 px-1">
            {allScenes.map((_, i) => (
              <div
                key={i}
                onClick={() => setActiveSceneIndex(i)}
                className={`h-1 flex-1 rounded-full cursor-pointer transition-all duration-300 ${
                  i === activeSceneIndex
                    ? 'bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)]'
                    : i < activeSceneIndex
                    ? 'bg-white/60'
                    : 'bg-white/20'
                }`}
              />
            ))}
          </div>

          {/* TikTok Top Header Tabs */}
          <div className="flex items-center justify-center gap-4 text-xs font-bold text-white/70 mt-2">
            <span className="hover:text-white cursor-pointer transition">Đang theo dõi</span>
            <span className="text-white border-b-2 border-white pb-0.5">Dành cho bạn</span>
          </div>
        </div>

        {/* CENTER STAGE: Visual Action Pill & Kinetic Captions */}
        <div className="relative z-20 px-3 flex flex-col items-center justify-center my-auto space-y-3">
          {/* Scene Selector Pill Navigation */}
          <div className="flex flex-wrap justify-center gap-1 max-w-[280px]">
            {allScenes.map((s, idx) => (
              <button
                key={idx}
                onClick={() => setActiveSceneIndex(idx)}
                className={`text-[9px] px-2 py-0.5 rounded-full font-bold transition shadow-xs ${
                  idx === activeSceneIndex
                    ? 'bg-yellow-400 text-slate-950 scale-105'
                    : 'bg-black/50 text-white/80 border border-white/20 hover:bg-black/70'
                }`}
              >
                {s.title}
              </button>
            ))}
          </div>

          {/* Visual Action Banner */}
          {currentScene.visual && (
            <div className="bg-black/70 backdrop-blur-md px-2.5 py-1.5 rounded-lg border border-amber-500/40 text-left max-w-[270px] shadow-lg animate-in fade-in duration-200">
              <div className="flex items-center gap-1 text-[10px] font-bold text-amber-300 mb-0.5">
                <Video className="w-3 h-3 text-amber-400" />
                <span>[Hành động hình ảnh / Visual]:</span>
              </div>
              <p className="text-[10px] text-white/90 leading-tight italic">
                {currentScene.visual}
              </p>
            </div>
          )}

          {/* Kinetic Voiceover Captions */}
          <div className="px-2 py-1 text-center max-w-[280px]">
            <p className="font-black text-xs sm:text-[13px] text-yellow-300 drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)] leading-snug tracking-wide">
              "{currentScene.voiceover}"
            </p>
          </div>
        </div>

        {/* RIGHT ACTION BAR & BOTTOM INFO AREA */}
        <div className="relative z-20 flex items-end justify-between px-3 pb-2">
          {/* Bottom Info: Creator Handle, Caption, Music Marquee */}
          <div className="flex-1 pr-3 text-white text-left space-y-1.5 max-w-[210px]">
            {/* Handle & Verified */}
            <div className="flex items-center gap-1">
              <span className="font-bold text-xs hover:underline cursor-pointer">
                @{brandName.toLowerCase().replace(/\s+/g, '_')}
              </span>
              <span className="w-3 h-3 bg-cyan-400 text-black rounded-full flex items-center justify-center text-[8px] font-black">
                ✓
              </span>
            </div>

            {/* Caption */}
            <p className="text-[11px] text-white/95 leading-tight line-clamp-2">
              {caption || hook3s}
            </p>

            {/* Hashtags */}
            <div className="text-[10px] font-semibold text-white/80 space-x-1">
              {hashtags.slice(0, 3).map((tag, i) => (
                <span key={i} className="hover:underline cursor-pointer">
                  {tag}
                </span>
              ))}
            </div>

            {/* Music Marquee */}
            <div className="flex items-center gap-1.5 text-[10px] text-white/90 overflow-hidden pt-0.5">
              <Music className="w-3 h-3 text-white shrink-0 animate-pulse" />
              <div className="truncate whitespace-nowrap">
                ♫ {effectiveAudio}
              </div>
            </div>
          </div>

          {/* Right Action Icons Column */}
          <div className="flex flex-col items-center gap-3 shrink-0 text-white">
            {/* Avatar with Follow Red Plus */}
            <div className="relative">
              <div className="w-9 h-9 rounded-full border-2 border-white overflow-hidden bg-gradient-to-tr from-pink-500 to-indigo-600 flex items-center justify-center text-xs font-bold shadow-md">
                {brandLogo ? (
                  <img src={brandLogo} alt={brandName} className="w-full h-full object-cover" />
                ) : (
                  brandName.slice(0, 1).toUpperCase()
                )}
              </div>
              <button
                onClick={() => setIsFollowed(!isFollowed)}
                className={`absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full flex items-center justify-center shadow transition ${
                  isFollowed ? 'bg-white text-rose-600' : 'bg-[#FE2C55] text-white'
                }`}
              >
                {isFollowed ? <Check className="w-2.5 h-2.5" /> : <Plus className="w-3 h-3" />}
              </button>
            </div>

            {/* Like Heart */}
            <button
              onClick={() => setIsLiked(!isLiked)}
              className="flex flex-col items-center group transition"
            >
              <div className={`p-1.5 rounded-full transition transform active:scale-125 ${isLiked ? 'text-[#FE2C55]' : 'text-white'}`}>
                <Heart className={`w-6 h-6 ${isLiked ? 'fill-[#FE2C55]' : ''}`} />
              </div>
              <span className="text-[10px] font-bold mt-[-2px]">
                {isLiked ? '142.9K' : '142.8K'}
              </span>
            </button>

            {/* Comments */}
            <div className="flex flex-col items-center">
              <div className="p-1.5 text-white">
                <MessageSquare className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold mt-[-2px]">2,390</span>
            </div>

            {/* Bookmark */}
            <button
              onClick={() => setIsBookmarked(!isBookmarked)}
              className="flex flex-col items-center"
            >
              <div className={`p-1.5 transition ${isBookmarked ? 'text-amber-400' : 'text-white'}`}>
                <Bookmark className={`w-6 h-6 ${isBookmarked ? 'fill-amber-400' : ''}`} />
              </div>
              <span className="text-[10px] font-bold mt-[-2px]">18.5K</span>
            </button>

            {/* Share */}
            <div className="flex flex-col items-center">
              <div className="p-1.5 text-white">
                <Share2 className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold mt-[-2px]">6,712</span>
            </div>

            {/* Vinyl Disc Rotating Animation */}
            <div className="w-8 h-8 rounded-full bg-slate-900 border-2 border-slate-700 flex items-center justify-center shadow-lg animate-spin [animation-duration:4s]">
              <div className="w-3.5 h-3.5 rounded-full bg-rose-500 border border-white flex items-center justify-center">
                <span className="w-1 h-1 bg-white rounded-full"></span>
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM HARDWARE: Home Indicator */}
        <div className="relative z-20 w-28 h-1 bg-white/40 rounded-full mx-auto mb-0.5"></div>
      </div>

      {/* Control bar dưới điện thoại: Đổi ảnh nền & thông tin phân cảnh */}
      {onImageChange && (
        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={() => setIsPickerOpen(!isPickerOpen)}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white text-xs font-medium rounded-xl shadow-xs transition flex items-center gap-1.5"
          >
            <ImageIcon className="w-3.5 h-3.5 text-indigo-400" />
            {imageUrl ? 'Đổi ảnh nền Video' : 'Gắn ảnh nền Video'}
          </button>
        </div>
      )}

      {/* Image Picker Dropdown */}
      {isPickerOpen && onImageChange && (
        <div className="mt-2 w-full max-w-[340px]">
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
    </div>
  );
};
