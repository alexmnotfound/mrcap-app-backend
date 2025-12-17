from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models import (
    CashMovement,
    CashMovementCreate,
    CashMovementUpdate,
    FundShareMovement,
    FundShareMovementCreate,
    FundShareMovementUpdate,
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
    """Create cash movement (admin only). If deposit with fund_id, automatically creates subscription."""
    # Verify account exists
    account = AccountRepository.find_by_id(movement_data.account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Verify fund exists if fund_id is provided
    if movement_data.fund_id:
        from app.db_models import FundRepository
        fund = FundRepository.find_by_id(movement_data.fund_id)
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fund with id {movement_data.fund_id} not found"
            )

    try:
        return MovementRepository.create_cash_movement(movement_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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


@router.get("/fund-share/{movement_id}", response_model=FundShareMovement)
async def get_fund_share_movement(
    movement_id: int,
    current_user = Depends(require_admin)
):
    """Get a specific fund share movement (admin only)"""
    movement = MovementRepository.find_fund_share_movement_by_id(movement_id)
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fund share movement with id {movement_id} not found"
        )
    return movement


@router.put("/fund-share/{movement_id}", response_model=FundShareMovement)
async def update_fund_share_movement(
    movement_id: int,
    movement_data: FundShareMovementUpdate,
    current_user = Depends(require_admin)
):
    """Update a fund share movement (admin only)"""
    movement = MovementRepository.update_fund_share_movement(movement_id, movement_data)
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fund share movement with id {movement_id} not found"
        )
    return movement


@router.delete("/fund-share/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fund_share_movement(
    movement_id: int,
    current_user = Depends(require_admin)
):
    """Delete a fund share movement (admin only)"""
    deleted = MovementRepository.delete_fund_share_movement(movement_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fund share movement with id {movement_id} not found"
        )
    return None


@router.get("/report/cash-share", response_model=List[MovementReportRow])
async def get_cash_and_fund_report(
    current_user = Depends(require_admin)
):
    """Get combined cash/fund share movements for all accounts (admin only)"""
    return MovementRepository.get_cash_and_fund_report()


@router.get("/cash", response_model=List[CashMovement])
async def list_all_cash_movements(
    current_user = Depends(require_admin)
):
    """List all cash movements (admin only)"""
    return MovementRepository.get_all_cash_movements()


@router.get("/cash/{movement_id}", response_model=CashMovement)
async def get_cash_movement(
    movement_id: int,
    current_user = Depends(require_admin)
):
    """Get a specific cash movement (admin only)"""
    movement = MovementRepository.find_cash_movement_by_id(movement_id)
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cash movement with id {movement_id} not found"
        )
    return movement


@router.put("/cash/{movement_id}", response_model=CashMovement)
async def update_cash_movement(
    movement_id: int,
    movement_data: CashMovementUpdate,
    current_user = Depends(require_admin)
):
    """Update a cash movement (admin only). If deposit with fund_id and no subscription exists, creates subscription."""
    # Verify fund exists if fund_id is provided
    if movement_data.fund_id:
        from app.db_models import FundRepository
        fund = FundRepository.find_by_id(movement_data.fund_id)
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fund with id {movement_data.fund_id} not found"
            )
    
    try:
        movement = MovementRepository.update_cash_movement(movement_id, movement_data)
        if not movement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cash movement with id {movement_id} not found"
            )
        return movement
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/cash/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cash_movement(
    movement_id: int,
    current_user = Depends(require_admin)
):
    """Delete a cash movement (admin only)"""
    deleted = MovementRepository.delete_cash_movement(movement_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cash movement with id {movement_id} not found"
        )
    return None

