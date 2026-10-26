from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Device, Structure, Zone
from app.schemas.structure import StructureCreate, ZoneCreate


class StructureService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_structures(self) -> list[Structure]:
        stmt = select(Structure).order_by(Structure.code)
        return list(self.db.execute(stmt).scalars().all())

    def get_structure(self, code: str) -> Optional[Structure]:
        stmt = select(Structure).where(Structure.code == code)
        return self.db.execute(stmt).scalars().first()

    def get_structure_by_id(self, pk: int) -> Optional[Structure]:
        return self.db.get(Structure, pk)

    def create_structure(self, payload: StructureCreate) -> Structure:
        obj = Structure(
            code=payload.code,
            name=payload.name,
            kind=payload.kind,
            location=payload.location,
            note=payload.note,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_zones(self, structure_id: Optional[int] = None) -> list[Zone]:
        stmt = select(Zone)
        if structure_id is not None:
            stmt = stmt.where(Zone.structure_id == structure_id)
        stmt = stmt.order_by(Zone.code)
        return list(self.db.execute(stmt).scalars().all())

    def get_zone(self, code: str) -> Optional[Zone]:
        stmt = select(Zone).where(Zone.code == code)
        return self.db.execute(stmt).scalars().first()

    def create_zone(self, payload: ZoneCreate) -> Zone:
        obj = Zone(
            code=payload.code,
            name=payload.name,
            structure_id=payload.structure_id,
            grid_size=payload.grid_size,
            area_sqm=payload.area_sqm,
            coating_thickness_mm=payload.coating_thickness_mm,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update_zone(self, zone: Zone, payload: dict) -> Zone:
        for field in ("name", "structure_id", "grid_size", "area_sqm", "coating_thickness_mm"):
            value = payload.get(field)
            if value is not None:
                setattr(zone, field, value)
        self.db.commit()
        self.db.refresh(zone)
        return zone

    def update_structure(self, structure: Structure, payload: dict) -> Structure:
        for field in ("name", "kind", "location", "note"):
            value = payload.get(field)
            if value is not None:
                setattr(structure, field, value)
        self.db.commit()
        self.db.refresh(structure)
        return structure

    def devices_of_zone(self, zone_id: int) -> list[Device]:
        stmt = select(Device).where(Device.zone_id == zone_id)
        return list(self.db.execute(stmt).scalars().all())
