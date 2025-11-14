from typing import Optional, Literal, Union, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, field_validator


# Enums
CashMovementType = Literal["deposit", "withdrawal", "fee"]
FundShareMovementType = Literal["subscription", "redemption"]
AppUserStatus = Literal["invited", "active", "suspended", "disabled"]


# User Models
class AppUserBase(BaseModel):
    firebase_uid: str
    email: str
    full_name: str
    is_admin: bool = False
    status: AppUserStatus = "invited"


class AppUserCreate(AppUserBase):
    pass


class AppUserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    status: Optional[AppUserStatus] = None


class AppUser(AppUserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Account Models
class AccountBase(BaseModel):
    account_number: str


class AccountCreate(AccountBase):
    user_id: int


class Account(AccountBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Cash Movement Models
class CashMovementBase(BaseModel):
    account_id: int
    type: CashMovementType
    amount: Union[str, Decimal]
    currency: str
    effective_date: date
    
    @field_validator('amount', mode='before')
    @classmethod
    def convert_amount(cls, v):
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if v is not None else None


class CashMovementCreate(CashMovementBase):
    pass


class CashMovement(CashMovementBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Fund Share Movement Models
class FundShareMovementBase(BaseModel):
    account_id: int
    fund_id: int
    cash_movement_id: Optional[int] = None
    type: FundShareMovementType
    shares_change: Union[str, Decimal]
    share_price: Union[str, Decimal]
    total_amount: Union[str, Decimal]
    effective_date: date
    
    @field_validator('shares_change', 'share_price', 'total_amount', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if v is not None else None


class FundShareMovementCreate(FundShareMovementBase):
    pass


class FundShareMovement(FundShareMovementBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Combined User Movement Model
class UserMovement(BaseModel):
    id: int
    type: Literal["cash", "fund_share"]
    account_id: int
    effective_date: date
    created_at: datetime
    # Cash movement fields
    cash_type: Optional[CashMovementType] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    # Fund share movement fields
    fund_id: Optional[int] = None
    fund_name: Optional[str] = None
    shares_change: Optional[str] = None
    share_price: Optional[str] = None
    total_amount: Optional[str] = None
    share_movement_type: Optional[FundShareMovementType] = None

    class Config:
        from_attributes = True


# Account Summary / Fund Performance Models
class FundPosition(BaseModel):
    fund_id: int
    fund_name: str
    currency: str
    total_shares: Union[str, Decimal]
    latest_nav_per_share: Optional[Union[str, Decimal]] = None
    market_value: Optional[Union[str, Decimal]] = None

    @field_validator('total_shares', 'latest_nav_per_share', 'market_value', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if v is not None else None


class AccountSummary(BaseModel):
    account_id: int
    account_number: str
    total_deposits: Union[str, Decimal]
    total_withdrawals: Union[str, Decimal]
    total_fees: Union[str, Decimal]
    net_invested: Union[str, Decimal]
    positions: List[FundPosition] = []
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None

    @field_validator('total_deposits', 'total_withdrawals', 'total_fees', 'net_invested', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if v is not None else None


class FundNavPoint(BaseModel):
    as_of_date: date
    nav_per_share: Union[str, Decimal]
    total_aum: Union[str, Decimal]

    @field_validator('nav_per_share', 'total_aum', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if v is not None else None


class FundPerformance(BaseModel):
    fund_id: int
    fund_name: str
    currency: str
    latest_nav_per_share: Optional[Union[str, Decimal]] = None
    navs: List[FundNavPoint] = []

    @field_validator('latest_nav_per_share', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if v is not None else None


class MovementReportRow(BaseModel):
    user_id: int
    user_full_name: str
    account_id: int
    account_number: str
    cash_movement_id: int
    cash_movement_type: CashMovementType
    effective_date: date
    amount: Union[str, Decimal]
    fund_share_movement_id: Optional[int] = None
    shares_change: Optional[Union[str, Decimal]] = None
    share_price: Optional[Union[str, Decimal]] = None

    @field_validator("amount", "shares_change", "share_price", mode="before")
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if v is not None else None

