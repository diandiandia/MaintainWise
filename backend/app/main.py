from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.init_db import init_db
from app.api.v1 import auth, users, locations, equipments, maintenance, faults, knowledge, training, dashboard, system

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行数据库与种子数据自检
    init_db()

    # 若启用了后台守护调度器 (Docker 生产环境)，启动后台定时任务
    scheduler = None
    if settings.RUN_BACKGROUND_SCHEDULER:
        from app.tasks.scheduler import start_background_scheduler
        scheduler = start_background_scheduler()

    yield

    if scheduler:
        scheduler.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# 1. 注册跨域资源共享 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 注册统一全局异常处理器
setup_exception_handlers(app)

# 3. 挂载 API V1 子路由
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(locations.router, prefix=settings.API_V1_STR)
app.include_router(equipments.router, prefix=settings.API_V1_STR)
app.include_router(maintenance.router, prefix=settings.API_V1_STR)
app.include_router(faults.router, prefix=settings.API_V1_STR)
app.include_router(knowledge.router, prefix=settings.API_V1_STR)
app.include_router(training.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(system.router, prefix=settings.API_V1_STR)

# 4. 健康检查探针
@app.get("/healthz", tags=["探针"])
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
