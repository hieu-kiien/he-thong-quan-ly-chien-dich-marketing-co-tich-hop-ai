/**
 * FEAT-FE-14: Export Campaign Contents to Excel (.csv UTF-8 with BOM) and PDF Print Layout
 * Đảm bảo 100% không bao giờ lỗi font tiếng Việt trên Microsoft Excel Windows.
 */

import { MarketingContent } from '../types';

/**
 * Thoát ký tự ô CSV an toàn
 */
function escapeCsvCell(value: any): string {
  if (value === null || value === undefined) return '""';
  const str = String(value).replace(/"/g, '""');
  return `"${str}"`;
}

/**
 * Xuất danh sách nội dung tiếp thị của chiến dịch ra file CSV UTF-8 with BOM
 */
export function exportCampaignContentsToCSV(campaignName: string, contents: MarketingContent[]): boolean {
  if (!contents || contents.length === 0) {
    alert('Chiến dịch chưa có nội dung nào để xuất dữ liệu.');
    return false;
  }

  // Tiền tố BOM chống vỡ font tiếng Việt trên Microsoft Excel
  const BOM = '\uFEFF';

  const headers = [
    'STT',
    'Kênh Truyền Thông',
    'Tiêu Đề Bài Viết',
    'Nội Dung Chi Tiết',
    'Lời Kêu Gọi (CTA)',
    'Link Ảnh / Banner',
    'Trạng Thái',
    'Phiên Bản',
    'Ngày Tạo'
  ];

  const rows = contents.map((c, index) => {
    const channelName = c.channel?.name || c.channel?.code || (c.channel_id === 1 ? 'Facebook' : c.channel_id === 4 ? 'TikTok' : 'Email');
    const createdDate = c.created_at ? new Date(c.created_at).toLocaleDateString('vi-VN') : '';
    return [
      escapeCsvCell(index + 1),
      escapeCsvCell(channelName),
      escapeCsvCell(c.title || ''),
      escapeCsvCell(c.body || ''),
      escapeCsvCell(c.cta || ''),
      escapeCsvCell(c.image_url || ''),
      escapeCsvCell(c.status || ''),
      escapeCsvCell(`v${c.version_no || 1}`),
      escapeCsvCell(createdDate)
    ].join(',');
  });

  const csvContent = BOM + [headers.map(escapeCsvCell).join(','), ...rows].join('\r\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  const safeCampaignName = (campaignName || 'Campaign')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9_-]/g, '_');
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');

  link.href = url;
  link.setAttribute('download', `Ke_Hoach_Chien_Dich_${safeCampaignName}_${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}

/**
 * Mở hộp thoại In / Lưu PDF với định dạng trang Agency chuẩn A4.
 * Tùy chọn nhận danh sách contents và campaignName để chuẩn bị sẵn sàng dữ liệu in.
 */
export function printCampaignPlan(contents?: MarketingContent[], campaignName?: string): void {
  if (contents && contents.length === 0) {
    alert('Không có nội dung để in hoặc xuất PDF.');
    return;
  }
  // Kích hoạt hộp thoại in tiêu chuẩn của trình duyệt (áp dụng stylesheet @media print)
  window.print();
}
