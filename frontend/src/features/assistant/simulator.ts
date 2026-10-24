import type { AiAction, AiMessage } from '@/lib/types';
import type { AssistantStreamEventCallback } from './types';

/**
 * Cờ kiểm tra chế độ mô phỏng SSE khi phát triển (DEV ONLY).
 * Phải được bật tường minh bằng VITE_ASSISTANT_SIMULATOR=true trong môi trường DEV.
 * Trong production build (import.meta.env.DEV === false), toàn bộ mã bên trong sẽ được loại bỏ (tree-shake).
 */
export const isSimulatorActive =
  import.meta.env.DEV && import.meta.env.VITE_ASSISTANT_SIMULATOR === 'true';

/**
 * Mô phỏng chuỗi sự kiện SSE thực tế cho một lượt trò chuyện với Trợ lý AI.
 * Trả về chuỗi các sự kiện: message_start -> status -> tool_call -> text -> action -> message_end.
 */
export async function simulateAssistantStream(
  threadId: number,
  userPrompt: string,
  callbacks: AssistantStreamEventCallback,
  signal?: AbortSignal,
): Promise<void> {
  if (!import.meta.env.DEV) {
    throw new Error('Chế độ mô phỏng chỉ được sử dụng trong môi trường phát triển (DEV).');
  }

  const delay = (ms: number) =>
    new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => resolve(), ms);
      if (signal) {
        signal.addEventListener('abort', () => {
          clearTimeout(timer);
          reject(new DOMException('Aborted', 'AbortError'));
        });
      }
    });

  const now = new Date().toISOString();
  const userMsgId = Date.now();
  const assistantMsgId = userMsgId + 1;
  const actionId = Math.floor(Math.random() * 100000) + 100;

  // 1. message_start
  const mockUserMessage: AiMessage = {
    id: userMsgId,
    thread_id: threadId,
    role: 'USER',
    content: userPrompt,
    parts_json: [],
    status: 'COMPLETE',
    error_code: null,
    model: null,
    latency_ms: null,
    created_at: now,
    updated_at: now,
  };

  callbacks.onMessageStart?.({
    user_message: mockUserMessage,
    assistant_message: {
      id: assistantMsgId,
      status: 'STREAMING',
    },
  });

  try {
    // 2. status: queued
    await delay(300);
    callbacks.onStatus?.({ phase: 'queued', queue_position: 1 });

    // 3. status: thinking
    await delay(500);
    callbacks.onStatus?.({ phase: 'thinking' });

    // 4. status: tool & tool_call 1: get_brand_profile
    await delay(600);
    callbacks.onStatus?.({ phase: 'tool' });
    callbacks.onToolCall?.({
      id: 'call_brand_1',
      name: 'get_brand_profile',
      args: {},
      status: 'running',
      summary: 'Đọc thông tin thương hiệu & từ khoá cấm...',
    });

    await delay(800);
    callbacks.onToolCall?.({
      id: 'call_brand_1',
      name: 'get_brand_profile',
      args: {},
      status: 'done',
      summary: 'Đã tải hồ sơ thương hiệu (giọng điệu mộc mạc, gần gũi, 12 từ cấm).',
    });

    // 5. tool_call 2: propose_content_drafts
    await delay(500);
    callbacks.onToolCall?.({
      id: 'call_drafts_2',
      name: 'propose_content_drafts',
      args: {
        channel_code: 'FACEBOOK',
        count: 2,
      },
      status: 'running',
      summary: 'Khởi tạo 2 đề xuất bản nháp nội dung cho Facebook...',
    });

    await delay(700);
    callbacks.onToolCall?.({
      id: 'call_drafts_2',
      name: 'propose_content_drafts',
      args: {
        channel_code: 'FACEBOOK',
        count: 2,
      },
      status: 'done',
      summary: 'Đã tạo 2 bản nháp nội dung mới chờ bạn kiểm tra.',
    });

    // 6. action event: AiAction
    const mockAction: AiAction = {
      id: actionId,
      thread_id: threadId,
      message_id: assistantMsgId,
      user_id: 1,
      tool: 'propose_content_drafts',
      args_json: {
        items: [
          {
            campaign_id: null,
            channel_code: 'FACEBOOK',
            content_type: 'SOCIAL_POST',
            title: 'Hương vị sớm mai — Đánh thức ngày mới cùng Robusta Mộc',
            body: 'Mỗi buổi sáng bắt đầu bằng một tách cà phê thơm dịu, rang mộc 100% từ cao nguyên Gia Lai.\n\nKhông phụ gia, không hương liệu tổng hợp — chỉ có vị đắng thanh thoát và hậu vị ngọt sâu lưu luyến.\n\nNhắn tin ngay cho chúng mình để nhận ưu đãi dùng thử gói 250g đầu tiên nhé!',
            cta: 'Nhắn tin để nhận ưu đãi',
            submit_mode: 'PENDING_REVIEW',
          },
          {
            campaign_id: null,
            channel_code: 'FACEBOOK',
            content_type: 'SOCIAL_POST',
            title: 'Bí quyết chọn hạt cà phê rang mộc chuẩn vị',
            body: 'Làm thế nào để nhận biết cà phê rang mộc nguyên chất?\n1. Màu hạt nâu cánh gián đồng đều, bề mặt khô ráo không bóng dầu mỡ.\n2. Hương thơm dịu nhẹ tự nhiên khi mở túi, không nồng gắt mùi bơ nhân tạo.\n3. Khi pha, bột cà phê nở phồng nhẹ và dòng chảy có sắc nâu hổ phách trong trẻo.\n\nKhám phá trọn vẹn bộ sưu tập hạt đặc sản tại cửa hàng của chúng tôi.',
            cta: 'Xem chi tiết sản phẩm',
            submit_mode: 'PENDING_REVIEW',
          },
        ],
      },
      summary: 'Đề xuất 2 bài đăng Facebook cho dòng sản phẩm cà phê rang mộc',
      status: 'PROPOSED',
      result_json: null,
      error: null,
      executed_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    callbacks.onAction?.(mockAction);

    // 7. status: writing & sequential text events (toàn bộ nội dung tích luỹ per §6)
    await delay(400);
    callbacks.onStatus?.({ phase: 'writing' });

    const textPart1 =
      'Chào bạn! Dựa trên hồ sơ thương hiệu và yêu cầu của bạn, tôi đã chuẩn bị **2 ý tưởng bài đăng Facebook** phù hợp với phong cách mộc mạc, tự nhiên:\n\n';

    const textPart2 =
      textPart1 +
      '### Tóm tắt định hướng nội dung\n' +
      '- **Bài 1 (Cảm xúc & Chuyển đổi):** Nhấn mạnh vào trải nghiệm thức giấc và tách cà phê sớm mai nguyên chất, thúc đẩy khách hàng nhắn tin nhận ưu đãi.\n' +
      '- **Bài 2 (Giáo dục & Giá trị):** Hướng dẫn 3 cách nhận biết hạt cà phê rang mộc chuẩn gu, xây dựng niềm tin chuyên gia trong lòng khách hàng.\n\n';

    const textPart3 =
      textPart2 +
      '> Bạn có thể kiểm tra trực tiếp, chỉnh sửa câu chữ hoặc chọn lưu nháp / gửi duyệt ở **panel bên phải** (Đề xuất & bản nháp). Nếu cần điều chỉnh thêm kênh khác (như TikTok hay Email), bạn cứ nhắn cho tôi nhé!';

    callbacks.onText?.({ content: textPart1 });
    await delay(350);
    callbacks.onText?.({ content: textPart2 });
    await delay(450);
    callbacks.onText?.({ content: textPart3 });
    await delay(300);

    // 8. message_end: AiMessage hoàn chỉnh
    const mockAssistantMessage: AiMessage = {
      id: assistantMsgId,
      thread_id: threadId,
      role: 'ASSISTANT',
      content: textPart3,
      parts_json: [
        {
          type: 'tool_call',
          id: 'call_brand_1',
          name: 'get_brand_profile',
          args: {},
          status: 'done',
          summary: 'Đã tải hồ sơ thương hiệu (giọng điệu mộc mạc, gần gũi, 12 từ cấm).',
        },
        {
          type: 'tool_call',
          id: 'call_drafts_2',
          name: 'propose_content_drafts',
          args: { channel_code: 'FACEBOOK', count: 2 },
          status: 'done',
          summary: 'Đã tạo 2 bản nháp nội dung mới chờ bạn kiểm tra.',
        },
        {
          type: 'action',
          action_id: actionId,
        },
      ],
      status: 'COMPLETE',
      error_code: null,
      model: 'opencode-zen',
      latency_ms: 3200,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    callbacks.onMessageEnd?.({ message: mockAssistantMessage });
  } catch (err) {
    if (signal?.aborted) {
      return;
    }
    throw err;
  }
}
