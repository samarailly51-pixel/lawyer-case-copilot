from contextlib import asynccontextmanager
import json
import logging
import time
import uuid
from sqlalchemy import text as sql_text

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.router import router
from api.auth_router import auth_router
from core.config import settings
from core.database import SessionLocal, init_db
from services.demo_data import backfill_document_quality, seed_demo_cases
from services.readiness import enforce_production_readiness
from core.auth import bootstrap_access


@asynccontextmanager
async def lifespan(app: FastAPI):
    enforce_production_readiness()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with SessionLocal() as db:
        if settings.seed_demo_data:
            seed_demo_cases(db)
        backfill_document_quality(db)
        bootstrap_access(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="面向案件负责律师的可追溯案件工作空间。系统仅提供办案辅助，不构成正式法律意见。",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(auth_router)


logger = logging.getLogger("lawyer_case_copilot.http")
logging.basicConfig(level=logging.INFO, format="%(message)s")

PUBLIC_DEMO_SAFE_POST_PATHS = {
    "/api/knowledge/search",
}


def public_demo_allows_mutation(method: str, path: str) -> bool:
    if method in {"GET", "HEAD", "OPTIONS"}:
        return True
    if method == "POST" and path in PUBLIC_DEMO_SAFE_POST_PATHS:
        return True
    if method == "POST" and path.startswith("/api/cases/") and path.endswith("/compensation-scenario"):
        return True
    return False


@app.middleware("http")
async def request_observability(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    if settings.public_demo_read_only and not public_demo_allows_mutation(request.method, request.url.path):
        response = JSONResponse(
            status_code=403,
            content={
                "detail": "公开演示环境为只读模式。请在本地运行项目体验创建、上传、复核和成员管理。",
                "code": "PUBLIC_DEMO_READ_ONLY",
            },
        )
    else:
        response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    logger.info(json.dumps({"event": "http_request", "request_id": request_id, "method": request.method,
                            "path": request.url.path, "status": response.status_code, "elapsed_ms": elapsed_ms},
                           ensure_ascii=False))
    return response


@app.get("/")
def root():
    if settings.serve_frontend and (settings.frontend_dist_dir / "index.html").exists():
        return FileResponse(settings.frontend_dist_dir / "index.html")
    return {"name": settings.app_name, "docs": "/docs", "disclaimer": "仅供办案辅助，须由律师复核。"}


@app.get("/health")
def public_health():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    with SessionLocal() as db:
        db.execute(sql_text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            response = await super().get_response("index.html", scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


if settings.serve_frontend and settings.frontend_dist_dir.exists():
    app.mount("/", SPAStaticFiles(directory=settings.frontend_dist_dir, html=True), name="frontend")
