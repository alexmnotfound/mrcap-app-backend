from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models import AppUser, AppUserCreate, AppUserUpdate
from app.db_models import UserRepository, AccountRepository
from app.middleware.auth import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[AppUser])
async def list_users(
    current_user: AppUser = Depends(require_admin)
):
    """List all users (admin only)"""
    return UserRepository.find_all()


@router.get("/{user_id}", response_model=AppUser)
async def get_user(
    user_id: int,
    current_user: AppUser = Depends(get_current_user)
):
    """Get user by ID (own profile or admin)"""
    user = UserRepository.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Users can view their own profile, admins can view any
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return user


@router.post("", response_model=AppUser, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: AppUserCreate,
    current_user: AppUser = Depends(require_admin)
):
    """Create user (admin only)"""
    # Check if user already exists
    existing = UserRepository.find_by_firebase_uid(user_data.firebase_uid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )

    return UserRepository.create(user_data)


@router.put("/{user_id}", response_model=AppUser)
async def update_user(
    user_id: int,
    user_data: AppUserUpdate,
    current_user: AppUser = Depends(require_admin)
):
    """Update user (admin only)"""
    user = UserRepository.update(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: AppUser = Depends(require_admin)
):
    """Delete user (admin only)"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    deleted = UserRepository.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.get("/{user_id}/accounts")
async def get_user_accounts(
    user_id: int,
    current_user: AppUser = Depends(get_current_user)
):
    """Get user's accounts"""
    # Users can view their own accounts, admins can view any
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return AccountRepository.find_by_user_id(user_id)

