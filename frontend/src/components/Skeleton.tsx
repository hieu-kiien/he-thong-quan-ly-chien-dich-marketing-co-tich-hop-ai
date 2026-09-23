import React from 'react';

export interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = 'h-4 w-full' }) => {
  return (
    <div className={`animate-pulse bg-slate-200/80 rounded-md ${className}`} />
  );
};

export const MetricCardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between h-36">
      <div className="space-y-2">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-7 w-20" />
      </div>
      <div className="flex items-end justify-between pt-4">
        <Skeleton className="h-3 w-36" />
        <Skeleton className="h-6 w-16 rounded-sm" />
      </div>
    </div>
  );
};

export const TableRowSkeleton: React.FC<{ cols?: number }> = ({ cols = 5 }) => {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: cols }).map((_, idx) => (
        <td key={idx} className="py-3.5 px-4">
          <div className="space-y-1.5">
            <Skeleton className={`h-3.5 ${idx === 0 ? 'w-48' : idx === 1 ? 'w-28' : 'w-20'}`} />
            {idx === 0 && <Skeleton className="h-2.5 w-32" />}
          </div>
        </td>
      ))}
    </tr>
  );
};

export const CampaignTableSkeleton: React.FC<{ rows?: number }> = ({ rows = 4 }) => {
  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
      <div className="p-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex gap-2">
          <Skeleton className="h-8 w-48 rounded-lg" />
          <Skeleton className="h-8 w-32 rounded-lg" />
        </div>
        <Skeleton className="h-4 w-28" />
      </div>
      <table className="w-full">
        <tbody className="divide-y divide-slate-100">
          {Array.from({ length: rows }).map((_, idx) => (
            <TableRowSkeleton key={idx} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const ReviewQueueSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-3 animate-pulse">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-24 rounded-full" />
              <Skeleton className="h-3 w-28" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-8 w-28 rounded-lg" />
              <Skeleton className="h-8 w-24 rounded-lg" />
            </div>
          </div>
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-16 w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
};

export const CampaignCardSkeleton: React.FC<{ count?: number }> = ({ count = 6 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4 animate-pulse">
          <div className="flex items-start justify-between">
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-3 w-20 rounded-full" />
              <Skeleton className="h-4 w-40" />
            </div>
            <Skeleton className="h-6 w-16 rounded-md" />
          </div>
          <Skeleton className="h-12 w-full rounded-lg" />
          <div className="pt-3 border-t border-slate-100 flex justify-between items-center">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-7 w-20 rounded-md" />
          </div>
        </div>
      ))}
    </div>
  );
};
