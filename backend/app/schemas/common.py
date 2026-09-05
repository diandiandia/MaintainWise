from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
import time

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="业务状态码，0表示成功")
    message: str = Field(default="操作成功", description="响应说明")
    data: Optional[T] = Field(default=None, description="业务数据载荷")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="时间戳")

class PageResult(BaseModel, Generic[T]):
    items: List[T] = Field(default_factory=list, description="当前页数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
