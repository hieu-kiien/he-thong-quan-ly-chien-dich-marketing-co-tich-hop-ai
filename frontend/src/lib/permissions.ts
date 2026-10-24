import type { CampaignListItem, Content, Metric, Schedule, User } from './types';

/** Kiểm tra quyền phía UI theo CONTRACT §2 (backend vẫn là nơi quyết định cuối). */

export const isManager = (user: User | null | undefined): boolean => user?.role === 'MANAGER';

export function canEditCampaign(user: User | null, campaign: Pick<CampaignListItem, 'owner'>): boolean {
  if (!user) return false;
  return isManager(user) || campaign.owner.id === user.id;
}

export function isContentCreator(user: User | null, content: Pick<Content, 'created_by'>): boolean {
  return !!user && content.created_by?.id === user.id;
}

export function canEditContent(user: User | null, content: Pick<Content, 'status' | 'created_by'>): boolean {
  if (!user) return false;
  if (isManager(user)) return content.status !== 'APPROVED' && content.status !== 'PUBLISHED';
  return isContentCreator(user, content) && (content.status === 'DRAFT' || content.status === 'REJECTED');
}

export function canDeleteContent(user: User | null, content: Pick<Content, 'status' | 'created_by'>): boolean {
  if (content.status !== 'DRAFT' && content.status !== 'REJECTED') return false;
  return canEditContent(user, content);
}

export function canSubmitContent(user: User | null, content: Pick<Content, 'status' | 'created_by'>): boolean {
  return isContentCreator(user, content) && (content.status === 'DRAFT' || content.status === 'REJECTED');
}

/** Trả về null nếu được duyệt, hoặc lý do không được duyệt (để hiển thị nút bị khoá kèm giải thích). */
export function reviewBlockReason(user: User | null, content: Pick<Content, 'status' | 'created_by'>): string | null {
  if (!isManager(user)) return 'Chỉ Quản lý được duyệt nội dung.';
  if (content.status !== 'PENDING_REVIEW') return 'Nội dung không ở trạng thái chờ duyệt.';
  if (isContentCreator(user, content)) return 'Bạn không thể tự duyệt nội dung do chính mình tạo.';
  return null;
}

export function canMarkPublished(
  user: User | null,
  content: Pick<Content, 'status' | 'created_by' | 'id'>,
  schedules: Pick<Schedule, 'assignee' | 'content_id' | 'status'>[] = [],
): boolean {
  if (!user || content.status !== 'APPROVED') return false;
  if (isManager(user) || isContentCreator(user, content)) return true;
  return schedules.some((s) => s.content_id === content.id && s.status === 'PLANNED' && s.assignee?.id === user.id);
}

export function canEditMetric(user: User | null, metric: Pick<Metric, 'entered_by'>): boolean {
  if (!user) return false;
  return isManager(user) || metric.entered_by?.id === user.id;
}
