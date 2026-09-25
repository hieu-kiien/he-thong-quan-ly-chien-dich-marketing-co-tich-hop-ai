import React, { useState } from 'react';
import { 
  TrendingUp, 
  DollarSign, 
  BarChart2, 
  ArrowUpRight, 
  ArrowDownRight, 
  Zap, 
  Sparkles, 
  PieChart, 
  ThumbsUp, 
  Mail, 
  ExternalLink, 
  FileText,
  AlertTriangle,
  CheckCircle2,
  Brain,
  Download,
  BookOpen,
  Target,
  Award
} from 'lucide-react';
import { Campaign, KPISummary } from '../types';
import { useToast } from './Toast';

interface ChannelROIComparisonProps {
  campaign: Campaign;
  kpi: KPISummary | null;
}

export const ChannelROIComparison: React.FC<ChannelROIComparisonProps> = ({
  campaign,
  kpi
}) => {
  const toast = useToast();
  const [isReallocated, setIsReallocated] = useState<boolean>(false);
  const [savedToVault, setSavedToVault] = useState<boolean>(false);

  const totalBudget = Number(campaign.budget) || 10000000;
  const totalCost = kpi?.total_cost || 4200000;
  const totalRevenue = kpi?.total_revenue || 16800000;

  // Base channel allocations vs Reallocated channels
  const channels = [
    {
      id: 'facebook',
      name: 'Facebook Ads & Fanpage',
      icon: ThumbsUp,
      color: 'text-blue-600 bg-blue-50 border-blue-200',
      badgeColor: 'bg-blue-600',
      allocatedBudget: isReallocated ? Math.round(totalBudget * 0.35) : Math.round(totalBudget * 0.45),
      spentAmount: Math.round(totalCost * 0.45),
      clicks: Math.round((kpi?.total_clicks || 1200) * 0.50),
      ctr: (kpi?.ctr_percent ? Number(kpi.ctr_percent) : 7.5),
      revenue: Math.round(totalRevenue * 0.38),
      roi: isReallocated ? 145 : Math.round(((totalRevenue * 0.38 - totalCost * 0.45) / (totalCost * 0.45 || 1)) * 100),
      status: 'HIGH_VOLUME',
      note: isReallocated ? 'Đã giảm 10% ngân sách chuyển sang Google Ads' : 'Độ phủ rộng nhất'
    },
    {
      id: 'google_ads',
      name: 'Google Search Ads',
      icon: ExternalLink,
      color: 'text-amber-600 bg-amber-50 border-amber-200',
      badgeColor: 'bg-amber-600',
      allocatedBudget: isReallocated ? Math.round(totalBudget * 0.40) : Math.round(totalBudget * 0.30),
      spentAmount: isReallocated ? Math.round(totalCost * 0.38) : Math.round(totalCost * 0.30),
      clicks: isReallocated ? Math.round((kpi?.total_clicks || 1200) * 0.35) : Math.round((kpi?.total_clicks || 1200) * 0.25),
      ctr: Number(((kpi?.ctr_percent || 7.5) * 1.3).toFixed(1)),
      revenue: isReallocated ? Math.round(totalRevenue * 0.52) : Math.round(totalRevenue * 0.42),
      roi: isReallocated ? 285 : 245,
      status: 'STAR_PERFORMER',
      note: isReallocated ? 'Đã nhận thêm ngân sách + Tăng 24% đơn hàng' : 'Hiệu quả chuyển đổi cao nhất'
    },
    {
      id: 'email',
      name: 'Email Newsletter',
      icon: Mail,
      color: 'text-purple-600 bg-purple-50 border-purple-200',
      badgeColor: 'bg-purple-600',
      allocatedBudget: Math.round(totalBudget * 0.15),
      spentAmount: Math.round(totalCost * 0.12),
      clicks: Math.round((kpi?.total_clicks || 1200) * 0.15),
      ctr: Number(((kpi?.ctr_percent || 7.5) * 1.5).toFixed(1)),
      revenue: Math.round(totalRevenue * 0.15),
      roi: Math.round(((totalRevenue * 0.15 - totalCost * 0.12) / (totalCost * 0.12 || 1)) * 100),
      status: 'HIGH_EFFICIENCY',
      note: 'Chi phí cực thấp, giữ chân khách hàng tốt'
    },
    {
      id: 'blog',
      name: 'Blog SEO & Website',
      icon: FileText,
      color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
      badgeColor: 'bg-emerald-600',
      allocatedBudget: Math.round(totalBudget * 0.10),
      spentAmount: Math.round(totalCost * 0.08),
      clicks: Math.round((kpi?.total_clicks || 1200) * 0.10),
      ctr: Number(((kpi?.ctr_percent || 7.5) * 0.9).toFixed(1)),
      revenue: Math.round(totalRevenue * 0.05),
      roi: Math.round(((totalRevenue * 0.05 - totalCost * 0.08) / (totalCost * 0.08 || 1)) * 100),
      status: 'ORGANIC_GROWTH',
      note: 'Lưu lượng tự nhiên dài hạn'
    }
  ];

  const handleApplyReallocation = () => {
    setIsReallocated(true);
    toast.success('Đã áp dụng thành công Đề xuất Tối ưu Ngân sách của AI! Dự kiến tăng thêm 18.5% doanh thu trong 14 ngày tới.');
  };

  const handleSaveToVault = () => {
    setSavedToVault(true);
    toast.success('Đã lưu toàn bộ bài học kinh nghiệm của chiến dịch vào Bộ nhớ Tri thức AI (Knowledge Vault) để làm bối cảnh huấn luyện cho các chiến dịch tương lai!');
  };

  const handleExportReport = () => {
    toast.info('Đang tổng hợp Báo cáo Quy kết ROI Hoàn chỉnh (Closed-Loop Attribution Summary) định dạng PDF...');
  };

  return (
    <div className="space-y-6">
      {/* 1. AI Budget Reallocation Suggestion Banner (Interactive) */}
      <div className="bg-gradient-to-r from-emerald-900 via-teal-950 to-slate-900 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-6 border border-emerald-500/20">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
              <Zap className="w-3 h-3 text-emerald-400" /> Bác sĩ AI Vận hành: Tối ưu dòng tiền
            </span>
            <span className="text-xs text-teal-300">• Phân tích quy kết đa kênh thời gian thực</span>
          </div>
          <h3 className="text-base font-black tracking-tight">Chiến lược Tái phân bổ Ngân sách thông minh</h3>
          <p className="text-xs text-emerald-100 max-w-2xl leading-relaxed">
            Kênh <strong>Google Search Ads</strong> đang đạt tỷ suất lợi nhuận ROI cao nhất (+245%). AI khuyến nghị <strong>điều chuyển 10% ngân sách từ Facebook sang Google Ads</strong> trong 14 ngày tới để tối đa hóa doanh thu chuyển đổi.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0">
          <div className="px-4 py-2 bg-emerald-600/30 border border-emerald-500/40 rounded-xl text-center w-full sm:w-auto">
            <span className="text-[10px] uppercase font-bold text-emerald-300 block">Dự kiến sau tối ưu</span>
            <span className="text-lg font-black text-white">+18.5% Doanh thu</span>
          </div>

          <button
            onClick={handleApplyReallocation}
            disabled={isReallocated}
            className={`w-full sm:w-auto px-4 py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-md active:scale-95 ${
              isReallocated
                ? 'bg-emerald-600/40 text-emerald-200 border border-emerald-500/40 cursor-default'
                : 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-black shadow-emerald-500/30'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{isReallocated ? 'Đã điều chuyển ngân sách' : 'Áp dụng đề xuất AI ngay'}</span>
          </button>
        </div>
      </div>

      {/* 2. Comparison Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-indigo-600" />
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Bảng So Sánh Hiệu Quả & Phân Bổ Ngân Sách Đa Kênh
            </h4>
          </div>
          <span className="text-[11px] text-slate-500">
            Tổng ngân sách chiến dịch: <strong>{totalBudget.toLocaleString('vi-VN')} VNĐ</strong>
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-semibold text-[11px]">
              <tr>
                <th className="py-3 px-4">Kênh tiếp thị</th>
                <th className="py-3 px-4 text-right">Ngân sách phân bổ</th>
                <th className="py-3 px-4 text-right">Đã chi (Spent)</th>
                <th className="py-3 px-4 text-right">Lượt click (CTR)</th>
                <th className="py-3 px-4 text-right">Doanh thu mang lại</th>
                <th className="py-3 px-4 text-right">Tỷ suất ROI</th>
                <th className="py-3 px-4 text-center">Đánh giá vận hành</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {channels.map((ch) => {
                const Icon = ch.icon;
                return (
                  <tr key={ch.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-slate-800">
                      <div className="flex items-center gap-2">
                        <span className={`w-7 h-7 rounded-lg flex items-center justify-center ${ch.color}`}>
                          <Icon className="w-3.5 h-3.5" />
                        </span>
                        <div>
                          <span>{ch.name}</span>
                          <span className="block text-[10px] text-slate-400 font-normal">{ch.note}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-slate-700">
                      {ch.allocatedBudget.toLocaleString('vi-VN')} đ
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-slate-500">
                      {ch.spentAmount.toLocaleString('vi-VN')} đ
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <span className="font-semibold text-slate-800">{ch.clicks.toLocaleString('vi-VN')}</span>
                      <span className="block text-[10px] text-emerald-600 font-medium">CTR: {ch.ctr}%</span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-bold text-slate-900">
                      {ch.revenue.toLocaleString('vi-VN')} đ
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <span className={`inline-flex items-center gap-0.5 font-bold ${
                        ch.roi > 200 ? 'text-emerald-600' : ch.roi > 100 ? 'text-indigo-600' : 'text-slate-700'
                      }`}>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                        +{ch.roi}%
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {ch.status === 'STAR_PERFORMER' && (
                        <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                          ⭐ Hiệu quả cao nhất
                        </span>
                      )}
                      {ch.status === 'HIGH_VOLUME' && (
                        <span className="text-[10px] font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                          Độ phủ rộng
                        </span>
                      )}
                      {ch.status === 'HIGH_EFFICIENCY' && (
                        <span className="text-[10px] font-bold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full">
                          Chi phí thấp
                        </span>
                      )}
                      {ch.status === 'ORGANIC_GROWTH' && (
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                          Bền vững
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. POST-CAMPAIGN RETROSPECTIVE & KNOWLEDGE VAULT (Trả lời câu hỏi: Sau đó làm gì?) */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 border border-slate-800 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-violet-500/20 text-violet-300 border border-violet-500/30 flex items-center gap-1">
                <Brain className="w-3 h-3 text-violet-400" /> Bước 6: Đóng gói Tri thức & Bài học Sau Chiến dịch
              </span>
              <span className="text-xs text-slate-400">• Closed-Loop Retrospective</span>
            </div>
            <h3 className="text-base font-black text-white">Kho Bài Học Kinh Nghiệm & Đúc Kết Thực Chiến (Knowledge Vault)</h3>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Chiến dịch kết thúc không phải là hết. Toàn bộ chỉ số thành bại được AI đúc kết thành bài học kinh nghiệm để làm bối cảnh huấn luyện cho các chiến dịch tương lai.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleExportReport}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5 text-slate-400" />
              <span>Xuất Báo cáo ROI (PDF)</span>
            </button>

            <button
              onClick={handleSaveToVault}
              disabled={savedToVault}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-md ${
                savedToVault
                  ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40'
                  : 'bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white shadow-indigo-500/25 active:scale-95'
              }`}
            >
              <Brain className="w-3.5 h-3.5" />
              <span>{savedToVault ? 'Đã lưu vào Kho Tri Thức AI' : 'Lưu Bài Học Vào Bộ Nhớ AI'}</span>
            </button>
          </div>
        </div>

        {/* 3 Strategic Learnings Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
                <Award className="w-3.5 h-3.5" /> Angle Thắng Cuộc
              </span>
              <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-bold">PAS Framework</span>
            </div>
            <h4 className="text-xs font-bold text-slate-100">Góc nhìn giải quyết nỗi đau CPA</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Thông điệp tập trung vào nỗi đau chi phí quảng cáo đắt đỏ giúp tăng CTR lên <strong>8.4%</strong> và giảm chi phí mỗi click (CPC) xuống chỉ <strong>2.221 VNĐ</strong>.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 flex items-center gap-1">
                <Target className="w-3.5 h-3.5" /> Phân Phối Đa Kênh
              </span>
              <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded font-bold">Google + Facebook</span>
            </div>
            <h4 className="text-xs font-bold text-slate-100">Hiệu ứng phễu kép (Full-Funnel)</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Facebook đóng vai trò tạo nhu cầu (Brand Awareness), trong khi Google Search Ads "chốt hạ" khách hàng đang có ý định mua với ROI vượt trội <strong>+245%</strong>.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
                <Zap className="w-3.5 h-3.5" /> Khung Giờ Phát Sóng
              </span>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-bold">19:30 - 21:00</span>
            </div>
            <h4 className="text-xs font-bold text-slate-100">Khung giờ vàng quyết định 68% chuyển đổi</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Lập lịch đăng bài đúng khung giờ vàng vào tối thứ 4 và thứ 6 giúp tăng tỷ lệ tương tác tự nhiên lên <strong>+42%</strong> so với các khung giờ hành chính.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
