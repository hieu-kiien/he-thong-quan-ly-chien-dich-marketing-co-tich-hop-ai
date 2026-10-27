// Plugin nội bộ của MarketFlow giúp phát từng mảnh văn bản (token delta) theo thời gian thực
// qua stdout JSONL trong khi OpenCode đang sinh câu trả lời, giảm TTFT từ ~30s xuống ~2-4s.
export const StreamDeltaPlugin = async () => ({
  event: async ({ event }) => {
    if (!event || event.type !== "message.part.delta") return;
    const props = event.properties;
    if (!props || props.field !== "text" || typeof props.delta !== "string" || !props.delta) {
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
});
