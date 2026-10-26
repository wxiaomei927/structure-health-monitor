"""初始化演示数据：结构、测区、设备、告警规则与成像结果。

按「工程结构 → 测区 → 采集终端」的层级铺一套数据，
其中有一次带裂缝异常的成像结果，用来看成像页面的效果。
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.db.base import Base
from app.db.session import engine
from app.models.entities import (
    AlertRecord,
    AlertRule,
    Device,
    ImagingResult,
    Measurement,
    Structure,
    Zone,
)
from app.services.imaging_service import synthesize_matrix
from app.services.measurement_service import MeasurementService
from app.schemas.measurement import MeasurementIn, ParamValue

STRUCTURES = [
    {
        "code": "GL-001",
        "name": "胶州湾海底隧道",
        "kind": "海底隧道",
        "location": "山东青岛",
        "note": "安全生产调度指挥中心接入点位",
    },
    {
        "code": "QD-002",
        "name": "青岛地铁 3 号线站台",
        "kind": "地铁车站",
        "location": "山东青岛",
        "note": "站厅结构长期监测",
    },
    {
        "code": "YZ-003",
        "name": "雨樟大桥主跨",
        "kind": "斜拉桥",
        "location": "贵州安顺",
        "note": "混凝土箱梁外表面涂层布设",
    },
]

ZONES = [
    {
        "code": "GL-001-Z1",
        "name": "隧道右幅 K12+300 段",
        "structure": "GL-001",
        "grid_size": 64,
        "area_sqm": 12.0,
        "coating_thickness_mm": 1.0,
    },
    {
        "code": "GL-001-Z2",
        "name": "隧道右幅 K12+500 段",
        "structure": "GL-001",
        "grid_size": 64,
        "area_sqm": 12.0,
        "coating_thickness_mm": 1.0,
    },
    {
        "code": "QD-002-Z1",
        "name": "站厅 B 柱迎墙面",
        "structure": "QD-002",
        "grid_size": 64,
        "area_sqm": 8.5,
        "coating_thickness_mm": 1.0,
    },
    {
        "code": "YZ-003-Z1",
        "name": "主跨跨中底板",
        "structure": "YZ-003",
        "grid_size": 64,
        "area_sqm": 16.0,
        "coating_thickness_mm": 1.2,
    },
]

DEVICES = [
    {
        "device_id": "WSD-01",
        "name": "采集终端 01",
        "model": "ESP32",
        "zone": "GL-001-Z1",
        "location": "隧道右幅 K12+300 段",
    },
    {
        "device_id": "WSD-02",
        "name": "采集终端 02",
        "model": "ESP32",
        "zone": "GL-001-Z2",
        "location": "隧道右幅 K12+500 段",
    },
    {
        "device_id": "WSD-03",
        "name": "采集终端 03",
        "model": "ESP32",
        "zone": "QD-002-Z1",
        "location": "青岛地铁 3 号线站厅",
    },
    {
        "device_id": "WSD-04",
        "name": "采集终端 04",
        "model": "ESP32",
        "zone": "YZ-003-Z1",
        "location": "雨樟大桥主跨",
    },
]

# 阈值贴着正常波动的上下沿取值，演示数据里少数点会越界
RULES = [
    {
        "name": "电阻越上限",
        "zone": "GL-001-Z1",
        "metric": "resistance_ohm",
        "lower_limit": None,
        "upper_limit": 1015.0,
        "trigger_count": 3,
        "severity": "critical",
    },
    {
        "name": "电阻越下限",
        "zone": "GL-001-Z1",
        "metric": "resistance_ohm",
        "lower_limit": 985.0,
        "upper_limit": None,
        "trigger_count": 3,
        "severity": "warning",
    },
    {
        "name": "应变超限",
        "zone": "GL-001-Z2",
        "metric": "strain_ue",
        "lower_limit": None,
        "upper_limit": 60.0,
        "trigger_count": 2,
        "severity": "critical",
    },
    {
        "name": "阻抗幅值偏高",
        "zone": "YZ-003-Z1",
        "metric": "impedance_magnitude_ohm",
        "lower_limit": None,
        "upper_limit": 2290.0,
        "trigger_count": 3,
        "severity": "warning",
    },
]

# 各测区电阻基准值
BASE_RESISTANCE = {
    "GL-001-Z1": 1000.0,
    "GL-001-Z2": 1000.0,
    "QD-002-Z1": 470.0,
    "YZ-003-Z1": 2200.0,
}

def build_payload(device_id: str, base: float, moment: datetime, index: int, rng: random.Random) -> MeasurementIn:
    slow = math.sin(index / 45.0) * 0.018
    fast = math.sin(index / 7.0) * 0.005
    drift = slow + fast
    noise = rng.uniform(-0.008, 0.008)

    resistance = base * (1.0 + drift + noise)
    impedance = resistance * 1.03
    phase = drift * 16.0 + rng.uniform(-0.3, 0.3)

    return MeasurementIn(
        device_id=device_id,
        id=f"sim-{device_id}",
        version="1.0",
        measured_at=moment,
        params={
            "resistance_ohm": ParamValue(value=round(resistance, 3)),
            "phase_deg": ParamValue(value=round(phase, 3)),
            "impedance_magnitude_ohm": ParamValue(value=round(impedance, 3)),
            "frequency_hz": ParamValue(value=1000),
        },
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="初始化平台演示数据")
    parser.add_argument("--rows", type=int, default=240, help="每台设备生成的采集记录条数")
    parser.add_argument("--interval", type=int, default=10, help="相邻两条的间隔秒数")
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--clear", action="store_true", help="生成前清空相关表")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    service = MeasurementService(SessionLocal())

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if args.clear:
            for model in (AlertRecord, ImagingResult, Measurement, AlertRule, Device, Zone, Structure):
                db.execute(delete(model))
            db.commit()
            print("已清空原有数据")

        zone_ids: dict[str, int] = {}
        structure_ids: dict[str, int] = {}
        for item in STRUCTURES:
            existing = db.execute(
                select(Structure).where(Structure.code == item["code"])
            ).scalars().first()
            if existing is None:
                existing = Structure(**item)
                db.add(existing)
                db.flush()
            structure_ids[item["code"]] = existing.id
            print(f"结构: {existing.code} {existing.name}")

        for item in ZONES:
            existing = db.execute(
                select(Zone).where(Zone.code == item["code"])
            ).scalars().first()
            payload = {
                "code": item["code"],
                "name": item["name"],
                "structure_id": structure_ids[item["structure"]],
                "grid_size": item["grid_size"],
                "area_sqm": item["area_sqm"],
                "coating_thickness_mm": item["coating_thickness_mm"],
            }
            if existing is None:
                existing = Zone(**payload)
                db.add(existing)
                db.flush()
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            zone_ids[item["code"]] = existing.id
        db.commit()
        print(f"测区: {len(zone_ids)} 个")

        for item in DEVICES:
            existing = db.execute(
                select(Device).where(Device.device_id == item["device_id"])
            ).scalars().first()
            if existing is None:
                db.add(
                    Device(
                        device_id=item["device_id"],
                        name=item["name"],
                        model=item["model"],
                        location=item["location"],
                        zone_id=zone_ids[item["zone"]],
                        status="online",
                    )
                )
            else:
                existing.name = item["name"]
                existing.model = item["model"]
                existing.location = item["location"]
                existing.zone_id = zone_ids[item["zone"]]
        db.commit()
        print(f"采集终端: {len(DEVICES)} 台")

        for item in RULES:
            exists = db.execute(
                select(AlertRule).where(AlertRule.name == item["name"])
            ).scalars().first()
            if exists is None:
                db.add(
                    AlertRule(
                        name=item["name"],
                        zone_id=zone_ids[item["zone"]],
                        metric=item["metric"],
                        lower_limit=item["lower_limit"],
                        upper_limit=item["upper_limit"],
                        trigger_count=item["trigger_count"],
                        severity=item["severity"],
                        enabled=True,
                    )
                )
        db.commit()
        print(f"告警规则: {len(RULES)} 条")

        end = datetime.now().replace(microsecond=0)
        for item in DEVICES:
            base = BASE_RESISTANCE[item["zone"]]
            start = end - timedelta(seconds=args.interval * (args.rows - 1))
            for index in range(args.rows):
                moment = start + timedelta(seconds=args.interval * index)
                payload = build_payload(item["device_id"], base, moment, index, rng)
                service.ingest(payload)
        print(f"采集记录: {len(DEVICES)} × {args.rows} 条")

        from app.services.imaging_service import ImagingService

        imaging = ImagingService(db)
        for zone_code in zone_ids:
            matrix = synthesize_matrix(grid_size=64, seed=args.seed)
            imaging.store(zone_id=zone_ids[zone_code], matrix=matrix, scan_cost_ms=20)

        matrix = synthesize_matrix(
            grid_size=64,
            anomaly=(38.0, 44.0, 95.0),
            seed=args.seed + 1,
        )
        imaging.store(
            zone_id=zone_ids["GL-001-Z1"],
            matrix=matrix,
            device_id="WSD-01",
            scan_cost_ms=20,
        )
        print("成像结果: 5 次（含 1 次含裂缝异常）")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
