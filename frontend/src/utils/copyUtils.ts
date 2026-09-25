/**
 * FEAT-FE-13: 1-Click Copy Format Tool
 * Chuẩn hóa Unicode NFC, bảo toàn 100% ngắt dòng, tab, emoji và ký tự đặc biệt.
 * Hỗ trợ định dạng chuyên biệt theo từng kênh mạng xã hội.
 */

export interface FacebookCopyPayload {
  title?: string;
  body: string;
  cta?: string;
  hashtags?: string[];
}

export interface TikTokSceneCopyItem {
  scene?: number;
  scene_number?: number;
  visual?: string;
  visual_action?: string;
  voiceover?: string;
  voiceover_script?: string;
  audio?: string;
}

export interface TikTokCopyPayload {
  hook3s?: string;
  scenes?: TikTokSceneCopyItem[];
  suggestedAudio?: string;
  caption?: string;
  hashtags?: string[];
}

export interface EmailCopyPayload {
  subject?: string;
  subjectOptions?: string[];
  preheader?: string;
  greeting?: string;
  body: string;
  ctaButton?: string;
  psNote?: string;
}

/**
 * Sao chép văn bản vào bộ nhớ tạm hệ điều hành với bảo toàn byte-level Unicode & ngắt dòng
 */
export async function copyToClipboardWithFormatting(text: string): Promise<boolean> {
  if (!text) return false;
  const normalized = text.normalize('NFC');

  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(normalized);
      return true;
    }
  } catch (err) {
    console.warn('navigator.clipboard failed, attempting textarea fallback', err);
  }

  // Fallback cho trình duyệt cũ hoặc môi trường iframe/HTTP
  try {
    const textArea = document.createElement('textarea');
    textArea.value = normalized;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    textArea.style.top = '-9999px';
    textArea.setAttribute('readonly', '');
    document.body.appendChild(textArea);
    textArea.select();
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    return successful;
  } catch (fallbackErr) {
    console.error('Fallback copy command failed:', fallbackErr);
    return false;
  }
}

/**
 * Định dạng bài viết Facebook chuẩn format để copy
 */
export function formatFacebookCopy(payload: FacebookCopyPayload): string {
  const parts: string[] = [];
  if (payload.title?.trim()) {
    parts.push(payload.title.trim());
  }
  if (payload.body?.trim()) {
    parts.push(payload.body.trim());
  }
  if (payload.cta?.trim()) {
    parts.push(`👉 ${payload.cta.trim()}`);
  }
  if (payload.hashtags && payload.hashtags.length > 0) {
    const tags = payload.hashtags
      .map(tag => (tag.startsWith('#') ? tag : `#${tag}`))
      .join(' ');
    parts.push(tags);
  }
  return parts.join('\n\n');
}

/**
 * Định dạng kịch bản TikTok 9:16 chuẩn format để copy
 */
export function formatTikTokCopy(payload: TikTokCopyPayload): string {
  const lines: string[] = ['🎬 KỊCH BẢN VIDEO TIKTOK / REELS NGẮN\n'];

  if (payload.hook3s?.trim()) {
    lines.push(`⚡ HOOK 3 GIÂY ĐẦU:\n"${payload.hook3s.trim()}"\n`);
  }

  if (payload.scenes && payload.scenes.length > 0) {
    lines.push('📋 PHÂN CẢNH CHI TIẾT:');
    payload.scenes.forEach((s, idx) => {
      const sceneNum = s.scene || s.scene_number || idx + 1;
      lines.push(`\n[Cảnh ${sceneNum}]`);
      const visual = s.visual_action || s.visual;
      if (visual) lines.push(`• Hình ảnh / Hành động: ${visual}`);
      const voice = s.voiceover_script || s.voiceover;
      if (voice) lines.push(`• Lời thoại (Voiceover): "${voice}"`);
      if (s.audio) lines.push(`• Âm thanh / Hiệu ứng: ${s.audio}`);
    });
    lines.push('');
  }

  if (payload.caption?.trim()) {
    lines.push(`📝 CAPTION:\n${payload.caption.trim()}`);
  }

  if (payload.hashtags && payload.hashtags.length > 0) {
    const tags = payload.hashtags
      .map(tag => (tag.startsWith('#') ? tag : `#${tag}`))
      .join(' ');
    lines.push(`🏷️ HASHTAGS:\n${tags}`);
  }

  if (payload.suggestedAudio?.trim()) {
    lines.push(`🎵 GỢI Ý ÂM NHẠC: ${payload.suggestedAudio.trim()}`);
  }

  return lines.join('\n');
}

/**
 * Định dạng Email Newsletter chuẩn format để copy
 */
export function formatEmailCopy(payload: EmailCopyPayload): string {
  const parts: string[] = [];

  const subject = payload.subject || (payload.subjectOptions && payload.subjectOptions[0]) || '';
  if (subject) {
    parts.push(`📧 TIÊU ĐỀ (SUBJECT): ${subject}`);
  }
  if (payload.preheader?.trim()) {
    parts.push(`🔍 ĐOẠN TRÍCH (PREHEADER): ${payload.preheader.trim()}`);
  }
  if (payload.greeting?.trim()) {
    parts.push(`${payload.greeting.trim()},\n`);
  }
  if (payload.body?.trim()) {
    parts.push(payload.body.trim());
  }
  if (payload.ctaButton?.trim()) {
    parts.push(`\n[ NÚT KÊU GỌI HÀNH ĐỘNG ]: 👉 ${payload.ctaButton.trim()}`);
  }
  if (payload.psNote?.trim()) {
    parts.push(`\nP.S. ${payload.psNote.trim()}`);
  }

  return parts.join('\n\n');
}
