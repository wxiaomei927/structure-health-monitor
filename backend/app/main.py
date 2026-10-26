from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.services.auth_service import ensure_admin_user, get_current_user

settings = get_settings()

# 前端构建产物目录，开发时用不到
frontend_dist_path = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表并准备管理员账号"""
    try:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            ensure_admin_user(db)
        app.state.db_ready = True
    except Exception as exc:
        app.state.db_ready = False
        app.state.database_error = str(exc)
        print(f"[Resistance] 数据库初始化失败: {exc}", file=sys.stderr, flush=True)
    yield

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="电阻阻抗测量数据云端采集与可视化平台后端 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上报接口不挂登录依赖，采集终端不持有平台账号
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get(f"{settings.api_v1_prefix}/health/detail", tags=["health"], summary="数据库连通性检查")
def health_detail(user=Depends(get_current_user)):
    """数据库连通性检查"""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get(f"{settings.api_v1_prefix}/overview", tags=["dashboard"], summary="平台概览统计")
def overview(user=Depends(get_current_user)):
    """总览页的汇总统计"""
    from sqlalchemy import func, select

    from app.models.entities import (
        AlertRecord,
        Device,
        Measurement,
        Structure,
        Zone,
    )

    with SessionLocal() as db:
        structure_count = int(
            db.execute(select(func.count(Structure.id))).scalar() or 0
        )
        zone_count = int(db.execute(select(func.count(Zone.id))).scalar() or 0)
        device_count = int(db.execute(select(func.count(Device.id))).scalar() or 0)
        measurement_count = int(
            db.execute(select(func.count(Measurement.id))).scalar() or 0
        )
        online_count = int(
            db.execute(
                select(func.count(Device.id)).where(Device.status == "online")
            ).scalar()
            or 0
        )
        open_alerts = int(
            db.execute(
                select(func.count(AlertRecord.id)).where(
                    AlertRecord.acknowledged_at.is_(None)
                )
            ).scalar()
            or 0
        )
        critical_alerts = int(
            db.execute(
                select(func.count(AlertRecord.id)).where(
                    AlertRecord.acknowledged_at.is_(None),
                    AlertRecord.severity == "critical",
                )
            ).scalar()
            or 0
        )

    return {
        "structure_count": structure_count,
        "zone_count": zone_count,
        "device_count": device_count,
        "online_count": online_count,
        "measurement_count": measurement_count,
        "open_alert_count": open_alerts,
        "critical_alert_count": critical_alerts,
    }

# 前端构建后的静态资源托管
if frontend_dist_path.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist_path / "assets"), name="assets")
