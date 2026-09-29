import React from 'react';
import { Campaign, KPISummary } from '../../types';
import { AttributionTrendChart } from '../analytics';
import { ChannelROIComparison } from '../ChannelROIComparison';

interface BudgetTabProps {
  campaign: Campaign;
  campaignKpi: KPISummary | null;
}

export const BudgetTab: React.FC<BudgetTabProps> = ({
  campaign,
  campaignKpi,
}) => {
  return (
    <div className="space-y-6">
      <AttributionTrendChart
        channels={campaignKpi?.channel_metrics || []}
        totalCost={campaignKpi?.total_cost}
        totalRevenue={campaignKpi?.total_revenue}
      />
      <ChannelROIComparison
        campaign={campaign}
        kpi={campaignKpi}
      />
    </div>
  );
};
