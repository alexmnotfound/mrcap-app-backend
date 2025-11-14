from typing import List
from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user, require_admin
from app.db_models import AccountRepository
from app.models import AccountSummary


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/me", response_model=List[AccountSummary])
async def list_my_accounts(current_user=Depends(get_current_user)):
    return AccountRepository.get_account_summaries_by_user(current_user.id)


@router.get("/summary", response_model=List[AccountSummary])
async def list_all_accounts(current_user=Depends(require_admin)):
    return AccountRepository.get_account_summaries_for_admin()

