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
} from 'lucide-react';
import { adAccountsApi, AdAccountItem, campaignApi, getApiErrorMessage } from '../services/api';
import { Campaign } from '../types';
import { formatNumber } from '../utils/format';
import { useToast } from './Toast';

interface AdAccountsHubProps {
  workspaceId?: number;
  onSynced?: () => void;
}

const PLATFORM_LABELS: Record<string, string> = {
  META_ADS: 'Meta Ads (Facebook / Instagram)',
  TIKTOK_ADS: 'TikTok Business Center',
  GOOGLE_ADS: 'Google Ads MCC',
  POS_SYSTEM: 'Phần mềm bán hàng (Sapo / Pancake POS)',
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
    label: 'Bị hạn chế (Cần đổi TK)',
    badgeClass: 'bg-[#FFF1F2] text-[#BE123C] border border-[#FECDD3]',
  },
};

export const AdAccountsHub: React.FC<AdAccountsHubProps> = ({ workspaceId, onSynced }) => {
  const toast = useToast();
  const [accounts, setAccounts] = useState<AdAccountItem[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [showPosForm, setShowPosForm] = useState<boolean>(false);

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

  const loadHubData = useCallback(async () => {
    setLoading(true);
    try {
      const [accRes, campList] = await Promise.all([
        adAccountsApi.list(workspaceId),
        campaignApi.getAll(undefined, undefined, workspaceId),
      ]);
      setAccounts(accRes.items || []);
      setCampaigns(campList || []);
      if (campList.length > 0 && !posCampaignId) {
        setPosCampaignId(String(campList[0].id));
        setNewCampaignId(String(campList[0].id));
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không tải được danh sách tài khoản quảng cáo');
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
      toast.success(
        `Đã đồng bộ ${res.synced_accounts_count} tài khoản quảng cáo & POS (${res.verified_metric_rows} dòng số liệu mới cập nhật).`
      );
      if (onSynced) onSynced();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 'Không thể đồng bộ số liệu');
    } finally {
      setSyncing(false);
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

  return (
    <div className="bg-white rounded-xl border border-[#E4E2DD] p-5 space-y-5">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#E4E2DD] pb-4">
        <div>
          <h3 className="text-base font-black text-[#121316] tracking-tight">
            Tài khoản quảng cáo &amp; Nguồn đồng bộ đơn hàng thực tế
          </h3>
          <p className="text-xs text-[#5A5E66] mt-1">
            Quản lý mã tài khoản quảng cáo (Meta BM, TikTok BC, Google MCC), gắn Pixel theo dõi, chuyển nhanh sang tài khoản dự phòng khi bị hạn chế và khớp doanh thu từ phần mềm bán hàng (Sapo / Pancake POS).
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
            <span>Ghi nhận đơn hàng từ POS</span>
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
            <span>Thêm tài khoản quảng cáo</span>
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
            <span>Đồng bộ chi phí &amp; đơn hàng ngay</span>
          </button>
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
              className="text-[#5A5E66] hover:text-[#121316]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
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
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
                Mã định danh tài khoản (Account ID)
              </label>
              <input
                type="text"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value)}
                placeholder="VD: act_1084920194 hoặc adv_738291"
                className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-mono text-[#121316] outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
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
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
                Mã Pixel / Dataset theo dõi chuyển đổi
              </label>
              <input
                type="text"
                value={newPixel}
                onChange={(e) => setNewPixel(e.target.value)}
                placeholder="VD: px_88392019283"
                className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-mono text-[#121316] outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
                Hạn mức chi tiêu tối đa / ngày (VNĐ)
              </label>
              <input
                type="number"
                min={0}
                step={500000}
                value={newCap}
                onChange={(e) => setNewCap(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-mono text-[#121316] outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
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
              placeholder="Access Token kết nối API trực tiếp (Không bắt buộc — VD: EAABsb...)"
              className="flex-1 px-3 py-1.5 text-xs bg-white border border-[#D0CEC7] rounded-lg font-mono text-[#121316] outline-none"
            />
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-3 py-1.5 text-xs font-semibold text-[#5A5E66] hover:text-[#121316]"
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
              <p className="text-[11px] text-[#5A5E66]">
                Khi khách nhắn tin từ quảng cáo và chốt đơn trên POS, doanh thu và số đơn sẽ cộng thẳng vào chiến dịch để tính lại hệ số ROAS thực tế ngay lập tức.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowPosForm(false)}
              className="text-[#5A5E66] hover:text-[#121316]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
            <div className="lg:col-span-2">
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
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
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
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
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
                Số đơn chốt mới
              </label>
              <input
                type="number"
                min={1}
                value={posOrderCount}
                onChange={(e) => setPosOrderCount(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-mono text-[#121316] outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#5A5E66] mb-1">
                Doanh thu thực thu (VNĐ)
              </label>
              <input
                type="number"
                min={1000}
                step={50000}
                value={posOrderValue}
                onChange={(e) => setPosOrderValue(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-[#D0CEC7] rounded-lg font-mono text-[#121316] outline-none"
              />
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-[#5A5E66] font-semibold">Chi phí quảng cáo phát sinh thêm (VNĐ):</span>
              <input
                type="number"
                min={0}
                step={50000}
                value={posAdSpend}
                onChange={(e) => setPosAdSpend(e.target.value)}
                className="w-36 px-2.5 py-1 bg-white border border-[#D0CEC7] rounded-lg font-mono text-[#121316] outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowPosForm(false)}
                className="px-3 py-1.5 text-xs font-semibold text-[#5A5E66] hover:text-[#121316]"
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
        <div className="py-8 text-center text-xs text-[#5A5E66] flex items-center justify-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Đang tải danh sách tài khoản quảng cáo...</span>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#E4E2DD] text-[11px] font-bold uppercase text-[#5A5E66] bg-[#F6F5F0]/60">
                <th className="py-2.5 px-3">Mã TK &amp; Nền tảng</th>
                <th className="py-2.5 px-3">Chiến dịch đang gắn</th>
                <th className="py-2.5 px-3 text-right">Hạn mức ngày</th>
                <th className="py-2.5 px-3 text-right">Tổng đã chi</th>
                <th className="py-2.5 px-3 text-right">Doanh thu &amp; Đơn</th>
                <th className="py-2.5 px-3">Trạng thái</th>
                <th className="py-2.5 px-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0EFEA]">
              {accounts.map((acc) => {
                const st = STATUS_LABELS[acc.status] || STATUS_LABELS.ACTIVE;
                return (
                  <tr key={acc.id} className="hover:bg-[#F6F5F0]/40 transition-colors">
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4 text-[#5A5E66] shrink-0" />
                        <div>
                          <div className="font-bold text-[#121316]">{acc.account_name}</div>
                          <div className="text-[11px] text-[#5A5E66] flex items-center gap-2 mt-0.5">
                            <span className="font-mono font-bold text-[#121316] bg-[#F6F5F0] px-1.5 py-0.5 rounded border border-[#E4E2DD]">
                              {acc.account_code}
                            </span>
                            <span>{PLATFORM_LABELS[acc.platform] || acc.platform}</span>
                            {acc.pixel_id && (
                              <span className="font-mono text-[10px] text-[#5A5E66]">
                                Pixel: {acc.pixel_id}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5">
                        <Link2 className="w-3.5 h-3.5 text-[#5A5E66] shrink-0" />
                        <select
                          value={acc.linked_campaign_id || ''}
                          onChange={(e) => handleChangeCampaignLink(acc, e.target.value)}
                          className="bg-white border border-[#D0CEC7] rounded-lg px-2 py-1 text-xs font-semibold text-[#121316] max-w-[210px] truncate outline-none"
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

                    <td className="py-3 px-3 text-right font-mono font-semibold text-[#121316] tabular-nums">
                      {acc.daily_spend_cap > 0 ? `${formatNumber(acc.daily_spend_cap)} đ` : 'Không giới hạn'}
                    </td>

                    <td className="py-3 px-3 text-right font-mono font-bold text-[#121316] tabular-nums">
                      {formatNumber(acc.today_spend)} đ
                    </td>

                    <td className="py-3 px-3 text-right font-mono tabular-nums">
                      <div className="font-bold text-[#15803D]">
                        {formatNumber(acc.total_revenue)} đ
                      </div>
                      <div className="text-[10px] text-[#5A5E66]">
                        {acc.total_orders} đơn · ROAS {acc.roas}x
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      <select
                        value={acc.status}
                        onChange={(e) => handleToggleAccountStatus(acc, e.target.value)}
                        className={`text-[11px] font-bold px-2 py-1 rounded-lg outline-none cursor-pointer ${st.badgeClass}`}
                      >
                        <option value="ACTIVE">Đang hoạt động</option>
                        <option value="SPEND_WARNING">Sắp chạm trần thẻ</option>
                        <option value="RESTRICTED">Bị hạn chế (Cần đổi TK)</option>
                      </select>
                    </td>

                    <td className="py-3 px-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {acc.status === 'RESTRICTED' && acc.linked_campaign_id && (
                          <button
                            type="button"
                            onClick={() => handleSwitchToBackupAccount(acc)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#D95D39] hover:bg-[#C04E2C] text-white font-bold text-[11px] rounded-lg"
                            title="Chuyển chiến dịch đang chạy sang tài khoản dự phòng"
                          >
                            <ArrowRightLeft className="w-3 h-3" />
                            <span>Chuyển sang TK dự phòng</span>
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteAccount(acc)}
                          className="p-1.5 text-[#5A5E66] hover:text-[#BE123C] rounded-lg hover:bg-[#FFF1F2]"
                          title="Gỡ tài khoản này"
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
      )}
    </div>
  );
};
