from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    zone_id: Optional[int] = None
    # 监测量，取值为 resistance_ohm / phase_deg / impedance_magnitude_ohm / strain_ue
    metric: str = Field(min_length=1, max_length=64)
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    trigger_count: int = Field(default=3, ge=1, le=50)
    enabled: bool = True
    severity: str = Field(default="warning", pattern="^(warning|critical)$")


class AlertRuleOut(BaseModel):
    id: int
    name: str
    zone_id: Optional[int] = None
    metric: str
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    trigger_count: int
    enabled: bool
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


class AlertRecordOut(BaseModel):
    id: int
    rule_id: Optional[int] = None
    zone_id: Optional[int] = None
    device_id: Optional[str] = None
    metric: str
    severity: str
    value: Optional[float] = None
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    message: str
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    class Config:
        from_attributes = True
