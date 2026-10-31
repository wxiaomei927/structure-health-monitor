from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import User
from app.schemas.structure import (
    ImagingIn,
    ImagingOut,
    StructureCreate,
    StructureOut,
    StructureUpdate,
    ZoneCreate,
    ZoneOut,
    ZoneUpdate,
)
from app.services.auth_service import require_editor
from app.services.imaging_service import ImagingService
from app.services.structure_service import StructureService

router = APIRouter(prefix="/structures", tags=["structures"])


@router.get("", response_model=list[StructureOut], summary="结构列表")
def list_structures(db: Session = Depends(get_db)):
    return StructureService(db).list_structures()


@router.post("", response_model=StructureOut, summary="登记被监测结构")
def create_structure(
    payload: StructureCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = StructureService(db)
    if service.get_structure(payload.code) is not None:
        raise HTTPException(status_code=409, detail=f"结构编号 {payload.code} 已存在")
    return service.create_structure(payload)


@router.get("/zones", response_model=list[ZoneOut], summary="测区列表")
def list_zones(
    structure_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return StructureService(db).list_zones(structure_id=structure_id)


@router.post("/zones", response_model=ZoneOut, summary="登记测区")
def create_zone(
    payload: ZoneCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = StructureService(db)
    if service.get_zone(payload.code) is not None:
        raise HTTPException(status_code=409, detail=f"测区编号 {payload.code} 已存在")
    if service.get_structure_by_id(payload.structure_id) is None:
        raise HTTPException(status_code=404, detail="所属结构不存在")
    return service.create_zone(payload)


@router.get("/zones/{zone_code}", response_model=ZoneOut, summary="测区详情")
def get_zone(zone_code: str, db: Session = Depends(get_db)):
    zone = StructureService(db).get_zone(zone_code)
    if zone is None:
        raise HTTPException(status_code=404, detail="测区不存在")
    return zone


@router.put("/zones/{zone_code}", response_model=ZoneOut, summary="修改测区信息")
def update_zone(
    zone_code: str,
    payload: ZoneUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = StructureService(db)
    zone = service.get_zone(zone_code)
    if zone is None:
        raise HTTPException(status_code=404, detail="测区不存在")
    if payload.structure_id is not None and service.get_structure_by_id(payload.structure_id) is None:
        raise HTTPException(status_code=404, detail="所属结构不存在")
    return service.update_zone(zone, payload.model_dump(exclude_none=True))


@router.delete("/zones/{zone_code}", summary="删除测区")
def delete_zone(
    zone_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = StructureService(db)
    zone = service.get_zone(zone_code)
    if zone is None:
        raise HTTPException(status_code=404, detail="测区不存在")
    if service.devices_of_zone(zone.id):
        raise HTTPException(status_code=409, detail="该测区下还有采集终端，请先移出")
    db.delete(zone)
    db.commit()
    return {"status": "ok", "zone_code": zone_code}


@router.put("/{structure_code}", response_model=StructureOut, summary="修改结构信息")
def update_structure(
    structure_code: str,
    payload: StructureUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = StructureService(db)
    structure = service.get_structure(structure_code)
    if structure is None:
        raise HTTPException(status_code=404, detail="结构不存在")
    return service.update_structure(structure, payload.model_dump(exclude_none=True))

imaging_router = APIRouter(prefix="/imaging", tags=["imaging"])


@imaging_router.get("/latest", summary="取某测区最新一次成像结果")
def latest_imaging(
    zone_code: str = Query(description="测区编号"),
    db: Session = Depends(get_db),
):
    service = ImagingService(db)
    zone = StructureService(db).get_zone(zone_code)
    if zone is None:
        raise HTTPException(status_code=404, detail="测区不存在")
    result = service.latest(zone.id)
    if result is None:
        return {"zone_code": zone_code, "available": False}
    return _to_payload(result, zone_code)


@imaging_router.get("/history", summary="取某测区的成像历史")
def imaging_history(
    zone_code: str = Query(description="测区编号"),
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = ImagingService(db)
    zone = StructureService(db).get_zone(zone_code)
    if zone is None:
        raise HTTPException(status_code=404, detail="测区不存在")
    results = service.list_results(zone.id, limit=limit)
    return [
        {
            "id": item.id,
            "zone_code": zone_code,
            "grid_size": item.grid_size,
            "anomaly_count": item.anomaly_count,
            "peak_x": item.peak_x,
            "peak_y": item.peak_y,
            "scan_cost_ms": item.scan_cost_ms,
            "created_at": item.created_at.isoformat(),
        }
        for item in results
    ]


@imaging_router.post("", summary="上传一次成像结果")
def upload_imaging(
    payload: ImagingIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = ImagingService(db)
    zone = StructureService(db).get_zone(payload.zone_code)
    if zone is None:
        raise HTTPException(status_code=404, detail="测区不存在")
    result = service.store(
        zone_id=zone.id,
        matrix=payload.matrix,
        device_id=payload.device_id,
        scan_cost_ms=payload.scan_cost_ms,
    )
    return _to_payload(result, payload.zone_code)


def _to_payload(result, zone_code: str) -> dict:
    matrix = [float(v) for v in result.data.split(",")]
    size = result.grid_size
    rows = [matrix[i * size : (i + 1) * size] for i in range(size)]
    return {
        "id": result.id,
        "zone_code": zone_code,
        "available": True,
        "grid_size": size,
        "matrix": rows,
        "anomaly_count": result.anomaly_count,
        "peak_x": result.peak_x,
        "peak_y": result.peak_y,
        "scan_cost_ms": result.scan_cost_ms,
        "created_at": result.created_at.isoformat(),
    }
