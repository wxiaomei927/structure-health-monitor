from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import AlertRecord, User
from app.schemas.alert import AlertRecordOut, AlertRuleCreate, AlertRuleOut
from app.services.alert_service import ALERT_METRICS, AlertService
from app.services.auth_service import require_editor

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/records", response_model=list[AlertRecordOut], summary="告警记录列表")
def list_records(
    only_open: bool = Query(default=False, description="只看未处理的告警"),
    only_done: bool = Query(default=False, description="只看已处理的告警"),
    zone_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    service = AlertService(db)
    items = service.list_records(only_open=only_open, zone_id=zone_id, limit=limit)
    if only_done:
        items = [item for item in items if item.acknowledged_at is not None]
    return items


@router.post("/records/{record_id}/acknowledge", response_model=AlertRecordOut, summary="标记告警为已处理")
def acknowledge_record(
    record_id: int,
    operator: str = Query(default="admin"),
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    record = db.get(AlertRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="告警记录不存在")
    return AlertService(db).acknowledge(record, operator)


@router.post("/records/{record_id}/reopen", response_model=AlertRecordOut, summary="撤销处理")
def reopen_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    record = db.get(AlertRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="告警记录不存在")
    return AlertService(db).reopen(record)


@router.get("/summary", summary="告警概览统计")
def alert_summary(db: Session = Depends(get_db)):
    service = AlertService(db)
    records = service.list_records(limit=1000)
    open_records = [item for item in records if item.acknowledged_at is None]
    critical = [item for item in open_records if item.severity == "critical"]
    warning = [item for item in open_records if item.severity == "warning"]
    return {
        "total": len(records),
        "open": len(open_records),
        "critical": len(critical),
        "warning": len(warning),
        "acknowledged": len(records) - len(open_records),
    }


@router.get("/rules", response_model=list[AlertRuleOut], summary="告警规则列表")
def list_rules(
    zone_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return AlertService(db).list_rules(zone_id=zone_id)


@router.post("/rules", response_model=AlertRuleOut, summary="新建告警规则")
def create_rule(
    payload: AlertRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    if payload.metric not in ALERT_METRICS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的监测量，可选值：{', '.join(ALERT_METRICS)}",
        )
    if payload.lower_limit is None and payload.upper_limit is None:
        raise HTTPException(status_code=400, detail="上下限至少要填一个")
    if (
        payload.lower_limit is not None
        and payload.upper_limit is not None
        and payload.lower_limit >= payload.upper_limit
    ):
        raise HTTPException(status_code=400, detail="下限必须小于上限")
    return AlertService(db).create_rule(payload.model_dump())


@router.delete("/rules/{rule_id}", summary="删除告警规则")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
):
    from app.models.entities import AlertRule

    service = AlertService(db)
    rule = db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    service.delete_rule(rule)
    return {"status": "ok", "rule_id": rule_id}
