"""往平台灌一批模拟测量数据。

没有真机时用它把页面跑起来看效果。
数据按"基准值 + 缓慢漂移 + 小幅噪声"生成，画出来的曲线和真实测量一样有起伏，
不会像纯随机数那样杂乱。
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 直接运行时 app 包不在搜索路径里，补上 backend 根目录
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.entities import Device, Measurement
from app.services.measurement_service import MeasurementService
from app.schemas.measurement import MeasurementIn, ParamValue

# 各设备的基准参数：电阻基准值、阻抗与电阻的比例、相位、频率
DEVICE_PROFILES = {
    "WSD-01": {
        "resistance": 1000.0,
        "impedance_ratio": 1.02,
        "phase": 0.0,
        "frequency": 1000,
        "noise": 0.012,
    },
    "WSD-02": {
        "resistance": 2200.0,
        "impedance_ratio": 1.05,
        "phase": 2.5,
        "frequency": 1000,
        "noise": 0.02,
    },
    "WSD-03": {
        "resistance": 470.0,
        "impedance_ratio": 0.98,
        "phase": -1.2,
        "frequency": 5000,
        "noise": 0.03,
    },
}

def build_measurement(
    device_id: str,
    profile: dict,
    moment: datetime,
    index: int,
    rng: random.Random,
) -> MeasurementIn:
    """构造一条模拟上报报文，格式与硬件侧实际发送的一致"""
    # 两个不同周期的正弦叠加，得到既有慢漂移又有小幅抖动的曲线
    slow = math.sin(index / 45.0) * 0.02
    fast = math.sin(index / 7.0) * 0.006
    drift = slow + fast
    noise = rng.uniform(-profile["noise"], profile["noise"])

    resistance = profile["resistance"] * (1.0 + drift + noise)
    impedance = resistance * profile["impedance_ratio"]
    phase = profile["phase"] + drift * 18.0 + rng.uniform(-0.4, 0.4)
    frequency = profile["frequency"]

    return MeasurementIn(
        device_id=device_id,
        id=f"sim-{device_id}",
        version="1.0",
        measured_at=moment,
        params={
            "resistance_ohm": ParamValue(value=round(resistance, 3)),
            "phase_deg": ParamValue(value=round(phase, 3)),
            "impedance_magnitude_ohm": ParamValue(value=round(impedance, 3)),
            "frequency_hz": ParamValue(value=int(frequency)),
        },
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="生成模拟测量数据")
    parser.add_argument("--devices", nargs="*", default=list(DEVICE_PROFILES.keys()))
    parser.add_argument("--rows", type=int, default=240, help="每台设备生成的记录条数")
    parser.add_argument("--interval", type=int, default=10, help="相邻两条的间隔秒数")
    parser.add_argument("--seed", type=int, default=20261024, help="随机种子，固定后结果可复现")
    parser.add_argument("--clear", action="store_true", help="生成前先清空该设备的旧数据")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    service = MeasurementService(SessionLocal())

    with SessionLocal() as db:
        for device_id in args.devices:
            profile = DEVICE_PROFILES.get(device_id)
            if profile is None:
                print(f"跳过未预置的设备 {device_id}")
                continue

            if args.clear:
                db.execute(delete(Measurement).where(Measurement.device_id == device_id))
                db.commit()

            existing = db.execute(
                select(Device).where(Device.device_id == device_id)
            ).scalars().first()
            if existing is None:
                db.add(
                    Device(
                        device_id=device_id,
                        name=f"阻抗测量终端 {device_id.split('-')[-1]}",
                        model="ESP32-AD7758",
                        location="材料性能实验室",
                    )
                )
                db.commit()

            # 以当前时间为终点往前推，时间轴落在最近时段
            end = datetime.now().replace(microsecond=0)
            start = end - timedelta(seconds=args.interval * (args.rows - 1))

            for index in range(args.rows):
                moment = start + timedelta(seconds=args.interval * index)
                payload = build_measurement(device_id, profile, moment, index, rng)
                service.ingest(payload)

            print(f"{device_id}: 已写入 {args.rows} 条，时间范围 {start} ~ {end}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
