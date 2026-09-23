from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import MarketingChannel, Product, ProductCategory, User
from app.schemas.schemas import ChannelResponse, ProductResponse, ProductCategoryResponse

router = APIRouter(tags=["Quản lý Kênh & Sản phẩm"])

@router.get("/channels", response_model=List[ChannelResponse])
def get_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channels = db.query(MarketingChannel).filter(MarketingChannel.status == "ACTIVE").all()
    return [ChannelResponse.model_validate(c) for c in channels]

@router.get("/products", response_model=List[ProductResponse])
def get_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(Product.status == "ACTIVE").all()
    return [ProductResponse.model_validate(p) for p in products]

@router.get("/product-categories", response_model=List[ProductCategoryResponse])
def get_product_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cats = db.query(ProductCategory).all()
    return [ProductCategoryResponse.model_validate(c) for c in cats]
