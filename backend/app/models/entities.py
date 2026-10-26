from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )


class Structure(Base, TimestampMixin):
    __tablename__ = "structures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[Optional[str]] = mapped_column(String(64))
    location: Mapped[Optional[str]] = mapped_column(String(128))
    note: Mapped[Optional[str]] = mapped_column(Text)

    zones: Mapped[list["Zone"]] = relationship(
        back_populates="structure",
        cascade="all, delete-orphan",
    )


class Zone(Base, TimestampMixin):

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    structure_id: Mapped[int] = mapped_column(
        ForeignKey("structures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 网格边长，128 表示 128×128 的电阻率矩阵
    grid_size: Mapped[int] = mapped_column(Integer, default=128, nullable=False)
    area_sqm: Mapped[Optional[float]] = mapped_column(Float)
    coating_thickness_mm: Mapped[Optional[float]] = mapped_column(Float)

    structure: Mapped[Structure] = relationship(back_populates="zones")
    devices: Mapped[list["Device"]] = relationship(back_populates="zone")


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(128))
    zone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"),
        index=True,
    )
    location: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="online", nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    zone: Mapped[Optional[Zone]] = relationship(back_populates="devices")
    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )


class Measurement(Base):
    """单次采集记录，四个量的字段名与单位沿用硬件侧原有约定"""

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resistance_ohm: Mapped[Optional[float]] = mapped_column(Float)
    phase_deg: Mapped[Optional[float]] = mapped_column(Float)
    impedance_magnitude_ohm: Mapped[Optional[float]] = mapped_column(Float)
    frequency_hz: Mapped[Optional[int]] = mapped_column(Integer)
    # 应变由平台侧根据电阻换算得到
    strain_ue: Mapped[Optional[float]] = mapped_column(Float)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    device: Mapped[Device] = relationship(back_populates="measurements")


class ImagingResult(Base):
    """一次电阻抗成像的结果，矩阵按行优先序列化存放"""

    __tablename__ = "imaging_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    grid_size: Mapped[int] = mapped_column(Integer, default=64, nullable=False)
    # 电阻率矩阵，逗号分隔的浮点数，按行优先排列
    data: Mapped[str] = mapped_column(Text, nullable=False)
    # 硬件侧成像耗时，单位毫秒
    scan_cost_ms: Mapped[Optional[int]] = mapped_column(Integer)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 异常点相对坐标，0-100 的百分比
    peak_x: Mapped[Optional[float]] = mapped_column(Float)
    peak_y: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)


class AlertRule(Base, TimestampMixin):

    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    zone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        index=True,
    )
    # 监测量，取值为 resistance_ohm / phase_deg / impedance_magnitude_ohm
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    lower_limit: Mapped[Optional[float]] = mapped_column(Float)
    upper_limit: Mapped[Optional[float]] = mapped_column(Float)
    # 连续越界达到这个点数才触发，用来滤掉瞬时抖动
    trigger_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="warning", nullable=False)


class AlertRecord(Base):

    __tablename__ = "alert_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        index=True,
    )
    zone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        index=True,
    )
    device_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="warning", nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float)
    lower_limit: Mapped[Optional[float]] = mapped_column(Float)
    upper_limit: Mapped[Optional[float]] = mapped_column(Float)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    # 确认时间，确认后不再计入待处理
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(64))


class User(Base, TimestampMixin):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(64))
    email: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
