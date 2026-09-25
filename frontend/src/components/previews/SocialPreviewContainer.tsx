import React, { useState } from 'react';
import { Eye, FileText, Copy, Check, Image as ImageIcon, Sparkles } from 'lucide-react';
import { MarketingContent } from '../../types';
import { FacebookPreviewCard } from './FacebookPreviewCard';
import { TikTokPhoneMockup, TikTokSceneItem } from './TikTokPhoneMockup';
import { EmailInboxPreview } from './EmailInboxPreview';
import { ImageAttachmentPicker } from './ImageAttachmentPicker';
import { copyToClipboardWithFormatting, formatFacebookCopy, formatTikTokCopy, formatEmailCopy } from '../../utils/copyUtils';

export type TikTokScene = TikTokSceneItem;

/**
 * Trích xuất danh sách phân cảnh TikTok chân thực từ content.body (R4 Remediation)
 * Tự động nhận diện định dạng có cấu trúc ([Cảnh 1: ...], Visual/Thoại, ---) hoặc văn bản thường (chia Hook, Thân bài, CTA)
 */
export function parseTikTokScenesFromBody(body?: string | null): TikTokSceneItem[] {
  if (!body || !body.trim()) return [];

  const rawText = body.trim();

  // 1. Kiểm tra cấu trúc phân cảnh chuẩn: [Cảnh 1: ...] hoặc Cảnh 1: hoặc Phân cảnh 1: hoặc Scene 1:
  const sceneRegex = /(?:\[\s*(?:Cảnh|Phân cảnh|Scene)\s*(\d+)[:\s-]*([^\]\n]*?)\]|(?:^|\n)\s*(?:Cảnh|Phân cảnh|Scene)\s*(\d+)[:\s-]*([^\n]*))/gi;
  
  const matches = [...rawText.matchAll(sceneRegex)];

  if (matches.length > 0) {
    const scenes: TikTokSceneItem[] = [];
    
    for (let i = 0; i < matches.length; i++) {
      const match = matches[i];
      const sceneNum = parseInt(match[1] || match[3] || String(i + 1), 10);
      const sceneName = (match[2] || match[4] || '').trim().replace(/\(\s*\d+\s*s\s*\)/i, '').trim();
      
      const startIndex = match.index! + match[0].length;
      const endIndex = (i + 1 < matches.length) ? matches[i + 1].index! : rawText.length;
      const block = rawText.slice(startIndex, endIndex);

      // Trích xuất Visual
      const visualMatch = block.match(/(?:-\s*)?(?:Visual|Hình ảnh|Thị giác|Hành động)\s*[:：]\s*([^\n\r]+)/i);
      const visual = visualMatch ? visualMatch[1].trim() : '';

      // Trích xuất Voiceover / Thoại
      const voiceMatch = block.match(/(?:-\s*)?(?:Thoại|Lời thoại|Voiceover|Voice|Kịch bản thoại)\s*[:：]\s*([^\n\r]+)/i);
      const voiceover = voiceMatch ? voiceMatch[1].trim().replace(/^["']|["']$/g, '') : '';

      // Trích xuất Âm thanh / Audio
      const audioMatch = block.match(/(?:-\s*)?(?:Âm thanh|Audio|Nhạc|Sound)\s*[:：]\s*([^\n\r]+)/i);
      const audio = audioMatch ? audioMatch[1].trim() : undefined;

      // Trích xuất thời lượng
      const durationMatch = (match[0] + block).match(/(\d+)\s*s\b/i);
      const duration = durationMatch ? parseInt(durationMatch[1], 10) : 5;

      const fallbackText = block
        .replace(/(?:-\s*)?(?:Visual|Hình ảnh|Thị giác|Hành động|Thoại|Lời thoại|Voiceover|Voice|Kịch bản thoại|Âm thanh|Audio|Nhạc|Sound)\s*[:：][^\n\r]+/gi, '')
        .replace(/(?:ÂM NHẠC ĐỀ XUẤT|HASHTAGS?)[\s\S]*/gi, '')
        .trim();

      const finalVisual = visual || (fallbackText ? `Góc quay mô tả: ${fallbackText.slice(0, 80)}` : `Chuyển cảnh minh họa Cảnh ${sceneNum}`);
      const finalVoiceover = voiceover || fallbackText || `Lời thoại kịch bản phân cảnh ${sceneNum}`;

      scenes.push({
        scene: sceneNum,
        scene_number: sceneNum,
        scene_name: sceneName || `Cảnh ${sceneNum}`,
        title: sceneName ? `Cảnh ${sceneNum}: ${sceneName}` : `Cảnh ${sceneNum}`,
        visual: finalVisual,
        visual_action: finalVisual,
        voiceover: finalVoiceover,
        voiceover_script: finalVoiceover,
        audio,
        duration_seconds: duration
      });
    }

    if (scenes.length > 0) return scenes;
  }

  // 2. Kiểm tra nếu các cảnh được phân cách bởi '---'
  if (rawText.includes('---')) {
    const rawParts = rawText.split('---').map(p => p.trim()).filter(Boolean);
    if (rawParts.length >= 2) {
      return rawParts.map((part, idx) => {
        const visualMatch = part.match(/(?:Visual|Hình ảnh)\s*[:：]\s*([^\n]+)/i);
        const voiceMatch = part.match(/(?:Thoại|Lời thoại|Voiceover)\s*[:：]\s*([^\n]+)/i);
        const cleanContent = part.replace(/(?:Visual|Thoại|Voiceover)[^:\n]*:[^\n]+/gi, '').trim();

        const title = idx === 0 ? 'Cảnh 1: Hook mở đầu' : idx === rawParts.length - 1 ? 'Cảnh 3: Kêu gọi hành động (CTA)' : `Cảnh ${idx + 1}: Thân bài & Giá trị`;
        const visual = visualMatch ? visualMatch[1].trim() : `Quay cận cảnh phân đoạn ${idx + 1}`;
        const voiceover = voiceMatch ? voiceMatch[1].trim() : (cleanContent || `Lời thoại phân đoạn ${idx + 1}`);

        return {
          scene: idx + 1,
          scene_number: idx + 1,
          title,
          scene_name: title,
          visual,
          visual_action: visual,
          voiceover,
          voiceover_script: voiceover,
          duration_seconds: 5
        };
      });
    }
  }

  // 3. Fallback: Body là văn bản thông thường (chia 3-4 cảnh: Hook, Thân bài/Giá trị, CTA)
  let cleanText = rawText
    .replace(/^HOOK\s*\([^)]*\)\s*[:：]?/im, '')
    .replace(/(?:ÂM NHẠC ĐỀ XUẤT|MUSIC|HASHTAGS?)[:\s][\s\S]*$/im, '')
    .trim();

  // Tách theo đoạn văn hoặc câu
  const paragraphs = cleanText.split(/\n+/).map(p => p.trim()).filter(p => p.length > 0);
  
  let sentences: string[] = [];
  if (paragraphs.length >= 3) {
    sentences = paragraphs;
  } else {
    sentences = cleanText
      .split(/(?<=[.!?。])\s+/)
      .map(s => s.trim())
      .filter(s => s.length > 5);
    
    if (sentences.length < 2) {
      sentences = paragraphs.length > 0 ? paragraphs : [cleanText];
    }
  }

  if (sentences.length <= 1) {
    const single = sentences[0] || cleanText;
    return [
      {
        scene: 1,
        scene_number: 1,
        title: 'Cảnh 1: Hook mở đầu',
        scene_name: 'Hook mở đầu',
        visual: 'Quay cận cảnh biểu cảm ấn tượng hoặc thông điệp gây chú ý trong 3 giây',
        visual_action: 'Quay cận cảnh biểu cảm ấn tượng hoặc thông điệp gây chú ý trong 3 giây',
        voiceover: single,
        voiceover_script: single,
        duration_seconds: 3
      },
      {
        scene: 2,
        scene_number: 2,
        title: 'Cảnh 2: Thân bài & Giá trị',
        scene_name: 'Thân bài & Giá trị',
        visual: 'Chuyển cảnh minh họa thực tế tính năng giải pháp và lợi ích nổi bật',
        visual_action: 'Chuyển cảnh minh họa thực tế tính năng giải pháp và lợi ích nổi bật',
        voiceover: 'Khám phá chi tiết giải pháp thông minh giúp tối ưu hóa hiệu suất vượt bậc.',
        voiceover_script: 'Khám phá chi tiết giải pháp thông minh giúp tối ưu hóa hiệu suất vượt bậc.',
        duration_seconds: 5
      },
      {
        scene: 3,
        scene_number: 3,
        title: 'Cảnh 3: Kêu gọi hành động (CTA)',
        scene_name: 'Kêu gọi hành động (CTA)',
        visual: 'Hiệu ứng trỏ vào link bio hoặc nút bấm nhận ưu đãi độc quyền',
        visual_action: 'Hiệu ứng trỏ vào link bio hoặc nút bấm nhận ưu đãi độc quyền',
        voiceover: 'Nhấn ngay vào link bên dưới để nhận tư vấn và ưu đãi đặc biệt hôm nay!',
        voiceover_script: 'Nhấn ngay vào link bên dưới để nhận tư vấn và ưu đãi đặc biệt hôm nay!',
        duration_seconds: 4
      }
    ];
  }

  if (sentences.length === 2) {
    return [
      {
        scene: 1,
        scene_number: 1,
        title: 'Cảnh 1: Hook mở đầu',
        scene_name: 'Hook mở đầu',
        visual: 'Quay cận cảnh tạo ấn tượng thị giác 3 giây đầu tiên',
        visual_action: 'Quay cận cảnh tạo ấn tượng thị giác 3 giây đầu tiên',
        voiceover: sentences[0],
        voiceover_script: sentences[0],
        duration_seconds: 3
      },
      {
        scene: 2,
        scene_number: 2,
        title: 'Cảnh 2: Thân bài & Giá trị',
        scene_name: 'Thân bài & Giá trị',
        visual: 'Mô phỏng trải nghiệm người dùng và kết quả thực tế vượt trội',
        visual_action: 'Mô phỏng trải nghiệm người dùng và kết quả thực tế vượt trội',
        voiceover: sentences[1],
        voiceover_script: sentences[1],
        duration_seconds: 6
      },
      {
        scene: 3,
        scene_number: 3,
        title: 'Cảnh 3: Kêu gọi hành động (CTA)',
        scene_name: 'Kêu gọi hành động (CTA)',
        visual: 'Hiển thị nút CTA và thông tin liên hệ / bio rõ ràng',
        visual_action: 'Hiển thị nút CTA và thông tin liên hệ / bio rõ ràng',
        voiceover: 'Theo dõi kênh và bấm link bio ngay để không bỏ lỡ!',
        voiceover_script: 'Theo dõi kênh và bấm link bio ngay để không bỏ lỡ!',
        duration_seconds: 4
      }
    ];
  }

  // sentences.length >= 3:
  const hookSentence = sentences[0];
  const ctaSentence = sentences[sentences.length - 1];
  const bodySentences = sentences.slice(1, sentences.length - 1);

  if (bodySentences.length === 1) {
    return [
      {
        scene: 1,
        scene_number: 1,
        title: 'Cảnh 1: Hook mở đầu',
        scene_name: 'Hook mở đầu',
        visual: 'Quay cận cảnh gương mặt hoặc biểu đồ thu hút chú ý trong 3 giây',
        visual_action: 'Quay cận cảnh gương mặt hoặc biểu đồ thu hút chú ý trong 3 giây',
        voiceover: hookSentence,
        voiceover_script: hookSentence,
        duration_seconds: 3
      },
      {
        scene: 2,
        scene_number: 2,
        title: 'Cảnh 2: Thân bài & Giá trị',
        scene_name: 'Thân bài & Giá trị',
        visual: 'Thao tác thực tế trên giải pháp, trình bày lợi ích cốt lõi',
        visual_action: 'Thao tác thực tế trên giải pháp, trình bày lợi ích cốt lõi',
        voiceover: bodySentences[0],
        voiceover_script: bodySentences[0],
        duration_seconds: 6
      },
      {
        scene: 3,
        scene_number: 3,
        title: 'Cảnh 3: Kêu gọi hành động (CTA)',
        scene_name: 'Kêu gọi hành động (CTA)',
        visual: 'Mũi tên sinh động chỉ vào link bio kèm ưu đãi độc quyền',
        visual_action: 'Mũi tên sinh động chỉ vào link bio kèm ưu đãi độc quyền',
        voiceover: ctaSentence,
        voiceover_script: ctaSentence,
        duration_seconds: 4
      }
    ];
  }

  // >= 4 sentences: create 4 scenes (Hook, Problem, Solution, CTA)
  const problemSentence = bodySentences[0];
  const solutionSentence = bodySentences.slice(1).join(' ');

  return [
    {
      scene: 1,
      scene_number: 1,
      title: 'Cảnh 1: Hook mở đầu',
      scene_name: 'Hook mở đầu',
      visual: 'Quay cận cảnh biểu cảm bất ngờ trước vấn đề nhức nhối',
      visual_action: 'Quay cận cảnh biểu cảm bất ngờ trước vấn đề nhức nhối',
      voiceover: hookSentence,
      voiceover_script: hookSentence,
      duration_seconds: 3
    },
    {
      scene: 2,
      scene_number: 2,
      title: 'Cảnh 2: Vấn đề / Thực trạng',
      scene_name: 'Vấn đề / Thực trạng',
      visual: 'Hình ảnh mô tả khó khăn thực tế mà khách hàng đang đối mặt',
      visual_action: 'Hình ảnh mô tả khó khăn thực tế mà khách hàng đang đối mặt',
      voiceover: problemSentence,
      voiceover_script: problemSentence,
      duration_seconds: 5
    },
    {
      scene: 3,
      scene_number: 3,
      title: 'Cảnh 3: Giải pháp đột phá',
      scene_name: 'Giải pháp đột phá',
      visual: 'Màn hình minh họa giải pháp tự động hóa giúp giải quyết triệt để vấn đề',
      visual_action: 'Màn hình minh họa giải pháp tự động hóa giúp giải quyết triệt để vấn đề',
      voiceover: solutionSentence,
      voiceover_script: solutionSentence,
      duration_seconds: 6
    },
    {
      scene: 4,
      scene_number: 4,
      title: 'Cảnh 4: Kêu gọi hành động (CTA)',
      scene_name: 'Kêu gọi hành động (CTA)',
      visual: 'Mũi tên chỉ vào bio kèm banner ưu đãi và lời kêu gọi dứt khoát',
      visual_action: 'Mũi tên chỉ vào bio kèm banner ưu đãi và lời kêu gọi dứt khoát',
      voiceover: ctaSentence,
      voiceover_script: ctaSentence,
      duration_seconds: 4
    }
  ];
}

export interface SocialPreviewContainerProps {
  content: MarketingContent;
  brandName?: string;
  brandLogo?: string;
  onImageChange?: (contentId: number, newImageUrl: string) => void;
  defaultToPreview?: boolean;
}

export const SocialPreviewContainer: React.FC<SocialPreviewContainerProps> = ({
  content,
  brandName = 'MarketFlow Brand',
  brandLogo,
  onImageChange,
  defaultToPreview = true
}) => {
  const [viewMode, setViewMode] = useState<'RAW' | 'PREVIEW'>(defaultToPreview ? 'PREVIEW' : 'RAW');
  const [copied, setCopied] = useState(false);
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  // Nhận diện loại kênh từ channel_id hoặc channel.code
  const channelCode = (content.channel?.code || '').toUpperCase();
  const isFacebook = content.channel_id === 1 || channelCode.includes('FACEBOOK') || channelCode.includes('FB');
  const isTikTok = content.channel_id === 4 || content.channel_id === 5 || channelCode.includes('TIKTOK');
  const isEmail = content.channel_id === 2 || channelCode.includes('EMAIL') || channelCode.includes('MAIL');

  // Phân tích kịch bản TikTok thực tế từ content.body (R4 Remediation)
  const parsedTikTokScenes = isTikTok ? parseTikTokScenesFromBody(content.body) : [];

  const channelLabel = isFacebook ? 'Facebook Feed & Ads' : isTikTok ? 'TikTok Video Script (9:16)' : isEmail ? 'Email Newsletter' : (content.channel?.name || 'Mạng xã hội');

  const handleCopyFormatted = async () => {
    let copyText = '';
    if (isFacebook) {
      copyText = formatFacebookCopy({
        title: content.title,
        body: content.body,
        cta: content.cta,
        hashtags: ['#MarketFlow', '#Omnichannel', '#AI']
      });
    } else if (isTikTok) {
      copyText = formatTikTokCopy({
        hook3s: content.title,
        caption: content.body,
        hashtags: ['#TikTokAI', '#Shorts', '#ViralMarketing']
      });
    } else if (isEmail) {
      copyText = formatEmailCopy({
        subject: content.title,
        body: content.body,
        ctaButton: content.cta
      });
    } else {
      copyText = `${content.title}\n\n${content.body}${content.cta ? `\n\n👉 ${content.cta}` : ''}`;
    }

    const success = await copyToClipboardWithFormatting(copyText);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleImageUpdated = (newUrl: string) => {
    if (onImageChange) {
      onImageChange(content.id, newUrl);
    }
  };

  return (
    <div className="bg-slate-50/60 rounded-2xl border border-slate-200 overflow-hidden shadow-xs social-preview-container">
      {/* Top Toolbar */}
      <div className="bg-white px-4 py-2.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          {/* Channel Tag */}
          <span className={`px-2.5 py-1 rounded-full font-bold text-[11px] flex items-center gap-1 ${
            isFacebook
              ? 'bg-blue-50 text-blue-700 border border-blue-200'
              : isTikTok
              ? 'bg-slate-900 text-pink-400 border border-slate-700'
              : isEmail
              ? 'bg-purple-50 text-purple-700 border border-purple-200'
              : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
          }`}>
            {channelLabel}
          </span>

          {/* Status Badge */}
          <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase ${
            content.status === 'APPROVED'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : content.status === 'IN_REVIEW'
              ? 'bg-amber-50 text-amber-700 border border-amber-200'
              : content.status === 'REJECTED'
              ? 'bg-rose-50 text-rose-700 border border-rose-200'
              : 'bg-slate-100 text-slate-700 border border-slate-200'
          }`}>
            {content.status}
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          {/* Gắn ảnh */}
          {onImageChange && (
            <button
              onClick={() => setIsPickerOpen(!isPickerOpen)}
              className="px-2.5 py-1 text-slate-700 hover:text-indigo-600 hover:bg-indigo-50 border border-slate-200 rounded-lg text-xs font-medium transition flex items-center gap-1 shadow-2xs"
            >
              <ImageIcon className="w-3.5 h-3.5 text-indigo-600" />
              <span>{content.image_url ? 'Đổi ảnh' : 'Gắn ảnh'}</span>
            </button>
          )}

          {/* 1-Click Copy */}
          <button
            onClick={handleCopyFormatted}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition flex items-center gap-1 shadow-2xs border ${
              copied
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                : 'bg-white text-slate-700 hover:text-indigo-600 hover:bg-indigo-50 border-slate-200'
            }`}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="font-semibold text-emerald-600">Đã copy!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-500" />
                <span>1-Click Copy</span>
              </>
            )}
          </button>

          {/* Toggle View Mode */}
          <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              onClick={() => setViewMode('RAW')}
              className={`px-2 py-0.5 rounded-md text-[11px] font-medium transition flex items-center gap-1 ${
                viewMode === 'RAW'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <FileText className="w-3 h-3" />
              Văn bản
            </button>
            <button
              onClick={() => setViewMode('PREVIEW')}
              className={`px-2 py-0.5 rounded-md text-[11px] font-medium transition flex items-center gap-1 ${
                viewMode === 'PREVIEW'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Eye className="w-3 h-3" />
              Mô phỏng
            </button>
          </div>
        </div>
      </div>

      {/* Image Picker Panel */}
      {isPickerOpen && onImageChange && (
        <div className="p-3 bg-white border-b border-slate-200">
          <ImageAttachmentPicker
            currentImageUrl={content.image_url}
            onSelectImage={(newUrl) => {
              handleImageUpdated(newUrl);
              setIsPickerOpen(false);
            }}
            onClose={() => setIsPickerOpen(false)}
          />
        </div>
      )}

      {/* Main View Area */}
      <div className="p-4 sm:p-6 flex justify-center">
        {viewMode === 'RAW' ? (
          <div className="w-full bg-white p-5 rounded-xl border border-slate-200 text-left space-y-3">
            <h4 className="font-bold text-slate-900 text-base">{content.title}</h4>
            <p className="whitespace-pre-line text-xs sm:text-sm text-slate-700 leading-relaxed font-mono bg-slate-50 p-4 rounded-lg border border-slate-100">
              {content.body}
            </p>
            {content.cta && (
              <div className="text-xs font-semibold text-indigo-700">
                Lời kêu gọi hành động: <span className="underline">{content.cta}</span>
              </div>
            )}
            {content.image_url && (
              <div className="text-xs text-slate-500">
                Link ảnh đính kèm:{' '}
                <a
                  href={content.image_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-600 hover:underline break-all"
                >
                  {content.image_url}
                </a>
              </div>
            )}
          </div>
        ) : (
          <div className="w-full">
            {isFacebook && (
              <FacebookPreviewCard
                brandName={brandName}
                brandLogo={brandLogo}
                title={content.title}
                body={content.body}
                cta={content.cta}
                imageUrl={content.image_url}
                onImageChange={onImageChange ? (url) => handleImageUpdated(url) : undefined}
              />
            )}

            {isTikTok && (
              <TikTokPhoneMockup
                hook3s={content.title}
                caption={content.body}
                scenes={parsedTikTokScenes}
                brandName={brandName}
                brandLogo={brandLogo}
                imageUrl={content.image_url}
                onImageChange={onImageChange ? (url) => handleImageUpdated(url) : undefined}
              />
            )}

            {isEmail && (
              <EmailInboxPreview
                brandName={brandName}
                subjectOptions={[content.title]}
                body={content.body}
                ctaButton={content.cta}
                imageUrl={content.image_url}
                onImageChange={onImageChange ? (url) => handleImageUpdated(url) : undefined}
              />
            )}

            {!isFacebook && !isTikTok && !isEmail && (
              <FacebookPreviewCard
                brandName={brandName}
                brandLogo={brandLogo}
                title={content.title}
                body={content.body}
                cta={content.cta}
                imageUrl={content.image_url}
                onImageChange={onImageChange ? (url) => handleImageUpdated(url) : undefined}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
