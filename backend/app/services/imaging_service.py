from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import ImagingResult, Zone


class ImagingService:
    """电阻抗成像结果的存取，重建算法在硬件侧完成"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def latest(self, zone_id: int) -> Optional[ImagingResult]:
        stmt = (
            select(ImagingResult)
            .where(ImagingResult.zone_id == zone_id)
            .order_by(ImagingResult.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def list_results(self, zone_id: int, limit: int = 50) -> list[ImagingResult]:
        stmt = (
            select(ImagingResult)
            .where(ImagingResult.zone_id == zone_id)
            .order_by(ImagingResult.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def store(
        self,
        zone_id: int,
        matrix: list[list[float]],
        device_id: Optional[str] = None,
        scan_cost_ms: Optional[int] = None,
    ) -> ImagingResult:
        grid_size = len(matrix)
        flat = [value for row in matrix for value in row]
        anomaly_count, peak_x, peak_y = self._detect_anomaly(matrix)

        result = ImagingResult(
            zone_id=zone_id,
            device_id=device_id,
            grid_size=grid_size,
            data=",".join(f"{value:.4f}" for value in flat),
            scan_cost_ms=scan_cost_ms,
            anomaly_count=anomaly_count,
            peak_x=peak_x,
            peak_y=peak_y,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    @staticmethod
    def _detect_anomaly(matrix: list[list[float]]) -> tuple[int, Optional[float], Optional[float]]:
        """找出电阻率偏高的区域，判据是均值加两倍标准差"""
        flat = [value for row in matrix for value in row]
        if not flat:
            return 0, None, None

        mean = sum(flat) / len(flat)
        variance = sum((value - mean) ** 2 for value in flat) / len(flat)
        std = math.sqrt(variance)
        threshold = mean + 2 * std

        count = 0
        peak_value = None
        peak_x = None
        peak_y = None
        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0

        for y, row in enumerate(matrix):
            for x, value in enumerate(row):
                if value > threshold:
                    count += 1
                if peak_value is None or value > peak_value:
                    peak_value = value
                    peak_x = round(x / max(cols - 1, 1) * 100, 2)
                    peak_y = round(y / max(rows - 1, 1) * 100, 2)

        return count, peak_x, peak_y


def synthesize_matrix(
    grid_size: int = 64,
    anomaly: Optional[tuple[float, float, float]] = None,
    seed: int = 20261024,
) -> list[list[float]]:
    """生成模拟电阻率分布矩阵，anomaly 位置造一个高阻区"""
    rng = random.Random(seed)
    matrix: list[list[float]] = []

    for y in range(grid_size):
        row: list[float] = []
        for x in range(grid_size):
            # 背景：低频起伏加细粒噪声，模拟重建结果的不均匀
            base = 120.0 + 14.0 * math.sin(x / 9.0) * math.cos(y / 11.0)
            base += rng.uniform(-2.5, 2.5)

            if anomaly is not None:
                ax, ay, strength = anomaly
                cx = ax / 100.0 * grid_size
                cy = ay / 100.0 * grid_size
                dist = math.hypot(x - cx, y - cy)
                # 高斯型隆起，中心高、边缘平滑衰减
                sigma = grid_size / 12.0
                base += strength * math.exp(-(dist**2) / (2 * sigma**2))

            row.append(round(base, 3))
        matrix.append(row)

    return matrix
