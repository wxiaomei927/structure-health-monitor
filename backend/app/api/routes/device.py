from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.measurement import DeviceCreate, DeviceOut, DeviceUpdate
from app.models.entities import User
from app.services.auth_service import require_editor
from app.services.measurement_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceOut], summary="设备列表")
def list_devices(db: Session = Depends(get_db)):
    return DeviceService(db).list_devices()


@router.post("", response_model=DeviceOut, summary="登记新设备")
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = DeviceService(db)
    if service.get_device(payload.device_id) is not None:
        raise HTTPException(status_code=409, detail=f"设备 {payload.device_id} 已存在")
    return service.create_device(payload)


@router.put("/{device_id}", response_model=DeviceOut, summary="修改设备信息")
def update_device(
    device_id: str,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = DeviceService(db)
    device = service.get_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return service.update_device(device, payload)


@router.delete("/{device_id}", summary="删除设备及其历史数据")
def delete_device(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    service = DeviceService(db)
    device = service.get_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    service.delete_device(device)
    return {"status": "ok", "device_id": device_id}
