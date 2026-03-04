from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class TokenData(BaseModel):
    username: Optional[str] = None

# -------------------------
# Auth / Token
# -------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------------------------
# Users
# -------------------------
class UserBase(BaseModel):
    username: str
    role: str = "viewer"              # admin, manager, viewer
    department: Optional[str] = None  # used for manager/viewer


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    role: Optional[str] = None
    department: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    department: Optional[str] = None

    class Config:
        from_attributes = True


# -------------------------
# Dashboard Outputs
# -------------------------
class KPIOut(BaseModel):
    metric_name: str
    total_value: float
    average_value: float
    count: int


class DataRecordOut(BaseModel):
    id: int
    date: date
    department: str
    metric_name: str
    value: float

    class Config:
        from_attributes = True


# -------------------------
# Audit Logs (B1)
# -------------------------
class AuditLogOut(BaseModel):
    id: int
    user_id: int
    action: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True