from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.measurement import (
    MeasurementAck,
    MeasurementIn,
    MeasurementOut,
    StatsSummary,
)
from app.services.auth_service import require_login
from app.services.measurement_service import MeasurementService

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.post("", response_model=MeasurementAck, summary="接收设备上报的测量数据")
def receive_measurement(payload: MeasurementIn, db: Session = Depends(get_db)) -> MeasurementAck:
    """设备侧的数据入口，报文沿用 OneNET 物模型格式，顶层多带一个 device_id 区分设备"""
    service = MeasurementService(db)
    record, values = service.ingest(payload)
    return MeasurementAck(
        status="ok",
        id=record.id,
        device_id=record.device_id,
        received_at=record.received_at,
        values=values,
    )


@router.get("", response_model=list[MeasurementOut], summary="按条件查询历史测量数据")
def list_measurements(
    device_id: str | None = Query(default=None, description="设备编号，不填表示全部设备"),
    start: str | None = Query(default=None, description="起始时间，格式 2026-10-24T08:00:00"),
    end: str | None = Query(default=None, description="结束时间，格式 2026-10-24T20:00:00"),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)
    service = MeasurementService(db)
    return service.list_measurements(
        device_id=device_id,
        start=start_dt,
        end=end_dt,
        limit=limit,
        offset=offset,
        order=order,
    )


@router.get("/latest", response_model=list[MeasurementOut], summary="取某设备最近若干条记录")
def latest_measurements(
    device_id: str = Query(description="设备编号"),
    limit: int = Query(default=50, ge=1, le=1000),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    service = MeasurementService(db)
    return service.latest(device_id, limit=limit)


@router.get("/count", summary="统计符合条件的记录条数")
def count_measurements(
    device_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    service = MeasurementService(db)
    total = service.count_measurements(
        device_id=device_id,
        start=_parse_dt(start),
        end=_parse_dt(end),
    )
    return {"count": total}


@router.get("/stats", response_model=list[StatsSummary], summary="按设备汇总统计量")
def measurement_stats(
    device_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    service = MeasurementService(db)
    return service.summary(
        device_id=device_id,
        start=_parse_dt(start),
        end=_parse_dt(end),
    )


def _parse_dt(value: str | None):
    """把查询串里的时间文本转成 datetime，只给日期时按当天 00:00 处理"""
    if not value:
        return None
    text = value.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"无法解析的时间格式: {value}")
