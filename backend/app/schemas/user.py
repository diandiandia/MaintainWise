from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional
from datetime import datetime

class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    full_name: str
    role_code: str
    work_type: str
    force_change_password: bool

class ForceChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8, description="新密码至少8位")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=64)
    employee_no: str = Field(..., min_length=2, max_length=32)
    email: EmailStr
    phone: Optional[str] = None
    role_code: str = Field(..., description="ADMIN, ENGINEER, TECHNICIAN")
    work_type: str = Field(..., description="ELECTRICAL, MECHANICAL, AUTOMATION, GENERAL")

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role_code: Optional[str] = None
    work_type: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    employee_no: str
    email: str
    phone: Optional[str] = None
    role_code: str
    work_type: str
    is_active: bool
    force_change_password: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
