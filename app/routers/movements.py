from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models import (
    CashMovement,
    CashMovementCreate,
    FundShareMovement,
    FundShareMovementCreate,
    UserMovement,
    MovementReportRow,
)
from app.db_models import MovementRepository, AccountRepository
from app.middleware.auth import get_current_user, require_admin

router = APIRouter(prefix="/movements", tags=["movements"])


@router.get("/user/{user_id}", response_model=List[UserMovement])
async def get_user_movements(
    user_id: int,
    current_user = Depends(get_current_user)
):
    """Get all movements for a user (own or admin)"""
    # Users can view their own movements, admins can view any
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return MovementRepository.get_user_movements(user_id)


@router.get("/account/{account_id}", response_model=List[UserMovement])
async def get_account_movements(
    account_id: int,
    current_user = Depends(get_current_user)
):
    """Get all movements for an account"""
    # Verify account belongs to user or user is admin
    account = AccountRepository.find_by_id(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    if not current_user.is_admin and account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return MovementRepository.get_account_movements(account_id)


@router.post("/cash", response_model=CashMovement, status_code=status.HTTP_201_CREATED)
async def create_cash_movement(
    movement_data: CashMovementCreate,
    current_user = Depends(require_admin)
):
    """Create cash movement (admin only)"""
    # Verify account exists
    account = AccountRepository.find_by_id(movement_data.account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return MovementRepository.create_cash_movement(movement_data)


@router.post("/fund-share", response_model=FundShareMovement, status_code=status.HTTP_201_CREATED)
async def create_fund_share_movement(
    movement_data: FundShareMovementCreate,
    current_user = Depends(require_admin)
):
    """Create fund share movement (admin only)"""
    # Verify account exists
    account = AccountRepository.find_by_id(movement_data.account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return MovementRepository.create_fund_share_movement(movement_data)


@router.get("/report/cash-share", response_model=List[MovementReportRow])
async def get_cash_and_fund_report(
    current_user = Depends(require_admin)
):
    """Get combined cash/fund share movements for all accounts (admin only)"""
    return MovementRepository.get_cash_and_fund_report()

