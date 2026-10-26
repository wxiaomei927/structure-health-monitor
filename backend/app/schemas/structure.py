from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StructureCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    kind: Optional[str] = Field(default=None, max_length=64)
    location: Optional[str] = Field(default=None, max_length=128)
    note: Optional[str] = None


class StructureOut(BaseModel):
    id: int
    code: str
    name: str
    kind: Optional[str] = None
    location: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ZoneCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    structure_id: int
    grid_size: int = Field(default=128, ge=16, le=256)
    area_sqm: Optional[float] = None
    coating_thickness_mm: Optional[float] = None


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    structure_id: Optional[int] = None
    grid_size: Optional[int] = Field(default=None, ge=16, le=256)
    area_sqm: Optional[float] = None
    coating_thickness_mm: Optional[float] = None


class StructureUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    kind: Optional[str] = Field(default=None, max_length=64)
    location: Optional[str] = Field(default=None, max_length=128)
    note: Optional[str] = None


class ZoneOut(BaseModel):
    id: int
    code: str
    name: str
    structure_id: int
    grid_size: int
    area_sqm: Optional[float] = None
    coating_thickness_mm: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ImagingIn(BaseModel):
    """一次成像结果的上报报文

    matrix 是重建后的电阻率矩阵，行优先的二维数组。
    """

    zone_code: str = Field(min_length=1, max_length=64)
    device_id: Optional[str] = Field(default=None, max_length=64)
    matrix: list[list[float]]
    scan_cost_ms: Optional[int] = None


class ImagingOut(BaseModel):
    id: int
    zone_code: str
    available: bool
    grid_size: Optional[int] = None
    matrix: Optional[list[list[float]]] = None
    anomaly_count: Optional[int] = None
    peak_x: Optional[float] = None
    peak_y: Optional[float] = None
    scan_cost_ms: Optional[int] = None
    created_at: Optional[str] = None
