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
} from 'lucide-react';
import {
  adAccountsApi,
  AdAccountItem,
  kolBookingsApi,
  KolBookingItem,
  campaignApi,
  getApiErrorMessage,
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

export const AdAccountsHub: React.FC<AdAccountsHubProps> = ({ workspaceId, onSynced }) => {
  const toast = useToast();
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
  const [connectingOAuth, setConnectingOAuth] = useState<string | null>(null);
  const [pushingAccountId, setPushingAccountId] = useState<number | null>(null);
  const [recordingKolId, setRecordingKolId] = useState<number | null>(null);
  const [firingWebhook, setFiringWebhook] = useState<boolean>(false);
  const [copiedCurl, setCopiedCurl] = useState<boolean>(false);
  const [copiedKolCode, setCopiedKolCode] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [showPosForm, setShowPosForm] = useState<boolean>(false);
  const [showKolForm, setShowKolForm] = useState<boolean>(false);

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

  const loadHubData = useCallback(async () => {
    setLoading(true);
    try {
      const [accRes, kolRes, campList] = await Promise.all([
        adAccountsApi.list(workspaceId),
        kolBookingsApi.list(workspaceId).catch(() => ({
          items: [],
          workspace_id: workspaceId || 1,
          summary: { total_creators: 0, total_cost: 0, total_revenue: 0, total_orders: 0, avg_roas: 0 },
        })),
        campaignApi.getAll(undefined, undefined, workspaceId),
      ]);
      setAccounts(accRes.items || []);
      setKolBookings(kolRes.items || []);
      if (kolRes.summary) setKolSummary(kolRes.summary);
      setCampaigns(campList || []);
      if (campList.length > 0 && !posCampaignId) {
        const firstId = String(campList[0].id);
        setPosCampaignId(firstId);
        setNewCampaignId(firstId);
        setKolCampaignId(firstId);
      }
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
      toast.success(
        `${pubMsg}Cộng +${res.kol_orders_added} đơn Affiliate KOL (+${formatNumber(res.kol_revenue_added)} đ) và đồng bộ ${res.synced_accounts_count} tài khoản QC.`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể chạy tiến trình Auto-Publish & Đồng bộ tự động');
    } finally {
      setRunningWorker(false);
    }
  };

  const handleOAuthQuickConnect = async (provider: string, label: string) => {
    if (connectingOAuth) return;
    setConnectingOAuth(provider);
    try {
      const targetCampId = posCampaignId ? Number(posCampaignId) : campaigns[0]?.id;
      const res = await adAccountsApi.quickConnectOAuth({
        provider,
        campaign_id: targetCampId,
        workspace_id: workspaceId,
      });
      toast.success(
        `Đã kết nối OAuth2 1-Click: ${res.account.account_name} (${res.account.account_code}).`
      );
      await loadHubData();
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), `Không thể kết nối nhanh ${label}`);
    } finally {
      setConnectingOAuth(null);
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
        `Đồng bộ 2 chiều (${res.account_code}): Đã đẩy trần ngân sách ngày mới ${formatNumber(res.daily_spend_cap)} đ lên nền tảng & chiến dịch "${res.linked_campaign_name || 'Đang gắn'}".`
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

  const handleCopyWebhookCurl = async () => {
    const curlCmd = `curl -X POST "${webhookEndpointUrl}" -H "Content-Type: application/json" -d '{"utm_campaign":"${activeCampCode}","utm_source":"tiktok","koc_code":"${activeKolCode}","order_count":2,"order_value":1850000,"ad_spend_delta":320000,"source_app":"Sapo POS + Affiliate Live"}'`;
    try {
      await navigator.clipboard.writeText(curlCmd);
      setCopiedCurl(true);
      toast.success('Đã sao chép lệnh Webhook (cURL / Sapo / Pancake / Mã KOC) vào bộ nhớ tạm.');
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

  return (
    <div className="space-y-6">
      {/* KHỐI 1: TÀI KHOẢN QUẢNG CÁO, AUTO-PUBLISH FANPAGE & ĐỒNG BỘ 2 CHIỀU */}
      <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-5">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#E4E2DD] pb-4">
          <div>
            <h3 className="text-base font-extrabold text-[#121316] tracking-tight">
              Tài khoản quảng cáo, Tự động đăng bài Fanpage &amp; Đồng bộ 2 chiều
            </h3>
            <p className="text-xs text-[#3B3F46] mt-1">
              Kết nối OAuth2 1-Click với Meta Business / Fanpage / TikTok Shop / Sapo POS, đẩy trần ngân sách 2 chiều và tự động xuất bản các bài viết đã duyệt theo lịch.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => {
                setShowPosForm((prev) => !prev);
                setShowAddForm(false);
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
              }}
              className="inline-flex items-center gap-1.5 bg-white hover:bg-[#F6F5F0] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3 py-2 rounded-xl transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 text-[#121316]" />
              <span>Thêm tài khoản QC</span>
            </button>

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
                Tự động nhận đơn từ Sapo POS, Pancake CRM, Ladipage hoặc mã voucher KOL/KOC (truyền <code className="font-bold text-[#121316]">utm_campaign</code> hoặc <code className="font-bold text-[#121316]">koc_code</code>).
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleCopyWebhookCurl}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
              >
                {copiedCurl ? <Check className="w-3.5 h-3.5 text-[#15803D]" /> : <Copy className="w-3.5 h-3.5 text-[#3B3F46]" />}
                <span>{copiedCurl ? 'Đã chép lệnh cURL' : 'Chép lệnh cURL mẫu'}</span>
              </button>

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
            </div>
          </div>

          <div className="lg:col-span-5 bg-[#F6F5F0] border border-[#E4E2DD] rounded-xl p-3.5 flex flex-col justify-between gap-2.5">
            <div>
              <div className="text-xs font-extrabold text-[#121316]">
                Kết nối nhanh OAuth2 (1-Click Quick-Connect)
              </div>
              <p className="text-xs text-[#3B3F46] mt-0.5">
                Ủy quyền tự động đăng bài Fanpage, đồng bộ TikTok Shop BC hoặc gắn Sapo POS không cần nhập Token thủ công.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={connectingOAuth !== null}
                onClick={() => handleOAuthQuickConnect('META_FANPAGE_BM', 'Meta Fanpage & BM')}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
              >
                {connectingOAuth === 'META_FANPAGE_BM' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5 text-[#1D4ED8]" />}
                <span>Meta Fanpage &amp; BM</span>
              </button>
              <button
                type="button"
                disabled={connectingOAuth !== null}
                onClick={() => handleOAuthQuickConnect('TIKTOK_SHOP_BC', 'TikTok Shop BC')}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
              >
                {connectingOAuth === 'TIKTOK_SHOP_BC' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5 text-[#121316]" />}
                <span>TikTok Shop BC</span>
              </button>
              <button
                type="button"
                disabled={connectingOAuth !== null}
                onClick={() => handleOAuthQuickConnect('SAPO_POS_LIVE', 'Sapo POS')}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] text-xs font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
              >
                {connectingOAuth === 'SAPO_POS_LIVE' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5 text-[#15803D]" />}
                <span>Sapo POS Live</span>
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
                placeholder="Access Token kết nối Meta Graph API / Fanpage Auto-Post trực tiếp (VD: EAABsb...)"
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
                  <option value="2">TikTok Ads</option>
                  <option value="3">Email / CRM</option>
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

        {/* Bảng danh sách tài khoản quảng cáo & POS (Thiết kế 100% chiều rộng, không thanh kéo ngang) */}
        {loading ? (
          <div className="py-8 text-center text-xs text-[#3B3F46] flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Đang tải danh sách tài khoản quảng cáo...</span>
          </div>
        ) : (
          <div className="w-full">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#E4E2DD] text-xs font-extrabold uppercase text-[#3B3F46] bg-[#F6F5F0]/70">
                  <th className="py-3 px-2.5 w-[26%]">Tài khoản &amp; Nền tảng</th>
                  <th className="py-3 px-2.5 w-[19%]">Chiến dịch đang gắn</th>
                  <th className="py-3 px-2.5 text-right w-[14%]">Trần ngày (2 chiều)</th>
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
                            <span>Đẩy trần +20%</span>
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

      {/* KHỐI 2: QUẢN LÝ CHIẾN DỊCH THUÊ KOL / KOC & AFFILIATE BÊN THỨ 3 */}
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
              Theo dõi hợp đồng booking KOL/KOC ngoài (TikTok Shop Affiliate, Facebook Reels, YouTube), tách bạch phí cát-xê cố định + % hoa hồng trên đơn và đo lường hệ số Net ROAS thực tế theo từng mã Tracking/Voucher riêng.
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

        {/* 4 thẻ KPI tổng hợp hiệu quả KOL / KOC */}
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

        {/* Form thêm hợp đồng KOL / KOC */}
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

        {/* Bảng danh sách KOL / KOC (Thiết kế 100% chiều rộng, không thanh kéo ngang) */}
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
