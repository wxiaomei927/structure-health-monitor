from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Device, Measurement, Zone
from app.schemas.measurement import (
    DeviceCreate,
    DeviceUpdate,
    MeasurementIn,
    MeasurementOut,
    StatsSummary,
)

# 硬件侧 params 下的字段名与数据库列同名，这里只做一次映射，之后各层都用统一的列名
PARAM_FIELDS = (
    "resistance_ohm",
    "phase_deg",
    "impedance_magnitude_ohm",
    "frequency_hz",
)

# 电阻到应变的换算系数，涂层开裂时两者同向变化，近似线性
STRAIN_COEFFICIENT = 0.85
STRAIN_OFFSET = -820.0


class DeviceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_devices(self) -> list[Device]:
        stmt = select(Device).order_by(Device.device_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_device(self, device_id: str) -> Optional[Device]:
        stmt = select(Device).where(Device.device_id == device_id)
        return self.db.execute(stmt).scalars().first()

    def get_by_id(self, pk: int) -> Optional[Device]:
        return self.db.get(Device, pk)

    def create_device(self, payload: DeviceCreate) -> Device:
        device = Device(
            device_id=payload.device_id,
            name=payload.name,
            model=payload.model,
            location=payload.location,
        )
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def update_device(self, device: Device, payload: DeviceUpdate) -> Device:
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(device, key, value)
        self.db.commit()
        self.db.refresh(device)
        return device

    def delete_device(self, device: Device) -> None:
        # measurements 上挂了 CASCADE，删设备时历史记录一并清掉
        self.db.delete(device)
        self.db.commit()

    def touch_seen(self, device_id: str, moment: datetime) -> None:
        device = self.get_device(device_id)
        if device is None:
            return
        device.last_seen_at = moment
        device.status = "online"
        self.db.commit()


class MeasurementService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _extract_values(self, payload: MeasurementIn) -> dict[str, Optional[float]]:
        values: dict[str, Optional[float]] = {}
        for field in PARAM_FIELDS:
            item = payload.params.get(field)
            values[field] = None if item is None else item.value
        return values

    def ingest(self, payload: MeasurementIn) -> tuple[Measurement, dict[str, Optional[float]]]:
        values = self._extract_values(payload)
        device = DeviceService(self.db).get_device(payload.device_id)
        if device is None:
            device = Device(
                device_id=payload.device_id,
                name=payload.device_id,
                status="online",
            )
            self.db.add(device)
            self.db.flush()

        received_at = datetime.now()
        record = Measurement(
            device_id=payload.device_id,
            resistance_ohm=values["resistance_ohm"],
            phase_deg=values["phase_deg"],
            impedance_magnitude_ohm=values["impedance_magnitude_ohm"],
            frequency_hz=None
            if values["frequency_hz"] is None
            else int(values["frequency_hz"]),
            strain_ue=self._to_strain(values["resistance_ohm"]),
            measured_at=payload.measured_at or received_at,
            received_at=received_at,
        )
        device.last_seen_at = received_at
        device.status = "online"

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        # 落库后立刻比对告警规则
        self._evaluate_alerts(record, device)

        return record, values

    @staticmethod
    def _to_strain(resistance: Optional[float]) -> Optional[float]:
        if resistance is None:
            return None
        return round(resistance * STRAIN_COEFFICIENT + STRAIN_OFFSET, 2)

    def _evaluate_alerts(self, record: Measurement, device: Device) -> None:
        from app.services.alert_service import AlertService

        if device.zone_id is None:
            return
        zone = self.db.get(Zone, device.zone_id)
        if zone is None:
            return
        AlertService(self.db).evaluate(record, zone)

    def list_measurements(
        self,
        device_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
        offset: int = 0,
        order: str = "desc",
    ) -> list[Measurement]:
        stmt = select(Measurement)
        if device_id:
            stmt = stmt.where(Measurement.device_id == device_id)
        if start:
            stmt = stmt.where(Measurement.measured_at >= start)
        if end:
            stmt = stmt.where(Measurement.measured_at <= end)

        # order 只接受 asc / desc，避免把用户输入拼进 SQL
        column = Measurement.measured_at if order == "asc" else Measurement.measured_at.desc()
        stmt = stmt.order_by(column).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def count_measurements(
        self,
        device_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        stmt = select(func.count(Measurement.id))
        if device_id:
            stmt = stmt.where(Measurement.device_id == device_id)
        if start:
            stmt = stmt.where(Measurement.measured_at >= start)
        if end:
            stmt = stmt.where(Measurement.measured_at <= end)
        return int(self.db.execute(stmt).scalar() or 0)

    def latest(self, device_id: str, limit: int = 50) -> list[Measurement]:
        stmt = (
            select(Measurement)
            .where(Measurement.device_id == device_id)
            .order_by(Measurement.measured_at.desc())
            .limit(limit)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return list(reversed(rows))

    def summary(
        self,
        device_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[StatsSummary]:
        stmt = select(
            Measurement.device_id,
            func.count(Measurement.id),
            func.avg(Measurement.resistance_ohm),
            func.min(Measurement.resistance_ohm),
            func.max(Measurement.resistance_ohm),
            func.avg(Measurement.phase_deg),
            func.avg(Measurement.impedance_magnitude_ohm),
            func.avg(Measurement.frequency_hz),
            func.avg(Measurement.strain_ue),
        )
        if device_id:
            stmt = stmt.where(Measurement.device_id == device_id)
        if start:
            stmt = stmt.where(Measurement.measured_at >= start)
        if end:
            stmt = stmt.where(Measurement.measured_at <= end)
        stmt = stmt.group_by(Measurement.device_id).order_by(Measurement.device_id)

        rows = self.db.execute(stmt).all()
        return [
            StatsSummary(
                device_id=row[0],
                count=int(row[1] or 0),
                resistance_avg=_round(row[2]),
                resistance_min=_round(row[3]),
                resistance_max=_round(row[4]),
                phase_avg=_round(row[5]),
                impedance_avg=_round(row[6]),
                frequency_avg=_round(row[7]),
                strain_avg=_round(row[8]),
            )
            for row in rows
        ]

    def purge_older_than(self, days: int) -> int:
        threshold = datetime.now() - timedelta(days=days)
        stmt = select(Measurement).where(Measurement.measured_at < threshold)
        rows = list(self.db.execute(stmt).scalars().all())
        for row in rows:
            self.db.delete(row)
        self.db.commit()
        return len(rows)


def _round(value, digits: int = 4):
    if value is None:
        return None
    return round(float(value), digits)
