from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.middleware.auth import get_current_user
from app.db_models import FundRepository
from app.models import Fund, FundPerformance


router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("", response_model=List[Fund])
async def list_funds(
    current_user=Depends(get_current_user),
):
    """List all available funds"""
    return FundRepository.find_all()


# Note: /performance must come before /{fund_id}/performance
# to avoid matching "performance" as a fund_id
@router.get("/performance", response_model=List[FundPerformance])
async def get_fund_performance(
    limit: Optional[int] = Query(12, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    return FundRepository.get_fund_performance(limit=limit)


@router.get("/{fund_id}/performance", response_model=FundPerformance)
async def get_fund_performance_by_id(
    fund_id: int,
    limit: Optional[int] = Query(12, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    """Get performance data for a specific fund"""
    performance = FundRepository.get_fund_performance_by_id(fund_id, limit=limit)
    if not performance:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fund with id {fund_id} not found"
        )
    return performance

