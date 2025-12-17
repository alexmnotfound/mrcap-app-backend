from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.middleware.auth import get_current_user, require_admin
from app.db_models import FundRepository
from app.models import Fund, FundPerformance, FundNav, FundNavCreate, FundNavUpdate


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


@router.get("/navs", response_model=List[FundNav])
async def list_all_navs(
    fund_id: Optional[int] = Query(None, description="Filter by fund ID"),
    current_user=Depends(require_admin),
):
    """List all NAVs (admin only)"""
    return FundRepository.get_all_navs(fund_id=fund_id)


@router.get("/{fund_id}/performance", response_model=FundPerformance)
async def get_fund_performance_by_id(
    fund_id: int,
    limit: Optional[int] = Query(12, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    """Get performance data for a specific fund"""
    performance = FundRepository.get_fund_performance_by_id(fund_id, limit=limit)
    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fund with id {fund_id} not found"
        )
    return performance


@router.post("/{fund_id}/navs", response_model=FundNav, status_code=status.HTTP_201_CREATED)
async def create_nav(
    fund_id: int,
    nav_data: FundNavCreate,
    current_user=Depends(require_admin),
):
    """Create a new NAV entry for a fund (admin only)"""
    # Verify fund exists
    funds = FundRepository.find_all()
    if not any(f.id == fund_id for f in funds):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fund with id {fund_id} not found"
        )
    
    # Ensure fund_id matches
    nav_data.fund_id = fund_id
    return FundRepository.create_nav(nav_data)


@router.put("/navs/{nav_id}", response_model=FundNav)
async def update_nav(
    nav_id: int,
    nav_data: FundNavUpdate,
    current_user=Depends(require_admin),
):
    """Update a NAV entry (admin only)"""
    nav = FundRepository.update_nav(nav_id, nav_data)
    if not nav:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NAV with id {nav_id} not found"
        )
    return nav


@router.delete("/navs/{nav_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nav(
    nav_id: int,
    current_user=Depends(require_admin),
):
    """Delete a NAV entry (admin only)"""
    deleted = FundRepository.delete_nav(nav_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NAV with id {nav_id} not found"
        )
    return None

