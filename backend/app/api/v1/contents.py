from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.entities import MarketingContent, Campaign, MarketingChannel, ContentReview, User
from app.schemas.schemas import ContentCreate, ContentUpdate, ContentResponse, ReviewCreate

router = APIRouter(prefix="/contents", tags=["Quản lý Nội dung Marketing"])

@router.get("", response_model=List[ContentResponse])
def get_contents(
    campaign_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(MarketingContent)
    if campaign_id:
        query = query.filter(MarketingContent.campaign_id == campaign_id)
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

    # Kiểm tra campaign và channel
    campaign = db.query(Campaign).filter(Campaign.id == req.campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    channel = db.query(MarketingChannel).filter(MarketingChannel.id == req.channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kênh truyền thông không tồn tại")

    content = MarketingContent(
        campaign_id=req.campaign_id,
        channel_id=req.channel_id,
        created_by=user_id,
        title=req.title,
        body=req.body,
        cta=req.cta,
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

@router.get("/{content_id}", response_model=ContentResponse)
def get_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")
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

    # BUG-BE-07: Không cho phép tự ý chuyển trạng thái sang APPROVED qua PUT
    if req.status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể chuyển trạng thái trực tiếp sang APPROVED. Bài viết phải qua quy trình duyệt của Quản lý (/approve)."
        )

    # BUG-BE-07: Nếu nội dung đang ở trạng thái APPROVED và bị chỉnh sửa tiêu đề/nội dung/CTA,
    # bắt buộc hạ trạng thái về AI_DRAFT để yêu cầu duyệt lại (Anti-tampering Human-in-the-loop)
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

    if content.status == "APPROVED" and is_content_edited:
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

    if content.status not in ["DRAFT", "AI_DRAFT", "REJECTED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể gửi duyệt nội dung ở trạng thái '{content.status}'"
        )

    content.status = "IN_REVIEW"
    db.commit()
    db.refresh(content)
    return ContentResponse.model_validate(content)

@router.post("/{content_id}/approve", response_model=ContentResponse)
def approve_content(
    content_id: int,
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER"])), # Chỉ Manager mới có quyền duyệt!
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
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER"])), # Chỉ Manager mới được từ chối
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
