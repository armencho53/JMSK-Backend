"""Metal Price API controller"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from typing import Optional

from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.metal import MetalPriceResponse
from app.domain.services.metal_price_service import MetalPriceService

router = APIRouter()


@router.get("/price/{metal_code}", response_model=Optional[MetalPriceResponse])
def get_metal_price(
    metal_code: str = Path(..., description="Metal code (e.g., GOLD_24K, SILVER_925)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current market price for a metal type.
    
    Returns the current price per gram with caching (15 minute TTL).
    If the external API is unavailable, returns None gracefully without
    blocking the user workflow.
    
    This endpoint is non-blocking - API failures return None with 200 status
    to allow users to proceed with manual price entry.
    
    Requirements: 8.1, 8.2, 8.3, 8.4
    """
    service = MetalPriceService(db)
    result = service.get_current_price(
        metal_code=metal_code,
        tenant_id=current_user.tenant_id,
    )
    
    # Return None if API unavailable (non-blocking behavior)
    return result
