from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _to_local_naive(value: datetime) -> datetime:
    """带时区的时间统一换算成本地时间再存。

    硬件的时钟时区和服务器不一定一致，原样存会让时间轴错乱
    """
    if value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)


class DeviceCreate(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    model: Optional[str] = Field(default=None, max_length=128)
    location: Optional[str] = Field(default=None, max_length=128)
    zone_id: Optional[int] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    model: Optional[str] = Field(default=None, max_length=128)
    location: Optional[str] = Field(default=None, max_length=128)
    status: Optional[str] = Field(default=None, max_length=16)
    zone_id: Optional[int] = None


class DeviceOut(BaseModel):
    id: int
    device_id: str
    name: str
    model: Optional[str] = None
    location: Optional[str] = None
    zone_id: Optional[int] = None
    status: str
    last_seen_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ParamValue(BaseModel):
    """OneNET 物模型属性格式：{"value": 1000.5}"""

    value: Optional[float] = None


class MeasurementIn(BaseModel):
    """设备上报的报文。

    顶层 device_id 是平台分配给设备的标识；params 里是各测量量的物模型属性
    """

    device_id: str = Field(min_length=1, max_length=64)
    id: Optional[str] = Field(default=None, max_length=64)
    version: Optional[str] = Field(default=None, max_length=16)
    params: dict[str, ParamValue] = Field(default_factory=dict)
    measured_at: Optional[datetime] = None

    @field_validator("measured_at")
    @classmethod
    def normalize_measured_at(cls, value: Optional[datetime]) -> Optional[datetime]:
        return None if value is None else _to_local_naive(value)


class MeasurementOut(BaseModel):
    id: int
    device_id: str
    resistance_ohm: Optional[float] = None
    phase_deg: Optional[float] = None
    impedance_magnitude_ohm: Optional[float] = None
    frequency_hz: Optional[int] = None
    strain_ue: Optional[float] = None
    measured_at: datetime
    received_at: datetime

    class Config:
        from_attributes = True


class MeasurementAck(BaseModel):

    status: str
    id: int
    device_id: str
    received_at: datetime
    values: dict[str, Optional[float]]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=64)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: Optional[str] = None
    role: str


class StatsSummary(BaseModel):
    device_id: str
    count: int
    resistance_avg: Optional[float] = None
    resistance_min: Optional[float] = None
    resistance_max: Optional[float] = None
    phase_avg: Optional[float] = None
    impedance_avg: Optional[float] = None
    frequency_avg: Optional[float] = None
    strain_avg: Optional[float] = None
