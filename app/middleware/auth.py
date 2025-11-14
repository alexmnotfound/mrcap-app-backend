from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth
from app.db_models import UserRepository
from app.models import AppUser
from app.config import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Initialize Firebase Admin (if configured)
firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global firebase_app
    if settings.firebase_credentials_path:
        try:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized")
        except Exception as e:
            logger.warning(f"Firebase initialization failed: {e}")
    else:
        logger.warning("Firebase credentials not configured - auth will be disabled")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AppUser:
    """Get current authenticated user from Firebase token or dev mode"""
    # Development mode: bypass auth if enabled
    if settings.dev_mode:
        if settings.dev_user_id:
            user = UserRepository.find_by_id(settings.dev_user_id)
            if user:
                logger.warning(f"DEV MODE: Using user ID {settings.dev_user_id}")
                return user
            else:
                logger.error(f"DEV MODE: User ID {settings.dev_user_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dev user ID {settings.dev_user_id} not found"
                )
        else:
            logger.warning("DEV MODE enabled but DEV_USER_ID not set")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DEV_MODE enabled but DEV_USER_ID not configured"
            )

    # Production mode: require Firebase
    if not firebase_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Set DEV_MODE=true for local testing."
        )

    try:
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        firebase_uid = decoded_token["uid"]

        user = UserRepository.find_by_firebase_uid(firebase_uid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active"
            )

        return user
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def require_admin(current_user: AppUser = Depends(get_current_user)) -> AppUser:
    """Require admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

