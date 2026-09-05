from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class SmtpConfigSaveRequest(BaseModel):
    smtp_host: str = Field(..., min_length=2, max_length=128, description="SMTP 服务器地址")
    smtp_port: int = Field(465, ge=1, le=65535, description="端口号，如 465, 587, 25")
    smtp_user: str = Field(..., min_length=2, max_length=128, description="发信认证账号/邮箱")
    smtp_pass: Optional[str] = Field(None, description="授权码/密码。留空或输入 ****** 则保持原密码不变")
    sender_name: str = Field("MaintainWise 智能运维中心", min_length=1, max_length=64, description="发件人显示昵称")
    use_ssl: bool = Field(True, description="是否启用 SSL/TLS")
    use_tls: bool = Field(False, description="是否启用 STARTTLS")
    is_active: bool = Field(True, description="是否启用邮件服务")

class SmtpConfigResponse(BaseModel):
    id: int
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass_masked: str = Field("******", description="已脱敏的密码显示")
    sender_name: str
    use_ssl: bool
    use_tls: bool
    is_active: bool
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class SmtpTestRequest(BaseModel):
    to_email: str = Field(..., min_length=3, max_length=128, description="目标收件邮箱")
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    sender_name: Optional[str] = None
    use_ssl: Optional[bool] = None
    use_tls: Optional[bool] = None
