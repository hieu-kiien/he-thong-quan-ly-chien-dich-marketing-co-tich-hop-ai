import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.entities import MarketingContent, Campaign, MarketingChannel, ContentReview, User, CampaignMember
from app.schemas.schemas import (
    ContentCreate, ContentUpdate, ContentResponse, ReviewCreate,
    ComplianceCheckRequest, ComplianceCheckResponse
)
from app.services.compliance.compliance_service import ComplianceScanner

router = APIRouter(prefix="/contents", tags=["Quản lý Nội dung Marketing"])

def check_content_access(content: MarketingContent, user: User, db: Session):
    """Xác thực phân quyền mức bản ghi (Record-level authorization):
    User ADMIN / MANAGER / AGENCY_MANAGER có toàn quyền.
    User MARKETER chỉ được thao tác trên bài viết do mình tạo HOẶC thuộc chiến dịch mình sở hữu / là thành viên.
    """
    if user.role in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
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
    if user.role in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
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

@router.get("", response_model=List[ContentResponse])
def get_contents(
    workspace_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(MarketingContent)

    # Record-level filtering cho Marketer
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
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

    if workspace_id is not None:
        query = query.filter(MarketingContent.workspace_id == workspace_id)
    if status_filter:
        query = query.filter(MarketingContent.status == status_filter)
    if channel_id:
        query = query.filter(MarketingContent.channel_id == channel_id)
    return [ContentResponse.model_validate(c) for c in query.order_by(MarketingContent.id.desc()).all()]

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

    ws_id = req.workspace_id or campaign.workspace_id or 1

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

    # State Machine Hardening: Cấm cập nhật trực tiếp sang APPROVED hoặc PUBLISHED
    if req.status in ["APPROVED", "PUBLISHED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể chuyển trạng thái trực tiếp sang APPROVED hoặc PUBLISHED. Direct transition to APPROVED or PUBLISHED via update is forbidden. Use dedicated workflow endpoints /submit, /approve, /publish."
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

    if content.status in ["APPROVED", "PUBLISHED"] and is_content_edited:
        content.status = "AI_DRAFT"
    elif req.status is not None:
        content.status = req.status

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

    if content.status != "IN_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể phê duyệt nội dung đang ở trạng thái chờ duyệt (IN_REVIEW)"
        )

    reviewer_id = int(user_payload.get("sub"))
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

    reviewer_id = int(user_payload.get("sub"))
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

    if content.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có thể xuất bản nội dung đã được phê duyệt (APPROVED), trạng thái hiện tại: '{content.status}'"
        )

    content.status = "PUBLISHED"
    db.commit()
    db.refresh(content)
    return ContentResponse.model_validate(content)
