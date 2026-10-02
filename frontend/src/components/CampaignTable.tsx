import React, { useState } from 'react';
import { Calendar, Sparkles, GitBranch, Trash2, Filter, Search, ArrowUpRight } from 'lucide-react';
import { Campaign } from '../types';
import { formatNumber } from '../utils/format';

interface CampaignTableProps {
  campaigns: Campaign[];
  onSelectCampaign: (campaign: Campaign) => void;
  onOpenWorkflow: (campaign: Campaign) => void;
  onOpenAIForCampaign: (campaign: Campaign) => void;
  /** Mở bước xác nhận xóa (không xóa thẳng) — việc xóa cần hộp thoại xác nhận
   *  thay vì `window.confirm` chặn cả trang. */
  onRequestDeleteCampaign?: (id: number) => void;
  /** Phần trăm ngân sách đã dùng, tính từ CampaignMetric thật. */
  spendPercentByCampaign?: Record<number, number>;
  userRole?: string;
}

export const CampaignTable: React.FC<CampaignTableProps> = ({
  campaigns,
  onSelectCampaign,
  onOpenWorkflow,
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
    // Dữ liệu partial/legacy có thể thiếu objective — `.toLowerCase()` trực tiếp
    // trên undefined làm hỏng cả bảng.
    const matchesSearch = needle === '' ||
      (c.name ?? '').toLowerCase().includes(needle) ||
      (c.objective ?? '').toLowerCase().includes(needle);
    return matchesStatus && matchesSearch;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Đang chạy (ACTIVE)
          </span>
        );
      case 'PLANNED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Kế hoạch (PLANNED)
          </span>
        );
      case 'DRAFT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            Bản nháp (DRAFT)
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
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
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Lọc chiến dịch theo tên"
              placeholder="Lọc chiến dịch theo tên..."
              className="text-xs pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 w-56"
            />
          </div>
          <div className="flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Lọc chiến dịch theo trạng thái"
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-slate-600 focus:outline-none"
            >
              <option value="ALL">Tất cả trạng thái</option>
              <option value="ACTIVE">Đang chạy</option>
              <option value="PLANNED">Kế hoạch</option>
              <option value="DRAFT">Bản nháp</option>
            </select>
          </div>
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Hiển thị <span className="font-bold text-slate-800">{filteredCampaigns.length}</span> chiến dịch
        </div>
      </div>

      {/* Table Content */}
      <div
        className="overflow-x-auto"
        role="region"
        aria-label="Bảng danh sách chiến dịch"
        tabIndex={0}
      >
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50/80 text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200/80">
            <tr>
              <th className="py-3 px-4">Tên chiến dịch & Mục tiêu</th>
              <th className="py-3 px-4">Thời gian</th>
              <th className="py-3 px-4">Ngân sách</th>
              <th className="py-3 px-4">Trạng thái</th>
              <th className="py-3 px-4 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredCampaigns.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-400 text-xs">
                  Không tìm thấy chiến dịch nào phù hợp
                </td>
              </tr>
            ) : (
              filteredCampaigns.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/60 transition-colors group">
                  <td className="py-3.5 px-4">
                    <button
                      type="button"
                      onClick={() => onSelectCampaign(c)}
                      className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors flex items-center gap-1.5 text-left"
                    >
                      {c.name}
                      <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                    <p className="text-xs text-slate-500 truncate mt-0.5">{c.objective}</p>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-1.5 text-xs text-slate-600">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{c.start_date} <span className="text-slate-400">→</span> {c.end_date}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="font-semibold text-slate-900 text-xs">
                      {formatNumber(c.budget)} đ
                    </div>
                    {/* Thanh nhịp chi tiêu: trước đây đặt cứng w-2/3 (66%) cho mọi
                        dòng bất kể đã chi bao nhiêu. */}
                    {(() => {
                      const pct = spendPercentByCampaign?.[c.id];
                      if (pct === undefined) {
                        return (
                          <div className="text-[10px] text-slate-400 mt-1 italic">
                            chưa ghi nhận chi phí
                          </div>
                        );
                      }
                      return (
                        <>
                          <div
                            className="w-24 bg-slate-100 h-1.5 rounded-full mt-1.5 overflow-hidden"
                            role="img"
                            aria-label={`Đã dùng ${pct.toFixed(1)}% ngân sách`}
                          >
                            <div
                              className={`h-full rounded-full ${pct >= 90 ? 'bg-rose-500' : pct >= 70 ? 'bg-amber-500' : 'bg-indigo-500'}`}
                              style={{ width: `${Math.min(pct, 100)}%` }}
                            ></div>
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">{pct.toFixed(1)}%</div>
                        </>
                      );
                    })()}
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    {getStatusBadge(c.status)}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => onOpenWorkflow(c)}
                        title="Xem luồng chiến dịch (Nodes)"
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-xs font-medium flex items-center gap-1 transition-colors"
                      >
                        <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Canvas</span>
                      </button>
                      <button
                        onClick={() => onOpenAIForCampaign(c)}
                        title="Mở AI Copilot cho chiến dịch này"
                        className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-md text-xs font-semibold flex items-center gap-1 transition-colors"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                        <span>AI Viết</span>
                      </button>
                                            {/* Backend DELETE /campaigns/{id} chỉ cho MANAGER/AGENCY_MANAGER;
                          đưa ADMIN vào đây khiến nút hiện ra rồi nhận 403. */}
                      {(userRole === 'MANAGER' || userRole === 'AGENCY_MANAGER') && onRequestDeleteCampaign && (
                        <button
                          type="button"
                          onClick={() => onRequestDeleteCampaign(c.id)}
                          aria-label={`Xóa chiến dịch ${c.name}`}
                          title="Xóa chiến dịch"
                          className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
