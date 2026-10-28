// Plugin nội bộ của MarketFlow giúp phát từng mảnh văn bản (token delta) theo thời gian thực
// qua stdout JSONL trong khi OpenCode đang sinh câu trả lời, giảm TTFT từ ~30s xuống ~2-4s.
// Lưu ý quan trọng: Chỉ phát delta của part có type === "text" (bỏ qua "reasoning" / suy nghĩ nội bộ).
export const StreamDeltaPlugin = async () => {
  const partMeta = new Map();

  return {
    event: async ({ event }) => {
      if (!event) return;

      if (event.type === "message.part.updated") {
        const part = event.properties?.part;
        if (part && typeof part.id === "string" && typeof part.type === "string") {
          partMeta.set(part.id, {
            type: part.type,
            ignored: Boolean(part.ignored),
          });
        }
        return;
      }

      if (event.type !== "message.part.delta") return;
      const props = event.properties;
      if (!props || props.field !== "text" || typeof props.delta !== "string" || !props.delta) {
        return;
      }

      const meta = partMeta.get(props.partID);
      if (!meta || meta.type !== "text" || meta.ignored) {
        return;
      }

      process.stdout.write(
        JSON.stringify({
          type: "text_delta",
          sessionID: props.sessionID,
          messageID: props.messageID,
          partID: props.partID,
          delta: props.delta,
        }) + "\n",
      );
    },
  };
};
