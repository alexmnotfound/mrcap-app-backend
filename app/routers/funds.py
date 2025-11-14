from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.middleware.auth import get_current_user
from app.db_models import FundRepository
from app.models import FundPerformance


router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("/performance", response_model=List[FundPerformance])
async def get_fund_performance(
    limit: Optional[int] = Query(12, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    return FundRepository.get_fund_performance(limit=limit)

