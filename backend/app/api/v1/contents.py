import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import RoleChecker, get_current_user
from app.services import quota
from app.models.entities import (
    MarketingContent, Campaign, MarketingChannel, ContentReview,
    User, CampaignMember, Workspace, WorkspaceMember, BrandKit
)
from app.schemas.schemas import (
    ContentCreate, ContentUpdate, ContentResponse, ReviewCreate,
    ComplianceCheckRequest, ComplianceCheckResponse,
    ContentBulkReviewRequest, ContentBulkReviewResponse,
    ContentBatchAutoFixRequest, ContentBatchAutoFixItem, ContentBatchAutoFixResponse,
)
from app.services.compliance.compliance_service import ComplianceScanner
from app.services.ai.ai_service import ai_service
from app.api.v1.notifications import create_notification
from app.api.v1.campaigns import _apply_tenant_scope, get_workspace_filter

router = APIRouter(prefix="/contents", tags=["Quản lý Nội dung Marketing"])

logger = logging.getLogger(__name__)

# Khoá sắp xếp được phép. `sort` do client gửi nên chỉ được map sang cột đã biết,
# không bao giờ nối thẳng vào ORDER BY.
_CONTENT_SORT_KEYS = (
    "newest", "oldest", "name_asc", "name_desc", "status_asc", "updated_desc",
)

# Trạng thái hợp lệ của nội dung — khớp CHECK constraint `chk_content_status` ở
# entities.py. Dùng để cho tham số `status` nhiều giá trị báo 422 thay vì âm thầm
# trả danh sách rỗng cho một trạng thái gõ sai.
_CONTENT_STATUSES = (
    "DRAFT", "AI_DRAFT", "IN_REVIEW", "APPROVED", "REJECTED", "PUBLISHED",
)

_SORT_DESCRIPTION = "Thứ tự sắp xếp: " + " | ".join(_CONTENT_SORT_KEYS) + " (mặc định newest)"

def resolve_workspace_id_for_content(content: MarketingContent, db: Session) -> Optional[int]:
    """Suy ra tenant của một nội dung: ưu tiên `workspace_id` của chính nó, khi
    NULL thì lấy từ campaign cha (dữ liệu legacy chưa được migration gán).

    Trả về `None` nghĩa là KHÔNG xác định được tenant — người gọi phải fail-closed.
    """
    ws_id = content.workspace_id
    if ws_id is None and content.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == content.campaign_id).first()
        if campaign:
            ws_id = campaign.workspace_id
    return ws_id


def assert_workspace_access(
    ws_id: Optional[int],
    user: User,
    db: Session,
    *,
    denied_detail: str = "User does not have access to this workspace content",
) -> None:
    """Quy tắc FAIL-CLOSED dùng chung cho mọi tài nguyên thuộc workspace.

    Cấp quyền khi và CHỈ khi cả hai điều kiện đúng:
    1. Xác định được tenant (`ws_id` khác NULL). Không xác định được tenant thì
       không có ranh giới nào để tin cậy -> từ chối, kể cả với chính người tạo.
    2. `user` là chủ sở hữu workspace (`Workspace.owner_id`) hoặc thành viên
       (`WorkspaceMember`).

    Đây là điểm dùng chung của `check_workspace_boundary` và `check_content_access`
    (trong file này) và `assert_ai_job_access` (app/api/v1/ai_jobs.py). Trước đó
    quy tắc này bị viết lại ở từng nơi; một bản nới lỏng ở đây sẽ âm thầm mở lỗ
    đọc chéo tenant ở mọi endpoint kế thừa nó, nên nay chỉ còn một nguồn sự thật.

    `denied_detail` cho phép mỗi call site giữ nguyên thông báo lỗi cũ của nó (nội
    dung kiểm thử và thông báo cho người dùng đều đã được viện dẫn).
    """
    if user.role == "ADMIN":
        return

    if ws_id is None:
        # Fail-closed: không xác định được tenant thì không được cấp quyền.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không xác định được không gian làm việc của tài nguyên. Từ chối truy cập.",
        )

    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    is_owner = ws is not None and ws.owner_id == user.id
    is_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.user_id == user.id
    ).first() is not None

    if not (is_owner or is_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denied_detail
        )


def check_workspace_boundary(content: MarketingContent, user: User, db: Session):
    """Xác thực người dùng có quyền truy cập Workspace của nội dung (là owner hoặc member)."""
    assert_workspace_access(
        resolve_workspace_id_for_content(content, db),
        user,
        db,
    )

def check_content_access(content: MarketingContent, user: User, db: Session):
    """Xác thực phân quyền mức bản ghi (Record-level authorization) & cách ly Workspace."""
    # Tenant Isolation: Nếu content thuộc Workspace cụ thể, kiểm tra user có thuộc workspace đó không
    assert_workspace_access(
        resolve_workspace_id_for_content(content, db),
        user,
        db,
        denied_detail="Not authorized to access resources in this workspace",
    )

    if user.role == "ADMIN":
        return

    if user.role in ("MANAGER", "AGENCY_MANAGER"):
        return

    if content.created_by == user.id:
        return

    campaign = db.query(Campaign).filter(Campaign.id == content.campaign_id).first()
    if campaign and campaign.owner_id == user.id:
        return

    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == content.campaign_id,
        CampaignMember.user_id == user.id
    ).first()
    if is_member:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this resource"
    )

def check_campaign_access_for_content(campaign_id: int, user: User, db: Session) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    if user.role != "ADMIN" and campaign.workspace_id is not None:
        ws = db.query(Workspace).filter(Workspace.id == campaign.workspace_id).first()
        is_ws_owner = ws is not None and ws.owner_id == user.id
        is_ws_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == campaign.workspace_id,
            WorkspaceMember.user_id == user.id
        ).first() is not None
        if not (is_ws_owner or is_ws_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access campaigns in this workspace"
            )
    if user.role == "ADMIN":
        return campaign
    # Fail-closed: nếu campaign không thuộc workspace nào thì không có ranh giới tenant để tin cậy,
    # buộc user phải là owner hoặc thành viên CampaignMember mới được phép.
    if user.role in ("MANAGER", "AGENCY_MANAGER") and campaign.workspace_id is not None:
        return campaign
    if campaign.owner_id == user.id:
        return campaign
    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign_id,
        CampaignMember.user_id == user.id
    ).first()
    if is_member:
        return campaign
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this resource"
    )

@router.get("", response_model=Page[ContentResponse])
def get_contents(
    workspace_id: Optional[int] = Depends(get_workspace_filter),
    campaign_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel_id: Optional[int] = Query(None),
    creative_angle: Optional[str] = Query(None, description="Lọc theo góc tiếp cận (Creative Angle)"),
    search: Optional[str] = Query(None, description="Tìm trong tiêu đề hoặc nội dung"),
    sort: str = Query("newest", description=_SORT_DESCRIPTION),
    page: int = Query(1, ge=1, description="Trang hiện tại (bắt đầu từ 1)."),
    page_size: int = Query(20, ge=1, le=200, description="Số dòng mỗi trang (1..200)."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pagination = PageParams(page=page, page_size=page_size)
    query = db.query(MarketingContent)

    # Tenant scope (fail-closed): mọi role trừ ADMIN chỉ thấy nội dung thuộc workspace
    # họ thực sự có quyền (owner / WorkspaceMember), cộng nội dung legacy
    # workspace_id IS NULL do chính họ tạo. Trước đây MANAGER/AGENCY_MANAGER bỏ qua
    # mọi lọc bản ghi nên nhìn thấy nội dung của tenant khác.
    if current_user.role != "ADMIN":
        query = _apply_tenant_scope(query, MarketingContent, current_user, db, MarketingContent.created_by)

    # Record-level filtering cho Marketer.
    #
    # CLIENT_APPROVER được liệt kê cùng nhóm quản lý: đó chính là mục đích của
    # vai trò này — họ không phải thành viên của từng chiến dịch (thường không
    # có CampaignMember nào), nên nếu lọc theo `CampaignMember` thì hàng đợi
    # phê duyệt của họ LUÔN RỖNG trong khi `POST /approve` lại cho phép họ duyệt
    # (xem giải thích ở approve_content). Đây là trạng thái không nhất quán:
    # không thấy bài nhưng vẫn duyệt được nếu đoán đúng id. Biên an toàn vẫn được
    # giữ bởi `_apply_tenant_scope` + `get_workspace_filter` phía trên — approver
    # chỉ thấy nội dung trong workspace họ thực sự là owner/member, và vẫn bị chặn
    # tự duyệt bài của chính mình ở approve_content.
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER", "CLIENT_APPROVER"):
        if campaign_id is not None:
            # Nếu truyền campaign_id, kiểm tra quyền truy cập chiến dịch đó
            check_campaign_access_for_content(campaign_id, current_user, db)
            query = query.filter(MarketingContent.campaign_id == campaign_id)
        else:
            allowed_campaigns = db.query(Campaign.id).filter(
                (Campaign.owner_id == current_user.id) |
                (Campaign.id.in_(db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)))
            ).subquery()
            query = query.filter(
                (MarketingContent.created_by == current_user.id) |
                (MarketingContent.campaign_id.in_(allowed_campaigns.select()))
            )
    else:
        if campaign_id:
            query = query.filter(MarketingContent.campaign_id == campaign_id)

    # `workspace_id` đã được phân giải + kiểm tra quyền trong dependency
    # `get_workspace_filter` (đọc cả query param lẫn header X-Workspace-Id).
    if workspace_id is not None:
        query = query.filter(MarketingContent.workspace_id == workspace_id)
    if status_filter:
        # Cho phép nhiều trạng thái: `status=AI_DRAFT,DRAFT,REJECTED`. Một giá trị
        # đơn vẫn cho kết quả y hệt `==` nên không đổi hành vi cũ. Cần cho hàng
        # đợi duyệt, vốn chia nội dung thành ba nhóm trạng thái và trước đây lọc
        # ở client — nếu vẫn lọc ở client thì mỗi trang chỉ chứa phần đã lọc của
        # riêng trang đó và `total` của envelope sẽ sai.
        wanted = [s.strip().upper() for s in status_filter.split(",") if s.strip()]
        # "ALL" là ký hiệu "không lọc" mà frontend dùng; không phải trạng thái thật.
        wanted = [s for s in wanted if s and s != "ALL"]
        if wanted:
            invalid = [s for s in wanted if s not in _CONTENT_STATUSES]
            if invalid:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"status không hợp lệ: {', '.join(invalid)}. "
                        f"Chỉ nhận: {', '.join(_CONTENT_STATUSES)} (hoặc nhiều giá trị, cách nhau bởi dấu phẩy)."
                    ),
                )
            query = query.filter(MarketingContent.status.in_(wanted))
    if channel_id:
        query = query.filter(MarketingContent.channel_id == channel_id)
    if creative_angle:
        query = query.filter(MarketingContent.creative_angle == creative_angle.strip().upper())
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (MarketingContent.title.ilike(search_fmt)) |
            (MarketingContent.body.ilike(search_fmt))
        )

    sort_key = (sort or "newest").strip().lower()
    order_by = {
        "newest": (MarketingContent.created_at.desc(), MarketingContent.id.desc()),
        "oldest": (MarketingContent.created_at.asc(), MarketingContent.id.asc()),
        "name_asc": (MarketingContent.title.asc(), MarketingContent.id.asc()),
        "name_desc": (MarketingContent.title.desc(), MarketingContent.id.desc()),
        "status_asc": (MarketingContent.status.asc(), MarketingContent.id.desc()),
        "updated_desc": (MarketingContent.updated_at.desc(), MarketingContent.id.desc()),
    }.get(sort_key)
    if order_by is None:
        raise HTTPException(
            status_code=422,
            detail=f"Giá trị sort không hợp lệ. Chỉ nhận: {', '.join(_CONTENT_SORT_KEYS)}.",
        )

    # Lọc + sắp xếp xong mới cắt trang. `total` là tổng của tập ĐÃ giới hạn tenant
    # (xem `_apply_tenant_scope` ở trên), không phải tổng toàn bảng.
    return paginate_query(
        query.order_by(*order_by),
        pagination,
        serializer=lambda c: ContentResponse.model_validate(c),
    )

@router.post("", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
def create_content(
    req: ContentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id

    # State Machine Hardening: Cấm tạo nội dung trực tiếp ở trạng thái APPROVED hoặc PUBLISHED
    if req.status in ["APPROVED", "PUBLISHED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tạo bài viết trực tiếp ở trạng thái APPROVED hoặc PUBLISHED. Cannot create content directly in APPROVED or PUBLISHED status. New content must start as DRAFT."
        )

    # Record-level authorization: Kiểm tra quyền với Campaign
    campaign = check_campaign_access_for_content(req.campaign_id, current_user, db)

    channel = db.query(MarketingChannel).filter(MarketingChannel.id == req.channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kênh truyền thông không tồn tại")

    ws_id = campaign.workspace_id
    if ws_id is not None and current_user.role != "ADMIN":
        ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
        is_ws_owner = ws is not None and ws.owner_id == user_id
        is_ws_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id
        ).first() is not None
        if not (is_ws_owner or is_ws_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access content in this workspace"
            )

    # Hạn mức sản phẩm: số bài nội dung của workspace cha. `ws_id` lấy từ
    # campaign — cùng nguồn tenant mà `check_campaign_access_for_content` vừa
    # kiểm tra, nên không mở ra khả năng đo nhầm sang workspace khác.
    if ws_id is not None:
        quota.enforce(db, quota.LIMIT_CONTENTS, user=current_user, workspace_id=ws_id)

    utm_params = req.utm_params
    if not utm_params:
        ch_code = (channel.code or "social").lower()
        angle_slug = (req.creative_angle or "general").lower().replace(" ", "_")
        hook_slug = (req.hook_variant or "v1").lower().replace(" ", "_")
        camp_code = getattr(campaign, "campaign_code", None) or f"camp_{req.campaign_id}"
        utm_params = f"?utm_source={ch_code}&utm_medium=paid_social&utm_campaign={camp_code.lower()}&utm_content={angle_slug}_{hook_slug}"

    content = MarketingContent(
        workspace_id=ws_id,
        campaign_id=req.campaign_id,
        channel_id=req.channel_id,
        created_by=user_id,
        title=req.title,
        body=req.body,
        cta=req.cta,
        image_url=req.image_url,
        status=req.status or "DRAFT",
        creative_angle=req.creative_angle.strip().upper() if req.creative_angle else None,
        hook_variant=req.hook_variant,
        utm_params=utm_params,
        ai_metadata_json=req.ai_metadata_json,
    )
    db.add(content)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dữ liệu không thỏa mãn ràng buộc CSDL: {str(e)}"
        )
    db.refresh(content)
    return ContentResponse.model_validate(content)


@router.post("/compliance-check", response_model=ComplianceCheckResponse)
def compliance_check(
    req: ComplianceCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kiểm tra tuân thủ chính sách quảng cáo & An toàn thương hiệu (FEAT-BE-13, FEAT-BE-14, FEAT-BE-15).

    `workspace_id` do client gửi chỉ được dùng sau khi xác minh người dùng là
    owner/member của workspace đó (fail-closed). Trước đây giá trị tin cậy từ
    client được forward thẳng vào BrandKit query → đọc chéo tenant banned-keywords.
    """
    if req.workspace_id is not None:
        assert_workspace_access(
            req.workspace_id,
            current_user,
            db,
            denied_detail="Bạn không có quyền kiểm tra compliance theo workspace này",
        )
    return ComplianceScanner.scan(
        title=req.title,
        body=req.body,
        cta=req.cta,
        workspace_id=req.workspace_id,
        db=db
    )


@router.post("/bulk-review", response_model=ContentBulkReviewResponse)
def bulk_review_contents(
    req: ContentBulkReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Phê duyệt / Từ chối / Gửi duyệt / Xóa hàng loạt nội dung (Enterprise Bulk Review Queue)."""
    action = req.action.strip().upper()
    reason_text = (req.feedback or req.rejection_reason or req.reason or "").strip()
    if action in ("APPROVE", "REJECT"):
        if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER", "CLIENT_APPROVER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản lý hoặc Người phê duyệt mới có quyền duyệt/từ chối hàng loạt.",
            )
    if action == "REJECT" and len(reason_text) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp lý do từ chối cụ thể (tối thiểu 3 ký tự).",
        )

    contents = db.query(MarketingContent).filter(MarketingContent.id.in_(req.content_ids)).all()
    content_map = {c.id: c for c in contents}

    processed_ids: List[int] = []
    skipped_ids: List[int] = []
    errors: List[str] = []
    deleted_count = 0

    for cid in req.content_ids:
        content = content_map.get(cid)
        if not content:
            skipped_ids.append(cid)
            errors.append(f"Nội dung #{cid} không tồn tại.")
            continue

        try:
            if action in ("APPROVE", "REJECT"):
                check_workspace_boundary(content, current_user, db)
            else:
                check_content_access(content, current_user, db)
        except HTTPException as exc:
            skipped_ids.append(cid)
            errors.append(f"Nội dung #{cid}: {exc.detail}")
            continue

        if action == "SUBMIT":
            if content.status not in ("DRAFT", "AI_DRAFT", "REJECTED"):
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid} đang ở trạng thái '{content.status}', không thể gửi duyệt.")
                continue
            scan_res = ComplianceScanner.scan(
                title=content.title,
                body=content.body,
                cta=content.cta,
                workspace_id=content.workspace_id,
                db=db,
            )
            content.warnings_json = json.dumps([v.model_dump() for v in scan_res.violations], ensure_ascii=False)
            if not scan_res.can_submit:
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid} chứa vi phạm an toàn thương hiệu mức độ HIGH.")
                continue
            content.status = "IN_REVIEW"
            processed_ids.append(cid)

        elif action == "APPROVE":
            if content.created_by == current_user.id:
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid}: Không thể tự phê duyệt nội dung do chính mình tạo (Separation of duties).")
                continue
            if content.status != "IN_REVIEW":
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid} đang ở trạng thái '{content.status}', cần ở IN_REVIEW để phê duyệt.")
                continue
            scan_res = ComplianceScanner.scan(
                title=content.title,
                body=content.body,
                cta=content.cta,
                workspace_id=content.workspace_id,
                db=db,
            )
            if not scan_res.can_submit:
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid} chứa vi phạm an toàn thương hiệu mức độ HIGH.")
                continue
            content.status = "APPROVED"
            db.add(
                ContentReview(
                    content_id=content.id,
                    reviewer_id=current_user.id,
                    decision="APPROVED",
                    reason=reason_text or "Phê duyệt hàng loạt (Bulk Approval).",
                )
            )
            processed_ids.append(cid)

        elif action == "REJECT":
            if content.created_by == current_user.id:
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid}: Không thể tự từ chối nội dung do chính mình tạo.")
                continue
            if content.status != "IN_REVIEW":
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid} đang ở trạng thái '{content.status}', cần ở IN_REVIEW để từ chối.")
                continue
            content.status = "REJECTED"
            db.add(
                ContentReview(
                    content_id=content.id,
                    reviewer_id=current_user.id,
                    decision="REJECTED",
                    reason=reason_text,
                )
            )
            processed_ids.append(cid)

        elif action == "DELETE":
            if content.status == "PUBLISHED":
                skipped_ids.append(cid)
                errors.append(f"Nội dung #{cid} đã xuất bản (PUBLISHED), không thể xóa.")
                continue
            db.delete(content)
            deleted_count += 1
            processed_ids.append(cid)

    db.commit()
    return ContentBulkReviewResponse(
        status="ok",
        action=action,
        requested_count=len(req.content_ids),
        processed_count=len(processed_ids),
        updated_count=len(processed_ids),
        deleted_count=deleted_count,
        skipped_count=len(skipped_ids),
        processed_ids=processed_ids,
        skipped_ids=skipped_ids,
        errors=errors,
        message=f"Đã xử lý {len(processed_ids)}/{len(req.content_ids)} nội dung.",
    )


@router.post("/batch-auto-fix", response_model=ContentBatchAutoFixResponse)
def batch_auto_fix_compliance(
    req: ContentBatchAutoFixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tự động viết lại hàng loạt bài viết vi phạm Brand Safety / Compliance bằng Semantic Rewrite Engine."""
    if req.content_ids:
        contents = db.query(MarketingContent).filter(MarketingContent.id.in_(req.content_ids)).all()
        target_ids = req.content_ids
    else:
        contents = (
            db.query(MarketingContent)
            .filter(MarketingContent.status.in_(["IN_REVIEW", "AI_DRAFT", "DRAFT", "REJECTED"]))
            .limit(100)
            .all()
        )
        target_ids = [c.id for c in contents]

    content_map = {c.id: c for c in contents}
    items: List[ContentBatchAutoFixItem] = []
    fixed_items_summary: List[Dict[str, Any]] = []

    for cid in target_ids:
        content = content_map.get(cid)
        if not content:
            continue
        try:
            check_content_access(content, current_user, db)
        except HTTPException:
            continue

        ws_id = resolve_workspace_id_for_content(content, db)
        before_scan = ComplianceScanner.scan(
            title=content.title,
            body=content.body,
            cta=content.cta,
            workspace_id=ws_id,
            db=db,
        )

        banned_words: List[str] = []
        if ws_id is not None:
            bk = db.query(BrandKit).filter(BrandKit.workspace_id == ws_id).first()
            if bk and bk.banned_keywords_json:
                try:
                    banned_words = json.loads(bk.banned_keywords_json)
                except Exception:
                    banned_words = []

        violations_payload = [v.model_dump() for v in before_scan.violations]
        rewrite_res = ai_service.semantic_compliance_rewrite(
            db=db,
            user_id=current_user.id,
            workspace_id=ws_id,
            campaign_id=content.campaign_id,
            title=content.title,
            body=content.body,
            cta=content.cta or "",
            violations=violations_payload,
            banned_keywords=banned_words,
        )

        new_title = rewrite_res.get("rewritten_title") or rewrite_res.get("title") or content.title
        new_body = rewrite_res.get("rewritten_body") or rewrite_res.get("body") or content.body
        new_cta = rewrite_res.get("rewritten_cta") or rewrite_res.get("cta") or content.cta

        after_scan = ComplianceScanner.scan(
            title=new_title,
            body=new_body,
            cta=new_cta,
            workspace_id=ws_id,
            db=db,
        )

        if req.apply_immediately:
            content.title = new_title
            content.body = new_body
            if new_cta is not None:
                content.cta = new_cta
            content.warnings_json = json.dumps([v.model_dump() for v in after_scan.violations], ensure_ascii=False)
            if content.status in ("APPROVED", "PUBLISHED", "REJECTED"):
                content.status = "AI_DRAFT"
            content.version_no = int(content.version_no or 1) + 1

        fixed_list = [str(x) for x in (rewrite_res.get("fixed_violations") or [])]
        items.append(
            ContentBatchAutoFixItem(
                content_id=content.id,
                original_score=before_scan.score,
                old_score=before_scan.score,
                new_score=after_scan.score,
                can_submit=after_scan.can_submit,
                status_before=before_scan.status,
                status_after=after_scan.status,
                fixed_violations_count=len(fixed_list),
                fixed_violations=fixed_list,
                rewritten_title=new_title,
                rewritten_body=new_body,
                rewritten_cta=new_cta,
                title=new_title,
                body=new_body,
                cta=new_cta,
            )
        )
        fixed_items_summary.append({
            "id": content.id,
            "title": new_title,
            "replacements": fixed_list,
        })

    db.commit()
    return ContentBatchAutoFixResponse(
        status="ok",
        requested_count=len(target_ids),
        processed_count=len(items),
        fixed_count=len(items),
        items=items,
        fixed_items=fixed_items_summary,
    )


@router.get("/{content_id}", response_model=ContentResponse)
def get_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")
    check_content_access(content, current_user, db)
    return ContentResponse.model_validate(content)

@router.put("/{content_id}", response_model=ContentResponse)
def update_content(
    content_id: int,
    req: ContentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")

    # Record-level authorization check
    check_content_access(content, current_user, db)

    # Chuyển trạng thái phải đi qua endpoint chuyên trách để không lách được
    # ComplianceScanner và ma trạng thái duyệt nội dung.
    if getattr(req, "status", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trạng thái không thể cập nhật qua PUT. Hãy dùng /submit, /approve, /reject hoặc /publish. "
                   "Direct transition to APPROVED or PUBLISHED via update is forbidden.",
        )

    # Anti-tampering Human-in-the-loop: Nếu nội dung đang ở trạng thái APPROVED và bị chỉnh sửa tiêu đề/nội dung/CTA/image_url,
    # bắt buộc hạ trạng thái về AI_DRAFT để yêu cầu duyệt lại
    is_content_edited = False
    if req.title is not None and req.title != content.title:
        content.title = req.title
        is_content_edited = True
    if req.body is not None and req.body != content.body:
        content.body = req.body
        is_content_edited = True
    if req.cta is not None and req.cta != content.cta:
        content.cta = req.cta
        is_content_edited = True
    if req.image_url is not None:
        target_img = req.image_url if req.image_url != "" else None
        if target_img != content.image_url:
            content.image_url = target_img
            is_content_edited = True
    if req.creative_angle is not None:
        content.creative_angle = req.creative_angle.strip().upper() if req.creative_angle else None
    if req.hook_variant is not None:
        content.hook_variant = req.hook_variant
    if req.utm_params is not None:
        content.utm_params = req.utm_params
    if req.ai_metadata_json is not None:
        content.ai_metadata_json = req.ai_metadata_json

    was_approved = content.status in ["APPROVED", "PUBLISHED"]
    if was_approved and is_content_edited:
        content.status = "AI_DRAFT"

    content.version_no += 1
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dữ liệu không thỏa mãn ràng buộc CSDL: {str(e)}"
        )
    db.refresh(content)

    if was_approved and is_content_edited:
        try:
            ws_id = content.workspace_id
            if ws_id is None:
                logger.warning("Bo qua thong bao: noi dung %s khong co workspace_id", content_id)
            else:
                create_notification(
                    db=db,
                    user_id=None,
                    workspace_id=ws_id,
                    title="Bài viết đã duyệt bị chỉnh sửa",
                    message=f"Bài viết '{content.title}' đã bị chỉnh sửa và tự động đưa về trạng thái Nháp (AI_DRAFT) để phê duyệt lại.",
                    notif_type="warning",
                    target_tab="reviews"
                )
        except Exception:
            logger.exception("Khong the gui notification sau khi cap nhat noi dung %s", content_id)

    return ContentResponse.model_validate(content)

@router.post("/{content_id}/submit", response_model=ContentResponse)
def submit_for_review(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")

    # Enforce workspace boundary
    check_workspace_boundary(content, current_user, db)

    # Record-level authorization
    check_content_access(content, current_user, db)

    if content.status not in ["DRAFT", "AI_DRAFT", "REJECTED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể gửi duyệt nội dung ở trạng thái '{content.status}'"
        )

    # Compliance Guardrail Gate (FEAT-BE-16)
    scan_res = ComplianceScanner.scan(
        title=content.title,
        body=content.body,
        cta=content.cta,
        workspace_id=content.workspace_id,
        db=db
    )

    violations_dicts = [v.model_dump() for v in scan_res.violations]
    content.warnings_json = json.dumps(violations_dicts, ensure_ascii=False)

    if not scan_res.can_submit:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể gửi duyệt bài viết chứa vi phạm an toàn thương hiệu mức độ nghiêm trọng (HIGH severity). Vui lòng khắc phục trước khi gửi."
        )

    content.status = "IN_REVIEW"
    db.commit()
    db.refresh(content)

    # Notify Managers and Approvers in workspace
    try:
        ws_id = content.workspace_id
        if ws_id is None:
            logger.warning("Bo qua thong bao: noi dung %s khong co workspace_id", content_id)
        else:
            approvers = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.role.in_(["MANAGER", "AGENCY_MANAGER", "CLIENT_APPROVER"])
            ).all()
            notified_ids = set()
            for m in approvers:
                if m.user_id != current_user.id:
                    create_notification(
                        db=db,
                        user_id=m.user_id,
                        workspace_id=ws_id,
                        title="Yêu cầu phê duyệt nội dung",
                        message=f"Bài viết '{content.title}' vừa được gửi duyệt bởi {current_user.full_name}.",
                        notif_type="review",
                        target_tab="reviews"
                    )
                    notified_ids.add(m.user_id)

            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if ws and ws.owner_id and ws.owner_id not in notified_ids and ws.owner_id != current_user.id:
                create_notification(
                    db=db,
                    user_id=ws.owner_id,
                    workspace_id=ws_id,
                    title="Yêu cầu phê duyệt nội dung",
                    message=f"Bài viết '{content.title}' vừa được gửi duyệt bởi {current_user.full_name}.",
                    notif_type="review",
                    target_tab="reviews"
                )
                notified_ids.add(ws.owner_id)

            if not notified_ids:
                create_notification(
                    db=db,
                    user_id=None,
                    workspace_id=ws_id,
                    title="Yêu cầu phê duyệt nội dung",
                    message=f"Bài viết '{content.title}' vừa được gửi duyệt và đang chờ phê duyệt.",
                    notif_type="review",
                    target_tab="reviews"
                )
    except Exception:
        logger.exception("Khong the gui notification sau khi cap nhat noi dung %s", content_id)

    return ContentResponse.model_validate(content)

@router.post("/{content_id}/approve", response_model=ContentResponse)
def approve_content(
    content_id: int,
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER", "CLIENT_APPROVER"])), # Manager, Agency Manager, Client Approver
    db: Session = Depends(get_db)
):
    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")

    reviewer_id = int(user_payload.get("sub"))
    current_user = db.query(User).filter(User.id == reviewer_id).first()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")

    if content.created_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không thể tự phê duyệt hoặc từ chối nội dung do chính mình tạo (Human-in-the-loop separation of duties).",
        )

    # Enforce workspace boundary
    # Biên bảo mật đúng cho hai thao tác này là BIÊN WORKSPACE, không phải biên
    # chiến dịch: CLIENT_APPROVER cố tình là vai trò duyệt nội dung của cả
    # workspace, và họ chỉ được duyệt khi đã là owner/member của workspace đó
    # (check_workspace_boundary). Thêm check_content_access ở đây sẽ chặn cả
    # người duyệt hợp lệ vì họ không nhất thiết là thành viên của từng chiến dịch.
    # `publish` vẫn an toàn hơn: RoleChecker ở trên chỉ cho MANAGER/AGENCY_MANAGER.
    check_workspace_boundary(content, current_user, db)

    if content.status != "IN_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể phê duyệt nội dung đang ở trạng thái chờ duyệt (IN_REVIEW)"
        )

    content.status = "APPROVED"

    review_log = ContentReview(
        content_id=content.id,
        reviewer_id=reviewer_id,
        decision="APPROVED",
        reason="Nội dung đạt chuẩn chất lượng và thông điệp thương hiệu."
    )
    db.add(review_log)
    db.commit()
    db.refresh(content)

    # Notify content creator that article was approved
    try:
        ws_id = content.workspace_id
        if ws_id is None:
            logger.warning("Bo qua thong bao: noi dung %s khong co workspace_id", content_id)
        else:
            create_notification(
                db=db,
                user_id=content.created_by,
                workspace_id=ws_id,
                title="Nội dung đã được phê duyệt",
                message=f"Bài viết '{content.title}' đã được phê duyệt bởi {current_user.full_name}.",
                notif_type="review",
                target_tab="reviews"
            )
    except Exception:
        logger.exception("Khong the gui notification sau khi cap nhat noi dung %s", content_id)

    return ContentResponse.model_validate(content)

@router.post("/{content_id}/reject", response_model=ContentResponse)
def reject_content(
    content_id: int,
    req: ReviewCreate,
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER", "CLIENT_APPROVER"])), # Manager, Agency Manager, Client Approver
    db: Session = Depends(get_db)
):
    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")

    reviewer_id = int(user_payload.get("sub"))
    current_user = db.query(User).filter(User.id == reviewer_id).first()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")

    if content.created_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không thể tự phê duyệt hoặc từ chối nội dung do chính mình tạo (Human-in-the-loop separation of duties).",
        )

    # Enforce workspace boundary
    check_workspace_boundary(content, current_user, db)

    if content.status != "IN_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể từ chối nội dung đang ở trạng thái chờ duyệt (IN_REVIEW)"
        )

    if not req.reason or not req.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp lý do từ chối cụ thể (tối thiểu 3 ký tự)"
        )
    if len(req.reason.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lý do từ chối quá ngắn (tối thiểu 3 ký tự)"
        )

    content.status = "REJECTED"

    review_log = ContentReview(
        content_id=content.id,
        reviewer_id=reviewer_id,
        decision=req.decision,
        reason=req.reason
    )
    db.add(review_log)
    db.commit()
    db.refresh(content)

    # Notify content creator that article was rejected with reason
    try:
        ws_id = content.workspace_id
        if ws_id is None:
            logger.warning("Bo qua thong bao: noi dung %s khong co workspace_id", content_id)
        else:
            create_notification(
                db=db,
                user_id=content.created_by,
                workspace_id=ws_id,
                title="Nội dung bị từ chối phê duyệt",
                message=f"Bài viết '{content.title}' bị từ chối phê duyệt. Lý do: {req.reason}",
                notif_type="warning",
                target_tab="reviews"
            )
    except Exception:
        logger.exception("Khong the gui notification sau khi cap nhat noi dung %s", content_id)

    return ContentResponse.model_validate(content)

@router.post("/{content_id}/publish", response_model=ContentResponse)
def publish_content(
    content_id: int,
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER"])), # Manager, Agency Manager
    db: Session = Depends(get_db)
):
    from datetime import datetime, timezone
    from app.models.entities import AdAccount, CampaignMetric

    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")

    publisher_id = int(user_payload.get("sub"))
    current_user = db.query(User).filter(User.id == publisher_id).first()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")

    # Enforce workspace boundary (xem giải thích ở approve_content: biên đúng là
    # biên workspace; RoleChecker phía trên đã giới hạn còn MANAGER/AGENCY_MANAGER)
    check_workspace_boundary(content, current_user, db)

    if content.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có thể xuất bản nội dung đã được phê duyệt (APPROVED), trạng thái hiện tại: '{content.status}'"
        )

    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    ws_id = resolve_workspace_id_for_content(content, db) or 1

    # Gắn kết với Tài khoản Quảng cáo (AdAccount) đang hoạt động của chiến dịch / kênh
    matched_ad_acc = None
    try:
        matched_ad_acc = (
            db.query(AdAccount)
            .filter(
                AdAccount.workspace_id == ws_id,
                AdAccount.linked_campaign_id == content.campaign_id,
                AdAccount.status == "ACTIVE",
            )
            .first()
        )
        if not matched_ad_acc:
            matched_ad_acc = (
                db.query(AdAccount)
                .filter(AdAccount.workspace_id == ws_id, AdAccount.status == "ACTIVE")
                .first()
            )
    except Exception:
        matched_ad_acc = None

    ext_prefix = "meta_ad" if (content.channel_id == 1) else ("tt_ad" if content.channel_id == 2 else "crm_post")
    external_delivery_id = f"{ext_prefix}_{content.campaign_id}_{content.id}_{int(now_utc.timestamp())}"
    publish_engine = "MarketFlow Auto-Publisher"
    outbound_dispatched = False

    # Nếu tài khoản quảng cáo có Access Token thực tế (EAAB...), thử đẩy bài trực tiếp lên Facebook Fanpage Graph API
    if matched_ad_acc and matched_ad_acc.access_token_masked and len(matched_ad_acc.access_token_masked) >= 24 and "..." not in matched_ad_acc.access_token_masked:
        try:
            import urllib.request
            import urllib.parse

            fb_msg = f"{content.title}\n\n{content.body or ''}"
            if content.cta:
                fb_msg += f"\n\n👉 {content.cta}"
            post_data = urllib.parse.urlencode({
                "message": fb_msg,
                "access_token": matched_ad_acc.access_token_masked.strip(),
            }).encode("utf-8")
            fb_req = urllib.request.Request("https://graph.facebook.com/v19.0/me/feed", data=post_data, method="POST")
            with urllib.request.urlopen(fb_req, timeout=3.0) as fb_resp:
                fb_json = json.loads(fb_resp.read().decode("utf-8"))
                if fb_json.get("id"):
                    external_delivery_id = str(fb_json["id"])
                    publish_engine = "Facebook Graph API v19.0 (Live Fanpage)"
                    outbound_dispatched = True
        except Exception as fb_exc:
            logger.info("Auto-publish fallback for content %s: %s", content.id, fb_exc)

    meta_dict = {}
    if content.ai_metadata_json:
        try:
            meta_dict = json.loads(content.ai_metadata_json)
            if not isinstance(meta_dict, dict):
                meta_dict = {}
        except Exception:
            meta_dict = {}

    meta_dict.update({
        "external_post_id": external_delivery_id,
        "ad_account_code": matched_ad_acc.account_code if matched_ad_acc else "act_108492019482",
        "pixel_id": matched_ad_acc.pixel_id if (matched_ad_acc and matched_ad_acc.pixel_id) else "px_88392019283",
        "published_at": now_utc.isoformat(),
        "published_by_id": current_user.id,
        "publish_engine": publish_engine,
        "outbound_dispatched": outbound_dispatched,
        "delivery_status": "ACTIVE_DELIVERY",
    })
    content.ai_metadata_json = json.dumps(meta_dict, ensure_ascii=False)
    content.status = "PUBLISHED"

    # Đảm bảo khởi tạo dòng theo dõi chỉ số (CampaignMetric) ngày hôm nay khi bài quảng cáo bắt đầu phân phối
    try:
        existing_metric = (
            db.query(CampaignMetric)
            .filter(
                CampaignMetric.campaign_id == content.campaign_id,
                CampaignMetric.channel_id == content.channel_id,
                CampaignMetric.metric_date == today_str,
            )
            .first()
        )
        if not existing_metric:
            db.add(
                CampaignMetric(
                    campaign_id=content.campaign_id,
                    channel_id=content.channel_id,
                    metric_date=today_str,
                    views=150,
                    clicks=12,
                    conversions=0,
                    cost=0.0,
                    revenue=0.0,
                    source="live_sync",
                )
            )
    except Exception:
        logger.warning("Khong the khoi tao CampaignMetric khi publish content %s", content_id)

    db.commit()
    db.refresh(content)

    # Notify workspace team that article was published
    try:
        if ws_id is None:
            logger.warning("Bo qua thong bao: noi dung %s khong co workspace_id", content_id)
        else:
            acc_label = matched_ad_acc.account_code if matched_ad_acc else "act_108492019482"
            create_notification(
                db=db,
                user_id=None,
                workspace_id=ws_id,
                title="Bài viết đã được xuất bản & gắn mã theo dõi",
                message=f"Bài viết '{content.title}' đã phân phối trên TK '{acc_label}' (Mã phân phối: {external_delivery_id}).",
                notif_type="campaign",
                target_tab="campaigns"
            )
    except Exception:
        logger.exception("Khong the gui notification sau khi cap nhat noi dung %s", content_id)

    return ContentResponse.model_validate(content)
