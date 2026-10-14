import React, { useState, useEffect } from 'react';
import {
  Bot,
  Cpu,
  Terminal,
  Database,
  Wrench,
  Sparkles,
  Play,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Code2,
  Layers,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Zap,
  FileCode2,
  ArrowRight,
} from 'lucide-react';
import { Campaign } from '../types';
import {
  mcpApi,
  MCPManifestResponse,
  MCPAgentRunResponse,
  MCPTraceStep,
  getApiErrorMessage,
} from '../services/api';
import { useToast } from './Toast';

interface MCPAgentStudioProps {
  campaigns: Campaign[];
  selectedCampaign: Campaign | null;
  onSelectCampaign: (c: Campaign | null) => void;
  onContentCreated?: () => void;
}

const PRESET_MISSIONS = [
  {
    id: 'full_audit_budget',
    label: '📊 Kiểm toán KPI & Tái phân bổ Ngân sách (ROAS)',
    goal: 'Kiểm toán toàn diện hiệu quả chiến dịch, chẩn đoán sức khỏe KPI và tự động tối ưu phân bổ lại ngân sách (budget rebalance) theo ROAS thực tế.',
    withDraft: false,
  },
  {
    id: 'compliance_autofix',
    label: '🛡️ Quét & Tự động Làm sạch Vi phạm Chính sách (100/100)',
    goal: 'Quét tuân thủ quảng cáo (compliance check) và tự động sửa lại các cụm từ vi phạm chính sách để đạt chuẩn an toàn thương hiệu 100/100.',
    withDraft: true,
  },
  {
    id: 'brandkit_draft',
    label: '✍️ Đọc Brand Kit & Tự động Tạo Bản nháp Chiến dịch',
    goal: 'Đọc Brand Kit của Workspace qua MCP Resource, kiểm tra chính sách và tự động khởi tạo lưu bản nháp bài viết mới vào chiến dịch.',
    withDraft: true,
  },
  {
    id: 'doctor_overview',
    label: '🩺 Tổng hợp Danh mục & Khám Sức khỏe Chiến dịch',
    goal: 'Liệt kê danh sách chiến dịch trong Workspace, trích xuất số liệu KPI và chạy Bác sĩ AI chẩn đoán điểm mạnh/điểm nghẽn.',
    withDraft: false,
  },
];

export const MCPAgentStudio: React.FC<MCPAgentStudioProps> = ({
  campaigns,
  selectedCampaign,
  onSelectCampaign,
  onContentCreated,
}) => {
  const toast = useToast();
  const activeCampaign = selectedCampaign || (campaigns.length > 0 ? campaigns[0] : null);

  // Manifest state
  const [manifest, setManifest] = useState<MCPManifestResponse | null>(null);
  const [loadingManifest, setLoadingManifest] = useState<boolean>(false);

  // Agentic Copilot state
  const [goal, setGoal] = useState<string>(PRESET_MISSIONS[0].goal);
  const [includeSampleDraft, setIncludeSampleDraft] = useState<boolean>(true);
  const [draftTitle, setDraftTitle] = useState<string>(
    'Cam kết 100% thành công ngay lập tức - Khóa học AI số 1 Việt Nam!',
  );
  const [draftBody, setDraftBody] = useState<string>(
    'Đăng ký ngay khóa học Kỹ sư AI thực chiến với cam kết 100% có việc làm lương nghìn đô, đảm bảo tuyệt đối hiệu quả tức thì vượt mặt mọi đối thủ!',
  );
  const [draftCta] = useState<string>('Đăng ký nhận ưu đãi miễn phí 100% ngay');
  const [channelCode, setChannelCode] = useState<string>('facebook');

  const [agentRunning, setAgentRunning] = useState<boolean>(false);
  const [agentResult, setAgentResult] = useState<MCPAgentRunResponse | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({ 1: true, 2: true });

  // MCP Inspector state
  const [inspectorTab, setInspectorTab] = useState<'tools' | 'resources' | 'prompts' | 'rpc'>('tools');
  const [rpcLoading, setRpcLoading] = useState<boolean>(false);
  const [rpcRequestPreview, setRpcRequestPreview] = useState<string>('');
  const [rpcResponsePreview, setRpcResponsePreview] = useState<string>('');

  // External Connectivity & Webhook Hub state
  const [connectorType, setConnectorType] = useState<string>('n8n_zapier');
  const [webhookEventType, setWebhookEventType] = useState<string>('content.published');
  const [webhookLoading, setWebhookLoading] = useState<boolean>(false);
  const [webhookResult, setWebhookResult] = useState<any>(null);
  const [mcpClientType, setMcpClientType] = useState<'claude_desktop' | 'cursor_ide' | 'curl_jsonrpc'>('claude_desktop');

  // Production Lab state: 4-Agent Squad, A/B & UTM Builder, AI Visual Banner
  const [labTab, setLabTab] = useState<'squad' | 'ab_utm' | 'visual'>('squad');
  const [squadLoading, setSquadLoading] = useState<boolean>(false);
  const [squadApplyDb, setSquadApplyDb] = useState<boolean>(true);
  const [squadResult, setSquadResult] = useState<any>(null);

  const [abLoading, setAbLoading] = useState<boolean>(false);
  const [abLandingUrl, setAbLandingUrl] = useState<string>('https://marketing.kienhieu.id.vn/landing');
  const [abTopic, setAbTopic] = useState<string>('');
  const [abSaveToDb, setAbSaveToDb] = useState<boolean>(true);
  const [abResult, setAbResult] = useState<any>(null);

  const [visualLoading, setVisualLoading] = useState<boolean>(false);
  const [visualRatio, setVisualRatio] = useState<'1:1' | '9:16' | '16:9'>('1:1');
  const [visualStyle, setVisualStyle] = useState<string>('Photorealistic Editorial Studio');
  const [visualHeadline, setVisualHeadline] = useState<string>('');
  const [visualResult, setVisualResult] = useState<any>(null);

  const handleRunSquadLab = async () => {
    setSquadLoading(true);
    try {
      const res = await mcpApi.runSquad({
        ...(activeCampaign?.id ? { campaign_id: activeCampaign.id } : {}),
        ...(activeCampaign?.workspace_id ? { workspace_id: activeCampaign.workspace_id } : {}),
        channel: channelCode,
        landing_url: abLandingUrl,
        aspect_ratio: visualRatio,
        apply_to_db: squadApplyDb,
      });
      setSquadResult(res);
      toast.success(
        `Biệt đội 4 AI Agents đã hoàn tất chiến dịch thực chiến (${res?.persistence?.saved_content_ids?.length || 0} bài nháp A/B & Banner đã lưu DB)!`,
      );
      if (onContentCreated) onContentCreated();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi điều phối Biệt đội 4 AI Agents');
    } finally {
      setSquadLoading(false);
    }
  };

  const handleRunAbUtmLab = async () => {
    setAbLoading(true);
    try {
      const res = await mcpApi.generateAbUtm({
        ...(activeCampaign?.id ? { campaign_id: activeCampaign.id } : {}),
        ...(activeCampaign?.workspace_id ? { workspace_id: activeCampaign.workspace_id } : {}),
        channel: channelCode,
        landing_url: abLandingUrl,
        ...(abTopic.trim() ? { topic: abTopic.trim() } : {}),
        save_to_db: abSaveToDb,
      });
      setAbResult(res);
      toast.success('Đã sinh 2 phiên bản A/B (PAS vs FAB) đạt chuẩn 100/100 kèm link UTM Tracking!');
      if (abSaveToDb && onContentCreated) onContentCreated();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi tạo A/B Variants & UTM');
    } finally {
      setAbLoading(false);
    }
  };

  const handleRunVisualLab = async () => {
    setVisualLoading(true);
    try {
      const res = await mcpApi.generateVisualBanner({
        ...(activeCampaign?.id ? { campaign_id: activeCampaign.id } : {}),
        ...(activeCampaign?.workspace_id ? { workspace_id: activeCampaign.workspace_id } : {}),
        channel: channelCode,
        aspect_ratio: visualRatio,
        visual_style: visualStyle,
        ...(visualHeadline.trim() ? { headline: visualHeadline.trim() } : {}),
        attach_to_latest_content: true,
      });
      setVisualResult(res);
      toast.success(`Đã kết xuất AI Visual Banner (${visualRatio}) và đính kèm vào bài viết chiến dịch!`);
      if (onContentCreated) onContentCreated();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi kết xuất AI Visual Banner');
    } finally {
      setVisualLoading(false);
    }
  };

  const handleTestExternalWebhook = async () => {
    setWebhookLoading(true);
    try {
      const res = await mcpApi.testWebhookDispatch({
        connector_type: connectorType,
        event_type: webhookEventType,
        ...(activeCampaign?.id ? { campaign_id: activeCampaign.id } : {}),
        ...(activeCampaign?.workspace_id ? { workspace_id: activeCampaign.workspace_id } : {}),
      });
      setWebhookResult(res);
      toast.success(`Đã ký số HMAC-SHA256 & bắn thử Outbound Webhook (${connectorType})!`);
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi bắn thử Outbound Webhook');
    } finally {
      setWebhookLoading(false);
    }
  };

  const getExternalClientSnippet = () => {
    const rpcUrl = `${window.location.origin}/api/v1/mcp/rpc`;
    const wsId = activeCampaign?.workspace_id || 1;
    if (mcpClientType === 'claude_desktop') {
      return JSON.stringify(
        {
          mcpServers: {
            'marketflow-ai': {
              url: rpcUrl,
              headers: {
                Authorization: 'Bearer <YOUR_MARKETFLOW_JWT_TOKEN>',
                'X-Workspace-Id': String(wsId),
              },
            },
          },
        },
        null,
        2,
      );
    }
    if (mcpClientType === 'cursor_ide') {
      return JSON.stringify(
        {
          mcpServers: {
            'marketflow-ai': {
              type: 'http',
              url: rpcUrl,
              headers: {
                Authorization: 'Bearer <YOUR_MARKETFLOW_JWT_TOKEN>',
              },
            },
          },
        },
        null,
        2,
      );
    }
    return `curl -X POST "${rpcUrl}" \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer <YOUR_MARKETFLOW_JWT_TOKEN>" \\\n  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'`;
  };

  const loadManifest = async () => {
    setLoadingManifest(true);
    try {
      const data = await mcpApi.getManifest();
      setManifest(data);
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không tải được MCP Manifest');
    } finally {
      setLoadingManifest(false);
    }
  };

  useEffect(() => {
    void loadManifest();
  }, []);

  const handleRunAgent = async () => {
    if (!goal.trim() || agentRunning) return;
    setAgentRunning(true);
    const payload = {
      goal: goal.trim(),
      ...(activeCampaign?.id ? { campaign_id: activeCampaign.id } : {}),
      channel: channelCode,
      ...(includeSampleDraft
        ? {
            draft_input: {
              title: draftTitle,
              body: draftBody,
              cta: draftCta,
            },
          }
        : {}),
    };

    try {
      const liveSteps: MCPTraceStep[] = [];

      const completedPayload = await mcpApi.streamAgent(payload, (step: MCPTraceStep) => {
        liveSteps.push(step);
        setExpandedSteps((prev) => ({ ...prev, [step.step]: true }));
        setAgentResult({
          server: 'marketflow-mcp-server (SSE Live)',
          protocol: 'MCP 2025-03-26 (SSE Stream)',
          goal: payload.goal,
          steps_executed: liveSteps.length,
          total_latency_ms: liveSteps.reduce((acc, s) => acc + (s.latency_ms || 0), 0),
          trace: [...liveSteps],
          artifacts: {},
          final_answer: 'Đang thực thi chuỗi công cụ MCP theo thời gian thực (Real-time SSE)...',
        });
      });

      setAgentResult(completedPayload);

      const openMap: Record<number, boolean> = {};
      completedPayload.trace.forEach((s: MCPTraceStep) => {
        openMap[s.step] = true;
      });
      setExpandedSteps(openMap);
      toast.success(
        `Agentic Copilot đã hoàn tất ${completedPayload.steps_executed} bước MCP trong ${completedPayload.total_latency_ms.toFixed(1)}ms!`,
      );
      if (onContentCreated) onContentCreated();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi chạy Agentic MCP Copilot');
    } finally {
      setAgentRunning(false);
    }
  };

  const handleTestResourceRead = async (uri: string) => {
    setInspectorTab('rpc');
    setRpcLoading(true);
    const reqObj = {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'resources/read',
      params: { uri },
    };
    setRpcRequestPreview(JSON.stringify(reqObj, null, 2));
    try {
      const res = await mcpApi.readResource(uri, activeCampaign?.workspace_id);
      setRpcResponsePreview(JSON.stringify(res, null, 2));
      toast.success(`Đã đọc MCP Resource: ${uri}`);
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Lỗi khi đọc MCP Resource');
    } finally {
      setRpcLoading(false);
    }
  };

  const handleTestToolCall = async (toolName: string) => {
    setInspectorTab('rpc');
    setRpcLoading(true);
    const defaultArgs: Record<string, Record<string, any>> = {
      list_workspace_campaigns: { workspace_id: activeCampaign?.workspace_id || 1 },
      get_campaign_metrics: { campaign_id: activeCampaign?.id || 1 },
      diagnose_campaign_health: { campaign_id: activeCampaign?.id || 1 },
      scan_content_compliance: {
        title: draftTitle,
        body: draftBody,
        cta: draftCta,
        channel: channelCode,
      },
      auto_fix_compliance_violations: {
        title: draftTitle,
        body: draftBody,
        cta: draftCta,
        channel: channelCode,
      },
      create_marketing_draft: {
        campaign_id: activeCampaign?.id || 1,
        channel: channelCode,
        topic: 'Bản nháp tạo từ MCP Tool Call chuẩn Brand Kit',
        save_to_db: false,
      },
      rebalance_campaign_budget: {
        campaign_id: activeCampaign?.id || 1,
        apply_changes: false,
      },
      dispatch_external_webhook: {
        connector_type: connectorType,
        event_type: webhookEventType,
        campaign_id: activeCampaign?.id || 1,
      },
      generate_utm_and_ab_variants: {
        campaign_id: activeCampaign?.id || 1,
        channel: channelCode,
        landing_url: abLandingUrl,
        save_to_db: false,
      },
      generate_visual_banner: {
        campaign_id: activeCampaign?.id || 1,
        channel: channelCode,
        aspect_ratio: visualRatio,
        visual_style: visualStyle,
        attach_to_latest_content: false,
      },
      run_multi_agent_squad: {
        campaign_id: activeCampaign?.id || 1,
        channel: channelCode,
        landing_url: abLandingUrl,
        aspect_ratio: visualRatio,
        apply_to_db: false,
      },
    };
    const args = defaultArgs[toolName] || {};
    const reqObj = {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: { name: toolName, arguments: args },
    };
    setRpcRequestPreview(JSON.stringify(reqObj, null, 2));
    try {
      const res = await mcpApi.callTool(toolName, args);
      setRpcResponsePreview(JSON.stringify(res, null, 2));
      toast.success(`Đã gọi MCP Tool: ${toolName}`);
    } catch (err) {
      toast.error(getApiErrorMessage(err), `Lỗi khi gọi MCP Tool ${toolName}`);
    } finally {
      setRpcLoading(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="mcp-agent-studio">
      {/* Top Architecture Overview Card */}
      <div className="bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white border border-indigo-500/30 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="bg-indigo-500/20 text-indigo-200 border border-indigo-400/30 text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-300" />
                Model Context Protocol • {manifest?.server?.protocolVersion || '2025-03-26'}
              </span>
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Multi-Tenant Workspace Isolated
              </span>
              <span className="bg-amber-500/20 text-amber-200 border border-amber-400/30 text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full">
                JSON-RPC 2.0 + Agentic Loop
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-black tracking-tight flex items-center gap-2">
              <Bot className="w-6 h-6 text-amber-400" />
              <span>MarketFlow MCP Server &amp; Agentic AI Copilot</span>
            </h2>
            <p className="text-xs text-indigo-200 max-w-3xl leading-relaxed">
              Chuẩn hóa toàn bộ năng lực tiếp thị (KPI Analytics, AI Performance Doctor, Brand Kit Memory, Compliance Guardrails &amp; ROAS Budget Optimizer) thành các <strong>MCP Tools &amp; Resources</strong> chuẩn JSON-RPC 2.0. Cho phép AI tự động lập kế hoạch và gọi chuỗi công cụ đa bước (Multi-Step Tool-Calling) có kiểm chứng.
            </p>
          </div>

          {/* Live Telemetry Counters */}
          <div className="grid grid-cols-3 gap-2.5 shrink-0">
            <div className="bg-slate-800/90 border border-slate-700 rounded-xl px-3.5 py-2.5 text-center">
              <span className="text-lg font-black text-amber-400 block">
                {manifest?.tools?.length ?? 7}
              </span>
              <span className="text-[11px] text-slate-300 font-semibold">MCP Tools</span>
            </div>
            <div className="bg-slate-800/90 border border-slate-700 rounded-xl px-3.5 py-2.5 text-center">
              <span className="text-lg font-black text-emerald-400 block">
                {manifest?.resources?.length ?? 3}
              </span>
              <span className="text-[11px] text-slate-300 font-semibold">MCP Resources</span>
            </div>
            <div className="bg-slate-800/90 border border-slate-700 rounded-xl px-3.5 py-2.5 text-center">
              <span className="text-lg font-black text-indigo-400 block">
                {manifest?.prompts?.length ?? 3}
              </span>
              <span className="text-[11px] text-slate-300 font-semibold">MCP Prompts</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main 2-Column Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN (7 cols): AGENTIC MULTI-STEP COPILOT */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  <span>Agentic Multi-Step Workflow Orchestrator</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Giao nhiệm vụ bằng ngôn ngữ tự nhiên — AI Agent sẽ tự động chọn và thực thi chuỗi MCP Resources &amp; Tools.
                </p>
              </div>

              {campaigns.length > 0 && (
                <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs shrink-0">
                  <span className="text-slate-600 font-medium">Chiến dịch:</span>
                  <select
                    value={activeCampaign?.id || ''}
                    onChange={(e) => {
                      const found = campaigns.find((c) => c.id === Number(e.target.value)) || null;
                      onSelectCampaign(found);
                    }}
                    aria-label="Chọn chiến dịch cho MCP Agent"
                    className="bg-transparent font-bold text-indigo-700 outline-none cursor-pointer"
                  >
                    {campaigns.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Preset Missions */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold uppercase text-slate-500 block">
                Kịch bản Agentic Mẫu (1-Click Demo):
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {PRESET_MISSIONS.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      setGoal(m.goal);
                      setIncludeSampleDraft(m.withDraft);
                    }}
                    className={`text-left text-xs p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-2 ${
                      goal === m.goal
                        ? 'bg-indigo-50/80 border-indigo-300 text-indigo-900 font-bold shadow-xs'
                        : 'bg-slate-50 hover:bg-slate-100 border-slate-200 text-slate-700 font-medium'
                    }`}
                  >
                    <span className="truncate">{m.label}</span>
                    <ArrowRight className="w-3.5 h-3.5 shrink-0 text-indigo-500" />
                  </button>
                ))}
              </div>
            </div>

            {/* Goal Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-800 block">
                Mục tiêu giao cho AI Agent (Agent Goal):
              </label>
              <textarea
                rows={2}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Nhập mục tiêu kiểm toán, chẩn đoán KPI, tối ưu ngân sách hoặc kiểm duyệt nội dung..."
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 leading-relaxed"
              />
            </div>

            {/* Optional Draft Payload for Compliance / Auto-Fix Tool Chain */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-3">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-xs font-bold text-slate-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeSampleDraft}
                    onChange={(e) => setIncludeSampleDraft(e.target.checked)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Đính kèm Bản nháp vào Context để Agent quét &amp; tự động sửa vi phạm (Compliance Auto-Fix)</span>
                </label>
                <span className="text-[11px] font-mono text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md">
                  Kênh: {channelCode.toUpperCase()}
                </span>
              </div>

              {includeSampleDraft && (
                <div className="space-y-2 pt-1">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div className="sm:col-span-2">
                      <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                        Tiêu đề nháp (chứa từ nhạy cảm để test MCP Guardrail):
                      </label>
                      <input
                        type="text"
                        value={draftTitle}
                        onChange={(e) => setDraftTitle(e.target.value)}
                        className="w-full text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                        Kênh phân phối:
                      </label>
                      <select
                        value={channelCode}
                        onChange={(e) => setChannelCode(e.target.value)}
                        className="w-full text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 font-semibold"
                      >
                        <option value="facebook">Facebook Ads</option>
                        <option value="tiktok">TikTok Script</option>
                        <option value="email">Email Marketing</option>
                        <option value="google_ads">Google Ads</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                      Nội dung thân bài:
                    </label>
                    <textarea
                      rows={2}
                      value={draftBody}
                      onChange={(e) => setDraftBody(e.target.value)}
                      className="w-full text-xs bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Run Agent Button */}
            <button
              type="button"
              data-testid="mcp-run-agent-btn"
              onClick={handleRunAgent}
              disabled={agentRunning}
              className="w-full py-3 px-5 bg-gradient-to-r from-indigo-600 via-violet-600 to-indigo-600 hover:from-indigo-700 hover:to-violet-700 text-white font-bold text-xs rounded-xl shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2 transition-all cursor-pointer active:scale-99"
            >
              {agentRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Đang điều phối chuỗi MCP Tools &amp; Resources...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Thực thi Chuỗi Tác vụ Agentic MCP (Multi-Step Tool Call)</span>
                </>
              )}
            </button>
          </div>

          {/* Agent Execution Trace Result */}
          {agentResult && (
            <div
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4"
              data-testid="mcp-agent-trace"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <h4 className="text-sm font-black text-slate-900">
                    Nhật ký Thực thi Chuỗi Công cụ MCP ({agentResult.steps_executed} bước)
                  </h4>
                </div>
                <div className="flex items-center gap-2 text-[11px] font-mono">
                  <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {agentResult.total_latency_ms.toFixed(1)} ms
                  </span>
                  <span className="bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full">
                    {agentResult.protocol}
                  </span>
                </div>
              </div>

              {/* Executive Summary */}
              <div className="bg-indigo-50/70 border border-indigo-200 rounded-xl p-3.5 text-xs text-slate-800 space-y-1">
                <span className="font-bold text-indigo-900 uppercase text-[11px] block">
                  Báo cáo Tổng hợp từ Agentic Orchestrator:
                </span>
                <p className="leading-relaxed whitespace-pre-line">{agentResult.final_answer}</p>
              </div>

              {/* Step-by-Step Timeline */}
              <div className="space-y-2.5">
                {agentResult.trace.map((st: MCPTraceStep) => {
                  const isExpanded = Boolean(expandedSteps[st.step]);
                  return (
                    <div
                      key={st.step}
                      className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50/60"
                    >
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedSteps((prev) => ({ ...prev, [st.step]: !prev[st.step] }))
                        }
                        className="w-full px-4 py-3 flex items-center justify-between gap-3 text-left hover:bg-slate-100/80 transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold flex items-center justify-center shrink-0">
                            {st.step}
                          </span>
                          <span
                            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border shrink-0 ${
                              st.kind === 'RESOURCE_READ'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : 'bg-amber-50 text-amber-800 border-amber-200'
                            }`}
                          >
                            {st.kind}
                          </span>
                          <span className="text-xs font-mono font-bold text-indigo-700 truncate">
                            {st.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[11px] font-mono text-slate-500">
                            {st.latency_ms.toFixed(1)} ms
                          </span>
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          )}
                        </div>
                      </button>

                      <div className="px-4 pb-2.5 text-xs text-slate-600">{st.summary}</div>

                      {isExpanded && (
                        <div className="px-4 pb-3 pt-1 border-t border-slate-200/70 bg-slate-900 text-slate-100 font-mono text-[11px] space-y-2 overflow-x-auto">
                          <div>
                            <span className="text-amber-300 font-bold">// INPUT PARAMS:</span>
                            <pre className="mt-0.5 text-slate-300 whitespace-pre-wrap">
                              {JSON.stringify(st.input, null, 2)}
                            </pre>
                          </div>
                          {st.output !== undefined && (
                            <div>
                              <span className="text-emerald-300 font-bold">// MCP OUTPUT PAYLOAD:</span>
                              <pre className="mt-0.5 text-emerald-100 whitespace-pre-wrap max-h-60 overflow-y-auto">
                                {JSON.stringify(st.output, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* PRODUCTION AI LAB: 4-AGENT SQUAD + A/B UTM BUILDER + AI VISUAL BANNER */}
          <div
            className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4"
            data-testid="mcp-production-lab"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
                  <Bot className="w-4 h-4 text-violet-600" />
                  <span>Phòng Thí Nghiệm Thực Chiến: 4-Agent Squad • A/B &amp; UTM • AI Visual Banner</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Biến kế hoạch AI thành tài sản quảng cáo thực tế (A/B Copy, UTM Tracking, Visual Banner 1:1/9:16/16:9) lưu trực tiếp vào SQLite Database.
                </p>
              </div>
              <span className="text-[10px] font-mono font-bold bg-violet-50 text-violet-700 border border-violet-200 px-2.5 py-1 rounded-full shrink-0">
                Real DB Persistence
              </span>
            </div>

            {/* Lab Sub-Tabs */}
            <div className="grid grid-cols-3 gap-1.5 bg-slate-100 p-1 rounded-xl text-xs font-bold">
              <button
                type="button"
                data-testid="lab-tab-squad"
                onClick={() => setLabTab('squad')}
                className={`py-2 px-2 rounded-lg transition-all cursor-pointer ${
                  labTab === 'squad'
                    ? 'bg-white text-violet-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                🤖 Biệt Đội 4 AI Agents
              </button>
              <button
                type="button"
                data-testid="lab-tab-ab-utm"
                onClick={() => setLabTab('ab_utm')}
                className={`py-2 px-2 rounded-lg transition-all cursor-pointer ${
                  labTab === 'ab_utm'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                🔗 A/B Testing &amp; UTM Builder
              </button>
              <button
                type="button"
                data-testid="lab-tab-visual"
                onClick={() => setLabTab('visual')}
                className={`py-2 px-2 rounded-lg transition-all cursor-pointer ${
                  labTab === 'visual'
                    ? 'bg-white text-emerald-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                🎨 AI Visual Banner (1:1 • 9:16 • 16:9)
              </button>
            </div>

            {/* SUB-TAB 1: 4-AGENT AUTONOMOUS SQUAD */}
            {labTab === 'squad' && (
              <div className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="font-black text-indigo-700 block">1. Market Researcher &amp; ICP</span>
                    <span className="text-[11px] text-slate-600">Đọc Brand Kit + Giải mã Insight &amp; Value Proposition</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="font-black text-emerald-700 block">2. Media Buyer &amp; ROAS Strategist</span>
                    <span className="text-[11px] text-slate-600">Kiểm toán CPA/ROAS &amp; Tái phân bổ Ngân sách tự động</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="font-black text-amber-700 block">3. A/B Copywriter &amp; UTM Architect</span>
                    <span className="text-[11px] text-slate-600">Sinh 2 bản A/B (PAS vs FAB) + gắn tham số UTM đầy đủ</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="font-black text-violet-700 block">4. Compliance Critic &amp; Art Director</span>
                    <span className="text-[11px] text-slate-600">Đảm bảo chuẩn 100/100 + Kết xuất AI Visual Banner</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 bg-violet-50/60 border border-violet-200 rounded-xl p-3">
                  <label className="flex items-center gap-2 text-xs font-bold text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={squadApplyDb}
                      onChange={(e) => setSquadApplyDb(e.target.checked)}
                      className="rounded border-slate-300 text-violet-600"
                    />
                    <span>Lưu trực tiếp Ngân sách mới, 2 Bài nháp A/B &amp; Ảnh Banner vào SQLite Database</span>
                  </label>
                  <button
                    type="button"
                    data-testid="run-squad-btn"
                    onClick={handleRunSquadLab}
                    disabled={squadLoading}
                    className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-bold shadow-sm transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    {squadLoading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Đang điều phối 4 AI Agents...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>Kích hoạt Biệt Đội 4 AI Agents</span>
                      </>
                    )}
                  </button>
                </div>

                {squadResult && (
                  <div className="space-y-3 border border-violet-200 bg-violet-50/30 rounded-xl p-3.5" data-testid="squad-result-panel">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-black text-violet-950">
                        ✅ {squadResult.squad_name} • Đã lưu {squadResult.persistence?.saved_content_ids?.length || 0} bản nháp vào Chiến dịch #{squadResult.campaign_id}
                      </span>
                      <span className="text-[11px] font-mono bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                        Compliance: 100/100 PASSED
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {(squadResult.agents || []).map((ag: any) => (
                        <div key={ag.agent_id} className="bg-white border border-slate-200 rounded-xl p-2.5 text-xs space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900">{ag.role}</span>
                            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                              {ag.latency_ms}ms
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-600 leading-relaxed">{ag.deliverable_summary}</p>
                        </div>
                      ))}
                    </div>

                    {squadResult.visual_asset?.image_url && (
                      <div className="bg-white border border-slate-200 rounded-xl p-3 flex flex-col sm:flex-row items-center gap-3">
                        <img
                          src={squadResult.visual_asset.image_url}
                          alt="Squad Generated Banner"
                          className="w-28 h-28 object-cover rounded-lg border border-slate-200 shrink-0"
                        />
                        <div className="space-y-1 text-xs min-w-0">
                          <div className="font-bold text-slate-900">
                            🎨 Banner AI ({squadResult.visual_asset.aspect_ratio} • {squadResult.visual_asset.dimensions}): {squadResult.visual_asset.typography_overlay?.headline}
                          </div>
                          <div className="text-[11px] text-slate-600 line-clamp-2">
                            Prompt: {squadResult.visual_asset.visual_prompt_en}
                          </div>
                          <div className="text-[11px] font-mono text-indigo-700 truncate">
                            UTM: {squadResult.ab_utm_package?.variants?.[0]?.utm?.full_tracking_url}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* SUB-TAB 2: A/B TESTING & UTM BUILDER */}
            {labTab === 'ab_utm' && (
              <div className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">
                      Landing Page đích (tự động gắn UTM Tracking):
                    </label>
                    <input
                      type="text"
                      value={abLandingUrl}
                      onChange={(e) => setAbLandingUrl(e.target.value)}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">
                      Chủ đề / Offer trọng tâm (tùy chọn):
                    </label>
                    <input
                      type="text"
                      value={abTopic}
                      onChange={(e) => setAbTopic(e.target.value)}
                      placeholder="VD: Ưu đãi 30% khóa học AI Marketing thực chiến..."
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 bg-indigo-50/60 border border-indigo-200 rounded-xl p-3">
                  <label className="flex items-center gap-2 text-xs font-bold text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={abSaveToDb}
                      onChange={(e) => setAbSaveToDb(e.target.checked)}
                      className="rounded border-slate-300 text-indigo-600"
                    />
                    <span>Lưu cả 2 phiên bản A/B vào kho nội dung chiến dịch (SQLite)</span>
                  </label>
                  <button
                    type="button"
                    data-testid="run-ab-utm-btn"
                    onClick={handleRunAbUtmLab}
                    disabled={abLoading}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-sm transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    {abLoading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Đang tạo A/B &amp; UTM...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Sinh 2 Bản A/B (PAS vs FAB) + Link UTM</span>
                      </>
                    )}
                  </button>
                </div>

                {abResult && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" data-testid="ab-utm-result-panel">
                    {(abResult.variants || []).map((v: any) => (
                      <div key={v.variant_id} className="border border-slate-200 rounded-xl p-3 bg-slate-50/70 space-y-2 text-xs">
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-black text-indigo-900">
                            Variant {v.variant_id}: {v.framework}
                          </span>
                          <span className="text-[10px] font-mono bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                            {v.compliance_score}/100 • Est CTR {v.estimated_ctr_pct}%
                          </span>
                        </div>
                        <div className="font-bold text-slate-900">{v.title}</div>
                        <p className="text-[11px] text-slate-600 whitespace-pre-line line-clamp-4">{v.body}</p>
                        <div className="bg-slate-900 text-emerald-300 font-mono text-[10px] p-2 rounded-lg break-all">
                          {v.utm?.full_tracking_url}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* SUB-TAB 3: AI VISUAL BANNER STUDIO */}
            {labTab === 'visual' && (
              <div className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">
                      Tỷ lệ khung hình (Aspect Ratio):
                    </label>
                    <select
                      value={visualRatio}
                      onChange={(e) => setVisualRatio(e.target.value as '1:1' | '9:16' | '16:9')}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-bold text-slate-800"
                    >
                      <option value="1:1">1:1 Square Feed (1080x1080)</option>
                      <option value="9:16">9:16 TikTok/Reels Story (1080x1920)</option>
                      <option value="16:9">16:9 YouTube/Web Hero (1920x1080)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">
                      Phong cách Nghệ thuật (Art Direction):
                    </label>
                    <select
                      value={visualStyle}
                      onChange={(e) => setVisualStyle(e.target.value)}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-semibold text-slate-800"
                    >
                      <option value="Photorealistic Editorial Studio">Photorealistic Editorial Studio</option>
                      <option value="Minimalist Luxury Product">Minimalist Luxury Product</option>
                      <option value="Neon Tech Futuristic">Neon Tech Futuristic</option>
                      <option value="High-Contrast Bold Typography">High-Contrast Bold Typography</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">
                      Tiêu đề phủ trên Banner (Headline Overlay):
                    </label>
                    <input
                      type="text"
                      value={visualHeadline}
                      onChange={(e) => setVisualHeadline(e.target.value)}
                      placeholder={activeCampaign?.name || 'Nhập tiêu đề chiến dịch...'}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  data-testid="run-visual-banner-btn"
                  onClick={handleRunVisualLab}
                  disabled={visualLoading}
                  className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition-all cursor-pointer flex items-center justify-center gap-2"
                >
                  {visualLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Đang kết xuất AI Visual Banner ({visualRatio})...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>🎨 Kết xuất AI Visual Banner ({visualRatio}) &amp; Đính kèm vào Bài viết Chiến dịch</span>
                    </>
                  )}
                </button>

                {visualResult && (
                  <div className="border border-emerald-200 bg-emerald-50/40 rounded-xl p-3.5 flex flex-col sm:flex-row gap-4 items-center" data-testid="visual-banner-result-panel">
                    <img
                      src={visualResult.image_url}
                      alt={visualResult.typography_overlay?.headline || 'AI Visual Banner'}
                      className="w-36 h-36 object-cover rounded-xl border border-emerald-300 shadow-sm shrink-0"
                    />
                    <div className="space-y-1.5 text-xs min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-black text-emerald-950">
                          {visualResult.typography_overlay?.headline}
                        </span>
                        <span className="text-[10px] font-mono bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                          {visualResult.aspect_ratio} ({visualResult.dimensions})
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 leading-relaxed">
                        <strong>AI Visual Prompt:</strong> {visualResult.visual_prompt_en}
                      </p>
                      <div className="text-[11px] text-emerald-800 font-semibold">
                        ✅ Đã đồng bộ ảnh vào Bài viết #{visualResult.attached_content_id || 'Mới nhất'} trong SQLite Database.
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN (5 cols): MCP PROTOCOL INSPECTOR & LIVE JSON-RPC PLAYGROUND */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-emerald-600" />
                  <span>MCP Registry &amp; JSON-RPC 2.0 Inspector</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Kiểm thử trực tiếp từng MCP Tool, Resource và xem khung truyền tải JSON-RPC 2.0.
                </p>
              </div>
              <button
                type="button"
                onClick={loadManifest}
                disabled={loadingManifest}
                className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors cursor-pointer"
                title="Làm mới MCP Manifest"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingManifest ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Inspector Tabs */}
            <div className="grid grid-cols-4 gap-1 bg-slate-100 p-1 rounded-xl text-xs font-bold">
              <button
                type="button"
                onClick={() => setInspectorTab('tools')}
                className={`py-1.5 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition-colors ${
                  inspectorTab === 'tools'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Wrench className="w-3.5 h-3.5" />
                <span>Tools ({manifest?.tools?.length ?? 7})</span>
              </button>
              <button
                type="button"
                onClick={() => setInspectorTab('resources')}
                className={`py-1.5 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition-colors ${
                  inspectorTab === 'resources'
                    ? 'bg-white text-emerald-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                <span>Resources ({manifest?.resources?.length ?? 3})</span>
              </button>
              <button
                type="button"
                onClick={() => setInspectorTab('prompts')}
                className={`py-1.5 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition-colors ${
                  inspectorTab === 'prompts'
                    ? 'bg-white text-amber-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Prompts ({manifest?.prompts?.length ?? 3})</span>
              </button>
              <button
                type="button"
                onClick={() => setInspectorTab('rpc')}
                className={`py-1.5 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition-colors ${
                  inspectorTab === 'rpc'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>JSON-RPC</span>
              </button>
            </div>

            {/* Tab 1: Tools */}
            {inspectorTab === 'tools' && (
              <div className="space-y-2.5 max-h-[540px] overflow-y-auto pr-1">
                {(manifest?.tools || []).map((t) => (
                  <div
                    key={t.name}
                    className="p-3 rounded-xl border border-slate-200 bg-slate-50/70 hover:border-indigo-200 transition-colors space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-700 flex items-center gap-1.5">
                        <Zap className="w-3.5 h-3.5 text-amber-500" />
                        {t.name}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleTestToolCall(t.name)}
                        className="text-[11px] font-bold bg-indigo-600 hover:bg-indigo-700 text-white px-2.5 py-1 rounded-lg transition-colors cursor-pointer shrink-0"
                      >
                        Test RPC ➔
                      </button>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{t.description}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Tab 2: Resources */}
            {inspectorTab === 'resources' && (
              <div className="space-y-2.5">
                {(manifest?.resources || []).map((r) => (
                  <div
                    key={r.uri}
                    className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-emerald-700 break-all">
                        {r.uri}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleTestResourceRead(r.uri)}
                        className="text-[11px] font-bold bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 rounded-lg transition-colors cursor-pointer shrink-0"
                      >
                        Đọc URI ➔
                      </button>
                    </div>
                    <div className="text-xs font-bold text-slate-800">{r.name}</div>
                    <p className="text-xs text-slate-600 leading-relaxed">{r.description}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Tab 3: Prompts */}
            {inspectorTab === 'prompts' && (
              <div className="space-y-2.5">
                {(manifest?.prompts || []).map((p) => (
                  <div
                    key={p.name}
                    className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-amber-800 flex items-center gap-1.5">
                        <FileCode2 className="w-3.5 h-3.5 text-amber-600" />
                        {p.name}
                      </span>
                      <span className="text-[10px] font-mono bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-md">
                        MCP Prompt Template
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{p.description}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Tab 4: Live JSON-RPC 2.0 Payload View */}
            {inspectorTab === 'rpc' && (
              <div className="space-y-3 font-mono text-[11px]">
                <div className="bg-slate-900 text-slate-100 rounded-xl p-3.5 space-y-1.5 overflow-x-auto">
                  <div className="flex items-center justify-between text-amber-300 font-bold">
                    <span>POST /api/v1/mcp/rpc (Request)</span>
                    {rpcLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  </div>
                  <pre className="text-slate-300 whitespace-pre-wrap">
                    {rpcRequestPreview ||
                      '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "tools/list",\n  "params": {}\n}'}
                  </pre>
                </div>

                <div className="bg-slate-900 text-emerald-100 rounded-xl p-3.5 space-y-1.5 overflow-x-auto max-h-80 overflow-y-auto">
                  <div className="text-emerald-400 font-bold">JSON-RPC 2.0 Response Payload</div>
                  <pre className="whitespace-pre-wrap">
                    {rpcResponsePreview ||
                      '// Bấm "Test RPC ➔" ở tab Tools hoặc "Đọc URI ➔" ở tab Resources để xem phản hồi thực tế từ máy chủ MCP.'}
                  </pre>
                </div>
              </div>
            )}
          </div>

          {/* Card 2: External Connectivity & Outbound Webhook Hub */}
          <div
            className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4"
            data-testid="mcp-external-connectivity-hub"
          >
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-500" />
                <span>Cổng Liên kết Hệ sinh thái Bên ngoài (Webhooks &amp; MCP Clients)</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Đồng bộ sự kiện xuất bản ra n8n/Zapier/Telegram/Slack kèm chữ ký số HMAC-SHA256 hoặc nối trực tiếp Claude Desktop / Cursor IDE vào MarketFlow.
              </p>
            </div>

            {/* Outbound Webhook Tester */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800">
                  1. Kiểm thử Outbound Webhook (Ký số HMAC-SHA256)
                </span>
                <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-md font-bold">
                  X-MarketFlow-Signature
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                    Nền tảng nhận sự kiện:
                  </label>
                  <select
                    value={connectorType}
                    onChange={(e) => setConnectorType(e.target.value)}
                    aria-label="Chọn nền tảng nhận Webhook"
                    className="w-full text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 font-semibold text-slate-800"
                  >
                    <option value="n8n_zapier">⚡ n8n / Make.com / Zapier</option>
                    <option value="telegram_bot">✈️ Telegram Bot API</option>
                    <option value="slack_discord">💬 Slack / Discord Webhook</option>
                    <option value="facebook_graph">📘 Meta (FB/IG) Graph API</option>
                    <option value="tiktok_business">🎵 TikTok Business API</option>
                    <option value="wordpress_cms">🌐 WordPress REST CMS</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                    Loại sự kiện (Event Trigger):
                  </label>
                  <select
                    value={webhookEventType}
                    onChange={(e) => setWebhookEventType(e.target.value)}
                    aria-label="Chọn loại sự kiện Webhook"
                    className="w-full text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 font-semibold text-slate-800"
                  >
                    <option value="content.published">content.published (Xuất bản bài)</option>
                    <option value="content.in_review">content.in_review (Gửi duyệt bài)</option>
                    <option value="campaign.budget_rebalanced">campaign.budget_rebalanced (Tối ưu ROAS)</option>
                    <option value="compliance.auto_fixed">compliance.auto_fixed (Làm sạch vi phạm)</option>
                  </select>
                </div>
              </div>

              <button
                type="button"
                data-testid="mcp-test-webhook-btn"
                onClick={handleTestExternalWebhook}
                disabled={webhookLoading}
                className="w-full py-2 px-3 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl transition-colors cursor-pointer flex items-center justify-center gap-2"
              >
                {webhookLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Đang ký số HMAC-SHA256 &amp; gửi gói tin...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    <span>🚀 Bắn thử Outbound Webhook &amp; Xem Chữ ký HMAC-SHA256</span>
                  </>
                )}
              </button>

              {webhookResult && (
                <div className="bg-slate-900 text-slate-100 rounded-xl p-3 font-mono text-[10px] space-y-1.5 overflow-x-auto max-h-52 overflow-y-auto">
                  <div className="flex items-center justify-between text-emerald-400 font-bold">
                    <span>HTTP 200 • {webhookResult.status}</span>
                    <span>{webhookResult.signature_algorithm}</span>
                  </div>
                  <div className="text-amber-300 truncate">
                    X-MarketFlow-Signature: {webhookResult.signature_header}
                  </div>
                  <pre className="text-slate-300 whitespace-pre-wrap">
                    {JSON.stringify(webhookResult.payload, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* External MCP Client Config Generator */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800">
                  2. Cấu hình kết nối từ AI IDE bên ngoài (External MCP Client)
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard?.writeText(getExternalClientSnippet());
                    toast.success('Đã sao chép cấu hình MCP Client vào bộ nhớ tạm!');
                  }}
                  className="text-[11px] font-bold text-indigo-700 hover:text-indigo-900 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-md cursor-pointer"
                >
                  Sao chép JSON
                </button>
              </div>

              <div className="grid grid-cols-3 gap-1 bg-slate-200/70 p-1 rounded-lg text-[11px] font-bold">
                <button
                  type="button"
                  onClick={() => setMcpClientType('claude_desktop')}
                  className={`py-1 rounded-md cursor-pointer ${
                    mcpClientType === 'claude_desktop'
                      ? 'bg-white text-indigo-700 shadow-xs'
                      : 'text-slate-600'
                  }`}
                >
                  Claude Desktop
                </button>
                <button
                  type="button"
                  onClick={() => setMcpClientType('cursor_ide')}
                  className={`py-1 rounded-md cursor-pointer ${
                    mcpClientType === 'cursor_ide'
                      ? 'bg-white text-indigo-700 shadow-xs'
                      : 'text-slate-600'
                  }`}
                >
                  Cursor IDE
                </button>
                <button
                  type="button"
                  onClick={() => setMcpClientType('curl_jsonrpc')}
                  className={`py-1 rounded-md cursor-pointer ${
                    mcpClientType === 'curl_jsonrpc'
                      ? 'bg-white text-indigo-700 shadow-xs'
                      : 'text-slate-600'
                  }`}
                >
                  cURL / n8n
                </button>
              </div>

              <pre className="bg-slate-900 text-indigo-100 rounded-xl p-3 font-mono text-[10px] overflow-x-auto whitespace-pre-wrap">
                {getExternalClientSnippet()}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
