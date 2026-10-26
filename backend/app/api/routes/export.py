from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.measurement_service import MeasurementService

router = APIRouter(prefix="/export", tags=["export"])

# 导出文件的列名用中文
COLUMN_LABELS = {
    "device_id": "设备编号",
    "resistance_ohm": "电阻(Ω)",
    "phase_deg": "相位角(°)",
    "impedance_magnitude_ohm": "阻抗幅值(Ω)",
    "frequency_hz": "频率(Hz)",
    "measured_at": "测量时间",
    "received_at": "接收时间",
}


@router.get("/measurements.csv", summary="导出测量数据为 CSV")
def export_csv(
    device_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """按条件导出测量记录"""
    rows = _fetch_rows(device_id, start, end, db)
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=list(COLUMN_LABELS.keys()))
    else:
        frame = frame.rename(columns=COLUMN_LABELS)

    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    # 加 BOM，否则 Excel 打开中文会乱码
    content = ("﻿" + buffer.getvalue()).encode("utf-8")

    filename = f"measurements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/measurements.xlsx", summary="导出测量数据为 Excel")
def export_excel(
    device_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = _fetch_rows(device_id, start, end, db)
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=list(COLUMN_LABELS.keys()))
    else:
        frame = frame.rename(columns=COLUMN_LABELS)
        for column in ("测量时间", "接收时间"):
            if column in frame.columns:
                frame[column] = frame[column].astype(str).str.slice(0, 19).str.replace("T", " ")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="测量数据", index=False)
    buffer.seek(0)

    filename = f"measurements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _fetch_rows(device_id, start, end, db):
    from app.api.routes.measurement import _parse_dt

    service = MeasurementService(db)
    records = service.list_measurements(
        device_id=device_id,
        start=_parse_dt(start),
        end=_parse_dt(end),
        limit=10000,
        order="asc",
    )
    return [
        {
            "device_id": item.device_id,
            "resistance_ohm": item.resistance_ohm,
            "phase_deg": item.phase_deg,
            "impedance_magnitude_ohm": item.impedance_magnitude_ohm,
            "frequency_hz": item.frequency_hz,
            "measured_at": item.measured_at.isoformat() if item.measured_at else "",
            "received_at": item.received_at.isoformat() if item.received_at else "",
        }
        for item in records
    ]
