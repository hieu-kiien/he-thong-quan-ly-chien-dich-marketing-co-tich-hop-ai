import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Sparkles,
  Send,
  RotateCcw,
  CheckCircle2,
  Copy,
  Check,
  Eye,
  EyeOff,
  Sliders,
  MessageSquare,
  FileEdit,
  Zap,
  ShieldCheck,
  ArrowRight,
  Trash2,
  Loader2,
  Info,
  Highlighter,
  Layers,
  Lock,
  Unlock,
  Plus,
  Bookmark,
  Brain,
  History,
  Download,
  Play,
  Undo2,
  Terminal,
  Trophy,
} from 'lucide-react';
import {
  aiApi,
  contentApi,
} from '../../services/api';
import {
  Campaign,
  BrandKit,
  AIChatMessage,
  AIChatCanvasSuggestion,
  ComplianceCheckResponse,
  CanvasBlockItem,
  AIChatThreadResponse,
  MuseBoardCardResponse,
  AgentStagedProposalResponse,
} from '../../types';
import { AntiAiCopyLinterCard } from '../AntiAiCopyLinterCard';
import { ComplianceAlertBadge } from '../ComplianceAlertBadge';

interface CanvasDraftState {
  title: string;
  body: string;
  cta: string;
  first_comment?: string;
  media_brief?: string;
}

interface ChatTurnItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  suggested_canvas?: AIChatCanvasSuggestion | null;
  staged_proposal?: AgentStagedProposalResponse | null;
  alternatives?: string[];
  context_used?: string[];
  prompt_preview?: string;
  compliance_score?: number | null;
  model_used?: string;
  is_fallback?: boolean;
}

interface InteractiveCanvasCopilotProps {
  activeCampaign?: Campaign;
  brandKit?: BrandKit | null;
  workspaceId?: number;
  selectedChannel: string;
  onChangeChannel: (ch: string) => void;
  preferredProvider: string;
  preferredModel: string;
  customBaseUrl?: string;
  expertMode?: boolean;
  initialDraft?: CanvasDraftState | null;
  customProduct: string;
  customUsp: string;
  onChangeCustomProduct: (v: string) => void;
  onChangeCustomUsp: (v: string) => void;
  onSavedSuccess?: () => void;
  onNavigateToReviews?: () => void;
}

const PLAYBOOK_PRESETS: {
  code: string;
  label: string;
  channel: string;
  description: string;
  defaultBlocks: CanvasBlockItem[];
}[] = [
  {
    code: 'FB_ADS_PACK',
    label: '📘 Gói Ads Tin nhắn Facebook (Có Comment đầu lách bóp reach)',
    channel: 'facebook',
    description: 'Bài chính + Comment đầu tiên chứa link/SĐT + Ghi chú làm ảnh/video.',
    defaultBlocks: [
      { id: 'b_hook', type: 'hook', label: '1. Câu mở đầu giữ chân (Hook 3s)', content: '', locked: false },
      { id: 'b_body', type: 'body', label: '2. Nội dung thuyết phục & Bằng chứng (Body)', content: '', locked: false },
      { id: 'b_cta', type: 'cta', label: '3. Kêu gọi nhắn tin (CTA)', content: '', locked: false },
      { id: 'b_fc', type: 'first_comment', label: '4. Bình luận đầu tiên (Gắn Link/SĐT tránh bóp tương tác FB)', content: '', locked: false },
      { id: 'b_mb', type: 'media_brief', label: '5. Ghi chú chụp ảnh / thiết kế Banner', content: '', locked: false },
    ],
  },
  {
    code: 'TIKTOK_REELS_35S',
    label: '🎬 Kịch bản TikTok / Reels 35s (Xuất phụ đề .SRT CapCut)',
    channel: 'tiktok',
    description: 'Chia sẵn phân cảnh 0-3s, 3-15s, 15-30s, 30-40s kèm nút tải file .SRT.',
    defaultBlocks: [
      { id: 'b_hook', type: 'hook', label: '1. Câu Hook 3 giây đầu (00:00 - 00:03)', content: '', locked: false },
      { id: 'b_body', type: 'body', label: '2. Phân cảnh chi tiết & Lời thoại (Voiceover)', content: '', locked: false },
      { id: 'b_cta', type: 'cta', label: '3. Kêu gọi bấm Giỏ hàng góc trái (CTA)', content: '', locked: false },
      { id: 'b_mb', type: 'media_brief', label: '4. Góc máy quay & Hiệu ứng âm thanh CapCut', content: '', locked: false },
    ],
  },
  {
    code: 'ZALO_CLOSING_5',
    label: '💬 Chuỗi Chốt đơn Inbox Zalo / Messenger 5 Bước',
    channel: 'zalo_oa',
    description: 'Chào hỏi <30s -> Báo giá neo -> Xử lý chê đắt/hỏi chồng -> Xin SĐT.',
    defaultBlocks: [
      { id: 'b_hook', type: 'hook', label: '1. Tin nhắn chào & Phân loại nhu cầu (<30 giây)', content: '', locked: false },
      { id: 'b_body', type: 'body', label: '2. Kịch bản Báo giá & Xử lý 3 lời từ chối', content: '', locked: false },
      { id: 'b_cta', type: 'cta', label: '3. Câu chốt xin SĐT + Địa chỉ lên đơn', content: '', locked: false },
      { id: 'b_fc', type: 'first_comment', label: '4. Tin nhắn nhắc lại sau 24h (Khi khách xem không trả lời)', content: '', locked: false },
    ],
  },
  {
    code: 'SHOPEE_SEO_PACK',
    label: '🛒 Gói Mô tả Chuẩn SEO Shopee / TikTok Shop',
    channel: 'landing_page',
    description: 'Tiêu đề chứa từ khóa tìm kiếm + Thông số kỹ thuật + Cam kết đổi trả.',
    defaultBlocks: [
      { id: 'b_hook', type: 'hook', label: '1. Tên sản phẩm chuẩn SEO Sàn TMĐT', content: '', locked: false },
      { id: 'b_body', type: 'body', label: '2. Công dụng, Thông số & Hướng dẫn sử dụng', content: '', locked: false },
      { id: 'b_cta', type: 'cta', label: '3. Chính sách Bảo hành & Đổi trả 7 ngày', content: '', locked: false },
    ],
  },
];

const QUICK_ACTIONS = [
  {
    code: 'POLISH_MANUAL',
    label: '✨ Chuốt mượt bài tự viết (Giữ ý gốc)',
    prompt: 'Hãy biên tập mượt lại câu chữ bài tôi đang viết trên bàn soạn thảo, giữ nguyên 100% ý tưởng, giọng điệu gốc và các khối tôi đã khóa.',
  },
  {
    code: 'HOOK_5',
    label: '🎯 Viết 5 câu mở đầu (Hook 3s)',
    prompt: 'Viết cho tôi 5 câu mở đầu (Hook 3 giây đầu) đa góc độ tâm lý bám sát sản phẩm và USP để tôi chọn lắp vào bài.',
  },
  {
    code: 'ANTI_CLICHE',
    label: '🧹 Khử sạch văn mẫu AI',
    prompt: 'Khử sạch các từ sáo rỗng kiểu AI (hàng đầu, toàn diện, giải pháp tối ưu...) và đổi sang tiếng Việt đời thường, sắc gọn.',
  },
  {
    code: 'SHORTEN_30',
    label: '✂️ Rút gọn 30% độ dài',
    prompt: 'Rút gọn khoảng 30% độ dài bài viết hiện tại, cắt bỏ từ thừa nhưng giữ nguyên thông tin cốt lõi và CTA.',
  },
  {
    code: 'ZALO_INBOX_SCRIPT',
    label: '💬 Kịch bản Chốt đơn Inbox Zalo/FB (5 bước)',
    prompt: 'Soạn kịch bản nhắn tin chốt đơn Inbox Messenger/Zalo 5 bước kèm 3 câu xử lý khi khách chê đắt hoặc bảo để hỏi ý kiến người nhà.',
  },
  {
    code: 'LIVESTREAM_SCRIPT',
    label: '🎥 Kịch bản Livestream Bán hàng 15p',
    prompt: 'Lên kịch bản phiên Livestream bán hàng 15 phút lặp vòng (Giữ mắt xem -> Demo USP -> Tung Deal -> Đếm ngược chốt giỏ hàng).',
  },
  {
    code: 'STAGE_LOG_METRICS',
    label: '📊 Báo cáo số liệu hôm nay (Bằng lời nói)',
    prompt: 'Báo cáo hôm nay: tiêu 500k, ra 25 tin nhắn, chốt 6 đơn thu về 2tr4',
  },
  {
    code: 'STAGE_CAMPAIGN_PLAN',
    label: '🚀 Lên Chiến dịch + Việc cần làm tự động',
    prompt: 'Hãy tạo chiến dịch mới ngân sách 5 triệu cùng gói bài viết nháp và danh sách việc cần làm cho sản phẩm này.',
  },
];

export const InteractiveCanvasCopilot: React.FC<InteractiveCanvasCopilotProps> = ({
  activeCampaign,
  brandKit,
  workspaceId,
  selectedChannel,
  onChangeChannel,
  preferredProvider,
  preferredModel,
  customBaseUrl,
  expertMode = false,
  initialDraft,
  customProduct,
  customUsp,
  onChangeCustomProduct,
  onChangeCustomUsp,
  onSavedSuccess,
  onNavigateToReviews,
}) => {
  // Chế độ hiển thị chính: 'workspace' (Bàn viết + Chat AI) | 'muse' (Bảng Tư Duy Muse AI & Bài Mẫu Ra Đơn)
  const [activeSubView, setActiveSubView] = useState<'workspace' | 'muse'>('workspace');
  const [selectedPlaybook, setSelectedPlaybook] = useState<string>('FB_ADS_PACK');

  const [canvas, setCanvas] = useState<CanvasDraftState>(() => ({
    title: initialDraft?.title || '',
    body: initialDraft?.body || '',
    cta: initialDraft?.cta || '',
    first_comment: initialDraft?.first_comment || '',
    media_brief: initialDraft?.media_brief || '',
  }));

  // Trạng thái khóa từng khối (Block Locking 🔒 — AI không bao giờ ghi đè khối đã khóa)
  const [lockedMap, setLockedMap] = useState<Record<string, boolean>>({
    hook: false,
    body: false,
    cta: false,
    first_comment: false,
    media_brief: false,
  });
  const [customBlocks, setCustomBlocks] = useState<CanvasBlockItem[]>([]);
  const [newBlockLabel, setNewBlockLabel] = useState<string>('');

  const [undoStack, setUndoStack] = useState<CanvasDraftState[]>([]);
  const [selectedText, setSelectedText] = useState<string>('');
  const bodyTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Context control flags
  const [includeCampaign, setIncludeCampaign] = useState<boolean>(true);
  const [includeProductUsp, setIncludeProductUsp] = useState<boolean>(true);
  const [includeBrandKit, setIncludeBrandKit] = useState<boolean>(true);
  const [includeCanvasDraft, setIncludeCanvasDraft] = useState<boolean>(true);
  const [includeMuseMemory, setIncludeMuseMemory] = useState<boolean>(true);
  const [includeWinningPosts, setIncludeWinningPosts] = useState<boolean>(true);
  const [showContextDrawer, setShowContextDrawer] = useState<boolean>(false);
  const [expandedPromptTurnId, setExpandedPromptTurnId] = useState<string | null>(null);

  // Persistent Chat Threads (Trò chuyện dài hạn lưu CSDL)
  const [threads, setThreads] = useState<AIChatThreadResponse[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [showThreadsList, setShowThreadsList] = useState<boolean>(false);

  // Muse AI Spatial Memory Board & Winning Posts + Custom /skills
  const [museCards, setMuseCards] = useState<MuseBoardCardResponse[]>([]);
  const [museFilter, setMuseFilter] = useState<string>('ALL');
  const [newCardType, setNewCardType] = useState<'WINNING_POST' | 'CUSTOM_SKILL' | 'NOTE'>('WINNING_POST');
  const [newCardTitle, setNewCardTitle] = useState<string>('');
  const [newCardContent, setNewCardContent] = useState<string>('');
  const [newCardTrigger, setNewCardTrigger] = useState<string>('');
  const [isCreatingCard, setIsCreatingCard] = useState<boolean>(false);

  // Multi-turn chat state
  const [chatInput, setChatInput] = useState<string>('');
  const [isSending, setIsSending] = useState<boolean>(false);
  const [turns, setTurns] = useState<ChatTurnItem[]>([]);
  const [copiedState, setCopiedState] = useState<boolean>(false);
  const [copiedFirstComment, setCopiedFirstComment] = useState<boolean>(false);
  const [executingProposalId, setExecutingProposalId] = useState<number | null>(null);

  // Save / Compliance state
  const [complianceResult, setComplianceResult] = useState<ComplianceCheckResponse | null>(null);
  const [isCheckingCompliance, setIsCheckingCompliance] = useState<boolean>(false);
  const [isSavingMode, setIsSavingMode] = useState<'DRAFT' | 'SOLO_APPROVE' | 'HITL_REVIEW' | null>(null);
  const [saveBanner, setSaveBanner] = useState<{ mode: string; message: string } | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Load persistent threads & Muse cards on mount
  const loadThreadsAndMuse = useCallback(async () => {
    try {
      const [thrList, mCards] = await Promise.all([
        aiApi.listThreads({ workspace_id: workspaceId }).catch(() => []),
        aiApi.listMuseCards({ workspace_id: workspaceId }).catch(() => []),
      ]);
      if (Array.isArray(thrList)) setThreads(thrList);
      if (Array.isArray(mCards)) setMuseCards(mCards);
    } catch {
      // Ignore offline errors
    }
  }, [workspaceId]);

  useEffect(() => {
    loadThreadsAndMuse();
  }, [loadThreadsAndMuse]);

  // Sync when parent pushes a draft into the canvas
  useEffect(() => {
    if (initialDraft && (initialDraft.title || initialDraft.body || initialDraft.cta)) {
      setCanvas((prev) => {
        if (prev.title || prev.body || prev.cta) {
          setUndoStack((stk) => [...stk.slice(-14), prev]);
        }
        return {
          title: initialDraft.title || '',
          body: initialDraft.body || '',
          cta: initialDraft.cta || '',
          first_comment: initialDraft.first_comment || prev.first_comment || '',
          media_brief: initialDraft.media_brief || prev.media_brief || '',
        };
      });
    }
  }, [initialDraft]);

  const buildCurrentBlocksPayload = (): CanvasBlockItem[] => {
    const core: CanvasBlockItem[] = [
      {
        id: 'b_hook',
        type: 'hook',
        label: 'Câu mở đầu (Hook 3s)',
        content: canvas.title,
        locked: Boolean(lockedMap.hook),
      },
      {
        id: 'b_body',
        type: 'body',
        label: 'Nội dung thân bài (Body)',
        content: canvas.body,
        locked: Boolean(lockedMap.body),
      },
      {
        id: 'b_cta',
        type: 'cta',
        label: 'Lời kêu gọi hành động (CTA)',
        content: canvas.cta,
        locked: Boolean(lockedMap.cta),
      },
      {
        id: 'b_fc',
        type: 'first_comment',
        label: 'Bình luận đầu tiên (Chứa Link/SĐT lách bóp tương tác)',
        content: canvas.first_comment || '',
        locked: Boolean(lockedMap.first_comment),
      },
      {
        id: 'b_mb',
        type: 'media_brief',
        label: 'Ghi chú sản xuất Ảnh / Video (Media Brief)',
        content: canvas.media_brief || '',
        locked: Boolean(lockedMap.media_brief),
      },
    ];
    return [...core, ...customBlocks];
  };

  const pushUndoAndSetCanvas = (next: CanvasDraftState) => {
    setUndoStack((prev) => [...prev.slice(-14), canvas]);
    setCanvas(next);
    setSaveBanner(null);
  };

  const handleUndo = () => {
    if (undoStack.length === 0) return;
    const previous = undoStack[undoStack.length - 1];
    setUndoStack((prev) => prev.slice(0, -1));
    setCanvas(previous);
  };

  const toggleLock = (key: string) => {
    setLockedMap((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleAddCustomBlock = () => {
    const lbl = newBlockLabel.trim() || `Khối bổ sung #${customBlocks.length + 1}`;
    setCustomBlocks((prev) => [
      ...prev,
      {
        id: `custom_${Date.now()}`,
        type: 'custom',
        label: lbl,
        content: '',
        locked: false,
      },
    ]);
    setNewBlockLabel('');
  };

  // Quản lý Phiên trò chuyện dài hạn (Persistent Chat Threads)
  const handleSelectThread = async (threadId: number) => {
    try {
      const detail: AIChatThreadResponse = await aiApi.getThreadDetail(threadId);
      setActiveThreadId(detail.id);
      setShowThreadsList(false);
      if (detail.messages && detail.messages.length > 0) {
        setTurns(
          detail.messages.map((m) => ({
            id: `db-${m.id}`,
            role: (m.role === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
            content: m.content,
            timestamp: new Date(m.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
            suggested_canvas: m.suggested_canvas,
            staged_proposal: m.staged_proposal,
            alternatives: m.alternatives || [],
            context_used: m.context_used || [],
            model_used: m.model_used || undefined,
            is_fallback: m.is_fallback,
          }))
        );
      } else {
        setTurns([]);
      }
    } catch {
      // ignore
    }
  };

  const handleStartNewThread = async () => {
    try {
      const created: AIChatThreadResponse = await aiApi.createThread({
        workspace_id: workspaceId,
        campaign_id: activeCampaign?.id ?? null,
        title: 'Cuộc trò chuyện mới',
        channel_code: selectedChannel,
      });
      setThreads((prev) => [created, ...prev]);
      setActiveThreadId(created.id);
      setTurns([]);
      setShowThreadsList(false);
    } catch {
      setActiveThreadId(null);
      setTurns([]);
    }
  };

  const handleDeleteThread = async (threadId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await aiApi.deleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.id !== threadId));
      if (activeThreadId === threadId) {
        setActiveThreadId(null);
        setTurns([]);
      }
    } catch {
      // ignore
    }
  };

  // Ghim nội dung bất kỳ lên Bảng Tư Duy Muse AI
  const handlePinToMuseBoard = async (
    title: string,
    content: string,
    cardType: 'WINNING_POST' | 'CUSTOM_SKILL' | 'NOTE' = 'NOTE'
  ) => {
    if (!content.trim()) return;
    try {
      const created = await aiApi.createMuseCard({
        workspace_id: workspaceId,
        campaign_id: activeCampaign?.id ?? null,
        card_type: cardType,
        title: title.trim() || 'Ý tưởng ghim từ Bàn viết',
        content: content.trim(),
        is_pinned: true,
      });
      setMuseCards((prev) => [created, ...prev]);
      setSaveBanner({
        mode: 'MUSE_PIN',
        message: `📌 Đã ghim "${created.title}" vào Bảng Tư Duy Muse AI (Bộ nhớ dài hạn của Shop)!`,
      });
    } catch {
      setSaveError('Không thể ghim thẻ vào Bảng Muse AI.');
    }
  };

  const handleCreateMuseCardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCardTitle.trim() || !newCardContent.trim() || isCreatingCard) return;
    setIsCreatingCard(true);
    try {
      const created = await aiApi.createMuseCard({
        workspace_id: workspaceId,
        campaign_id: activeCampaign?.id ?? null,
        card_type: newCardType,
        title: newCardTitle.trim(),
        content: newCardContent.trim(),
        skill_trigger: newCardType === 'CUSTOM_SKILL' ? (newCardTrigger.trim() || '/viet_nhanh') : null,
        is_pinned: true,
      });
      setMuseCards((prev) => [created, ...prev]);
      setNewCardTitle('');
      setNewCardContent('');
      setNewCardTrigger('');
    } catch {
      setSaveError('Không thể lưu thẻ mới vào Bảng Muse AI.');
    } finally {
      setIsCreatingCard(false);
    }
  };

  const handleDeleteMuseCard = async (cardId: number) => {
    try {
      await aiApi.deleteMuseCard(cardId);
      setMuseCards((prev) => prev.filter((c) => c.id !== cardId));
    } catch {
      // ignore
    }
  };

  const handleBodySelection = () => {
    const el = bodyTextareaRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    if (end > start) {
      const sel = el.value.substring(start, end).trim();
      setSelectedText(sel.length >= 4 ? sel : '');
    } else {
      setSelectedText('');
    }
  };

  const handleSendChat = async (overrideMsg?: string, quickAction?: string) => {
    const textToSend = (overrideMsg ?? chatInput).trim();
    if (!textToSend || isSending) return;

    const userTurn: ChatTurnItem = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    };

    const historyForApi: AIChatMessage[] = turns.slice(-10).map((t) => ({
      role: t.role,
      content: t.content,
    }));

    setTurns((prev) => [...prev, userTurn]);
    if (!overrideMsg) setChatInput('');
    setIsSending(true);
    setSaveError(null);

    try {
      // Tự động tạo Thread lưu trữ dài hạn nếu chưa có
      let targetThreadId = activeThreadId;
      if (!targetThreadId) {
        try {
          const newThr = await aiApi.createThread({
            workspace_id: workspaceId,
            campaign_id: activeCampaign?.id ?? null,
            title: textToSend.slice(0, 70),
            channel_code: selectedChannel,
          });
          if (newThr?.id) {
            targetThreadId = newThr.id;
            setActiveThreadId(newThr.id);
            setThreads((prev) => [newThr, ...prev]);
          }
        } catch {
          // Tiếp tục kể cả khi offline
        }
      }

      const res = await aiApi.chatCanvas({
        workspace_id: workspaceId,
        campaign_id: activeCampaign?.id ?? null,
        thread_id: targetThreadId,
        channel_code: selectedChannel,
        message: textToSend,
        quick_action: quickAction || null,
        history: historyForApi,
        canvas: {
          title: canvas.title,
          body: canvas.body,
          cta: canvas.cta,
          first_comment: canvas.first_comment || '',
          media_brief: canvas.media_brief || '',
          playbook_code: selectedPlaybook,
          blocks: buildCurrentBlocksPayload(),
          selected_text: selectedText || null,
        },
        context_flags: {
          include_campaign: includeCampaign,
          include_product_usp: includeProductUsp,
          include_brand_kit: includeBrandKit,
          include_canvas_draft: includeCanvasDraft,
          include_muse_memory: includeMuseMemory,
          include_winning_posts: includeWinningPosts,
          enable_project_control: true,
          custom_product_name: customProduct || undefined,
          custom_product_usp: customUsp || undefined,
        },
        preferred_provider: preferredProvider || undefined,
        preferred_model: preferredModel || undefined,
        custom_base_url: customBaseUrl || undefined,
      });

      const assistantTurn: ChatTurnItem = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: res.reply,
        timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        suggested_canvas: res.suggested_canvas,
        staged_proposal: res.staged_proposal,
        alternatives: res.alternatives || [],
        context_used: res.context_used || [],
        prompt_preview: res.prompt_preview,
        compliance_score: res.compliance_score,
        model_used: res.model_used,
        is_fallback: res.is_fallback,
      };
      setTurns((prev) => [...prev, assistantTurn]);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Không thể kết nối tới dịch vụ AI.';
      setTurns((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ Lỗi khi gọi AI: ${detail}. Bài viết thủ công của bạn ở cột bên trái vẫn được giữ nguyên an toàn.`,
          timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  // Thực thi hoặc Hoàn tác (Undo) Thẻ Kế Hoạch Agent
  const handleExecuteProposal = async (turnId: string, proposalId: number) => {
    setExecutingProposalId(proposalId);
    try {
      const updated = await aiApi.executeProposal(proposalId);
      setTurns((prev) =>
        prev.map((t) => (t.id === turnId ? { ...t, staged_proposal: updated } : t))
      );
      setSaveBanner({
        mode: 'AGENT_EXECUTED',
        message: `⚡ Đã thực thi thành công: "${updated.summary || updated.goal_summary}"! Bạn có thể bấm [Hoàn tác (Undo)] ngay trong thẻ chat nếu muốn quay lại.`,
      });
      if (onSavedSuccess) onSavedSuccess();
      loadThreadsAndMuse();
    } catch (err: any) {
      setSaveError(err?.response?.data?.detail || 'Không thể thực thi đề xuất của AI.');
    } finally {
      setExecutingProposalId(null);
    }
  };

  const handleUndoProposal = async (turnId: string, proposalId: number) => {
    setExecutingProposalId(proposalId);
    try {
      const rolledBack = await aiApi.undoProposal(proposalId);
      setTurns((prev) =>
        prev.map((t) => (t.id === turnId ? { ...t, staged_proposal: rolledBack } : t))
      );
      setSaveBanner({
        mode: 'AGENT_UNDO',
        message: '↩️ Đã hoàn tác (Undo) toàn bộ bản ghi vừa tạo về trạng thái ban đầu!',
      });
      if (onSavedSuccess) onSavedSuccess();
    } catch (err: any) {
      setSaveError(err?.response?.data?.detail || 'Không thể hoàn tác thao tác.');
    } finally {
      setExecutingProposalId(null);
    }
  };

  const handleApplySuggestion = (
    sug: AIChatCanvasSuggestion,
    mode: 'FULL' | 'TITLE_ONLY' | 'APPEND_BODY' | 'REPLACE_SELECTION'
  ) => {
    // Tôn trọng tuyệt đối các khối người dùng đã bấm Khóa (lockedMap)
    if (mode === 'FULL') {
      pushUndoAndSetCanvas({
        title: lockedMap.hook ? canvas.title : (sug.title || canvas.title),
        body: lockedMap.body ? canvas.body : (sug.body || canvas.body),
        cta: lockedMap.cta ? canvas.cta : (sug.cta || canvas.cta),
        first_comment: lockedMap.first_comment
          ? canvas.first_comment
          : (sug.first_comment ?? canvas.first_comment ?? ''),
        media_brief: lockedMap.media_brief
          ? canvas.media_brief
          : (sug.media_brief ?? canvas.media_brief ?? ''),
      });
    } else if (mode === 'TITLE_ONLY') {
      if (lockedMap.hook) return;
      pushUndoAndSetCanvas({
        ...canvas,
        title: sug.title || canvas.title,
      });
    } else if (mode === 'APPEND_BODY') {
      if (lockedMap.body) return;
      pushUndoAndSetCanvas({
        ...canvas,
        body: canvas.body ? `${canvas.body.trim()}\n\n${sug.body}` : sug.body,
      });
    } else if (mode === 'REPLACE_SELECTION' && selectedText && sug.replaced_selection) {
      pushUndoAndSetCanvas({
        ...canvas,
        body: canvas.body.replace(selectedText, sug.replaced_selection),
      });
      setSelectedText('');
    }
  };

  const handleCheckCompliance = async () => {
    if (!canvas.title.trim() && !canvas.body.trim()) return;
    setIsCheckingCompliance(true);
    try {
      const res = await contentApi.checkCompliance({
        workspace_id: workspaceId || activeCampaign?.workspace_id || 1,
        channel: selectedChannel,
        title: canvas.title,
        body: canvas.body,
        cta: canvas.cta,
      });
      setComplianceResult(res);
    } catch (err: any) {
      setSaveError(err?.response?.data?.detail || 'Không thể kiểm tra chính sách quảng cáo.');
    } finally {
      setIsCheckingCompliance(false);
    }
  };

  const handleSaveContent = async (mode: 'DRAFT' | 'SOLO_APPROVE' | 'HITL_REVIEW') => {
    if (!canvas.title.trim() && !canvas.body.trim()) {
      setSaveError('Bàn soạn thảo đang trống. Hãy tự gõ nội dung hoặc chọn một gợi ý từ AI trước khi lưu.');
      return;
    }

    setIsSavingMode(mode);
    setSaveError(null);
    setSaveBanner(null);

    try {
      const chMap: Record<string, number> = {
        facebook: 1,
        zalo_oa: 1,
        instagram: 1,
        email: 2,
        blog: 3,
        landing_page: 3,
        google_ads: 4,
        tiktok: 5,
      };
      const chId = chMap[selectedChannel] || 1;
      // Hỗ trợ Lưu Tự Do (Scratchpad): không bắt buộc phải chọn Chiến dịch trước!
      const created = await contentApi.create({
        campaign_id: activeCampaign?.id,
        workspace_id: workspaceId,
        channel_id: chId,
        title:
          canvas.title.trim() ||
          `Bài viết ${selectedChannel.toUpperCase()} — ${activeCampaign?.name || 'Kho Nháp Tự Do'}`,
        body: canvas.body.trim(),
        cta: canvas.cta.trim() || undefined,
        status: 'DRAFT',
        blocks_json: JSON.stringify(buildCurrentBlocksPayload()),
      });

      if (mode === 'SOLO_APPROVE') {
        await contentApi.submitForReview(created.id);
        await contentApi.approve(created.id);
        setSaveBanner({
          mode: 'SOLO_APPROVE',
          message:
            'Đã lưu Gói Nội Dung & Tự duyệt ngay (APPROVED)! Sẵn sàng lên lịch đăng không cần qua bước chờ duyệt trung gian.',
        });
      } else if (mode === 'HITL_REVIEW') {
        await contentApi.submitForReview(created.id);
        setSaveBanner({
          mode: 'HITL_REVIEW',
          message: 'Đã lưu & Đưa vào Hàng đợi kiểm duyệt (IN_REVIEW) dành cho Quản lý / Khách hàng!',
        });
      } else {
        setSaveBanner({
          mode: 'DRAFT',
          message: activeCampaign
            ? `Đã lưu Gói Nội Dung vào chiến dịch "${activeCampaign.name}" thành công!`
            : 'Đã lưu vào "Kho Nháp Tự Do (Scratchpad)" thành công (Không cần tạo Chiến dịch trước)!',
        });
      }

      if (onSavedSuccess) onSavedSuccess();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setSaveError(
        typeof detail === 'string'
          ? detail
          : detail?.message || 'Lỗi khi lưu bài viết.'
      );
    } finally {
      setIsSavingMode(null);
    }
  };

  // Smart Copy chuẩn định dạng Facebook / Zalo (giữ dòng trắng & icon)
  const handleCopyCanvas = () => {
    const customTexts = customBlocks
      .filter((b) => b.content.trim())
      .map((b) => `${b.label}:\n${b.content.trim()}`);
    const full = [
      canvas.title,
      canvas.body,
      ...customTexts,
      canvas.cta ? `👉 ${canvas.cta}` : '',
    ]
      .filter(Boolean)
      .join('\n\n');
    navigator.clipboard.writeText(full);
    setCopiedState(true);
    setTimeout(() => setCopiedState(false), 2000);
  };

  const handleCopyFirstComment = () => {
    if (!canvas.first_comment?.trim()) return;
    navigator.clipboard.writeText(canvas.first_comment.trim());
    setCopiedFirstComment(true);
    setTimeout(() => setCopiedFirstComment(false), 2000);
  };

  // Xuất file phụ đề .SRT chuẩn để kéo thẳng vào CapCut
  const handleDownloadSrtForCapCut = () => {
    const rawLines = (canvas.body || canvas.title || '')
      .split(/\n+/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0 && !l.startsWith('🎬') && !l.startsWith('🎥'));
    if (rawLines.length === 0) return;

    const formatTime = (sec: number) => {
      const hrs = Math.floor(sec / 3600);
      const mins = Math.floor((sec % 3600) / 60);
      const secs = Math.floor(sec % 60);
      return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')},000`;
    };

    let currentSec = 0;
    const srtBlocks = rawLines.map((line, idx) => {
      const duration = Math.max(3, Math.min(7, Math.ceil(line.split(/\s+/).length / 3.5)));
      const startStr = formatTime(currentSec);
      const endStr = formatTime(currentSec + duration);
      currentSec += duration;
      return `${idx + 1}\n${startStr} --> ${endStr}\n${line.replace(/^[•\-*]\s*/, '')}\n`;
    });

    const blob = new Blob([srtBlocks.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kich-ban-capcut-${Date.now()}.srt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const effectiveProduct =
    customProduct.trim() ||
    activeCampaign?.product?.name ||
    brandKit?.brand_name ||
    activeCampaign?.name ||
    'Chưa đặt tên sản phẩm';
  const effectiveUsp =
    customUsp.trim() ||
    activeCampaign?.product?.usp ||
    brandKit?.usp ||
    activeCampaign?.key_message ||
    activeCampaign?.objective ||
    'Chưa nhập USP';

  const customSkills = museCards.filter((c) => c.card_type === 'CUSTOM_SKILL');
  const filteredMuseCards = museCards.filter((c) =>
    museFilter === 'ALL' ? true : c.card_type === museFilter
  );

  return (
    <div className="space-y-4" data-testid="interactive-canvas-copilot">
      {/* Thanh Điều Hướng Cấp Cao: Bàn Soạn Thảo + Chat Dài Hạn <-> Bảng Tư Duy Muse AI & Kho Bài Mẫu Ra Đơn */}
      <div className="bg-white rounded-2xl border border-slate-200 p-3.5 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveSubView('workspace')}
            className={`px-3.5 py-2 rounded-xl text-xs font-extrabold flex items-center gap-2 transition-all cursor-pointer ${
              activeSubView === 'workspace'
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            <FileEdit className="w-3.5 h-3.5" />
            <span>Bàn Viết Linh Hoạt &amp; Trò Chuyện AI Dài Hạn</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSubView('muse')}
            data-testid="toggle-muse-board-btn"
            className={`px-3.5 py-2 rounded-xl text-xs font-extrabold flex items-center gap-2 transition-all cursor-pointer ${
              activeSubView === 'muse'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-indigo-50 text-indigo-800 hover:bg-indigo-100 border border-indigo-200'
            }`}
          >
            <Brain className="w-3.5 h-3.5" />
            <span>Bảng Tư Duy Muse AI &amp; Kho Bài Mẫu Ra Đơn ({museCards.length})</span>
          </button>
        </div>

        {/* Khuôn Mẫu Ngành Hàng Linh Hoạt (Playbook Selector) */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-bold text-slate-600">Khung bài viết (Playbook):</span>
          <select
            value={selectedPlaybook}
            onChange={(e) => {
              const code = e.target.value;
              setSelectedPlaybook(code);
              const found = PLAYBOOK_PRESETS.find((p) => p.code === code);
              if (found) onChangeChannel(found.channel);
            }}
            aria-label="Chọn khung bài viết linh hoạt"
            className="px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-xs font-bold text-slate-800 outline-none focus:border-indigo-500"
          >
            {PLAYBOOK_PRESETS.map((pb) => (
              <option key={pb.code} value={pb.code}>
                {pb.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* CHẾ ĐỘ 2: BẢNG TƯ DUY DÀI HẠN KIỂU MUSE AI & KHO BÀI MẪU RA ĐƠN (FEW-SHOT DNA + LỆNH /SKILL) */}
      {activeSubView === 'muse' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-5" data-testid="muse-ai-board-view">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
                <Brain className="w-4 h-4 text-indigo-600" />
                <span>Không Gian Tư Duy Muse AI — Kho Bài Mẫu Ra Đơn &amp; Lệnh Tắt Tùy Biến (/skill)</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Mọi bài mẫu thắng lớn (Winning Post), ý tưởng rời rạc và lệnh tắt <code>/skill</code> ghim tại đây sẽ trở thành <strong>trí nhớ dài hạn</strong> của AI khi trò chuyện với bạn.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-1.5">
              {[
                { code: 'ALL', label: `Tất cả (${museCards.length})` },
                { code: 'WINNING_POST', label: '🏆 Bài Mẫu Ra Đơn (Few-Shot DNA)' },
                { code: 'CUSTOM_SKILL', label: '⚡ Lệnh tắt /skill' },
                { code: 'NOTE', label: '💡 Ý tưởng & Insight' },
              ].map((tab) => (
                <button
                  key={tab.code}
                  type="button"
                  onClick={() => setMuseFilter(tab.code)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                    museFilter === tab.code
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Form Thêm Thẻ Mới Vào Bảng Muse AI */}
          <form onSubmit={handleCreateMuseCardSubmit} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
              <div className="md:col-span-3">
                <label className="text-[11px] font-bold text-slate-700 block mb-1">Loại thẻ ghi nhớ:</label>
                <select
                  value={newCardType}
                  onChange={(e) => setNewCardType(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-xs font-bold text-slate-800"
                >
                  <option value="WINNING_POST">🏆 Bài Mẫu Đã Ra Đơn (AI học văn phong)</option>
                  <option value="CUSTOM_SKILL">⚡ Lệnh tắt tùy biến (/lenh_rieng)</option>
                  <option value="NOTE">💡 Thẻ Ý tưởng / Insight khách hàng</option>
                </select>
              </div>

              <div className={newCardType === 'CUSTOM_SKILL' ? 'md:col-span-5' : 'md:col-span-9'}>
                <label className="text-[11px] font-bold text-slate-700 block mb-1">Tiêu đề thẻ:</label>
                <input
                  type="text"
                  value={newCardTitle}
                  onChange={(e) => setNewCardTitle(e.target.value)}
                  placeholder={
                    newCardType === 'WINNING_POST'
                      ? 'VD: Bài chạy Ads Kem Chống Nắng ra 120 đơn tuần trước'
                      : newCardType === 'CUSTOM_SKILL'
                      ? 'VD: Lệnh viết kịch bản Seeding 3 người tung hứng'
                      : 'VD: Khách hàng 25-35 tuổi rất sợ kem bết dính khi đội mũ bảo hiểm'
                  }
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-xs text-slate-900"
                />
              </div>

              {newCardType === 'CUSTOM_SKILL' && (
                <div className="md:col-span-4">
                  <label className="text-[11px] font-bold text-emerald-700 block mb-1">Gõ lệnh tắt để gọi trong Chat:</label>
                  <input
                    type="text"
                    value={newCardTrigger}
                    onChange={(e) => setNewCardTrigger(e.target.value)}
                    placeholder="VD: /seeding_3_nguoi"
                    className="w-full px-3 py-2 rounded-lg border border-emerald-300 bg-white font-mono text-xs font-bold text-emerald-900"
                  />
                </div>
              )}
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-700 block mb-1">
                {newCardType === 'WINNING_POST'
                  ? 'Dán nguyên văn bài viết đã chạy ra nhiều đơn (AI sẽ bắt chước cách ngắt dòng, xưng hô & nhịp câu):'
                  : newCardType === 'CUSTOM_SKILL'
                  ? 'Hướng dẫn chi tiết cho AI khi bạn gõ lệnh này:'
                  : 'Nội dung ghi chú / góc nhìn chiến lược:'}
              </label>
              <textarea
                rows={3}
                value={newCardContent}
                onChange={(e) => setNewCardContent(e.target.value)}
                placeholder="Nhập nội dung tại đây..."
                className="w-full p-3 rounded-lg border border-slate-200 bg-white text-xs text-slate-800"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isCreatingCard || !newCardTitle.trim() || !newCardContent.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Lưu vào Bảng Tư Duy Muse AI</span>
              </button>
            </div>
          </form>

          {/* Lưới Thẻ Tư Duy Không Gian (Spatial Cards Grid) */}
          {filteredMuseCards.length === 0 ? (
            <div className="p-8 rounded-2xl border border-dashed border-slate-200 text-center space-y-2">
              <Trophy className="w-8 h-8 text-amber-500 mx-auto" />
              <p className="text-xs font-bold text-slate-700">
                Bảng Tư Duy đang trống. Hãy dán 1-2 bài viết từng ra nhiều đơn nhất của Shop vào đây để AI học đúng giọng văn thực chiến của bạn!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredMuseCards.map((card) => (
                <div
                  key={card.id}
                  className="p-4 rounded-2xl border border-slate-200 bg-white hover:shadow-md transition-all flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-extrabold uppercase ${
                          card.card_type === 'WINNING_POST'
                            ? 'bg-amber-100 text-amber-900'
                            : card.card_type === 'CUSTOM_SKILL'
                            ? 'bg-emerald-100 text-emerald-900'
                            : 'bg-indigo-100 text-indigo-900'
                        }`}
                      >
                        {card.card_type === 'WINNING_POST'
                          ? '🏆 Bài Mẫu Ra Đơn'
                          : card.card_type === 'CUSTOM_SKILL'
                          ? `⚡ Lệnh ${card.skill_trigger || card.trigger_command || '/skill'}`
                          : '💡 Ghi Nhớ Muse'}
                      </span>

                      <button
                        type="button"
                        onClick={() => handleDeleteMuseCard(card.id)}
                        className="text-slate-400 hover:text-rose-600 cursor-pointer"
                        title="Xóa thẻ"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <h4 className="text-xs font-extrabold text-slate-900">{card.title}</h4>
                    <p className="text-[11px] text-slate-600 whitespace-pre-line line-clamp-5 leading-relaxed">
                      {card.content}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        pushUndoAndSetCanvas({
                          ...canvas,
                          title: card.title,
                          body: card.content,
                        });
                        setActiveSubView('workspace');
                      }}
                      className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-[11px] font-bold cursor-pointer"
                    >
                      Đưa sang Bàn viết
                    </button>

                    {(card.skill_trigger || card.trigger_command) && (
                      <button
                        type="button"
                        onClick={() => {
                          const trig = card.skill_trigger || card.trigger_command || '';
                          setActiveSubView('workspace');
                          handleSendChat(`${trig} áp dụng cho sản phẩm ${effectiveProduct}`);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold cursor-pointer"
                      >
                        Chạy lệnh {card.skill_trigger || card.trigger_command}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Thanh Kiểm Soát Ngữ Cảnh Minh Bạch (User Context Control Bar) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5 mr-1">
              <Sliders className="w-3.5 h-3.5 text-indigo-600" />
              <span>Dữ liệu nạp cho AI:</span>
            </span>

            <button
              type="button"
              onClick={() => setIncludeCampaign((v) => !v)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer flex items-center gap-1 ${
                includeCampaign
                  ? 'bg-indigo-50 text-indigo-800 border-indigo-200'
                  : 'bg-slate-50 text-slate-400 border-slate-200 line-through'
              }`}
            >
              <span>@Chiến dịch: {activeCampaign ? activeCampaign.name.slice(0, 22) : 'Kho Nháp Tự Do'}</span>
            </button>

            <button
              type="button"
              onClick={() => setIncludeProductUsp((v) => !v)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer flex items-center gap-1 ${
                includeProductUsp
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-slate-50 text-slate-400 border-slate-200 line-through'
              }`}
            >
              <span>@Sản phẩm &amp; USP: {effectiveProduct.slice(0, 20)}</span>
            </button>

            <button
              type="button"
              onClick={() => setIncludeWinningPosts((v) => !v)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer flex items-center gap-1 ${
                includeWinningPosts
                  ? 'bg-amber-50 text-amber-900 border-amber-200'
                  : 'bg-slate-50 text-slate-400 border-slate-200 line-through'
              }`}
              title="Cho phép AI học giọng văn từ các Bài Mẫu Ra Đơn trên Bảng Muse AI"
            >
              <span>@Bài Mẫu Ra Đơn ({museCards.filter((c) => c.card_type === 'WINNING_POST').length})</span>
            </button>

            <button
              type="button"
              onClick={() => setIncludeMuseMemory((v) => !v)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer flex items-center gap-1 ${
                includeMuseMemory
                  ? 'bg-sky-50 text-sky-900 border-sky-200'
                  : 'bg-slate-50 text-slate-400 border-slate-200 line-through'
              }`}
            >
              <span>@Trí nhớ Muse AI</span>
            </button>

            <button
              type="button"
              onClick={() => setIncludeBrandKit((v) => !v)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer flex items-center gap-1 ${
                includeBrandKit
                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                  : 'bg-slate-50 text-slate-400 border-slate-200 line-through'
              }`}
            >
              <span>@Khử Mùi AI</span>
            </button>

            <button
              type="button"
              onClick={() => setIncludeCanvasDraft((v) => !v)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer flex items-center gap-1 ${
                includeCanvasDraft
                  ? 'bg-purple-50 text-purple-800 border-purple-200'
                  : 'bg-slate-50 text-slate-400 border-slate-200 line-through'
              }`}
            >
              <span>@Bài đang viết ({canvas.body.length} ký tự)</span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => setShowContextDrawer((v) => !v)}
            className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-50/60 hover:bg-indigo-100/70 transition-colors cursor-pointer"
          >
            {showContextDrawer ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span>{showContextDrawer ? 'Ẩn chi tiết Sản phẩm/USP' : 'Sửa nhanh Sản phẩm & USP'}</span>
          </button>
        </div>

        {showContextDrawer && (
          <div className="pt-2 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Tên sản phẩm / Dịch vụ cụ thể (AI sẽ bám sát tên này, không tự bịa):
              </label>
              <input
                type="text"
                value={customProduct}
                onChange={(e) => onChangeCustomProduct(e.target.value)}
                placeholder={effectiveProduct}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:border-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Điểm bán hàng độc nhất (USP / Giá bán / Cam kết bảo hành thực tế):
              </label>
              <input
                type="text"
                value={customUsp}
                onChange={(e) => onChangeCustomUsp(e.target.value)}
                placeholder={effectiveUsp}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:border-indigo-500 outline-none"
              />
            </div>
          </div>
        )}
      </div>

      {/* Bố cục Split-Screen 2 cột: Trái = Bàn Soạn Thảo Đa Khối | Phải = Chat AI Dài Hạn + Điều Khiển Dự Án */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* CỘT TRÁI (7/12): BÀN SOẠN THẢO GÓI NỘI DUNG BÁN HÀNG (CREATIVE PACK CANVAS) */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
          {/* Header Bàn soạn thảo */}
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-slate-900 text-white flex items-center justify-center">
                <FileEdit className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xs font-extrabold text-slate-900">
                  Gói Nội Dung Bán Hàng Linh Hoạt (Creative Pack)
                </h3>
                <p className="text-[11px] text-slate-500">
                  Bấm biểu tượng <strong>🔒 Khóa</strong> ở khối nào đã ưng ý để cấm AI tự sửa khối đó.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-1.5">
              <select
                value={selectedChannel}
                onChange={(e) => onChangeChannel(e.target.value)}
                aria-label="Chọn kênh xuất bản"
                className="px-2.5 py-1.5 text-xs font-bold bg-white border border-slate-200 rounded-lg text-slate-800 outline-none focus:border-indigo-500"
              >
                <option value="facebook">📘 Facebook Ads / Fanpage</option>
                <option value="tiktok">🎵 TikTok / Reels Script</option>
                <option value="zalo_oa">💬 Zalo OA / Inbox Chốt đơn</option>
                <option value="instagram">📸 Instagram / Threads</option>
                <option value="email">✉️ Email / Bản tin</option>
                <option value="landing_page">🌐 Shopee / Landing Page</option>
              </select>

              <button
                type="button"
                onClick={handleUndo}
                disabled={undoStack.length === 0}
                title="Hoàn tác về phiên bản trước khi sửa"
                className="px-2.5 py-1.5 rounded-lg text-xs font-bold border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 text-slate-700 flex items-center gap-1 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Hoàn tác ({undoStack.length})</span>
              </button>

              <button
                type="button"
                onClick={handleCopyCanvas}
                className="px-2.5 py-1.5 rounded-lg text-xs font-bold border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-800 flex items-center gap-1 transition-colors cursor-pointer"
                title="Sao chép chuẩn định dạng Facebook / Zalo (giữ nguyên dòng trắng)"
              >
                {copiedState ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedState ? 'Đã chép chuẩn FB/Zalo' : 'Copy chuẩn FB/Zalo'}</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadSrtForCapCut}
                disabled={!canvas.body.trim() && !canvas.title.trim()}
                className="px-2.5 py-1.5 rounded-lg text-xs font-bold border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 text-slate-700 flex items-center gap-1 transition-colors cursor-pointer"
                title="Xuất file phụ đề .SRT chuẩn mốc thời gian để kéo vào CapCut"
              >
                <Download className="w-3.5 h-3.5 text-indigo-600" />
                <span>.SRT CapCut</span>
              </button>
            </div>
          </div>

          {/* Thân Bàn Soạn Thảo Đa Khối */}
          <div className="p-5 space-y-4">
            {/* KHỐI 1: Tiêu đề / Hook 3 giây + Nút Khóa */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-extrabold text-slate-700 uppercase tracking-wide flex items-center gap-1.5">
                  <span>1. Câu mở đầu giữ chân (Hook 3s / Tiêu đề)</span>
                  {lockedMap.hook && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px]">
                      🔒 Đã khóa bảo vệ
                    </span>
                  )}
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => toggleLock('hook')}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 cursor-pointer border ${
                      lockedMap.hook
                        ? 'bg-amber-50 text-amber-900 border-amber-300'
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {lockedMap.hook ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                    <span>{lockedMap.hook ? 'Đã khóa (AI cấm sửa)' : 'Khóa khối này'}</span>
                  </button>
                  <span className="text-[11px] text-slate-400">{canvas.title.length} ký tự</span>
                </div>
              </div>
              <input
                type="text"
                value={canvas.title}
                onChange={(e) => setCanvas({ ...canvas, title: e.target.value })}
                placeholder="Gõ câu mở đầu của bạn (hoặc bấm 'Viết 5 câu mở đầu' ở khung Chat bên phải)..."
                className="w-full px-3.5 py-2.5 text-sm font-bold text-slate-900 bg-slate-50/70 focus:bg-white rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15 outline-none transition-all"
              />
            </div>

            {/* KHỐI 2: Thân bài + Bôi đen sửa cục bộ + Nút Khóa */}
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                <label className="text-[11px] font-extrabold text-slate-700 uppercase tracking-wide flex items-center gap-1.5">
                  <span>2. Nội dung chính / Kịch bản chi tiết (Body Copy)</span>
                  {lockedMap.body && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px]">
                      🔒 Đã khóa bảo vệ
                    </span>
                  )}
                </label>
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <button
                    type="button"
                    onClick={() => toggleLock('body')}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 cursor-pointer border ${
                      lockedMap.body
                        ? 'bg-amber-50 text-amber-900 border-amber-300'
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {lockedMap.body ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                    <span>{lockedMap.body ? 'Đã khóa' : 'Khóa thân bài'}</span>
                  </button>
                  <span>
                    {canvas.body.trim() ? canvas.body.trim().split(/\s+/).length : 0} từ · {canvas.body.length} ký tự
                  </span>
                  {canvas.body && (
                    <button
                      type="button"
                      onClick={() => handlePinToMuseBoard(canvas.title || 'Bài mẫu từ Bàn viết', canvas.body, 'WINNING_POST')}
                      className="text-indigo-600 hover:underline font-bold flex items-center gap-0.5 cursor-pointer"
                      title="Lưu bài này vào Kho Bài Mẫu Ra Đơn trên Bảng Muse AI"
                    >
                      <Bookmark className="w-3 h-3" /> Lưu làm Bài Mẫu
                    </button>
                  )}
                  {canvas.body && (
                    <button
                      type="button"
                      onClick={() =>
                        pushUndoAndSetCanvas({ title: '', body: '', cta: '', first_comment: '', media_brief: '' })
                      }
                      className="text-rose-600 hover:underline font-semibold flex items-center gap-0.5 cursor-pointer"
                    >
                      <Trash2 className="w-3 h-3" /> Xóa trắng
                    </button>
                  )}
                </div>
              </div>

              {selectedText && (
                <div className="mb-2 p-2.5 rounded-xl bg-amber-50 border border-amber-200 flex flex-wrap items-center justify-between gap-2 text-xs text-amber-900">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Highlighter className="w-4 h-4 text-amber-600 shrink-0" />
                    <span className="truncate">
                      Đang bôi đen: <strong>&ldquo;{selectedText.slice(0, 75)}{selectedText.length > 75 ? '...' : ''}&rdquo;</strong>
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() =>
                        handleSendChat(
                          `Hãy viết lại đoạn tôi đang bôi đen ("${selectedText}") cho sắc bén, thuyết phục và tự nhiên hơn.`,
                          'REWRITE_SELECTION'
                        )
                      }
                      disabled={isSending}
                      className="px-2.5 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-[11px] cursor-pointer"
                    >
                      Bảo AI viết lại đoạn bôi đen
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedText('')}
                      className="px-2 py-1 rounded-lg bg-white border border-amber-200 text-slate-600 text-[11px] font-semibold cursor-pointer"
                    >
                      Bỏ chọn
                    </button>
                  </div>
                </div>
              )}

              <textarea
                ref={bodyTextareaRef}
                rows={10}
                value={canvas.body}
                onChange={(e) => setCanvas({ ...canvas, body: e.target.value })}
                onSelect={handleBodySelection}
                placeholder={
                  "Bạn có thể:\n" +
                  "• Tự gõ bài viết thủ công tại đây và bấm Lưu ngay (không bắt buộc phải tạo Chiến dịch trước).\n" +
                  "• Khóa (🔒) đoạn nào đã ưng ý để AI chỉ viết tiếp những phần còn thiếu.\n" +
                  "• Bôi đen bất kỳ câu nào chưa ưng để yêu cầu AI sửa đúng câu đó."
                }
                className="w-full p-4 text-xs text-slate-800 leading-relaxed bg-slate-50/60 focus:bg-white rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15 outline-none transition-all resize-y font-sans"
              />
            </div>

            {/* KHỐI 3: Lời kêu gọi hành động (CTA) */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-extrabold text-slate-700 uppercase tracking-wide">
                  3. Lời kêu gọi hành động (Call To Action)
                </label>
                <button
                  type="button"
                  onClick={() => toggleLock('cta')}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 cursor-pointer border ${
                    lockedMap.cta
                      ? 'bg-amber-50 text-amber-900 border-amber-300'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {lockedMap.cta ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                  <span>{lockedMap.cta ? 'Đã khóa' : 'Khóa CTA'}</span>
                </button>
              </div>
              <input
                type="text"
                value={canvas.cta}
                onChange={(e) => setCanvas({ ...canvas, cta: e.target.value })}
                placeholder="VD: Nhắn tin ngay nhận báo giá ưu đãi hôm nay / Chấm (.) để shop gửi bảng giá..."
                className="w-full px-3.5 py-2 text-xs font-bold text-indigo-900 bg-indigo-50/40 focus:bg-white rounded-xl border border-indigo-200 focus:border-indigo-500 outline-none transition-all"
              />
            </div>

            {/* KHỐI 4 & 5: Bình luận đầu tiên (Lách bóp tương tác FB) + Ghi chú làm Ảnh/Video */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between gap-1">
                  <label className="text-[11px] font-extrabold text-slate-800">
                    4. Comment đầu tiên (Link/SĐT lách bóp reach FB)
                  </label>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={handleCopyFirstComment}
                      disabled={!canvas.first_comment?.trim()}
                      className="px-2 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-bold text-indigo-700 hover:bg-indigo-50 disabled:opacity-40 cursor-pointer"
                    >
                      {copiedFirstComment ? 'Đã chép' : 'Copy Comment'}
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleLock('first_comment')}
                      className="p-1 rounded bg-white border border-slate-200 text-slate-600 cursor-pointer"
                      title="Khóa Comment đầu tiên"
                    >
                      {lockedMap.first_comment ? <Lock className="w-3 h-3 text-amber-600" /> : <Unlock className="w-3 h-3" />}
                    </button>
                  </div>
                </div>
                <textarea
                  rows={2}
                  value={canvas.first_comment || ''}
                  onChange={(e) => setCanvas({ ...canvas, first_comment: e.target.value })}
                  placeholder="Đặt link Shopee / Website / SĐT Zalo ở Comment đầu để bài chính không bị Facebook bóp tương tác..."
                  className="w-full p-2 text-xs bg-white rounded-lg border border-slate-200 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between gap-1">
                  <label className="text-[11px] font-extrabold text-slate-800">
                    5. Ghi chú làm Ảnh / Quay dựng Video
                  </label>
                  <button
                    type="button"
                    onClick={() => toggleLock('media_brief')}
                    className="p-1 rounded bg-white border border-slate-200 text-slate-600 cursor-pointer"
                    title="Khóa ghi chú hình ảnh"
                  >
                    {lockedMap.media_brief ? <Lock className="w-3 h-3 text-amber-600" /> : <Unlock className="w-3 h-3" />}
                  </button>
                </div>
                <textarea
                  rows={2}
                  value={canvas.media_brief || ''}
                  onChange={(e) => setCanvas({ ...canvas, media_brief: e.target.value })}
                  placeholder="Ghi chú góc quay, chữ chèn lên ảnh đầu tiên hoặc nhạc nền..."
                  className="w-full p-2 text-xs bg-white rounded-lg border border-slate-200 outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Các Khối Tùy Chỉnh Do Người Dùng Tự Thêm (+ Thêm khối) */}
            {customBlocks.map((blk, idx) => (
              <div key={blk.id} className="p-3 rounded-xl bg-indigo-50/30 border border-indigo-100 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-extrabold text-indigo-950">{blk.label}</span>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() =>
                        setCustomBlocks((prev) =>
                          prev.map((item, i) => (i === idx ? { ...item, locked: !item.locked } : item))
                        )
                      }
                      className="text-[10px] font-bold px-2 py-0.5 rounded bg-white border border-slate-200"
                    >
                      {blk.locked ? '🔒 Đã khóa' : '🔓 Mở khóa'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setCustomBlocks((prev) => prev.filter((_, i) => i !== idx))}
                      className="text-rose-500 hover:text-rose-700"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                <textarea
                  rows={2}
                  value={blk.content}
                  onChange={(e) =>
                    setCustomBlocks((prev) =>
                      prev.map((item, i) => (i === idx ? { ...item, content: e.target.value } : item))
                    )
                  }
                  placeholder={`Nhập nội dung cho "${blk.label}"...`}
                  className="w-full p-2 text-xs bg-white rounded-lg border border-slate-200 outline-none"
                />
              </div>
            ))}

            {/* Thanh [+ Thêm khối nội dung tùy chỉnh] */}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="text"
                value={newBlockLabel}
                onChange={(e) => setNewBlockLabel(e.target.value)}
                placeholder="Thêm khối tùy biến (VD: Kịch bản Seeding 3 người, Câu trả lời khi khách chê đắt...)"
                className="flex-1 px-3 py-1.5 text-xs rounded-xl border border-dashed border-slate-300 bg-slate-50/60 outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={handleAddCustomBlock}
                className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-xs font-bold text-slate-700 flex items-center gap-1 cursor-pointer shrink-0"
              >
                <Plus className="w-3.5 h-3.5 text-indigo-600" />
                <span>Thêm khối</span>
              </button>
            </div>

            {/* Bộ Soi Mùi AI & 5 Luật Viết Chữ trực tiếp trên bài đang gõ */}
            {(canvas.title.trim() || canvas.body.trim()) && (
              <AntiAiCopyLinterCard
                title={canvas.title}
                body={canvas.body}
                cta={canvas.cta}
                onApplyCleanCopy={(next) =>
                  pushUndoAndSetCanvas({
                    ...canvas,
                    title: next.title,
                    body: next.body,
                    cta: next.cta,
                  })
                }
              />
            )}

            {/* Kết quả Quét Chính sách Quảng cáo */}
            {complianceResult && (
              <ComplianceAlertBadge
                result={complianceResult}
                isLoading={isCheckingCompliance}
              />
            )}

            {saveError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-700">
                {saveError}
              </div>
            )}

            {saveBanner && (
              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800 flex flex-wrap items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{saveBanner.message}</span>
                </span>
                {onNavigateToReviews && (
                  <button
                    type="button"
                    onClick={onNavigateToReviews}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold cursor-pointer"
                  >
                    Mở Kho Bài Viết &amp; Lịch Đăng
                  </button>
                )}
              </div>
            )}

            {/* Thanh Hành Động Lưu Bài (Hỗ trợ cả Lưu Nháp Tự Do không cần Chiến dịch, 1-Click Solo & Đội nhóm HITL) */}
            <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={handleCheckCompliance}
                disabled={isCheckingCompliance || (!canvas.title.trim() && !canvas.body.trim())}
                className="px-3 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-bold text-slate-700 flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {isCheckingCompliance ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                )}
                <span>Quét chính sách Ads</span>
              </button>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleSaveContent('DRAFT')}
                  disabled={Boolean(isSavingMode)}
                  className="px-3.5 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 cursor-pointer disabled:opacity-50"
                  title="Lưu ngay cả khi chưa chọn Chiến dịch (tự động đưa vào Kho Nháp Tự Do)"
                >
                  {isSavingMode === 'DRAFT'
                    ? 'Đang lưu...'
                    : activeCampaign
                    ? 'Lưu Nháp (DRAFT)'
                    : 'Lưu Nháp Tự Do (Scratchpad)'}
                </button>

                <button
                  type="button"
                  onClick={() => handleSaveContent('SOLO_APPROVE')}
                  disabled={Boolean(isSavingMode)}
                  title="Dành cho Chủ shop / Solo Marketer: Lưu và chuyển thẳng sang trạng thái ĐÃ DUYỆT (APPROVED)"
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50"
                >
                  {isSavingMode === 'SOLO_APPROVE' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Zap className="w-3.5 h-3.5" />
                  )}
                  <span>Lưu &amp; Duyệt Ngay (Chủ Shop 1-Click)</span>
                </button>

                {expertMode && (
                  <button
                    type="button"
                    onClick={() => handleSaveContent('HITL_REVIEW')}
                    disabled={Boolean(isSavingMode)}
                    title="Dành cho đội nhóm / Agency: Đưa bài vào hàng đợi IN_REVIEW"
                    className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50"
                  >
                    {isSavingMode === 'HITL_REVIEW' ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    <span>Gửi Duyệt Đội Nhóm</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* CỘT PHẢI (5/12): TRỢ LÝ HỘI THOẠI DÀI HẠN & ĐIỀU KHIỂN DỰ ÁN (PERSISTENT COPILOT & PROJECT CONTROLLER) */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
          {/* Header Chat + Quản lý Lịch sử Phiên Trò Chuyện Dài Hạn */}
          <div className="p-4 bg-gradient-to-r from-indigo-950 via-slate-900 to-indigo-950 text-white space-y-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-indigo-300" />
                </div>
                <div>
                  <h3 className="text-xs font-extrabold flex items-center gap-1.5">
                    <span>Trợ Lý AI Đồng Hành &amp; Điều Khiển Dự Án</span>
                  </h3>
                  <p className="text-[11px] text-slate-300">
                    Lưu lịch sử trò chuyện lâu dài · Điều khiển chiến dịch &amp; số liệu có nút Hoàn tác
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setShowThreadsList((v) => !v)}
                  className="text-[11px] text-indigo-200 hover:text-white px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/15 flex items-center gap-1 cursor-pointer"
                  title="Xem danh sách các cuộc trò chuyện dài hạn đã lưu"
                >
                  <History className="w-3.5 h-3.5" />
                  <span>Lịch sử ({threads.length})</span>
                </button>
                <button
                  type="button"
                  onClick={handleStartNewThread}
                  className="text-[11px] text-white px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-bold flex items-center gap-1 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Phiên mới</span>
                </button>
              </div>
            </div>

            {/* Danh sách các phiên trò chuyện dài hạn */}
            {showThreadsList && (
              <div className="p-2.5 rounded-xl bg-slate-900/95 border border-slate-700 max-h-44 overflow-y-auto space-y-1">
                <div className="text-[10px] font-bold uppercase text-slate-400 px-1">
                  Các cuộc trò chuyện đã lưu của bạn:
                </div>
                {threads.length === 0 ? (
                  <div className="text-[11px] text-slate-400 px-1 py-2">
                    Chưa có cuộc trò chuyện nào được lưu. Khi bạn nhắn tin, hệ thống sẽ tự động lưu lại.
                  </div>
                ) : (
                  threads.map((thr) => (
                    <div
                      key={thr.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => handleSelectThread(thr.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          handleSelectThread(thr.id);
                        }
                      }}
                      className={`px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between gap-2 cursor-pointer ${
                        activeThreadId === thr.id
                          ? 'bg-indigo-600/40 text-white font-bold'
                          : 'hover:bg-white/10 text-slate-200'
                      }`}
                    >
                      <span className="truncate">{thr.title}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] text-slate-400">{thr.message_count} tin</span>
                        <button
                          type="button"
                          onClick={(e) => handleDeleteThread(thr.id, e)}
                          className="text-slate-400 hover:text-rose-400"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* 1-Click Quick Action Chips + Lệnh tắt /skill của Shop */}
          <div className="p-3 bg-slate-50 border-b border-slate-200 space-y-2">
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 block">
              Thao tác nhanh thực chiến &amp; Điều khiển dự án (1-Click):
            </span>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_ACTIONS.map((qa) => (
                <button
                  key={qa.code}
                  type="button"
                  disabled={isSending}
                  onClick={() => handleSendChat(qa.prompt, qa.code)}
                  className="px-2.5 py-1 rounded-lg bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 border border-slate-200 hover:border-indigo-200 text-[11px] font-semibold transition-all cursor-pointer disabled:opacity-50"
                >
                  {qa.label}
                </button>
              ))}
            </div>

            {customSkills.length > 0 && (
              <div className="pt-1 flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] font-extrabold text-emerald-700 flex items-center gap-1">
                  <Terminal className="w-3 h-3" /> Lệnh riêng của Shop:
                </span>
                {customSkills.map((sk) => {
                  const cmd = sk.skill_trigger || sk.trigger_command || '/skill';
                  return (
                    <button
                      key={sk.id}
                      type="button"
                      disabled={isSending}
                      onClick={() => handleSendChat(`${cmd} cho sản phẩm ${effectiveProduct}`)}
                      className="px-2 py-0.5 rounded-md bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-mono text-[11px] font-bold cursor-pointer"
                    >
                      {cmd}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Luồng Hội Thoại (Chat Thread) */}
          <div className="p-4 space-y-4 max-h-[560px] min-h-[380px] overflow-y-auto bg-slate-50/40">
            {turns.length === 0 ? (
              <div className="p-5 rounded-2xl bg-white border border-dashed border-slate-200 text-center space-y-2.5 my-6">
                <Sparkles className="w-7 h-7 text-indigo-500 mx-auto" />
                <h4 className="text-xs font-extrabold text-slate-800">
                  Trò chuyện lâu dài với AI &amp; Điều khiển dự án bằng lời nói
                </h4>
                <p className="text-xs text-slate-500 leading-relaxed">
                  • Nhắn chỉnh sửa bài: <em>&ldquo;Đổi giọng gần gũi hơn, giữ nguyên câu mở đầu đã khóa&rdquo;</em>.<br />
                  • Báo cáo số liệu bằng câu nói tự nhiên: <em>&ldquo;Hôm nay tiêu 500k, ra 25 tin nhắn, chốt 6 đơn thu về 2tr4&rdquo;</em>.<br />
                  • Gõ <code>/luu_lenh /seeding</code> để dạy AI quy trình riêng của bạn.
                </p>
              </div>
            ) : (
              turns.map((turn) => (
                <div
                  key={turn.id}
                  className={`flex flex-col ${turn.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[96%] rounded-2xl p-3.5 text-xs leading-relaxed space-y-3 ${
                      turn.role === 'user'
                        ? 'bg-indigo-600 text-white rounded-br-xs'
                        : 'bg-white border border-slate-200 text-slate-800 rounded-bl-xs shadow-2xs'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3 text-[10px] opacity-75">
                      <span className="font-bold">
                        {turn.role === 'user' ? 'Bạn' : `Trợ lý AI (${turn.model_used || preferredModel})`}
                      </span>
                      <div className="flex items-center gap-2">
                        {turn.role === 'assistant' && (
                          <button
                            type="button"
                            onClick={() => handlePinToMuseBoard('Ghi chú từ Trợ lý AI', turn.content, 'NOTE')}
                            className="text-indigo-600 hover:underline font-bold flex items-center gap-0.5 cursor-pointer"
                            title="Ghim câu trả lời này lên Bảng Tư Duy Muse AI"
                          >
                            <Bookmark className="w-3 h-3" /> Ghim vào Muse
                          </button>
                        )}
                        <span>{turn.timestamp}</span>
                      </div>
                    </div>

                    <div className="whitespace-pre-line">{turn.content}</div>

                    {/* THẺ KẾ HOẠCH THỰC THI DỰ ÁN (EXECUTION PLAN APPROVAL CARD + ATOMIC UNDO) */}
                    {turn.staged_proposal && (
                      <div
                        className="p-3.5 rounded-xl bg-amber-50/80 border-2 border-amber-300 space-y-2.5"
                        data-testid="agent-staged-proposal-card"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] font-black text-amber-950 flex items-center gap-1.5">
                            <Zap className="w-4 h-4 text-amber-600" />
                            <span>
                              Kế hoạch thao tác hệ thống: {turn.staged_proposal.summary || turn.staged_proposal.goal_summary}
                            </span>
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                              turn.staged_proposal.status === 'EXECUTED'
                                ? 'bg-emerald-100 text-emerald-800'
                                : turn.staged_proposal.status === 'ROLLED_BACK'
                                ? 'bg-slate-200 text-slate-700'
                                : 'bg-amber-200 text-amber-950'
                            }`}
                          >
                            {turn.staged_proposal.status === 'EXECUTED'
                              ? 'ĐÃ THỰC THI'
                              : turn.staged_proposal.status === 'ROLLED_BACK'
                              ? 'ĐÃ HOÀN TÁC'
                              : 'CHỜ BẠN DUYỆT'}
                          </span>
                        </div>

                        <div className="space-y-1.5">
                          {(turn.staged_proposal.actions || []).map((act) => (
                            <div
                              key={act.action_id}
                              className="p-2 rounded-lg bg-white border border-amber-200 text-[11px] space-y-0.5"
                            >
                              <div className="font-extrabold text-slate-900">{act.label}</div>
                              <div className="text-slate-600">{act.description || act.summary}</div>
                            </div>
                          ))}
                        </div>

                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          {turn.staged_proposal.status === 'PENDING' && (
                            <button
                              type="button"
                              disabled={executingProposalId === turn.staged_proposal.id}
                              onClick={() => handleExecuteProposal(turn.id, turn.staged_proposal!.id)}
                              className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold flex items-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-50"
                            >
                              {executingProposalId === turn.staged_proposal.id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Play className="w-3.5 h-3.5" />
                              )}
                              <span>Xác nhận &amp; Thực thi vào Hệ thống</span>
                            </button>
                          )}

                          {turn.staged_proposal.status === 'EXECUTED' && turn.staged_proposal.can_undo && (
                            <button
                              type="button"
                              disabled={executingProposalId === turn.staged_proposal.id}
                              onClick={() => handleUndoProposal(turn.id, turn.staged_proposal!.id)}
                              className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-extrabold flex items-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-50"
                            >
                              {executingProposalId === turn.staged_proposal.id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Undo2 className="w-3.5 h-3.5" />
                              )}
                              <span>Hoàn tác (Undo toàn bộ thao tác này)</span>
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Cảnh báo minh bạch nếu chưa cắm API Key */}
                    {turn.role === 'assistant' && turn.is_fallback && (
                      <div className="p-2 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-900 flex items-start gap-1.5">
                        <Info className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                        <span>
                          Đang xử lý bằng <strong>Bộ biên tập cục bộ trên dữ liệu thật của bạn</strong>. Bạn có thể chọn nhà cung cấp OpenCode Free hoặc cắm khóa API ở mục Cài đặt.
                        </span>
                      </div>
                    )}

                    {/* Các phương án lựa chọn nhanh (Alternatives: 5 Hooks / 3 mẫu câu) */}
                    {turn.alternatives && turn.alternatives.length > 0 && (
                      <div className="space-y-1.5 pt-1">
                        <span className="text-[10px] font-extrabold uppercase text-slate-500 block">
                          Các phương án gợi ý (Bấm để đưa sang bàn viết):
                        </span>
                        {turn.alternatives.map((alt, idx) => (
                          <div
                            key={idx}
                            className="p-2 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2"
                          >
                            <span className="text-[11px] text-slate-800 flex-1">{alt}</span>
                            <div className="flex items-center gap-1 shrink-0">
                              <button
                                type="button"
                                onClick={() =>
                                  pushUndoAndSetCanvas({
                                    ...canvas,
                                    title: alt.replace(/^\[[^\]]+\]\s*/, ''),
                                  })
                                }
                                className="px-2 py-1 rounded-md bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-200 text-[10px] font-bold cursor-pointer"
                              >
                                Dùng làm Hook
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  pushUndoAndSetCanvas({
                                    ...canvas,
                                    body: canvas.body ? `${canvas.body.trim()}\n\n${alt}` : alt,
                                  })
                                }
                                className="px-2 py-1 rounded-md bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-bold cursor-pointer"
                              >
                                + Chèn vào bài
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Thẻ Đề Xuất Chỉnh Sửa Gói Nội Dung (Suggested Canvas Diff Card) */}
                    {turn.suggested_canvas && (turn.suggested_canvas.title || turn.suggested_canvas.body) && (
                      <div className="p-3 rounded-xl bg-indigo-50/50 border border-indigo-200 space-y-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] font-extrabold text-indigo-950 flex items-center gap-1">
                            <Layers className="w-3.5 h-3.5 text-indigo-600" />
                            <span>Bản đề xuất: {turn.suggested_canvas.change_summary}</span>
                          </span>
                          {typeof turn.compliance_score === 'number' && (
                            <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                              An toàn Ads: {turn.compliance_score}/100
                            </span>
                          )}
                        </div>

                        <div className="p-2.5 rounded-lg bg-white border border-slate-200 space-y-1.5 max-h-48 overflow-y-auto">
                          {turn.suggested_canvas.title && (
                            <div className="text-xs font-extrabold text-slate-900">
                              {turn.suggested_canvas.title}
                            </div>
                          )}
                          <div className="text-[11px] text-slate-700 whitespace-pre-line">
                            {turn.suggested_canvas.body}
                          </div>
                          {turn.suggested_canvas.cta && (
                            <div className="text-[11px] font-bold text-indigo-700 pt-1">
                              👉 {turn.suggested_canvas.cta}
                            </div>
                          )}
                          {turn.suggested_canvas.first_comment && (
                            <div className="text-[10px] text-slate-600 pt-1 border-t border-slate-100">
                              💬 <strong>Comment đầu:</strong> {turn.suggested_canvas.first_comment}
                            </div>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleApplySuggestion(turn.suggested_canvas!, 'FULL')}
                            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] font-bold flex items-center gap-1 cursor-pointer shadow-2xs"
                          >
                            <ArrowRight className="w-3.5 h-3.5" />
                            <span>Áp dụng sang Bàn viết (Giữ nguyên khối đã khóa 🔒)</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => handleApplySuggestion(turn.suggested_canvas!, 'APPEND_BODY')}
                            className="px-2.5 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-[11px] font-semibold cursor-pointer"
                          >
                            + Nối thêm vào cuối bài
                          </button>

                          {turn.suggested_canvas.replaced_selection && selectedText && (
                            <button
                              type="button"
                              onClick={() => handleApplySuggestion(turn.suggested_canvas!, 'REPLACE_SELECTION')}
                              className="px-2.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-bold cursor-pointer"
                            >
                              Chỉ thay đúng đoạn bôi đen
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Minh bạch Ngữ cảnh & Xem Prompt thật gửi cho AI */}
                    {turn.role === 'assistant' && turn.context_used && turn.context_used.length > 0 && (
                      <div className="pt-2 border-t border-slate-100 space-y-1.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] text-slate-500">
                            Dữ liệu AI đã đọc: {turn.context_used.join(' · ')}
                          </span>
                          {expertMode && turn.prompt_preview && (
                            <button
                              type="button"
                              onClick={() =>
                                setExpandedPromptTurnId((id) => (id === turn.id ? null : turn.id))
                              }
                              className="text-[10px] font-bold text-indigo-600 hover:underline cursor-pointer shrink-0"
                            >
                              {expandedPromptTurnId === turn.id
                                ? 'Ẩn lệnh gốc'
                                : '🔍 Xem lệnh gốc gửi AI'}
                            </button>
                          )}
                        </div>
                        {expertMode && expandedPromptTurnId === turn.id && turn.prompt_preview && (
                          <pre className="p-2.5 rounded-lg bg-slate-900 text-slate-100 text-[10px] font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
                            {turn.prompt_preview}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Ô nhập lệnh hội thoại trực tiếp */}
          <div className="p-3 bg-white border-t border-slate-200">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChat();
              }}
              className="flex items-end gap-2"
            >
              <textarea
                rows={2}
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendChat();
                  }
                }}
                placeholder="Nhắn với AI (VD: 'Viết thêm ưu đãi Freeship', 'Báo cáo hôm nay: tiêu 500k, chốt 6 đơn thu 2tr4', hoặc gõ /lenh)..."
                className="flex-1 p-2.5 text-xs text-slate-800 bg-slate-50 focus:bg-white rounded-xl border border-slate-200 focus:border-indigo-500 outline-none resize-none"
              />
              <button
                type="submit"
                disabled={isSending || !chatInput.trim()}
                className="px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shrink-0"
              >
                {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                <span>Gửi</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
