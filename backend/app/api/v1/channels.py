from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import Campaign, CampaignMetric, MarketingChannel, MarketingContent, Product, ProductCategory, User
from app.schemas.schemas import (
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    ProductCategoryResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(tags=["Quản lý Kênh & Sản phẩm"])


def _ensure_category_id(db: Session, requested_category_id: int | None) -> int:
    target_id = requested_category_id or 1
    cat = db.query(ProductCategory).filter(ProductCategory.id == target_id).first()
    if cat:
        return cat.id
    first_cat = db.query(ProductCategory).order_by(ProductCategory.id.asc()).first()
    if first_cat:
        return first_cat.id
    default_cat = ProductCategory(name="Sản phẩm & Dịch vụ", description="Danh mục mặc định")
    db.add(default_cat)
    db.flush()
    return default_cat.id


@router.get("/channels", response_model=List[ChannelResponse])
def get_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channels = db.query(MarketingChannel).filter(MarketingChannel.status == "ACTIVE").all()
    return [ChannelResponse.model_validate(c) for c in channels]


@router.post("/channels", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
def create_channel(
    req: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    code_norm = req.code.strip().lower()
    existing = db.query(MarketingChannel).filter(MarketingChannel.code == code_norm).first()
    if existing:
        existing.name = req.name.strip()
        if req.format_rules is not None:
            existing.format_rules = req.format_rules.strip() if req.format_rules else None
        existing.status = "ACTIVE"
        db.commit()
        db.refresh(existing)
        return ChannelResponse.model_validate(existing)

    channel = MarketingChannel(
        code=code_norm,
        name=req.name.strip(),
        format_rules=req.format_rules.strip() if req.format_rules else None,
        status="ACTIVE",
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return ChannelResponse.model_validate(channel)


@router.put("/channels/{channel_id}", response_model=ChannelResponse)
def update_channel(
    channel_id: int,
    req: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channel = db.query(MarketingChannel).filter(MarketingChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kênh truyền thông")

    update_data = req.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] is not None:
        channel.code = update_data["code"].strip().lower()
    if "name" in update_data and update_data["name"] is not None:
        channel.name = update_data["name"].strip()
    if "format_rules" in update_data:
        channel.format_rules = update_data["format_rules"].strip() if update_data["format_rules"] else None
    if "status" in update_data and update_data["status"] is not None:
        channel.status = update_data["status"]

    db.commit()
    db.refresh(channel)
    return ChannelResponse.model_validate(channel)


@router.delete("/channels/{channel_id}")
def delete_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channel = db.query(MarketingChannel).filter(MarketingChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kênh truyền thông")

    has_content = db.query(MarketingContent.id).filter(MarketingContent.channel_id == channel_id).first() is not None
    has_metric = db.query(CampaignMetric.id).filter(CampaignMetric.channel_id == channel_id).first() is not None
    if has_content or has_metric:
        channel.status = "INACTIVE"
    else:
        db.delete(channel)
    db.commit()
    return {"status": "DELETED", "id": channel_id}


@router.get("/products", response_model=List[ProductResponse])
def get_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(Product.status == "ACTIVE").all()
    return [ProductResponse.model_validate(p) for p in products]


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    req: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat_id = _ensure_category_id(db, req.category_id)
    product = Product(
        name=req.name.strip(),
        category_id=cat_id,
        description=req.description.strip() if req.description else None,
        usp=req.usp.strip() if req.usp else None,
        status="ACTIVE",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductResponse.model_validate(product)


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    req: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")

    update_data = req.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is not None:
        product.name = update_data["name"].strip()
    if "category_id" in update_data and update_data["category_id"] is not None:
        product.category_id = _ensure_category_id(db, update_data["category_id"])
    if "description" in update_data:
        product.description = update_data["description"].strip() if update_data["description"] else None
    if "usp" in update_data:
        product.usp = update_data["usp"].strip() if update_data["usp"] else None
    if "status" in update_data and update_data["status"] is not None:
        product.status = update_data["status"]

    db.commit()
    db.refresh(product)
    return ProductResponse.model_validate(product)


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")

    referenced = db.query(Campaign.id).filter(Campaign.product_id == product_id).first() is not None
    if referenced:
        product.status = "INACTIVE"
    else:
        db.delete(product)
    db.commit()
    return {"status": "DELETED", "id": product_id}


@router.get("/product-categories", response_model=List[ProductCategoryResponse])
def get_product_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cats = db.query(ProductCategory).all()
    return [ProductCategoryResponse.model_validate(c) for c in cats]
