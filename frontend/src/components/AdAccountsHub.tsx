import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  Plus,
  Trash2,
  ArrowRightLeft,
  CreditCard,
  ShoppingBag,
  Link2,
  Loader2,
  X,
  Copy,
  Check,
  Terminal,
  Zap,
  Users,
  Send,
  Sliders,
  Calculator,
  MessageSquare,
  Calendar,
  ShieldCheck,
  QrCode,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import {
  adAccountsApi,
  AdAccountItem,
  kolBookingsApi,
  KolBookingItem,
  campaignApi,
  getApiErrorMessage,
  isOfflineDemoEnabled,
} from '../services/api';
import { Campaign } from '../types';
import { formatNumber } from '../utils/format';
import { useToast } from './Toast';

interface AdAccountsHubProps {
  workspaceId?: number;
  onSynced?: () => void;
}

const PLATFORM_LABELS: Record<string, string> = {
  META_ADS: 'Meta Ads (FB / IG)',
  TIKTOK_ADS: 'TikTok Business',
  GOOGLE_ADS: 'Google Ads MCC',
  POS_SYSTEM: 'Sapo / Pancake POS',
};

const STATUS_LABELS: Record<string, { label: string; badgeClass: string }> = {
  ACTIVE: {
    label: 'Đang hoạt động',
    badgeClass: 'bg-[#ECFDF5] text-[#15803D] border border-[#A7F3D0]',
  },
  SPEND_WARNING: {
    label: 'Sắp chạm trần thẻ',
    badgeClass: 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]',
  },
  RESTRICTED: {
    label: 'Bị hạn chế (Đổi TK)',
    badgeClass: 'bg-[#FFF1F2] text-[#BE123C] border border-[#FECDD3]',
  },
};

const LEAD_STAGE_META: Record<string, { label: string; badge: string }> = {
  NEW_INBOX: {
    label: 'Mới hỏi giá Inbox',
    badge: 'bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7]',
  },
  SILENT_24H: {
    label: 'Sắp khóa 24h Meta (Cần ZNS)',
    badge: 'bg-[#FFF1F2] text-[#BE123C] border border-[#FECDD3]',
  },
  WAITING_TRANSFER: {
    label: 'Chờ chuyển khoản VietQR',
    badge: 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]',
  },
  PAYDAY_15_25: {
    label: 'Hẹn lương về 15 / 25',
    badge: 'bg-[#F6F5F0] text-[#D95D39] border border-[#D0CEC7]',
  },
  CLOSED_POS: {
    label: 'Đã chốt đơn POS',
    badge: 'bg-[#ECFDF5] text-[#15803D] border border-[#A7F3D0]',
  },
};

export const AdAccountsHub: React.FC<AdAccountsHubProps> = ({ workspaceId, onSynced }) => {
  const toast = useToast();
  const [activeModuleTab, setActiveModuleTab] = useState<
    'ALL' | 'ADS_POS' | 'KOL_PNL' | 'ZALO_MEGA' | 'SAAS_BILLING'
  >('ALL');

  const [accounts, setAccounts] = useState<AdAccountItem[]>([]);
  const [kolBookings, setKolBookings] = useState<KolBookingItem[]>([]);
  const [kolSummary, setKolSummary] = useState<{
    total_creators: number;
    total_cost: number;
    total_revenue: number;
    total_orders: number;
    avg_roas: number;
  }>({
    total_creators: 0,
    total_cost: 0,
    total_revenue: 0,
    total_orders: 0,
    avg_roas: 0,
  });
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [runningWorker, setRunningWorker] = useState<boolean>(false);
  const [pushingAccountId, setPushingAccountId] = useState<number | null>(null);
  const [recordingKolId, setRecordingKolId] = useState<number | null>(null);
  const [firingWebhook, setFiringWebhook] = useState<boolean>(false);
  const [copiedCurl, setCopiedCurl] = useState<boolean>(false);
  const [copiedKolCode, setCopiedKolCode] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [showPosForm, setShowPosForm] = useState<boolean>(false);
  const [showKolForm, setShowKolForm] = useState<boolean>(false);
  const [showConnectorForm, setShowConnectorForm] = useState<boolean>(false);
  const [showLeadForm, setShowLeadForm] = useState<boolean>(false);

  // Form thêm tài khoản quảng cáo mới
  const [newPlatform, setNewPlatform] = useState<string>('META_ADS');
  const [newCode, setNewCode] = useState<string>('');
  const [newName, setNewName] = useState<string>('');
  const [newPixel, setNewPixel] = useState<string>('');
  const [newCap, setNewCap] = useState<string>('15000000');
  const [newCampaignId, setNewCampaignId] = useState<string>('');
  const [newToken, setNewToken] = useState<string>('');
  const [savingAccount, setSavingAccount] = useState<boolean>(false);

  // Form ghi nhận đơn hàng POS / UTM thực tế
  const [posCampaignId, setPosCampaignId] = useState<string>('');
  const [posChannelId, setPosChannelId] = useState<string>('1');
  const [posOrderCount, setPosOrderCount] = useState<string>('3');
  const [posOrderValue, setPosOrderValue] = useState<string>('4500000');
  const [posAdSpend, setPosAdSpend] = useState<string>('650000');
  const [savingPosOrder, setSavingPosOrder] = useState<boolean>(false);

  // Form thêm hợp đồng thuê KOL / KOC bên thứ 3
  const [kolName, setKolName] = useState<string>('');
  const [kolHandle, setKolHandle] = useState<string>('');
  const [kolPlatform, setKolPlatform] = useState<string>('TIKTOK');
  const [kolTier, setKolTier] = useState<string>('Micro KOC (120K Flw)');
  const [kolCode, setKolCode] = useState<string>('');
  const [kolCost, setKolCost] = useState<string>('6000000');
  const [kolCommission, setKolCommission] = useState<string>('10');
  const [kolCampaignId, setKolCampaignId] = useState<string>('');
  const [savingKol, setSavingKol] = useState<boolean>(false);

  // Vietnam Priority #1: TikTok Shop / Shopee P&L & Break-Even ROAS State
  const [pnlSellingPrice, setPnlSellingPrice] = useState<string>('380000');
  const [pnlCogs, setPnlCogs] = useState<string>('115000');
  const [pnlPlatformFee, setPnlPlatformFee] = useState<string>('12.5');
  const [pnlAffiliatePct, setPnlAffiliatePct] = useState<string>('10');
  const [pnlReturnRate, setPnlReturnRate] = useState<string>('14');
  const [pnlReturnShipFee, setPnlReturnShipFee] = useState<string>('28000');
  const [pnlResult, setPnlResult] = useState<any>(null);
  const [calculatingPnl, setCalculatingPnl] = useState<boolean>(false);

  // Vietnam Priority #2: Zalo OA / ZNS & Messenger Click-to-Chat Lead CRM State
  const [vnLeads, setVnLeads] = useState<any[]>([]);
  const [vnLeadsSummary, setVnLeadsSummary] = useState<{
    total_leads: number;
    urgent_24h_count: number;
    open_pipeline_value: number;
    closed_won_value: number;
  }>({
    total_leads: 0,
    urgent_24h_count: 0,
    open_pipeline_value: 0,
    closed_won_value: 0,
  });
  const [leadName, setLeadName] = useState<string>('');
  const [leadPhone, setLeadPhone] = useState<string>('');
  const [leadSource, setLeadSource] = useState<string>('FB_MESSENGER');
  const [leadStage] = useState<string>('NEW_INBOX');
  const [leadProduct, setLeadProduct] = useState<string>('Combo Liệu Trình Chuyên Sâu');
  const [leadValue, setLeadValue] = useState<string>('790000');
  const [savingLead, setSavingLead] = useState<boolean>(false);
  const [processingLeadId, setProcessingLeadId] = useState<number | null>(null);
  const [applyingBlueprint, setApplyingBlueprint] = useState<string | null>(null);

  // SaaS Billing & Clean Production Mode State
  const [billingData, setBillingData] = useState<any>(null);
  const [upgradingTier, setUpgradingTier] = useState<string | null>(null);
  const [togglingCleanMode, setTogglingCleanMode] = useState<boolean>(false);
  const [webhookSecretInput, setWebhookSecretInput] = useState<string>('mf_pos_live_vn2026');
  const [zaloTokenInput, setZaloTokenInput] = useState<string>('');
  const [smtpKeyInput, setSmtpKeyInput] = useState<string>('');
  const [savingConnectors, setSavingConnectors] = useState<boolean>(false);

  const loadHubData = useCallback(async () => {
    setLoading(true);
    try {
      const [accRes, kolRes, campList, leadsRes, billingRes] = await Promise.all([
        adAccountsApi.list(workspaceId),
        kolBookingsApi.list(workspaceId).catch(() => ({
          items: [],
          workspace_id: workspaceId || 1,
          summary: { total_creators: 0, total_cost: 0, total_revenue: 0, total_orders: 0, avg_roas: 0 },
        })),
        campaignApi.getAll(undefined, undefined, workspaceId),
        adAccountsApi.listVnLeads(workspaceId).catch(() => ({
          items: [],
          summary: { total_leads: 0, urgent_24h_count: 0, open_pipeline_value: 0, closed_won_value: 0 },
        })),
        adAccountsApi.getBillingPlan(workspaceId).catch(() => null),
      ]);
      setAccounts(accRes.items || []);
      setKolBookings(kolRes.items || []);
      if (kolRes.summary) setKolSummary(kolRes.summary);
      setCampaigns(campList || []);
      setVnLeads(leadsRes.items || []);
      if (leadsRes.summary) setVnLeadsSummary(leadsRes.summary);
      if (billingRes) {
        setBillingData(billingRes);
        if (billingRes.webhook_secret_key) {
          setWebhookSecretInput(billingRes.webhook_secret_key);
        }
      }
      const defaultCampId = campList.length > 0 ? campList[0].id : undefined;
      if (defaultCampId && !posCampaignId) {
        const firstId = String(defaultCampId);
        setPosCampaignId(firstId);
        setNewCampaignId(firstId);
        setKolCampaignId(firstId);
      }
      // Tính điểm hòa vốn mặc định lần đầu
      const pnlInit = await adAccountsApi
        .calculateVnEcommercePnl({
          campaign_id: defaultCampId || null,
          selling_price: 380000,
          cogs_per_unit: 115000,
          platform_fee_pct: 12.5,
          affiliate_commission_pct: 10,
          return_rate_pct: 14,
          return_shipping_fee: 28000,
        })
        .catch(() => null);
      if (pnlInit) setPnlResult(pnlInit);
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không tải được dữ liệu kết nối quảng cáo & KOL');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, posCampaignId, toast]);

  useEffect(() => {
    void loadHubData();
  }, [loadHubData]);

  const handleSyncAll = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      const res = await adAccountsApi.syncAll(workspaceId);
      setAccounts(res.items || []);
      const addedRev = res.added_revenue_today ? ` (+${formatNumber(res.added_revenue_today)} đ doanh thu mới)` : '';
      toast.success(
        `Đã đồng bộ ${res.synced_accounts_count} tài khoản quảng cáo & POS (${res.verified_metric_rows} dòng chỉ số cập nhật)${addedRev}.`
      );
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể đồng bộ số liệu');
    } finally {
      setSyncing(false);
    }
  };

  const handleRunAutoWorkerTick = async () => {
    if (runningWorker) return;
    setRunningWorker(true);
    try {
      const res = await adAccountsApi.runAutoWorkerTick(workspaceId);
      const pubMsg =
        res.auto_published_posts_count > 0
          ? `Đã tự động đăng ${res.auto_published_posts_count} bài đã duyệt lên Fanpage/TikTok · `
          : `Đã kích hoạt ${res.schedules_triggered} lịch xuất bản tự động · `;
      const znsMsg = res.zns_auto_care_triggered
        ? ` · Tự động bắn ${res.zns_auto_care_triggered} tin Zalo ZNS chăm sóc khách`
        : '';
      toast.success(
        `${pubMsg}Cộng +${res.kol_orders_added} đơn Affiliate KOL (+${formatNumber(res.kol_revenue_added)} đ) và đồng bộ ${res.synced_accounts_count} tài khoản QC${znsMsg}.`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể chạy tiến trình Auto-Publish & Đồng bộ tự động');
    } finally {
      setRunningWorker(false);
    }
  };

  const handlePushTwoWayBudget = async (acc: AdAccountItem) => {
    if (pushingAccountId) return;
    setPushingAccountId(acc.id);
    try {
      const nextCap = Math.max(5000000, Math.round((acc.daily_spend_cap || 15000000) * 1.2));
      const res = await adAccountsApi.pushTwoWayBudget(acc.id, {
        daily_spend_cap: nextCap,
        remote_status: 'ACTIVE',
      });
      toast.success(
        (res as any).execution_mode === 'LIVE_GRAPH_API'
          ? `Đã đồng bộ hạn mức ngày mới (${formatNumber(res.daily_spend_cap)} đ/ngày) lên ${acc.account_name}.`
          : `Đã cập nhật hạn mức chi tiêu ngày (${formatNumber(res.daily_spend_cap)} đ/ngày) cho ${acc.account_name}.`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể đẩy ngân sách 2 chiều');
    } finally {
      setPushingAccountId(null);
    }
  };

  const webhookEndpointUrl = `${window.location.origin}/api/v1/ad-accounts/external-webhook`;
  const activeCampCode = campaigns[0]?.campaign_code || 'CMP_001';
  const activeKolCode = kolBookings[0]?.tracking_code || 'KOC_HALINH_25';
  const activeWebhookKey = billingData?.webhook_secret_key || webhookSecretInput || 'mf_pos_live_vn2026';

  const handleCopyWebhookCurl = async () => {
    const curlCmd = `curl -X POST "${webhookEndpointUrl}" -H "Content-Type: application/json" -H "X-MarketFlow-Webhook-Key: ${activeWebhookKey}" -d '{"utm_campaign":"${activeCampCode}","utm_source":"tiktok","koc_code":"${activeKolCode}","order_count":2,"order_value":1850000,"ad_spend_delta":320000,"webhook_key":"${activeWebhookKey}","source_app":"Sapo POS + Affiliate Live"}'`;
    try {
      await navigator.clipboard.writeText(curlCmd);
      setCopiedCurl(true);
      toast.success('Đã sao chép lệnh Webhook kèm khóa bảo mật X-MarketFlow-Webhook-Key vào bộ nhớ tạm.');
      setTimeout(() => setCopiedCurl(false), 2500);
    } catch {
      toast.warning('Không thể sao chép tự động, vui lòng bôi đen URL.');
    }
  };

  const handleFireLiveWebhookTest = async () => {
    if (firingWebhook) return;
    setFiringWebhook(true);
    try {
      const targetCampId = posCampaignId ? Number(posCampaignId) : campaigns[0]?.id;
      const res = await adAccountsApi.fireExternalWebhook({
        workspace_id: workspaceId || 1,
        campaign_id: targetCampId,
        utm_campaign: activeCampCode,
        utm_source: 'tiktok',
        order_count: 2,
        order_value: 1850000,
        ad_spend_delta: 320000,
        source_app: 'Sapo POS / Pancake Webhook',
      });
      toast.success(
        `Webhook thực tế (${res.order_code}): Đã cộng +${res.added_orders} đơn (+${formatNumber(res.added_revenue)} đ) vào "${res.campaign_name}" · ROAS ngày: ${res.day_roas}x.`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể bắn đơn hàng qua cổng Webhook');
    } finally {
      setFiringWebhook(false);
    }
  };

  const handleToggleCleanWorkspace = async (mode: 'purge_demo' | 'restore_demo') => {
    if (togglingCleanMode) return;
    setTogglingCleanMode(true);
    try {
      const res = await adAccountsApi.toggleCleanWorkspace({
        workspace_id: workspaceId,
        mode,
      });
      toast.success(res.message || 'Đã cập nhật Chế độ Production Sạch.');
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể chuyển đổi chế độ dữ liệu');
    } finally {
      setTogglingCleanMode(false);
    }
  };

  const handleSaveConnectors = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingConnectors(true);
    try {
      await adAccountsApi.updateLiveConnectors({
        workspace_id: workspaceId,
        webhook_secret_key: webhookSecretInput.trim(),
        zalo_oa_token: zaloTokenInput.trim() || undefined,
        smtp_or_resend_key: smtpKeyInput.trim() || undefined,
      });
      toast.success('Đã lưu khóa bảo mật POS Webhook & Token kết nối Zalo ZNS / Email thật.');
      setShowConnectorForm(false);
      await loadHubData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể lưu cấu hình kết nối');
    } finally {
      setSavingConnectors(false);
    }
  };

  const handleCalculatePnl = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setCalculatingPnl(true);
    try {
      const targetCampId = posCampaignId ? Number(posCampaignId) : campaigns[0]?.id || null;
      const res = await adAccountsApi.calculateVnEcommercePnl({
        campaign_id: targetCampId,
        selling_price: Math.max(10000, Number(pnlSellingPrice) || 380000),
        cogs_per_unit: Math.max(0, Number(pnlCogs) || 115000),
        platform_fee_pct: Math.max(0, Number(pnlPlatformFee) || 12.5),
        affiliate_commission_pct: Math.max(0, Number(pnlAffiliatePct) || 10),
        return_rate_pct: Math.max(0, Number(pnlReturnRate) || 14),
        return_shipping_fee: Math.max(0, Number(pnlReturnShipFee) || 28000),
      });
      setPnlResult(res);
      toast.success(
        `Đã tính Điểm Hòa Vốn: ROAS Hòa Vốn = ${res.unit_economics.break_even_roas}x · CPA Tối Đa = ${formatNumber(res.unit_economics.max_allowable_cpa)} đ/đơn.`
      );
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể tính P&L TikTok Shop / Shopee');
    } finally {
      setCalculatingPnl(false);
    }
  };

  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leadName.trim() || !leadPhone.trim()) {
      toast.warning('Vui lòng nhập Tên khách hàng và Số điện thoại Zalo.');
      return;
    }
    setSavingLead(true);
    try {
      const targetCampId = posCampaignId ? Number(posCampaignId) : campaigns[0]?.id || null;
      await adAccountsApi.createVnLead({
        workspace_id: workspaceId,
        campaign_id: targetCampId,
        customer_name: leadName.trim(),
        phone: leadPhone.trim(),
        source_channel: leadSource,
        lead_stage: leadStage,
        product_interest: leadProduct.trim() || 'Combo Sản phẩm Chủ lực',
        estimated_value: Math.max(10000, Number(leadValue) || 500000),
      });
      toast.success(`Đã thêm khách hàng "${leadName.trim()}" vào Phễu Chốt Đơn Zalo / Messenger.`);
      setLeadName('');
      setLeadPhone('');
      setShowLeadForm(false);
      await loadHubData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể thêm khách hàng tiềm năng');
    } finally {
      setSavingLead(false);
    }
  };

  const handleSendZnsLead = async (lead: any, templateType: string) => {
    if (processingLeadId) return;
    setProcessingLeadId(lead.id);
    try {
      const res = await adAccountsApi.sendVnLeadZns(lead.id, templateType);
      toast.success(res.message_sent || `Đã bắn Zalo ZNS chăm sóc khách ${lead.customer_name}.`);
      await loadHubData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể gửi tin nhắn Zalo ZNS');
    } finally {
      setProcessingLeadId(null);
    }
  };

  const handleCloseLeadToOrder = async (lead: any) => {
    if (processingLeadId) return;
    setProcessingLeadId(lead.id);
    try {
      const res = await adAccountsApi.closeVnLeadOrder(lead.id);
      toast.success(
        `Đã chốt đơn thành công cho ${lead.customer_name} (+${formatNumber(res.added_revenue)} đ) và đồng bộ trực tiếp vào doanh thu Chiến dịch!`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể chốt đơn từ Lead');
    } finally {
      setProcessingLeadId(null);
    }
  };

  const handleDeleteLead = async (lead: any) => {
    try {
      await adAccountsApi.deleteVnLead(lead.id);
      toast.success(`Đã xóa khách hàng ${lead.customer_name}.`);
      await loadHubData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể xóa Lead');
    }
  };

  const handleApplyMegaSaleBlueprint = async (code: string, label: string) => {
    const targetCampId = posCampaignId ? Number(posCampaignId) : campaigns[0]?.id;
    if (!targetCampId) {
      toast.warning('Vui lòng tạo hoặc chọn ít nhất 1 chiến dịch trước.');
      return;
    }
    setApplyingBlueprint(code);
    try {
      const res = await adAccountsApi.applyVnMegaSaleBlueprint({
        campaign_id: targetCampId,
        blueprint_code: code,
      });
      toast.success(
        `Đã áp dụng kịch bản "${res.blueprint_title}" vào chiến dịch "${res.campaign_name}": Tạo mới ${res.created_tasks_count} đầu việc theo Khung Giờ Vàng & phân bổ lại ngân sách!`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), `Không thể áp dụng lịch ${label}`);
    } finally {
      setApplyingBlueprint(null);
    }
  };

  const handleUpgradeBilling = async (tier: 'FREE' | 'PRO' | 'AGENCY') => {
    if (upgradingTier) return;
    setUpgradingTier(tier);
    try {
      const res = await adAccountsApi.upgradeBillingPlan({
        workspace_id: workspaceId,
        plan_tier: tier,
        billing_cycle: 'MONTHLY',
      });
      toast.success(res.message || `Đã nâng cấp lên gói ${tier} thành công!`);
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể nâng cấp gói cước');
    } finally {
      setUpgradingTier(null);
    }
  };

  const handleSimulateSePayTransfer = async (tier: 'PRO' | 'AGENCY') => {
    if (upgradingTier) return;
    setUpgradingTier(`SEPAY_${tier}`);
    try {
      const wsId = workspaceId || billingData?.workspace_id || 1;
      const amount = tier === 'AGENCY' ? 1490000 : 499000;
      const res = await adAccountsApi.simulateSePayWebhook({
        content: `MARKETFLOW WS${wsId} ${tier}`,
        transferAmount: amount,
      });
      toast.success(
        `Đối soát SePay / Napas 247 thành công (${res.payment_ref}): Đã nhận ${formatNumber(res.transfer_amount)} đ và tự động mở khóa gói ${res.upgraded_to}!`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể giả lập Webhook ngân hàng SePay');
    } finally {
      setUpgradingTier(null);
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode.trim() || !newName.trim()) {
      toast.warning('Vui lòng nhập Mã tài khoản (VD: act_1084...) và Tên gợi nhớ.');
      return;
    }
    setSavingAccount(true);
    try {
      await adAccountsApi.create({
        platform: newPlatform,
        account_code: newCode.trim(),
        account_name: newName.trim(),
        pixel_id: newPixel.trim() || undefined,
        daily_spend_cap: Number(newCap) || 0,
        linked_campaign_id: newCampaignId ? Number(newCampaignId) : null,
        access_token: newToken.trim() || undefined,
        workspace_id: workspaceId,
      });
      toast.success('Đã thêm tài khoản quảng cáo và gắn với chiến dịch.');
      setNewCode('');
      setNewName('');
      setNewPixel('');
      setNewToken('');
      setShowAddForm(false);
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể thêm tài khoản');
    } finally {
      setSavingAccount(false);
    }
  };

  const handleChangeCampaignLink = async (acc: AdAccountItem, nextCampaignId: string) => {
    try {
      await adAccountsApi.update(acc.id, {
        linked_campaign_id: nextCampaignId ? Number(nextCampaignId) : null,
      });
      toast.success('Đã đổi chiến dịch gắn với tài khoản quảng cáo.');
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể đổi liên kết chiến dịch');
    }
  };

  const handleToggleAccountStatus = async (acc: AdAccountItem, nextStatus: string) => {
    try {
      await adAccountsApi.update(acc.id, { status: nextStatus });
      toast.success(`Đã cập nhật trạng thái tài khoản ${acc.account_code}.`);
      await loadHubData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể đổi trạng thái tài khoản');
    }
  };

  const handleSwitchToBackupAccount = async (restrictedAcc: AdAccountItem) => {
    const backup = accounts.find(
      (a) =>
        a.id !== restrictedAcc.id &&
        a.platform === restrictedAcc.platform &&
        a.status === 'ACTIVE'
    );
    if (!backup) {
      toast.warning('Chưa có tài khoản dự phòng cùng nền tảng đang hoạt động. Hãy thêm tài khoản dự phòng trước.');
      return;
    }
    try {
      await adAccountsApi.update(backup.id, {
        linked_campaign_id: restrictedAcc.linked_campaign_id,
      });
      await adAccountsApi.update(restrictedAcc.id, {
        linked_campaign_id: null,
      });
      toast.success(
        `Đã chuyển chiến dịch sang tài khoản dự phòng ${backup.account_code} (${backup.account_name}).`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể chuyển sang tài khoản dự phòng');
    }
  };

  const handleDeleteAccount = async (acc: AdAccountItem) => {
    try {
      await adAccountsApi.delete(acc.id);
      toast.success(`Đã gỡ tài khoản ${acc.account_code}.`);
      await loadHubData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể gỡ tài khoản');
    }
  };

  const handleRecordPosOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!posCampaignId) {
      toast.warning('Vui lòng chọn chiến dịch nhận đơn hàng.');
      return;
    }
    setSavingPosOrder(true);
    try {
      const res = await adAccountsApi.recordPosOrder({
        campaign_id: Number(posCampaignId),
        channel_id: Number(posChannelId) || 1,
        order_count: Math.max(1, Number(posOrderCount) || 1),
        order_value: Math.max(1000, Number(posOrderValue) || 0),
        ad_spend_delta: Math.max(0, Number(posAdSpend) || 0),
      });
      toast.success(
        `Đã cộng +${res.added_orders} đơn hàng (+${formatNumber(res.added_revenue)} đ) từ POS vào chiến dịch "${res.campaign_name}".`
      );
      setShowPosForm(false);
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể ghi nhận đơn hàng POS');
    } finally {
      setSavingPosOrder(false);
    }
  };

  const handleCreateKolBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kolName.trim() || !kolHandle.trim()) {
      toast.warning('Vui lòng nhập Tên KOL/KOC và Handle kênh (VD: @halinh.official).');
      return;
    }
    setSavingKol(true);
    try {
      const created = await kolBookingsApi.create({
        creator_name: kolName.trim(),
        handle: kolHandle.trim(),
        platform: kolPlatform,
        followers_tier: kolTier.trim() || 'Micro KOC (90K Flw)',
        campaign_id: kolCampaignId ? Number(kolCampaignId) : null,
        tracking_code: kolCode.trim() || undefined,
        booking_cost: Math.max(0, Number(kolCost) || 0),
        commission_pct: Math.max(0, Number(kolCommission) || 0),
        workspace_id: workspaceId,
      });
      toast.success(
        `Đã tạo hợp đồng KOL/KOC "${created.creator_name}" kèm mã theo dõi ${created.tracking_code}.`
      );
      setKolName('');
      setKolHandle('');
      setKolCode('');
      setShowKolForm(false);
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể thêm hợp đồng KOL/KOC');
    } finally {
      setSavingKol(false);
    }
  };

  const handleRecordKolOrder = async (kol: KolBookingItem) => {
    if (recordingKolId) return;
    setRecordingKolId(kol.id);
    try {
      const res = await kolBookingsApi.recordOrder(kol.id, {
        order_count: 3,
        order_value: 2850000,
        added_views: 5200,
        added_clicks: 210,
      });
      toast.success(
        `Mã ${kol.tracking_code} (${kol.creator_name}): Đã cộng +${res.added_orders} đơn Affiliate (+${formatNumber(res.added_revenue)} đ, hoa hồng ${formatNumber(res.commission_cost_added)} đ) · ROAS đạt ${res.booking.net_roas}x.`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể cộng đơn Affiliate KOL/KOC');
    } finally {
      setRecordingKolId(null);
    }
  };

  const handleDeleteKol = async (kol: KolBookingItem) => {
    try {
      await kolBookingsApi.delete(kol.id);
      toast.success(`Đã xóa hợp đồng KOL/KOC ${kol.creator_name}.`);
      await loadHubData();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể xóa hợp đồng KOL/KOC');
    }
  };

  const handleCopyKolLink = async (kol: KolBookingItem) => {
    try {
      await navigator.clipboard.writeText(kol.utm_link);
      setCopiedKolCode(kol.tracking_code);
      toast.success(`Đã chép link Bio gắn mã UTM (${kol.tracking_code}) của ${kol.creator_name}.`);
      setTimeout(() => setCopiedKolCode(null), 2000);
    } catch {
      toast.warning('Không thể sao chép tự động.');
    }
  };

  const isCleanProd = Boolean(billingData?.clean_demo_mode);
  const currentPlanTier = billingData?.plan_tier || 'FREE';

  return (
    <div className="space-y-6">
      {/* THANH ĐIỀU HƯỚNG TỔNG ĐÀI THƯƠNG MẠI HÓA & MARKETING ĐẶC THÙ VIỆT NAM */}
      <div className="bg-white rounded-xl border border-[#E4E2DD] p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: 'ALL', label: 'Tất cả phân hệ (All-in-One)' },
            { id: 'ADS_POS', label: '1. Tài khoản QC & POS Webhook' },
            { id: 'KOL_PNL', label: '2. KOL Affiliate & Điểm Hòa Vốn Sàn TMĐT' },
            { id: 'ZALO_MEGA', label: '3. Phễu Zalo ZNS / Messenger & Lịch Mega Sale VN' },
            { id: 'SAAS_BILLING', label: `4. Gói Cước SaaS & VietQR (${currentPlanTier})` },
          ].map((tab) => {
            const active = activeModuleTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveModuleTab(tab.id as any)}
                className={`px-3 py-1.5 rounded-xl text-xs font-extrabold transition-colors cursor-pointer ${
                  active
                    ? 'bg-[#121316] text-white'
                    : 'bg-[#F6F5F0] text-[#3B3F46] hover:text-[#121316] border border-[#E4E2DD]'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-extrabold border bg-[#ECFDF5] text-[#15803D] border-[#A7F3D0]"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Chế độ Production (Số liệu thực tế)</span>
          </span>

          {(!isCleanProd || isOfflineDemoEnabled()) && (
            <button
              type="button"
              disabled={togglingCleanMode}
              onClick={() =>
                handleToggleCleanWorkspace(
                  isCleanProd && isOfflineDemoEnabled() ? 'restore_demo' : 'purge_demo'
                )
              }
              className="inline-flex items-center gap-1.5 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
            >
              {togglingCleanMode ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-[#D95D39]" />
              )}
              <span>
                {isCleanProd && isOfflineDemoEnabled()
                  ? 'Khôi phục dữ liệu mẫu'
                  : 'Xóa toàn bộ dữ liệu mẫu'}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* KHỐI 1: QUẢN LÝ TÀI KHOẢN QUẢNG CÁO, ĐỒNG BỘ CSV & CỔNG WEBHOOK POS */}
      {(activeModuleTab === 'ALL' || activeModuleTab === 'ADS_POS') && (
        <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-5">
          {/* Header */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#E4E2DD] pb-4">
            <div>
              <h3 className="text-base font-extrabold text-[#121316] tracking-tight">
                Quản lý Tài khoản Quảng cáo, Đồng bộ CSV &amp; Cổng Webhook POS
              </h3>
              <p className="text-xs text-[#3B3F46] mt-1">
                Lưu trữ tài khoản quảng cáo, nhập file CSV báo cáo chi phí hoặc đẩy trần ngân sách qua API thực (khi có Access Token) và xác thực khóa bảo mật POS Webhook.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => {
                  setShowConnectorForm((prev) => !prev);
                  setShowPosForm(false);
                  setShowAddForm(false);
                }}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3 py-2 rounded-xl transition-colors cursor-pointer"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-[#D95D39]" />
                <span>Khóa Webhook &amp; Zalo/Email API</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowPosForm((prev) => !prev);
                  setShowAddForm(false);
                  setShowConnectorForm(false);
                }}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3 py-2 rounded-xl transition-colors cursor-pointer"
              >
                <ShoppingBag className="w-3.5 h-3.5 text-[#15803D]" />
                <span>Ghi nhận đơn POS</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowAddForm((prev) => !prev);
                  setShowPosForm(false);
                  setShowConnectorForm(false);
                }}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3 py-2 rounded-xl transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5 text-[#121316]" />
                <span>Thêm tài khoản QC</span>
              </button>

              {isOfflineDemoEnabled() && (
                <button
                  type="button"
                  disabled={runningWorker}
                  onClick={handleRunAutoWorkerTick}
                  className="inline-flex items-center gap-1.5 bg-[#121316] hover:bg-[#26282D] text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-colors cursor-pointer"
                >
                  {runningWorker ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5 text-[#FDE68A]" />
                  )}
                  <span>Auto-Publish Fanpage &amp; Chạy Worker</span>
                </button>
              )}

              <button
                type="button"
                disabled={syncing}
                onClick={handleSyncAll}
                className="inline-flex items-center gap-1.5 bg-[#D95D39] hover:bg-[#C04E2C] text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-colors cursor-pointer"
              >
                {syncing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
                <span>Đồng bộ chi phí &amp; đơn ngay</span>
              </button>
            </div>
          </div>

          {/* Form cấu hình Khóa bảo mật POS Webhook & Token Zalo OA / Email thật */}
          {showConnectorForm && (
            <form
              onSubmit={handleSaveConnectors}
              className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-extrabold text-[#121316]">
                  Cấu hình Khóa bảo mật POS Webhook (X-MarketFlow-Webhook-Key), Token Zalo OA ZNS &amp; Email API thật
                </span>
                <button
                  type="button"
                  onClick={() => setShowConnectorForm(false)}
                  className="text-[#3B3F46] hover:text-[#121316]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="block font-bold text-[#3B3F46] mb-1">
                    Khóa bảo mật POS Webhook (Secret Key)
                  </label>
                  <input
                    type="text"
                    value={webhookSecretInput}
                    onChange={(e) => setWebhookSecretInput(e.target.value)}
                    placeholder="VD: mf_pos_live_vn2026"
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold text-[#121316] outline-none"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#3B3F46] mb-1">
                    Zalo Official Account Access Token (Bắn ZNS thật)
                  </label>
                  <input
                    type="password"
                    value={zaloTokenInput}
                    onChange={(e) => setZaloTokenInput(e.target.value)}
                    placeholder="Điền Zalo OA Token để gọi openapi.zalo.me..."
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] outline-none"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#3B3F46] mb-1">
                    Resend / SMTP API Key (Gửi báo cáo &amp; cảnh báo Email)
                  </label>
                  <input
                    type="password"
                    value={smtpKeyInput}
                    onChange={(e) => setSmtpKeyInput(e.target.value)}
                    placeholder="VD: re_123456789..."
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] outline-none"
                  />
                </div>
              </div>
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowConnectorForm(false)}
                  className="px-3 py-1.5 text-xs font-semibold text-[#3B3F46]"
                >
                  Đóng
                </button>
                <button
                  type="submit"
                  disabled={savingConnectors}
                  className="px-4 py-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold rounded-lg cursor-pointer"
                >
                  {savingConnectors ? 'Đang lưu...' : 'Lưu khóa bảo mật & Kết nối'}
                </button>
              </div>
            </form>
          )}

          {/* Thanh OAuth2 Quick-Connect & Cổng Webhook nhận đơn tự động */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
            <div className="lg:col-span-7 bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5 flex flex-col justify-between gap-2.5">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 text-xs font-extrabold text-[#121316]">
                    <Terminal className="w-3.5 h-3.5 text-[#D95D39]" />
                    <span>Webhook nhận đơn POS &amp; Mã KOL/KOC:</span>
                  </span>
                  <code className="text-xs font-bold text-[#15803D] bg-white px-2 py-0.5 rounded border border-[#D0CEC7] select-all break-all">
                    POST {webhookEndpointUrl}
                  </code>
                </div>
                <p className="text-xs text-[#3B3F46]">
                  Tự động nhận đơn từ Sapo POS, Pancake CRM, Haravan, Ladipage kèm khóa <code className="font-bold text-[#121316]">{activeWebhookKey}</code>.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyWebhookCurl}
                  className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                >
                  {copiedCurl ? <Check className="w-3.5 h-3.5 text-[#15803D]" /> : <Copy className="w-3.5 h-3.5 text-[#3B3F46]" />}
                  <span>{copiedCurl ? 'Đã chép lệnh cURL' : 'Chép lệnh cURL (Kèm Khóa)'}</span>
                </button>

                {isOfflineDemoEnabled() && (
                  <button
                    type="button"
                    disabled={firingWebhook}
                    onClick={handleFireLiveWebhookTest}
                    className="inline-flex items-center gap-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                  >
                    {firingWebhook ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5 text-[#FDE68A]" />
                    )}
                    <span>Bắn thử đơn Webhook thật (+2 đơn / 1,85tr)</span>
                  </button>
                )}
              </div>
            </div>

            <div className="lg:col-span-5 bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5 flex flex-col justify-between gap-2.5">
              <div>
                <div className="text-xs font-extrabold text-[#121316]">
                  Khai báo nhanh theo Nền tảng Quảng cáo / POS
                </div>
                <p className="text-xs text-[#3B3F46] mt-0.5">
                  Chọn nền tảng để mở biểu mẫu nhập Account ID, Pixel ID và Access Token thực tế của doanh nghiệp.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setNewPlatform('META_ADS');
                    setShowAddForm(true);
                    setShowPosForm(false);
                    setShowConnectorForm(false);
                  }}
                  className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5 text-[#1D4ED8]" />
                  <span>Meta Fanpage &amp; BM</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNewPlatform('TIKTOK_ADS');
                    setShowAddForm(true);
                    setShowPosForm(false);
                    setShowConnectorForm(false);
                  }}
                  className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5 text-[#121316]" />
                  <span>TikTok Shop BC</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNewPlatform('POS_SYSTEM');
                    setShowAddForm(true);
                    setShowPosForm(false);
                    setShowConnectorForm(false);
                  }}
                  className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5 text-[#15803D]" />
                  <span>Sapo / Pancake POS</span>
                </button>
              </div>
            </div>
          </div>

          {/* Form 1: Thêm tài khoản quảng cáo mới */}
          {showAddForm && (
            <form
              onSubmit={handleCreateAccount}
              className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-extrabold text-[#121316]">
                  Khai báo tài khoản quảng cáo hoặc nguồn POS mới
                </span>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="text-[#3B3F46] hover:text-[#121316]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Nền tảng
                  </label>
                  <select
                    value={newPlatform}
                    onChange={(e) => setNewPlatform(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] font-semibold outline-none"
                  >
                    <option value="META_ADS">Meta Ads (Facebook / Instagram)</option>
                    <option value="TIKTOK_ADS">TikTok Business Center</option>
                    <option value="GOOGLE_ADS">Google Ads MCC</option>
                    <option value="POS_SYSTEM">Phần mềm bán hàng (Sapo / Pancake)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Mã định danh tài khoản (Account ID)
                  </label>
                  <input
                    type="text"
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                    placeholder="VD: act_1084920194 hoặc adv_738291"
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold text-[#121316] outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Tên tài khoản &amp; Thẻ thanh toán
                  </label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="VD: BM Chính - Thẻ Visa VPBank 8821"
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Mã Pixel / Dataset theo dõi chuyển đổi
                  </label>
                  <input
                    type="text"
                    value={newPixel}
                    onChange={(e) => setNewPixel(e.target.value)}
                    placeholder="VD: px_88392019283"
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold text-[#121316] outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Hạn mức chi tiêu tối đa / ngày (VNĐ)
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={500000}
                    value={newCap}
                    onChange={(e) => setNewCap(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold tabular-nums text-[#121316] outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Gắn chạy cho chiến dịch
                  </label>
                  <select
                    value={newCampaignId}
                    onChange={(e) => setNewCampaignId(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] font-semibold outline-none"
                  >
                    <option value="">-- Tài khoản dự phòng (Chưa gắn) --</option>
                    {campaigns.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
                <input
                  type="password"
                  value={newToken}
                  onChange={(e) => setNewToken(e.target.value)}
                  placeholder="Access Token kết nối Meta Graph API v19.0 / TikTok API trực tiếp (VD: EAABsb...)"
                  className="flex-1 px-3 py-1.5 text-xs bg-white border border-[#D0CEC7] rounded-lg text-[#121316] outline-none"
                />
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="px-3 py-1.5 text-xs font-semibold text-[#3B3F46] hover:text-[#121316]"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={savingAccount}
                    className="px-4 py-1.5 bg-[#121316] hover:bg-[#26282D] text-white text-xs font-bold rounded-lg"
                  >
                    {savingAccount ? 'Đang lưu...' : 'Lưu tài khoản quảng cáo'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Form 2: Ghi nhận đơn hàng thật từ POS / Website qua mã UTM */}
          {showPosForm && (
            <form
              onSubmit={handleRecordPosOrder}
              className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-extrabold text-[#121316]">
                    Đẩy đơn hàng chốt thành công từ POS (Sapo / Pancake / Website) vào Chiến dịch
                  </span>
                  <p className="text-xs text-[#3B3F46]">
                    Khi khách nhắn tin từ quảng cáo và chốt đơn trên POS, doanh thu và số đơn sẽ cộng thẳng vào chiến dịch để tính lại hệ số ROAS thực tế ngay lập tức.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowPosForm(false)}
                  className="text-[#3B3F46] hover:text-[#121316]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
                <div className="lg:col-span-2">
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Chiến dịch nhận đơn (Khớp theo mã utm_campaign)
                  </label>
                  <select
                    value={posCampaignId}
                    onChange={(e) => setPosCampaignId(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] font-semibold outline-none"
                  >
                    {campaigns.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Kênh quảng cáo dẫn khách
                  </label>
                  <select
                    value={posChannelId}
                    onChange={(e) => setPosChannelId(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] font-semibold outline-none"
                  >
                    <option value="1">Facebook Ads</option>
                    <option value="5">TikTok Ads</option>
                    <option value="4">Google Ads</option>
                    <option value="2">Zalo OA / Email / CRM</option>
                    <option value="3">Website / Blog SEO</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Số đơn chốt mới
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={posOrderCount}
                    onChange={(e) => setPosOrderCount(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold tabular-nums text-[#121316] outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                    Doanh thu thực thu (VNĐ)
                  </label>
                  <input
                    type="number"
                    min={1000}
                    step={50000}
                    value={posOrderValue}
                    onChange={(e) => setPosOrderValue(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold tabular-nums text-[#121316] outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-[#3B3F46] font-semibold">Chi phí quảng cáo phát sinh thêm (VNĐ):</span>
                  <input
                    type="number"
                    min={0}
                    step={50000}
                    value={posAdSpend}
                    onChange={(e) => setPosAdSpend(e.target.value)}
                    className="w-36 px-2.5 py-1 bg-white border border-[#D0CEC7] rounded-lg font-bold tabular-nums text-[#121316] outline-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowPosForm(false)}
                    className="px-3 py-1.5 text-xs font-semibold text-[#3B3F46] hover:text-[#121316]"
                  >
                    Đóng
                  </button>
                  <button
                    type="submit"
                    disabled={savingPosOrder}
                    className="px-4 py-1.5 bg-[#15803D] hover:bg-[#166534] text-white text-xs font-bold rounded-lg"
                  >
                    {savingPosOrder ? 'Đang cộng số liệu...' : 'Cộng đơn hàng & Cập nhật ROAS'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Bảng danh sách tài khoản quảng cáo & POS */}
          {loading ? (
            <div className="py-8 text-center text-xs text-[#3B3F46] flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Đang tải danh sách tài khoản quảng cáo...</span>
            </div>
          ) : accounts.length === 0 ? (
            <div className="py-8 text-center bg-[#F6F5F0] rounded-xl border border-[#E4E2DD] p-4 space-y-2">
              <div className="text-sm font-extrabold text-[#121316]">
                Chưa có tài khoản quảng cáo nào được khai báo trong không gian làm việc này
              </div>
              <p className="text-xs text-[#3B3F46]">
                Hãy bấm &ldquo;Thêm tài khoản QC&rdquo; ở trên để gắn tài khoản quảng cáo hoặc nguồn POS thực tế của doanh nghiệp.
              </p>
            </div>
          ) : (
            <div className="w-full">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[#E4E2DD] text-xs font-extrabold uppercase text-[#3B3F46] bg-[#F6F5F0]/70">
                    <th className="py-3 px-2.5 w-[26%]">Tài khoản &amp; Nền tảng</th>
                    <th className="py-3 px-2.5 w-[19%]">Chiến dịch đang gắn</th>
                    <th className="py-3 px-2.5 text-right w-[14%]">Hạn mức ngày</th>
                    <th className="py-3 px-2.5 text-right w-[12%]">Tổng đã chi</th>
                    <th className="py-3 px-2.5 text-right w-[15%]">Doanh thu &amp; Đơn</th>
                    <th className="py-3 px-2.5 w-[9%]">Trạng thái</th>
                    <th className="py-3 px-2.5 text-right w-[5%]">Xóa</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0EFEA]">
                  {accounts.map((acc) => {
                    const st = STATUS_LABELS[acc.status] || STATUS_LABELS.ACTIVE;
                    return (
                      <tr key={acc.id} className="hover:bg-[#F6F5F0]/40 transition-colors">
                        <td className="py-3 px-2.5">
                          <div className="flex items-start gap-2">
                            <CreditCard className="w-4 h-4 text-[#3B3F46] shrink-0 mt-0.5" />
                            <div className="min-w-0">
                              <div className="font-bold text-sm text-[#121316] leading-snug">{acc.account_name}</div>
                              <div className="text-xs text-[#3B3F46] flex flex-wrap items-center gap-1.5 mt-1">
                                <span className="font-bold text-[#121316] bg-[#F6F5F0] px-1.5 py-0.5 rounded border border-[#E4E2DD]">
                                  {acc.account_code}
                                </span>
                                <span className="font-semibold">{PLATFORM_LABELS[acc.platform] || acc.platform}</span>
                                {acc.pixel_id && (
                                  <span className="text-xs text-[#3B3F46]">
                                    · Pixel: {acc.pixel_id}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="py-3 px-2.5">
                          <div className="flex items-center gap-1.5">
                            <Link2 className="w-3.5 h-3.5 text-[#3B3F46] shrink-0" />
                            <select
                              value={acc.linked_campaign_id || ''}
                              onChange={(e) => handleChangeCampaignLink(acc, e.target.value)}
                              className="w-full bg-white border border-[#D0CEC7] rounded-lg px-2 py-1 text-xs font-semibold text-[#121316] truncate outline-none"
                            >
                              <option value="">-- Dự phòng (Chưa gắn) --</option>
                              {campaigns.map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        </td>

                        <td className="py-3 px-2.5 text-right tabular-nums">
                          <div className="font-bold text-[#121316]">
                            {acc.daily_spend_cap > 0 ? `${formatNumber(acc.daily_spend_cap)} đ` : 'Không giới hạn'}
                          </div>
                          {acc.platform !== 'POS_SYSTEM' && (
                            <button
                              type="button"
                              disabled={pushingAccountId === acc.id}
                              onClick={() => handlePushTwoWayBudget(acc)}
                              className="mt-1 inline-flex items-center gap-1 text-[11px] font-bold text-[#D95D39] hover:text-[#121316] cursor-pointer"
                              title="Đẩy lệnh tăng 20% trần chi tiêu ngày từ MarketFlow lên nền tảng quảng cáo"
                            >
                              {pushingAccountId === acc.id ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <Sliders className="w-3 h-3" />
                              )}
                              <span>Tăng hạn mức +20%</span>
                            </button>
                          )}
                        </td>

                        <td className="py-3 px-2.5 text-right font-extrabold text-sm text-[#121316] tabular-nums">
                          {formatNumber(acc.today_spend)} đ
                        </td>

                        <td className="py-3 px-2.5 text-right tabular-nums">
                          <div className="font-extrabold text-sm text-[#15803D]">
                            {formatNumber(acc.total_revenue)} đ
                          </div>
                          <div className="text-xs font-semibold text-[#3B3F46]">
                            {acc.total_orders} đơn · ROAS {acc.roas}x
                          </div>
                        </td>

                        <td className="py-3 px-2.5">
                          <div className="flex flex-col gap-1">
                            <select
                              value={acc.status}
                              onChange={(e) => handleToggleAccountStatus(acc, e.target.value)}
                              className={`text-xs font-bold px-2 py-1 rounded-lg outline-none cursor-pointer ${st.badgeClass}`}
                            >
                              <option value="ACTIVE">Đang chạy</option>
                              <option value="SPEND_WARNING">Sắp chạm trần</option>
                              <option value="RESTRICTED">Bị hạn chế</option>
                            </select>
                            {acc.status === 'RESTRICTED' && acc.linked_campaign_id && (
                              <button
                                type="button"
                                onClick={() => handleSwitchToBackupAccount(acc)}
                                className="inline-flex items-center justify-center gap-1 px-2 py-1 bg-[#D95D39] hover:bg-[#C04E2C] text-white font-bold text-xs rounded-lg"
                                title="Chuyển chiến dịch đang chạy sang tài khoản dự phòng"
                              >
                                <ArrowRightLeft className="w-3 h-3" />
                                <span>Đổi TK dự phòng</span>
                              </button>
                            )}
                          </div>
                        </td>

                        <td className="py-3 px-2.5 text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteAccount(acc)}
                            className="p-1.5 text-[#3B3F46] hover:text-[#BE123C] rounded-lg hover:bg-[#FFF1F2]"
                            title="Gỡ tài khoản này"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* KHỐI 2: CHIẾN DỊCH KOL/KOC AFFILIATE & BỘ TÍNH ĐIỂM HÒA VỐN TIKTOK SHOP / SHOPEE */}
      {(activeModuleTab === 'ALL' || activeModuleTab === 'KOL_PNL') && (
        <div className="space-y-6">
          {/* BỘ TÍNH ĐIỂM HÒA VỐN & LỢI NHUẬN RÒNG SÀN TMĐT VIỆT NAM (CHỐNG BẪY DOANH THU ẢO GMV) */}
          <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-[#E4E2DD] pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <Calculator className="w-4 h-4 text-[#D95D39]" />
                  <h3 className="text-base font-extrabold text-[#121316] tracking-tight">
                    Bộ Tính Điểm Hòa Vốn (Break-Even ROAS) &amp; Lợi Nhuận Ròng TikTok Shop / Shopee / Livestream
                  </h3>
                </div>
                <p className="text-xs text-[#3B3F46] mt-1">
                  Giải quyết nỗi đau lớn nhất của nhà bán hàng Việt Nam: &ldquo;Báo cáo Ads nhảy ROAS 3.0x tưởng lãi đậm, nhưng cuối tháng đối soát LỖ NẶNG vì Phí sàn 12.5%, Hoa hồng KOC 10%, Giá vốn và Bom hàng COD 14%&rdquo;.
                </p>
              </div>
              <button
                type="button"
                disabled={calculatingPnl}
                onClick={() => handleCalculatePnl()}
                className="inline-flex items-center gap-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-colors cursor-pointer shrink-0"
              >
                {calculatingPnl ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Calculator className="w-3.5 h-3.5 text-[#FDE68A]" />}
                <span>Tính lại Điểm Hòa Vốn &amp; Lãi Ròng</span>
              </button>
            </div>

            <form onSubmit={handleCalculatePnl} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-2.5">
                <label className="block font-bold text-[#3B3F46] mb-1">Giá bán TB đơn (AOV)</label>
                <input
                  type="number"
                  value={pnlSellingPrice}
                  onChange={(e) => setPnlSellingPrice(e.target.value)}
                  className="w-full bg-white border border-[#D0CEC7] rounded-lg px-2 py-1.5 font-extrabold text-[#121316] tabular-nums outline-none"
                />
              </div>
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-2.5">
                <label className="block font-bold text-[#3B3F46] mb-1">Giá vốn + Hộp (VNĐ)</label>
                <input
                  type="number"
                  value={pnlCogs}
                  onChange={(e) => setPnlCogs(e.target.value)}
                  className="w-full bg-white border border-[#D0CEC7] rounded-lg px-2 py-1.5 font-extrabold text-[#121316] tabular-nums outline-none"
                />
              </div>
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-2.5">
                <label className="block font-bold text-[#3B3F46] mb-1">Phí sàn TikTok/Shopee (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={pnlPlatformFee}
                  onChange={(e) => setPnlPlatformFee(e.target.value)}
                  className="w-full bg-white border border-[#D0CEC7] rounded-lg px-2 py-1.5 font-extrabold text-[#121316] tabular-nums outline-none"
                />
              </div>
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-2.5">
                <label className="block font-bold text-[#3B3F46] mb-1">Hoa hồng KOC (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={pnlAffiliatePct}
                  onChange={(e) => setPnlAffiliatePct(e.target.value)}
                  className="w-full bg-white border border-[#D0CEC7] rounded-lg px-2 py-1.5 font-extrabold text-[#121316] tabular-nums outline-none"
                />
              </div>
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-2.5">
                <label className="block font-bold text-[#3B3F46] mb-1">Tỷ lệ hoàn / Bom COD (%)</label>
                <input
                  type="number"
                  step="1"
                  value={pnlReturnRate}
                  onChange={(e) => setPnlReturnRate(e.target.value)}
                  className="w-full bg-white border border-[#D0CEC7] rounded-lg px-2 py-1.5 font-extrabold text-[#BE123C] tabular-nums outline-none"
                />
              </div>
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-2.5">
                <label className="block font-bold text-[#3B3F46] mb-1">Phí ship đơn hoàn (VNĐ)</label>
                <input
                  type="number"
                  step="1000"
                  value={pnlReturnShipFee}
                  onChange={(e) => setPnlReturnShipFee(e.target.value)}
                  className="w-full bg-white border border-[#D0CEC7] rounded-lg px-2 py-1.5 font-extrabold text-[#121316] tabular-nums outline-none"
                />
              </div>
            </form>

            {pnlResult && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                    <div className="text-xs font-bold text-[#3B3F46]">ROAS Hòa Vốn Bắt Buộc</div>
                    <div className="text-xl font-extrabold text-[#D95D39] mt-1 tabular-nums">
                      {pnlResult.unit_economics.break_even_roas}x
                    </div>
                    <div className="text-xs text-[#3B3F46] mt-0.5">
                      ROAS hiện tại: <strong className="text-[#121316]">{pnlResult.unit_economics.actual_gross_roas}x</strong>
                    </div>
                  </div>

                  <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                    <div className="text-xs font-bold text-[#3B3F46]">CPA Tối Đa Cho Phép / Đơn</div>
                    <div className="text-xl font-extrabold text-[#121316] mt-1 tabular-nums">
                      {formatNumber(pnlResult.unit_economics.max_allowable_cpa)} đ
                    </div>
                    <div className="text-xs text-[#3B3F46] mt-0.5">
                      CPA thực tế: <strong className="text-[#121316]">{formatNumber(pnlResult.unit_economics.actual_cpa)} đ</strong>
                    </div>
                  </div>

                  <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                    <div className="text-xs font-bold text-[#3B3F46]">Phí Sàn + KOC + Bom COD</div>
                    <div className="text-xl font-extrabold text-[#B45309] mt-1 tabular-nums">
                      {formatNumber(
                        pnlResult.campaign_pnl.total_platform_fee +
                          pnlResult.campaign_pnl.total_affiliate_fee +
                          pnlResult.campaign_pnl.total_cod_and_ops_fee
                      )}{' '}
                      đ
                    </div>
                    <div className="text-xs text-[#3B3F46] mt-0.5">
                      {pnlResult.campaign_pnl.returned_cod_orders} đơn hoàn / {pnlResult.campaign_pnl.total_orders} tổng đơn
                    </div>
                  </div>

                  <div
                    className={`rounded-xl p-3.5 border ${
                      pnlResult.campaign_pnl.real_net_profit >= 0
                        ? 'bg-[#ECFDF5] border-[#A7F3D0]'
                        : 'bg-[#FFF1F2] border-[#FECDD3]'
                    }`}
                  >
                    <div className="text-xs font-bold text-[#3B3F46]">Lợi Nhuận Ròng Bỏ Túi Thực Tế</div>
                    <div
                      className={`text-xl font-extrabold mt-1 tabular-nums ${
                        pnlResult.campaign_pnl.real_net_profit >= 0 ? 'text-[#15803D]' : 'text-[#BE123C]'
                      }`}
                    >
                      {pnlResult.campaign_pnl.real_net_profit >= 0 ? '+' : ''}
                      {formatNumber(pnlResult.campaign_pnl.real_net_profit)} đ
                    </div>
                    <div className="text-xs font-bold text-[#121316] mt-0.5">
                      Biên lãi ròng: {pnlResult.campaign_pnl.net_margin_pct}% sau mọi chi phí
                    </div>
                  </div>
                </div>

                <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5 flex flex-col lg:flex-row lg:items-center justify-between gap-2">
                  <div className="space-y-1">
                    <div className="text-xs font-extrabold text-[#121316] flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-[#D95D39] shrink-0" />
                      <span>{pnlResult.headline}</span>
                    </div>
                    {pnlResult.recommendations?.map((rec: string, i: number) => (
                      <div key={i} className="text-xs text-[#3B3F46]">
                        • {rec}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* BẢNG QUẢN LÝ KOL / KOC AFFILIATE */}
          <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-5">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#E4E2DD] pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-[#D95D39]" />
                  <h3 className="text-base font-extrabold text-[#121316] tracking-tight">
                    Chiến dịch thuê KOL / KOC &amp; Đối tác Affiliate bên thứ 3
                  </h3>
                </div>
                <p className="text-xs text-[#3B3F46] mt-1">
                  Theo dõi hợp đồng booking KOL/KOC ngoài (TikTok Shop Affiliate, Facebook Reels, YouTube), tách bạch phí cát-xê cố định + % hoa hồng trên đơn và đo lường hệ số Net ROAS thực tế.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowKolForm((prev) => !prev)}
                  className="inline-flex items-center gap-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Thêm hợp đồng KOL / KOC mới</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#3B3F46]">Tổng KOL / KOC đang chạy</div>
                <div className="text-xl font-extrabold text-[#121316] mt-1 tabular-nums">
                  {kolSummary.total_creators} Creator
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">Đo lường qua mã UTM &amp; Voucher riêng</div>
              </div>

              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#3B3F46]">Tổng Cát-xê + Hoa hồng</div>
                <div className="text-xl font-extrabold text-[#121316] mt-1 tabular-nums">
                  {formatNumber(kolSummary.total_cost)} đ
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">Đã gồm phí booking &amp; chiết khấu đơn</div>
              </div>

              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#3B3F46]">Doanh thu từ mã KOL / KOC</div>
                <div className="text-xl font-extrabold text-[#15803D] mt-1 tabular-nums">
                  {formatNumber(kolSummary.total_revenue)} đ
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">
                  {formatNumber(kolSummary.total_orders)} đơn chốt thành công
                </div>
              </div>

              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#3B3F46]">Hệ số Net KOL ROAS</div>
                <div className="text-xl font-extrabold text-[#D95D39] mt-1 tabular-nums">
                  {kolSummary.avg_roas}x
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">Doanh thu / (Cát-xê + Hoa hồng)</div>
              </div>
            </div>

            {showKolForm && (
              <form
                onSubmit={handleCreateKolBooking}
                className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold text-[#121316]">
                    Khai báo hợp đồng thuê KOL / KOC hoặc đối tác Affiliate mới
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowKolForm(false)}
                    className="text-[#3B3F46] hover:text-[#121316]"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  <div>
                    <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                      Tên KOL / KOC / Reviewer
                    </label>
                    <input
                      type="text"
                      value={kolName}
                      onChange={(e) => setKolName(e.target.value)}
                      placeholder="VD: Châu Muối Review"
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold text-[#121316] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                      Handle kênh (@username)
                    </label>
                    <input
                      type="text"
                      value={kolHandle}
                      onChange={(e) => setKolHandle(e.target.value)}
                      placeholder="VD: @chaumuoi.official"
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                      Nền tảng &amp; Phân khúc Follower
                    </label>
                    <div className="grid grid-cols-2 gap-1.5">
                      <select
                        value={kolPlatform}
                        onChange={(e) => setKolPlatform(e.target.value)}
                        className="w-full px-2 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] font-semibold outline-none"
                      >
                        <option value="TIKTOK">TikTok</option>
                        <option value="FACEBOOK">Facebook</option>
                        <option value="YOUTUBE">YouTube</option>
                      </select>
                      <input
                        type="text"
                        value={kolTier}
                        onChange={(e) => setKolTier(e.target.value)}
                        placeholder="KOC 120K Flw"
                        className="w-full px-2 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                      Mã Tracking / Voucher riêng
                    </label>
                    <input
                      type="text"
                      value={kolCode}
                      onChange={(e) => setKolCode(e.target.value)}
                      placeholder="Tự sinh nếu để trống (VD: KOC_CHAU_15)"
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold text-[#121316] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                      Cát-xê Booking cố định (VNĐ)
                    </label>
                    <input
                      type="number"
                      min={0}
                      step={500000}
                      value={kolCost}
                      onChange={(e) => setKolCost(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold tabular-nums text-[#121316] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                      Hoa hồng Affiliate (% doanh thu)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={80}
                      step={1}
                      value={kolCommission}
                      onChange={(e) => setKolCommission(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold tabular-nums text-[#121316] outline-none"
                    />
                  </div>

                  <div className="lg:col-span-2">
                    <label className="block text-xs font-bold text-[#3B3F46] mb-1">
                      Chiến dịch nhận số liệu chuyển đổi
                    </label>
                    <select
                      value={kolCampaignId}
                      onChange={(e) => setKolCampaignId(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] font-semibold outline-none"
                    >
                      {campaigns.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowKolForm(false)}
                    className="px-3 py-1.5 text-xs font-semibold text-[#3B3F46] hover:text-[#121316]"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={savingKol}
                    className="px-4 py-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold rounded-lg"
                  >
                    {savingKol ? 'Đang tạo mã...' : 'Lưu hợp đồng & Sinh link Bio UTM'}
                  </button>
                </div>
              </form>
            )}

            <div className="w-full">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[#E4E2DD] text-xs font-extrabold uppercase text-[#3B3F46] bg-[#F6F5F0]/70">
                    <th className="py-3 px-2.5 w-[24%]">KOL / KOC &amp; Chiến dịch</th>
                    <th className="py-3 px-2.5 w-[18%]">Mã Voucher / Link Bio</th>
                    <th className="py-3 px-2.5 text-right w-[16%]">Cát-xê + Hoa hồng</th>
                    <th className="py-3 px-2.5 text-right w-[13%]">Lượt xem &amp; Nhấp</th>
                    <th className="py-3 px-2.5 text-right w-[15%]">Đơn chốt &amp; Doanh thu</th>
                    <th className="py-3 px-2.5 text-right w-[14%]">Net ROAS &amp; Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0EFEA]">
                  {kolBookings.map((kol) => (
                    <tr key={kol.id} className="hover:bg-[#F6F5F0]/40 transition-colors">
                      <td className="py-3 px-2.5">
                        <div className="font-bold text-sm text-[#121316]">{kol.creator_name}</div>
                        <div className="text-xs text-[#3B3F46] flex flex-wrap items-center gap-1.5 mt-0.5">
                          <span className="font-semibold text-[#121316]">{kol.handle}</span>
                          <span>· {kol.platform}</span>
                          <span>· {kol.followers_tier}</span>
                        </div>
                        {kol.campaign_name && (
                          <div className="text-xs font-semibold text-[#3B3F46] mt-0.5 truncate">
                            Chiến dịch: {kol.campaign_name}
                          </div>
                        )}
                      </td>

                      <td className="py-3 px-2.5">
                        <div className="inline-flex items-center gap-1.5 bg-[#F6F5F0] border border-[#D0CEC7] px-2 py-0.5 rounded font-bold text-[#121316]">
                          <span>{kol.tracking_code}</span>
                        </div>
                        <div className="mt-1">
                          <button
                            type="button"
                            onClick={() => handleCopyKolLink(kol)}
                            className="inline-flex items-center gap-1 text-xs font-bold text-[#1D4ED8] hover:underline cursor-pointer"
                          >
                            {copiedKolCode === kol.tracking_code ? (
                              <Check className="w-3 h-3 text-[#15803D]" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                            <span>{copiedKolCode === kol.tracking_code ? 'Đã chép link Bio' : 'Chép link Bio UTM'}</span>
                          </button>
                        </div>
                      </td>

                      <td className="py-3 px-2.5 text-right tabular-nums">
                        <div className="font-extrabold text-sm text-[#121316]">
                          {formatNumber(kol.total_cost)} đ
                        </div>
                        <div className="text-xs text-[#3B3F46]">
                          Cát-xê {formatNumber(kol.booking_cost)} đ + {kol.commission_pct}% HH
                        </div>
                      </td>

                      <td className="py-3 px-2.5 text-right tabular-nums">
                        <div className="font-bold text-[#121316]">{formatNumber(kol.views_count)} views</div>
                        <div className="text-xs text-[#3B3F46]">{formatNumber(kol.clicks_count)} nhấp link</div>
                      </td>

                      <td className="py-3 px-2.5 text-right tabular-nums">
                        <div className="font-extrabold text-sm text-[#15803D]">
                          {formatNumber(kol.revenue_generated)} đ
                        </div>
                        <div className="text-xs font-semibold text-[#3B3F46]">
                          {kol.orders_count} đơn · CPA {formatNumber(kol.cpa)} đ
                        </div>
                      </td>

                      <td className="py-3 px-2.5 text-right tabular-nums">
                        <div className="flex items-center justify-end gap-1.5">
                          <span
                            className={`inline-block px-2 py-0.5 rounded font-extrabold text-xs ${
                              kol.net_roas >= 3
                                ? 'bg-[#ECFDF5] text-[#15803D] border border-[#A7F3D0]'
                                : 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]'
                            }`}
                          >
                            ROAS {kol.net_roas}x
                          </span>
                          <button
                            type="button"
                            onClick={() => handleDeleteKol(kol)}
                            className="p-1 text-[#3B3F46] hover:text-[#BE123C] rounded"
                            title="Xóa hợp đồng KOL/KOC"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {isOfflineDemoEnabled() && (
                          <div className="mt-1.5 flex justify-end">
                            <button
                              type="button"
                              disabled={recordingKolId === kol.id}
                              onClick={() => handleRecordKolOrder(kol)}
                              className="inline-flex items-center gap-1 bg-[#15803D] hover:bg-[#166534] text-white font-bold text-[11px] px-2 py-1 rounded-lg cursor-pointer"
                            >
                              {recordingKolId === kol.id ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <Plus className="w-3 h-3" />
                              )}
                              <span>+3 đơn Affiliate</span>
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* KHỐI 3: PHỄU CHỐT ĐƠN TIN NHẮN (ZALO ZNS / MESSENGER 24H) & LỊCH MÙA VỤ MEGA SALE VIỆT NAM */}
      {(activeModuleTab === 'ALL' || activeModuleTab === 'ZALO_MEGA') && (
        <div className="space-y-6">
          {/* PHỄU ZALO OA / ZNS & FACEBOOK CLICK-TO-MESSENGER LEAD CRM */}
          <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-5">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#E4E2DD] pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-[#D95D39]" />
                  <h3 className="text-base font-extrabold text-[#121316] tracking-tight">
                    Phễu Chốt Đơn Tin Nhắn (Zalo OA / ZNS &amp; Facebook Click-to-Messenger 24h Care)
                  </h3>
                </div>
                <p className="text-xs text-[#3B3F46] mt-1">
                  Giải quyết bài toán đặc thù tại Việt Nam: 75% ngân sách chạy Quảng cáo Tin nhắn nhưng rớt 80% khách sau khi báo giá và bị khóa Inbox sau 24 giờ của Meta. Tự động bắn Zalo ZNS nhắc lịch và 1-Click chốt đơn sang POS.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowLeadForm((prev) => !prev)}
                className="inline-flex items-center gap-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-colors cursor-pointer shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm Khách Hỏi Giá Inbox / Zalo</span>
              </button>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#3B3F46]">Tổng Khách Hỏi Giá (Leads)</div>
                <div className="text-xl font-extrabold text-[#121316] mt-1 tabular-nums">
                  {vnLeadsSummary.total_leads} Khách
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">Từ Messenger, Zalo OA &amp; Bio KOC</div>
              </div>
              <div className="bg-[#FFF1F2] border border-[#FECDD3] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#BE123C]">Cần Chăm Sóc Ngay (&lt;24h Meta)</div>
                <div className="text-xl font-extrabold text-[#BE123C] mt-1 tabular-nums">
                  {vnLeadsSummary.urgent_24h_count} Khách
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">Sắp đóng cửa sổ nhắn tin miễn phí</div>
              </div>
              <div className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#3B3F46]">Doanh Thu Chờ Chốt (Pipeline)</div>
                <div className="text-xl font-extrabold text-[#D95D39] mt-1 tabular-nums">
                  {formatNumber(vnLeadsSummary.open_pipeline_value)} đ
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">Đang chờ CK VietQR / Hẹn lương về</div>
              </div>
              <div className="bg-[#ECFDF5] border border-[#A7F3D0] rounded-xl p-3.5">
                <div className="text-xs font-bold text-[#15803D]">Đã Chốt Sang POS Thực Tế</div>
                <div className="text-xl font-extrabold text-[#15803D] mt-1 tabular-nums">
                  {formatNumber(vnLeadsSummary.closed_won_value)} đ
                </div>
                <div className="text-xs text-[#3B3F46] mt-0.5">Đã cộng vào ROAS Chiến dịch</div>
              </div>
            </div>

            {showLeadForm && (
              <form
                onSubmit={handleCreateLead}
                className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold text-[#121316]">
                    Ghi nhận khách hàng mới từ Inbox Fanpage / Zalo OA / TikTok Bio
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowLeadForm(false)}
                    className="text-[#3B3F46] hover:text-[#121316]"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
                  <div>
                    <label className="block font-bold text-[#3B3F46] mb-1">Tên khách hàng</label>
                    <input
                      type="text"
                      value={leadName}
                      onChange={(e) => setLeadName(e.target.value)}
                      placeholder="VD: Chị Lan Anh (Hà Nội)"
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold text-[#121316] outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-[#3B3F46] mb-1">Số điện thoại Zalo</label>
                    <input
                      type="text"
                      value={leadPhone}
                      onChange={(e) => setLeadPhone(e.target.value)}
                      placeholder="VD: 0987654321"
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold text-[#121316] outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-[#3B3F46] mb-1">Nguồn tin nhắn</label>
                    <select
                      value={leadSource}
                      onChange={(e) => setLeadSource(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-semibold text-[#121316] outline-none"
                    >
                      <option value="FB_MESSENGER">Facebook Click-to-Messenger</option>
                      <option value="ZALO_OA">Zalo Official Account (OA)</option>
                      <option value="TIKTOK_BIO">Link Bio TikTok / KOC</option>
                      <option value="LANDING_FORM">Ladipage / Website Form</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-bold text-[#3B3F46] mb-1">Sản phẩm quan tâm</label>
                    <input
                      type="text"
                      value={leadProduct}
                      onChange={(e) => setLeadProduct(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg text-[#121316] outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-[#3B3F46] mb-1">Giá trị đơn dự kiến (VNĐ)</label>
                    <input
                      type="number"
                      value={leadValue}
                      onChange={(e) => setLeadValue(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-bold tabular-nums text-[#121316] outline-none"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowLeadForm(false)}
                    className="px-3 py-1.5 text-xs font-semibold text-[#3B3F46]"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={savingLead}
                    className="px-4 py-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold rounded-lg cursor-pointer"
                  >
                    {savingLead ? 'Đang lưu...' : 'Lưu vào Phễu Chăm Sóc Zalo ZNS'}
                  </button>
                </div>
              </form>
            )}

            <div className="w-full">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[#E4E2DD] text-xs font-extrabold uppercase text-[#3B3F46] bg-[#F6F5F0]/70">
                    <th className="py-3 px-2.5 w-[24%]">Khách hàng &amp; SĐT Zalo</th>
                    <th className="py-3 px-2.5 w-[25%]">Sản phẩm &amp; Ghi chú Inbox</th>
                    <th className="py-3 px-2.5 w-[16%]">Trạng thái Phễu 24h</th>
                    <th className="py-3 px-2.5 text-right w-[13%]">Giá trị dự kiến</th>
                    <th className="py-3 px-2.5 text-right w-[22%]">Bắn Zalo ZNS &amp; Chốt Đơn POS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0EFEA]">
                  {vnLeads.map((ld) => {
                    const st = LEAD_STAGE_META[ld.lead_stage] || LEAD_STAGE_META.NEW_INBOX;
                    return (
                      <tr key={ld.id} className="hover:bg-[#F6F5F0]/40 transition-colors">
                        <td className="py-3 px-2.5">
                          <div className="font-bold text-sm text-[#121316]">{ld.customer_name}</div>
                          <div className="text-xs text-[#3B3F46] flex flex-wrap items-center gap-1.5 mt-0.5">
                            <span className="font-bold text-[#121316] bg-[#F6F5F0] px-1.5 py-0.5 rounded border border-[#D0CEC7]">
                              {ld.phone}
                            </span>
                            <span>· {ld.source_channel}</span>
                            <span>· ZNS đã gửi: {ld.zns_sent_count}</span>
                          </div>
                        </td>
                        <td className="py-3 px-2.5">
                          <div className="font-bold text-[#121316]">{ld.product_interest}</div>
                          <div className="text-xs text-[#3B3F46] mt-0.5 line-clamp-2">{ld.last_message_note}</div>
                        </td>
                        <td className="py-3 px-2.5">
                          <span className={`inline-block px-2 py-1 rounded-lg font-extrabold text-xs ${st.badge}`}>
                            {st.label}
                          </span>
                        </td>
                        <td className="py-3 px-2.5 text-right font-extrabold text-sm text-[#121316] tabular-nums">
                          {formatNumber(ld.estimated_value)} đ
                        </td>
                        <td className="py-3 px-2.5 text-right">
                          <div className="flex flex-wrap items-center justify-end gap-1.5">
                            <button
                              type="button"
                              disabled={processingLeadId === ld.id}
                              onClick={() => handleSendZnsLead(ld, 'REMIND_24H_META')}
                              className="inline-flex items-center gap-1 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] font-bold text-[11px] px-2 py-1 rounded-lg cursor-pointer"
                              title="Bắn tin nhắn Zalo ZNS giữ ưu đãi trước khi hết 24h của Meta"
                            >
                              <Send className="w-3 h-3 text-[#D95D39]" />
                              <span>Bắn Zalo ZNS</span>
                            </button>
                            {ld.lead_stage !== 'CLOSED_POS' && (
                              <button
                                type="button"
                                disabled={processingLeadId === ld.id}
                                onClick={() => handleCloseLeadToOrder(ld)}
                                className="inline-flex items-center gap-1 bg-[#15803D] hover:bg-[#166534] text-white font-bold text-[11px] px-2 py-1 rounded-lg cursor-pointer"
                                title="Chốt đơn thành công và cộng doanh thu thẳng vào Chiến dịch"
                              >
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Chốt đơn POS</span>
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleDeleteLead(ld)}
                              className="p-1 text-[#3B3F46] hover:text-[#BE123C]"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* LỊCH MÙA VỤ & KHUNG GIỜ VÀNG MEGA SALE ĐẶC THÙ VIỆT NAM */}
          <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-[#E4E2DD] pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-[#D95D39]" />
                  <h3 className="text-base font-extrabold text-[#121316] tracking-tight">
                    1-Click Kịch Bản Mùa Vụ &amp; Khung Giờ Vàng Mega Sale Việt Nam
                  </h3>
                </div>
                <p className="text-xs text-[#3B3F46] mt-1">
                  Tự động tạo bộ đầu việc chuẩn Khung Giờ Vàng (0h-2h, 12h-13h, 20h-24h) và tái phân bổ ngân sách kênh cho chiến dịch đang chọn.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                {
                  code: 'DOUBLE_DAY',
                  title: 'Siêu Sale Ngày Đôi (10/10, 11/11, 12/12)',
                  hours: 'Khung Giờ Vàng: 00:00-02:00 · 12:00-13:00 · 20:00-23:59',
                  desc: 'Tối ưu Teasing Bỏ Giỏ Hàng D-3 & Bơm trần Ads vào 2 tiếng đầu mở màn.',
                },
                {
                  code: 'PAYDAY_15_25',
                  title: 'Sale Lương Về (Mùng 15 & 25 Hàng Tháng)',
                  hours: 'Khung Giờ Vàng: 11:30-13:30 · 20:30-22:30',
                  desc: 'Đánh trúng tâm lý dân văn phòng vừa nhận lương, đẩy mạnh Click-to-Messenger & Zalo ZNS.',
                },
                {
                  code: 'MEGA_LIVESTREAM',
                  title: 'Chiến Dịch Mega Livestream TikTok Shop',
                  hours: 'Khung Giờ Vàng: 19:30 Warm-up · 20:00-22:30 Tung Deal',
                  desc: 'Phối hợp KOC cắt clip ngắn dẫn lịch hẹn Live và gọi/ZNS xác nhận đơn COD sáng hôm sau.',
                },
                {
                  code: 'TET_HOLIDAY',
                  title: 'Chiến Dịch Tết Nguyên Đán & Quà Biếu',
                  hours: 'Khung Giờ Vàng: 09:00-11:00 (B2B) · 20:00-22:30 (Gia đình)',
                  desc: 'Kịch bản Hộp Quà Tết doanh nghiệp & chốt chặn đơn COD đi tỉnh trước 23 tháng Chạp.',
                },
              ].map((bp) => (
                <div
                  key={bp.code}
                  className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-4 flex flex-col justify-between gap-3"
                >
                  <div className="space-y-1.5">
                    <div className="font-extrabold text-sm text-[#121316]">{bp.title}</div>
                    <div className="text-xs font-bold text-[#D95D39]">{bp.hours}</div>
                    <p className="text-xs text-[#3B3F46] leading-relaxed">{bp.desc}</p>
                  </div>
                  <button
                    type="button"
                    disabled={applyingBlueprint !== null}
                    onClick={() => handleApplyMegaSaleBlueprint(bp.code, bp.title)}
                    className="w-full inline-flex items-center justify-center gap-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-bold py-2 px-3 rounded-lg transition-colors cursor-pointer"
                  >
                    {applyingBlueprint === bp.code ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5 text-[#FDE68A]" />
                    )}
                    <span>Áp dụng vào Chiến dịch</span>
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* KHỐI 4: GÓI CƯỚC SAAS (FREE / PRO / AGENCY) & THANH TOÁN TỰ ĐỘNG VIETQR NAPAS 247 + SEPAY */}
      {(activeModuleTab === 'ALL' || activeModuleTab === 'SAAS_BILLING') && (
        <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#E4E2DD] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <QrCode className="w-4 h-4 text-[#D95D39]" />
                <h3 className="text-base font-extrabold text-[#121316] tracking-tight">
                  Gói Cước SaaS &amp; Cổng Thanh Toán Tự Động VietQR Napas 247 (SePay / PayOS Webhook)
                </h3>
              </div>
              <p className="text-xs text-[#3B3F46] mt-1">
                Thu tiền tự động từ khách hàng SME &amp; Agency tại Việt Nam: Quét mã QR chuyển khoản ngân hàng nhận diện theo cú pháp <code className="font-bold text-[#121316]">MARKETFLOW WS{workspaceId || 1} PRO</code>, tự động mở khóa trần hạn mức AI Jobs, Chiến dịch &amp; Thành viên ngay lập tức!
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-xs font-extrabold text-[#15803D]">
                Gói hiện tại: {currentPlanTier}
              </span>
            </div>
          </div>

          {/* Thanh hiển thị Hạn mức Quota thực tế đang mở khóa */}
          {billingData?.quota_snapshot?.limits && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
              {billingData.quota_snapshot.limits.map((lim: any) => (
                <div
                  key={lim.limit_code}
                  className="bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3"
                >
                  <div className="text-[11px] font-bold text-[#3B3F46] capitalize">{lim.label}</div>
                  <div className="text-base font-extrabold text-[#121316] mt-1 tabular-nums">
                    {lim.used} / {lim.limit}
                  </div>
                  <div className="text-[11px] text-[#15803D] font-semibold mt-0.5">
                    Còn {lim.remaining} lượt
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 3 Gói Cước + Mã VietQR trực quan */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-3 gap-3">
              {(billingData?.catalog || []).map((plan: any) => {
                const isCurrent = currentPlanTier === plan.tier;
                return (
                  <div
                    key={plan.tier}
                    className={`rounded-xl p-4 border flex flex-col justify-between gap-4 ${
                      isCurrent
                        ? 'bg-[#F6F5F0] border-[#121316] ring-1 ring-[#121316]'
                        : 'bg-white border-[#E4E2DD]'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-extrabold uppercase tracking-wider text-[#D95D39]">
                          {plan.badge}
                        </span>
                        {isCurrent && (
                          <span className="text-[11px] font-extrabold bg-[#121316] text-white px-2 py-0.5 rounded">
                            Đang dùng
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-extrabold text-[#121316]">{plan.name}</div>
                      <div className="text-xl font-extrabold text-[#121316] tabular-nums">
                        {plan.monthly_price_vnd === 0
                          ? '0 đ / tháng'
                          : `${formatNumber(plan.monthly_price_vnd)} đ / tháng`}
                      </div>
                      <ul className="space-y-1.5 pt-2 border-t border-[#E4E2DD] text-xs text-[#3B3F46]">
                        {(plan.highlights || []).map((h: string, idx: number) => (
                          <li key={idx} className="flex items-start gap-1.5">
                            <Check className="w-3.5 h-3.5 text-[#15803D] shrink-0 mt-0.5" />
                            <span>{h}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <button
                      type="button"
                      disabled={isCurrent || upgradingTier !== null}
                      onClick={() => handleUpgradeBilling(plan.tier)}
                      className={`w-full py-2 px-3 rounded-lg text-xs font-extrabold transition-colors cursor-pointer ${
                        isCurrent
                          ? 'bg-[#E4E2DD] text-[#3B3F46] cursor-default'
                          : 'bg-[#121316] hover:bg-[#D95D39] text-white'
                      }`}
                    >
                      {isCurrent
                        ? 'Gói đang kích hoạt'
                        : upgradingTier === plan.tier
                        ? 'Đang mở khóa...'
                        : `Kích hoạt gói ${plan.tier}`}
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Cột Mã QR Chuyển Khoản VietQR Napas 247 & Đối Soát Tự Động */}
            <div className="lg:col-span-4 bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-4 flex flex-col justify-between gap-3">
              <div className="space-y-2">
                <div className="text-xs font-extrabold text-[#121316] flex items-center justify-between">
                  <span>Quét Mã VietQR Napas 247 Tự Động</span>
                  <span className="text-[#15803D]">Tức thì 24/7</span>
                </div>
                {billingData?.vietqr && (
                  <div className="bg-white border border-[#D0CEC7] rounded-xl p-3 flex flex-col items-center text-center gap-2">
                    <img
                      src={billingData.vietqr.pro_qr_url}
                      alt="VietQR Napas 247 MarketFlow"
                      className="w-40 h-40 object-contain rounded-lg border border-[#E4E2DD]"
                    />
                    <div className="text-xs font-extrabold text-[#121316]">
                      {billingData.vietqr.bank_name}
                    </div>
                    <div className="text-xs text-[#3B3F46]">
                      STK: <strong className="text-[#121316]">{billingData.vietqr.account_number}</strong> · Nội dung:{' '}
                      <code className="font-extrabold text-[#D95D39]">{billingData.vietqr.pro_memo}</code>
                    </div>
                  </div>
                )}
              </div>

              {isOfflineDemoEnabled() && (
                <div className="space-y-2">
                  <button
                    type="button"
                    disabled={upgradingTier !== null}
                    onClick={() => handleSimulateSePayTransfer('PRO')}
                    className="w-full inline-flex items-center justify-center gap-1.5 bg-[#15803D] hover:bg-[#166534] text-white text-xs font-extrabold py-2 px-3 rounded-lg transition-colors cursor-pointer"
                  >
                    {upgradingTier === 'SEPAY_PRO' ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5 text-[#FDE68A]" />
                    )}
                    <span>Test Webhook Ngân Hàng (+499k Mở Khóa PRO)</span>
                  </button>
                  <button
                    type="button"
                    disabled={upgradingTier !== null}
                    onClick={() => handleSimulateSePayTransfer('AGENCY')}
                    className="w-full inline-flex items-center justify-center gap-1.5 bg-[#121316] hover:bg-[#D95D39] text-white text-xs font-extrabold py-2 px-3 rounded-lg transition-colors cursor-pointer"
                  >
                    {upgradingTier === 'SEPAY_AGENCY' ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-[#FDE68A]" />
                    )}
                    <span>Test Webhook Ngân Hàng (+1,49tr Mở Khóa AGENCY)</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
