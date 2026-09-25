import React, { useState, useEffect } from 'react';
import { 
  Megaphone, 
  Plus, 
  Search, 
  Filter, 
  Calendar, 
  DollarSign, 
  GitBranch, 
  Sparkles, 
  Trash2, 
  ArrowUpRight, 
  X, 
  Loader2, 
  CheckCircle2, 
  LayoutGrid, 
  Table as TableIcon,
  Tag,
  Target,
  Users
} from 'lucide-react';
import { Campaign, Product } from '../types';
import { campaignApi, productApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { CampaignCardSkeleton, CampaignTableSkeleton } from '../components/Skeleton';

interface CampaignsProps {
  onSelectCampaign: (campaign: Campaign) => void;
  onOpenWorkflow: (campaign: Campaign) => void;
  onOpenAI: (campaign: Campaign) => void;
  userRole?: string;
}

export const Campaigns: React.FC<CampaignsProps> = ({
  onSelectCampaign,
  onOpenWorkflow,
  onOpenAI,
  userRole
}) => {
  const toast = useToast();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    product_id: 1,
    objective: '',
    audience: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    budget: 10000000
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cList, pList] = await Promise.all([
        campaignApi.getAll(),
        productApi.getAll().catch(() => [] as Product[])
      ]);
      setCampaigns(cList);
      setProducts(pList);
      if (pList.length > 0) {
        setFormData(prev => ({ ...prev, product_id: pList[0].id }));
      }
    } catch (e) {
      console.error(e);
      toast.error(getApiErrorMessage(e), 'Lỗi khi tải danh sách chiến dịch');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim() || formData.name.trim().length < 3) {
      toast.warning('Tên chiến dịch phải có ít nhất 3 ký tự');
      return;
    }

    if (formData.end_date < formData.start_date) {
      toast.warning('Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu');
      return;
    }

    if (Number(formData.budget) < 0) {
      toast.warning('Ngân sách không được nhỏ hơn 0');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await campaignApi.create({
        name: formData.name.trim(),
        product_id: Number(formData.product_id),
        objective: formData.objective.trim() || 'Tăng cường nhận diện thương hiệu và tương tác',
        audience: formData.audience.trim() || 'Khách hàng tiềm năng đa kênh',
        start_date: formData.start_date,
        end_date: formData.end_date,
        budget: Number(formData.budget)
      });

      toast.success(`Đã tạo thành công chiến dịch: "${created.name}"`);
      setIsModalOpen(false);
      // Reset form
      setFormData({
        name: '',
        product_id: products[0]?.id || 1,
        objective: '',
        audience: '',
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        budget: 10000000
      });
      loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi khởi tạo chiến dịch');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteCampaign = async (id: number, name: string) => {
    if (userRole !== 'MANAGER') {
      toast.warning('Chỉ Quản lý (Manager) mới có quyền xóa chiến dịch');
      return;
    }

    const confirmDelete = window.confirm(`Bạn có chắc chắn muốn xóa chiến dịch "${name}"? Hành động này không thể hoàn tác.`);
    if (!confirmDelete) return;

    setDeletingId(id);
    try {
      await campaignApi.delete(id);
      toast.success(`Đã xóa thành công chiến dịch "${name}"`);
      loadData();
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi khi xóa chiến dịch');
    } finally {
      setDeletingId(null);
    }
  };

  const filteredCampaigns = campaigns.filter((c) => {
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
    const matchesSearch = c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.objective.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.audience.toLowerCase().includes(searchTerm.toLowerCase());
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

  const totalBudget = campaigns.reduce((sum, c) => sum + Number(c.budget || 0), 0);
  const activeCount = campaigns.filter(c => c.status === 'ACTIVE').length;
  const plannedCount = campaigns.filter(c => c.status === 'PLANNED').length;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      
      {/* Header & New Campaign Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black text-slate-900 tracking-tight">Quản lý Chiến dịch</h2>
            <span className="text-xs bg-indigo-50 text-indigo-700 font-bold px-2.5 py-0.5 rounded-full border border-indigo-200">
              {campaigns.length} Chiến dịch
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Tổng quan vòng đời chiến dịch, ngân sách, tích hợp AI Assistant và sơ đồ luồng tự động hóa.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-md shadow-indigo-600/20 transition-all active:scale-95 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Tạo Chiến Dịch Mới</span>
        </button>
      </div>

      {/* Bento Summary Metric Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Tổng chiến dịch</p>
          <p className="text-2xl font-black text-slate-900 mt-1">{campaigns.length}</p>
          <p className="text-[11px] text-slate-500 mt-1">Toàn bộ chiến dịch trong hệ thống</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-600">Đang chạy (ACTIVE)</p>
          <p className="text-2xl font-black text-emerald-600 mt-1">{activeCount}</p>
          <p className="text-[11px] text-slate-500 mt-1">Chiến dịch đang phát sinh tương tác</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-blue-600">Kế hoạch (PLANNED)</p>
          <p className="text-2xl font-black text-blue-600 mt-1">{plannedCount}</p>
          <p className="text-[11px] text-slate-500 mt-1">Chuẩn bị xuất bản trong tháng</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-600">Tổng ngân sách phân bổ</p>
          <p className="text-2xl font-black text-indigo-600 mt-1">{totalBudget.toLocaleString('vi-VN')} đ</p>
          <p className="text-[11px] text-slate-500 mt-1">Hạn mức toàn hệ thống</p>
        </div>
      </div>

      {/* Filter & View Mode Controls */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Tìm kiếm chiến dịch, mục tiêu, đối tượng..."
              className="text-xs pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 w-64 text-slate-800"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden font-medium"
            >
              <option value="ALL">Tất cả trạng thái</option>
              <option value="ACTIVE">Đang chạy (ACTIVE)</option>
              <option value="PLANNED">Kế hoạch (PLANNED)</option>
              <option value="DRAFT">Bản nháp (DRAFT)</option>
              <option value="COMPLETED">Hoàn tất (COMPLETED)</option>
            </select>
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg self-end sm:self-auto">
          <button
            onClick={() => setViewMode('grid')}
            title="Dạng lưới Bento Cards"
            className={`p-1.5 rounded-md transition-all ${
              viewMode === 'grid' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('table')}
            title="Dạng bảng dữ liệu"
            className={`p-1.5 rounded-md transition-all ${
              viewMode === 'table' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <TableIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Campaigns Listing */}
      {loading ? (
        viewMode === 'grid' ? <CampaignCardSkeleton count={6} /> : <CampaignTableSkeleton rows={5} />
      ) : filteredCampaigns.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center text-slate-400 text-xs space-y-2">
          <Megaphone className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="font-semibold text-slate-600">Không tìm thấy chiến dịch nào phù hợp</p>
          <p>Thử thay đổi bộ lọc hoặc tạo mới một chiến dịch tiếp thị ngay hôm nay.</p>
        </div>
      ) : viewMode === 'grid' ? (
        /* Bento Grid Cards View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCampaigns.map((c) => (
            <div
              key={c.id}
              className="bg-white rounded-xl border border-slate-200/80 hover:border-indigo-300 p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between group"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1 flex-1">
                    <span className="text-[10px] bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded uppercase">
                      {c.product?.name || `Sản phẩm #${c.product_id}`}
                    </span>
                    <h4 
                      onClick={() => onSelectCampaign(c)}
                      className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors cursor-pointer text-sm line-clamp-1 mt-1 flex items-center gap-1"
                    >
                      {c.name}
                      <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </h4>
                  </div>
                  <div>{getStatusBadge(c.status)}</div>
                </div>

                <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed bg-slate-50/60 p-2.5 rounded-lg border border-slate-100">
                  {c.objective}
                </p>

                <div className="space-y-1.5 text-xs text-slate-500 pt-1">
                  <div className="flex items-center gap-2">
                    <Users className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="truncate">Đối tượng: {c.audience}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{c.start_date} → {c.end_date}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="font-semibold text-slate-900">{Number(c.budget).toLocaleString('vi-VN')} đ</span>
                  </div>
                </div>
              </div>

              {/* Card Actions */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => onOpenWorkflow(c)}
                    title="Mở Trung tâm Điều phối & Pipeline"
                    className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-xs font-semibold flex items-center gap-1 transition-colors"
                  >
                    <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Điều phối & Pipeline</span>
                  </button>
                  <button
                    onClick={() => onOpenAI(c)}
                    title="Mở AI Copilot cho chiến dịch này"
                    className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-md text-xs font-semibold flex items-center gap-1 transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                    <span>AI Copilot</span>
                  </button>
                </div>

                {userRole === 'MANAGER' && (
                  <button
                    onClick={() => handleDeleteCampaign(c.id, c.name)}
                    disabled={deletingId === c.id}
                    title="Xóa chiến dịch (Chỉ Quản lý)"
                    className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  >
                    {deletingId === c.id ? <Loader2 className="w-4 h-4 animate-spin text-rose-600" /> : <Trash2 className="w-4 h-4" />}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-[11px] font-bold uppercase text-slate-500 border-b border-slate-200/80">
              <tr>
                <th className="py-3 px-4">Tên chiến dịch & Mục tiêu</th>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Ngân sách</th>
                <th className="py-3 px-4">Trạng thái</th>
                <th className="py-3 px-4 text-right">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredCampaigns.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/60 transition-colors group">
                  <td className="py-3.5 px-4">
                    <div 
                      onClick={() => onSelectCampaign(c)}
                      className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      {c.name}
                      <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">{c.objective}</p>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-600">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{c.start_date} → {c.end_date}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap text-xs font-semibold text-slate-900">
                    {Number(c.budget).toLocaleString('vi-VN')} đ
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    {getStatusBadge(c.status)}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => onOpenWorkflow(c)}
                        title="Mở Trung tâm Điều phối & Pipeline"
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-xs font-semibold flex items-center gap-1 transition-colors"
                      >
                        <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Điều phối & Pipeline</span>
                      </button>
                      <button
                        onClick={() => onOpenAI(c)}
                        title="Mở AI Copilot cho chiến dịch này"
                        className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-md text-xs font-semibold flex items-center gap-1 transition-colors"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                        <span>AI Copilot</span>
                      </button>
                      {userRole === 'MANAGER' && (
                        <button
                          onClick={() => handleDeleteCampaign(c.id, c.name)}
                          disabled={deletingId === c.id}
                          className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                        >
                          {deletingId === c.id ? <Loader2 className="w-4 h-4 animate-spin text-rose-600" /> : <Trash2 className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: Tạo Chiến Dịch Mới */}
      {isModalOpen && (
        <div 
          onClick={() => setIsModalOpen(false)}
          className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden"
          >
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
                  <Megaphone className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">Tạo Chiến Dịch Marketing Mới</h3>
                  <p className="text-[11px] text-slate-500">Điền thông tin mục tiêu và phân bổ ngân sách cho chiến dịch.</p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleCreateCampaign} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Tên chiến dịch <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ví dụ: Chiến dịch Khóa học Lập trình AI Mùa Thu"
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Sản phẩm quảng bá <span className="text-rose-500">*</span>
                </label>
                <select
                  value={formData.product_id}
                  onChange={(e) => setFormData({ ...formData, product_id: Number(e.target.value) })}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 text-slate-900 font-medium"
                >
                  {products.length === 0 ? (
                    <option value={1}>Sản phẩm mặc định #1</option>
                  ) : (
                    products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} {p.usp ? `(${p.usp})` : ''}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Mục tiêu chiến dịch (Objective)
                </label>
                <textarea
                  rows={2}
                  value={formData.objective}
                  onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
                  placeholder="Ví dụ: Đạt 1,000 học viên đăng ký mới qua Facebook Ads và Email"
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Đối tượng khách hàng mục tiêu (Audience)
                </label>
                <input
                  type="text"
                  value={formData.audience}
                  onChange={(e) => setFormData({ ...formData, audience: e.target.value })}
                  placeholder="Ví dụ: Sinh viên ngành CNTT, kỹ sư phần mềm tại Việt Nam"
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 text-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Ngày bắt đầu <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Ngày kết thúc <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 text-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Ngân sách dự kiến (VNĐ) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  min={0}
                  step={500000}
                  required
                  value={formData.budget}
                  onChange={(e) => setFormData({ ...formData, budget: Number(e.target.value) })}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:border-indigo-500 text-slate-900 font-semibold"
                />
              </div>

              {/* Modal Actions */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-indigo-600/20 transition-all active:scale-95"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  )}
                  <span>Tạo Chiến Dịch</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
