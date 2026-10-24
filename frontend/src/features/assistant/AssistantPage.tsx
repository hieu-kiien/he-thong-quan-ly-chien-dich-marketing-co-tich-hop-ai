import { useParams, useSearchParams } from 'react-router-dom';
import { useDocumentTitle } from '@/lib/hooks';

/**
 * Placeholder cho khu vực Trợ lý AI (do agent khác xây dựng).
 * Trang được render trong <main> không padding, chiều cao đầy đủ (`h-full`),
 * tự quản lý bố cục 3 cột: danh sách phiên | hội thoại | "Đề xuất & bản nháp".
 * Tham số: `/assistant/:threadId`, và `?campaign_id=<id>` để mở phiên mới gắn chiến dịch.
 */
export default function AssistantPage() {
  useDocumentTitle('Trợ lý AI');
  const { threadId } = useParams();
  const [params] = useSearchParams();
  const campaignId = params.get('campaign_id');
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="text-center">
        <h1 className="text-xl font-semibold text-fg">Trợ lý AI</h1>
        <p className="mt-2 text-sm text-fg-muted">
          {threadId ? `Phiên #${threadId}` : campaignId ? `Phiên mới cho chiến dịch #${campaignId}` : 'Khu vực trợ lý đang được xây dựng.'}
        </p>
      </div>
    </div>
  );
}
