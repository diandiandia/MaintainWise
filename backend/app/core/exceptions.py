from fastapi import Request, HTTPException, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time

class BusinessException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400, data: any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(self.message)

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": exc.data,
                "timestamp": int(time.time())
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # 格式化 Pydantic 参数错误信息
        errors = exc.errors()
        err_msg = "; ".join([f"{err.get('loc', [])}: {err.get('msg', '')}" for err in errors])
        return JSONResponse(
            status_code=400,
            content={
                "code": 20006, # 统一参数非法错误码
                "message": f"请求参数校验失败: {err_msg}",
                "data": errors,
                "timestamp": int(time.time())
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code = 10003 if exc.status_code == 403 else (10004 if exc.status_code == 401 else exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": code,
                "message": str(exc.detail),
                "data": None,
                "timestamp": int(time.time())
            }
        )
