import { useEffect, useRef, useState } from 'react';

/**
 * Hook tạo hiệu ứng gõ chữ mượt mà phía client cho phần văn bản mới nhận từ SSE.
 * Do SSE gửi toàn văn tích luỹ (accumulated text per §6 & §11), hook sẽ chỉ cho hiện dần
 * phần đuôi mới thêm vào. Bỏ qua hiệu ứng nếu người dùng bật chế độ giảm chuyển động
 * (prefers-reduced-motion), khi tab đang ẩn, hoặc khi luồng stream đã kết thúc.
 */
export function useTypingReveal(targetText: string, isStreaming: boolean): string {
  const [revealedLength, setRevealedLength] = useState(() => targetText.length);
  const targetRef = useRef(targetText);
  targetRef.current = targetText;

  // Kiểm tra prefers-reduced-motion
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Khi người dùng đổi tab trình duyệt rồi quay lại, đồng bộ ngay toàn bộ văn bản đã nhận
  useEffect(() => {
    if (typeof document === 'undefined') return;
    const handleVisibility = () => {
      if (document.visibilityState === 'visible' || document.visibilityState === 'hidden') {
        setRevealedLength(targetRef.current.length);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);

  useEffect(() => {
    const isTabHidden = typeof document !== 'undefined' && document.visibilityState === 'hidden';

    // Nếu giảm chuyển động, tab đang ẩn, hoặc không còn stream -> hiển thị toàn bộ ngay lập tức
    if (prefersReducedMotion || !isStreaming || isTabHidden) {
      setRevealedLength(targetText.length);
      return;
    }

    // Nếu văn bản bị rút ngắn (vd người dùng xoá hoặc tạo lại), đặt lại độ dài
    if (revealedLength > targetText.length) {
      setRevealedLength(targetText.length);
      return;
    }

    // Nếu đã hiển thị đủ thì không cần chạy timer
    if (revealedLength >= targetText.length) {
      return;
    }

    let animationFrameId: number;
    let lastTime = performance.now();

    const step = (currentTime: number) => {
      const elapsed = currentTime - lastTime;

      // Cập nhật mỗi ~25ms
      if (elapsed >= 25) {
        lastTime = currentTime;
        setRevealedLength((current) => {
          const target = targetRef.current.length;
          if (current >= target) {
            return target;
          }
          // Tự động tăng tốc độ tiết lộ nếu lượng chữ tồn đọng nhiều
          const remaining = target - current;
          const chunk = Math.max(2, Math.ceil(remaining / 6));
          const next = Math.min(target, current + chunk);
          return next;
        });
      }

      if (revealedLength < targetRef.current.length) {
        animationFrameId = requestAnimationFrame(step);
      }
    };

    animationFrameId = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [targetText, isStreaming, revealedLength, prefersReducedMotion]);

  if (prefersReducedMotion || !isStreaming) {
    return targetText;
  }

  return targetText.slice(0, revealedLength);
}
