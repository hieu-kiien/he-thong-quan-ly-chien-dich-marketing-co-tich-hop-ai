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
from app.models.entities import MarketingContent, Campaign, MarketingChannel, ContentReview, User, CampaignMember, Workspace, WorkspaceMember
from app.schemas.schemas import (
    ContentCreate, ContentUpdate, ContentResponse, ReviewCreate,
    ComplianceCheckRequest, ComplianceCheckResponse
)
from app.services.compliance.compliance_service import ComplianceScanner
from app.api.v1.notifications import create_notification
from app.api.v1.campaigns import _apply_tenant_scope, get_workspace_filter

router = APIRouter(prefix="/contents", tags=["Quản lý Nội dung Marketing"])

logger = logging.getLogger(__name__)

# Khoá sắp xếp được phép. `sort` do client gửi nên chỉ được map sang cột đã biết,
# không bao giờ nối thẳng vào ORDER BY.
_CONTENT_SORT_KEYS = (
    "newest", "oldest", "name_asc", "name_desc", "status_asc", "updated_desc",
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
    search: Optional[str] = Query(None, description="Tìm trong tiêu đề hoặc nội dung"),
    sort: str = Query("newest", description=_SORT_DESCRIPTION),
    pagination: PageParams = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
        query = query.filter(MarketingContent.status == status_filter)
    if channel_id:
        query = query.filter(MarketingContent.channel_id == channel_id)
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

    content = MarketingContent(
        workspace_id=ws_id,
        campaign_id=req.campaign_id,
        channel_id=req.channel_id,
        created_by=user_id,
        title=req.title,
        body=req.body,
        cta=req.cta,
        image_url=req.image_url,
        status=req.status or "DRAFT"
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
    """Kiểm tra tuân thủ chính sách quảng cáo & An toàn thương hiệu (FEAT-BE-13, FEAT-BE-14, FEAT-BE-15)."""
    return ComplianceScanner.scan(
        title=req.title,
        body=req.body,
        cta=req.cta,
        workspace_id=req.workspace_id,
        db=db
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

    content.status = "PUBLISHED"
    db.commit()
    db.refresh(content)

    # Notify workspace team that article was published
    try:
        ws_id = content.workspace_id
        if ws_id is None:
            logger.warning("Bo qua thong bao: noi dung %s khong co workspace_id", content_id)
        else:
            create_notification(
                db=db,
                user_id=None,
                workspace_id=ws_id,
                title="Bài viết đã được xuất bản",
                message=f"Bài viết '{content.title}' đã được xuất bản thành công lên kênh truyền thông.",
                notif_type="campaign",
                target_tab="campaigns"
            )
    except Exception:
        logger.exception("Khong the gui notification sau khi cap nhat noi dung %s", content_id)

    return ContentResponse.model_validate(content)
