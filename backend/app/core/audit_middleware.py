import time
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import AuditLog
from app.core.audit_context import current_user_id, current_username

AUDIT_EXCLUDED_PATHS = {"/healthz", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json", "/api/v1/auth/login"}

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        path = request.url.path
        if path in AUDIT_EXCLUDED_PATHS or path.startswith("/uploads/"):
            return response

        uid = current_user_id.get(None)
        uname = current_username.get(None)

        try:
            db: Session = SessionLocal()
            client_ip = request.client.host if request.client else "unknown"
            module_name = path.split("/")[3] if len(path.split("/")) > 3 else "unknown"
            method = request.method
            if method == "POST":
                action = "CREATE"
            elif method in ("PUT", "PATCH"):
                action = "UPDATE"
            elif method == "DELETE":
                action = "DELETE"
            else:
                action = "READ"

            log = AuditLog(
                user_id=uid,
                username=uname or "anonymous",
                client_ip=client_ip,
                module_name=module_name,
                action_type=action,
                request_url=path,
                request_method=method,
                status_code=response.status_code,
                diff_payload=None
            )
            db.add(log)
            db.commit()
            db.close()
        except Exception:
            pass

        return response