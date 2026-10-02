import React from 'react';
import { CalendarCheck, Stethoscope, ArrowRight } from 'lucide-react';
import { Campaign, MarketingContent } from '../../types';
import { MarketingCalendar } from '../MarketingCalendar';

interface CalendarTabProps {
  campaign: Campaign;
  campaigns?: Campaign[];
  contents: MarketingContent[];
  onSelectCampaign?: (c: Campaign | null) => void;
  onNavigateToDoctor?: () => void;
}

export const CalendarTab: React.FC<CalendarTabProps> = ({
  campaign,
  campaigns = [],
  contents,
  onSelectCampaign,
  onNavigateToDoctor,
}) => {
  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-xl border border-blue-200/80 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-slate-700">
          <CalendarCheck className="w-5 h-5 text-blue-600 shrink-0" />
          <span>
            Lịch biểu thị các nội dung tiếp thị đã được xếp lịch tự động đăng tải theo từng khung giờ tối ưu (Giờ Vàng AI gợi ý).
          </span>
        </div>
        {onNavigateToDoctor && (
          <button
            onClick={onNavigateToDoctor}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs shadow-sm transition-colors flex items-center gap-1.5 shrink-0"
          >
            <Stethoscope className="w-4 h-4" />
            <span>Chuyển sang Bác sĩ AI Vận hành</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <MarketingCalendar
        campaigns={campaigns.length > 0 ? campaigns : [campaign]}
        contents={contents}
        selectedCampaign={campaign}
        onSelectCampaign={onSelectCampaign || (() => {})}
      />
    </div>
  );
};
