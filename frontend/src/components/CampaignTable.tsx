import React, { useState } from 'react';
import { Calendar, Sparkles, Trash2, Filter, Search, ArrowUpRight, Eye } from 'lucide-react';
import { Campaign } from '../types';
import { formatNumber } from '../utils/format';

interface CampaignTableProps {
  campaigns: Campaign[];
  onSelectCampaign: (campaign: Campaign) => void;
  onOpenWorkflow: (campaign: Campaign) => void;
  onOpenAIForCampaign: (campaign: Campaign) => void;
  onRequestDeleteCampaign?: (id: number) => void;
  spendPercentByCampaign?: Record<number, number>;
  userRole?: string;
}

export const CampaignTable: React.FC<CampaignTableProps> = ({
  campaigns,
  onSelectCampaign,
  onOpenAIForCampaign,
  onRequestDeleteCampaign,
  spendPercentByCampaign,
  userRole
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filteredCampaigns = campaigns.filter((c) => {
    const needle = searchTerm.trim().toLowerCase();
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
    const matchesSearch = needle === '' ||
      (c.name ?? '').toLowerCase().includes(needle) ||
      (c.objective ?? '').toLowerCase().includes(needle);
    return matchesStatus && matchesSearch;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-[#F0FDF4] text-[#15803D] border border-[#BBF7D0]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#15803D]"></span>
            Đang chạy
          </span>
        );
      case 'PAUSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#B45309]"></span>
            Tạm dừng
          </span>
        );
      case 'PLANNED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
            Kế hoạch
          </span>
        );
      case 'DRAFT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-[#F6F5F0] text-[#5A5E66] border border-[#E4E2DD]">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            Bản nháp
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
            Hoàn tất
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-xl border border-[#E4E2DD] overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-4 border-b border-[#F0EFEA] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-[#5A5E66] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Lọc chiến dịch theo tên"
              placeholder="Tìm tên chiến dịch..."
              className="text-xs pl-8 pr-3 py-1.5 bg-[#F6F5F0] border border-[#D0CEC7] rounded-lg focus:outline-none focus:border-[#D95D39] w-56 text-[#121316]"
            />
          </div>
          <div className="flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-[#5A5E66]" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Lọc chiến dịch theo trạng thái"
              className="text-xs bg-[#F6F5F0] border border-[#D0CEC7] rounded-lg px-2.5 py-1.5 text-[#121316] font-semibold focus:outline-none"
            >
              <option value="ALL">Tất cả trạng thái</option>
              <option value="ACTIVE">Đang chạy</option>
              <option value="PAUSED">Tạm dừng</option>
              <option value="PLANNED">Kế hoạch</option>
              <option value="DRAFT">Bản nháp</option>
            </select>
          </div>
        </div>

        <div className="text-xs text-[#5A5E66] font-medium">
          Hiển thị <span className="font-bold text-[#121316]">{filteredCampaigns.length}</span> chiến dịch
        </div>
      </div>

      {/* Table Content — Bố cục tự co giãn vừa khít khung, không thanh kéo ngang */}
      <div
        role="region"
        aria-label="Bảng danh sách chiến dịch"
      >
        <table className="w-full text-left text-sm text-[#121316] border-collapse">
          <thead className="bg-[#F6F5F0] text-xs font-bold uppercase tracking-wider text-[#3B3F46] border-b border-[#E4E2DD]">
            <tr>
              <th className="py-3.5 px-4 w-[32%]">Chiến dịch &amp; Mục tiêu</th>
              <th className="py-3.5 px-4 w-[22%]">Đã chi / Ngân sách</th>
              <th className="py-3.5 px-4 w-[22%]">Doanh thu &amp; ROAS</th>
              <th className="py-3.5 px-3 w-[11%]">Trạng thái</th>
              <th className="py-3.5 px-4 w-[13%] text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F0EFEA]">
            {filteredCampaigns.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-[#3B3F46] text-sm">
                  Không tìm thấy chiến dịch nào phù hợp
                </td>
              </tr>
            ) : (
              filteredCampaigns.map((c) => {
                const ms = c.metrics_summary;
                const spent = Number(ms?.cost ?? ms?.total_cost ?? 0);
                const revenue = Number(ms?.revenue ?? ms?.total_revenue ?? 0);
                const conversions = Number(ms?.conversions ?? ms?.total_conversions ?? 0);
                const budgetNum = Number(c.budget) || 0;
                const pct = spendPercentByCampaign?.[c.id] ?? (budgetNum > 0 ? Math.min(100, (spent / budgetNum) * 100) : 0);
                const roas = spent > 0 ? revenue / spent : null;

                return (
                  <tr key={c.id} className="hover:bg-[#F6F5F0]/60 transition-colors group">
                    <td className="py-4 px-4 align-top">
                      <button
                        type="button"
                        onClick={() => onSelectCampaign(c)}
                        className="text-sm font-bold text-[#121316] group-hover:text-[#D95D39] transition-colors flex items-center gap-1.5 text-left cursor-pointer"
                      >
                        <span>{c.name}</span>
                        <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                      </button>
                      <p className="text-xs text-[#3B3F46] mt-1 leading-relaxed">
                        {c.objective}
                      </p>
                      <div className="text-xs text-[#4E535C] flex items-center gap-1.5 mt-1 font-medium">
                        <Calendar className="w-3.5 h-3.5 text-[#5A5E66] shrink-0" />
                        <span className="tabular-nums">{c.start_date} &rarr; {c.end_date}</span>
                      </div>
                    </td>

                    <td className="py-4 px-4 align-top tabular-nums">
                      <div className="text-sm font-bold text-[#121316]">
                        <span className="font-medium text-[#3B3F46]">Đã chi: </span>
                        <span>{formatNumber(spent)} đ</span>
                      </div>
                      <div className="text-xs text-[#3B3F46] mt-1 font-medium">
                        Ngân sách: {formatNumber(budgetNum)} đ ({pct.toFixed(0)}%)
                      </div>
                      <div
                        className="w-full max-w-[140px] bg-[#E4E2DD] h-1.5 rounded-full mt-2 overflow-hidden"
                        role="img"
                        aria-label={`Đã dùng ${pct.toFixed(1)}% ngân sách`}
                      >
                        <div
                          className={`h-full rounded-full ${pct >= 90 ? 'bg-[#BE123C]' : pct >= 75 ? 'bg-[#B45309]' : 'bg-[#121316]'}`}
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                    </td>

                    <td className="py-4 px-4 align-top tabular-nums">
                      {spent > 0 || revenue > 0 ? (
                        <>
                          <div className="text-sm font-bold text-[#15803D]">
                            <span className="font-medium text-[#3B3F46]">Thu về: </span>
                            <span>{formatNumber(revenue)} đ</span>
                          </div>
                          <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                            {roas !== null && (
                              <span
                                className={`px-2 py-0.5 rounded-md text-xs font-bold border ${
                                  roas >= 2.0
                                    ? 'bg-[#F0FDF4] text-[#15803D] border-[#BBF7D0]'
                                    : roas >= 1.0
                                      ? 'bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]'
                                      : 'bg-[#FFF1F2] text-[#BE123C] border-[#FECDD3]'
                                }`}
                              >
                                ROAS {roas.toFixed(2)}x {roas >= 2.0 ? '(Lãi tốt)' : roas >= 1.0 ? '(Hòa vốn / Lãi nhẹ)' : '(Đang lỗ)'}
                              </span>
                            )}
                            <span className="text-xs font-semibold text-[#3B3F46]">
                              · {formatNumber(conversions)} đơn
                            </span>
                          </div>
                        </>
                      ) : (
                        <span className="text-xs text-[#4E535C] italic">Chưa nhập số liệu</span>
                      )}
                    </td>

                    <td className="py-4 px-3 align-top">
                      {getStatusBadge(c.status)}
                    </td>

                    <td className="py-4 px-4 text-right align-top">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => onSelectCampaign(c)}
                          title="Xem chi tiết, bài quảng cáo và nhập số liệu"
                          className="px-3 py-1.5 bg-[#F6F5F0] hover:bg-[#EAE8E1] text-[#121316] border border-[#D0CEC7] rounded-lg text-xs font-bold inline-flex items-center gap-1.5 transition-colors cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5 text-[#121316]" />
                          <span>Chi tiết</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => onOpenAIForCampaign(c)}
                          title="Viết bài quảng cáo mới cho chiến dịch này"
                          className="px-3 py-1.5 bg-[#D95D39] hover:bg-[#C04E2C] text-white rounded-lg text-xs font-bold inline-flex items-center gap-1.5 transition-colors cursor-pointer"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Soạn QC</span>
                        </button>
                        {(userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER') && onRequestDeleteCampaign && (
                          <button
                            type="button"
                            onClick={() => onRequestDeleteCampaign(c.id)}
                            aria-label={`Xóa chiến dịch ${c.name}`}
                            title="Xóa chiến dịch"
                            className="p-1.5 text-[#3B3F46] hover:text-[#BE123C] hover:bg-[#FFF1F2] rounded-lg transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
