from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, model_validator


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # User ID as UUID string
    exp: int  # Expiration epoch


class JobSearchStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    CLOSED = "CLOSED"


class UserPreferencesUpdate(BaseModel):
    job_search_status: JobSearchStatus
    weekly_digest_enabled: bool
    email_notifications: bool


class UserPreferencesResponse(UserPreferencesUpdate):
    user_id: UUID

    class Config:
        from_attributes = True


class CareerGoalsUpdate(BaseModel):
    target_role: str
    target_compensation_min: float
    target_compensation_max: float
    target_companies: list[str]
    timeline_months: int

    @model_validator(mode="after")
    def validate_compensation(self) -> CareerGoalsUpdate:
        if self.target_compensation_min > self.target_compensation_max:
            raise ValueError(
                "target_compensation_min cannot be greater than target_compensation_max"
            )
        return self


class CareerGoalsResponse(CareerGoalsUpdate):
    user_id: UUID

    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str

