from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import AlertRecord, AlertRule, Measurement, Zone

# 告警规则里允许配置的监测量
ALERT_METRICS = {
    "resistance_ohm": "电阻",
    "phase_deg": "相位角",
    "impedance_magnitude_ohm": "阻抗幅值",
    "strain_ue": "应变",
}


class AlertService:
    """告警规则与告警记录的处理"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_rules(self, zone_id: Optional[int] = None) -> list[AlertRule]:
        stmt = select(AlertRule)
        if zone_id is not None:
            stmt = stmt.where(AlertRule.zone_id == zone_id)
        stmt = stmt.order_by(AlertRule.id)
        return list(self.db.execute(stmt).scalars().all())

    def create_rule(self, payload: dict) -> AlertRule:
        rule = AlertRule(
            name=payload["name"],
            zone_id=payload.get("zone_id"),
            metric=payload["metric"],
            lower_limit=payload.get("lower_limit"),
            upper_limit=payload.get("upper_limit"),
            trigger_count=payload.get("trigger_count", 3),
            enabled=payload.get("enabled", True),
            severity=payload.get("severity", "warning"),
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule: AlertRule) -> None:
        self.db.delete(rule)
        self.db.commit()

    def list_records(
        self,
        only_open: bool = False,
        zone_id: Optional[int] = None,
        limit: int = 200,
    ) -> list[AlertRecord]:
        stmt = select(AlertRecord)
        if only_open:
            stmt = stmt.where(AlertRecord.acknowledged_at.is_(None))
        if zone_id is not None:
            stmt = stmt.where(AlertRecord.zone_id == zone_id)
        stmt = stmt.order_by(AlertRecord.triggered_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def acknowledge(self, record: AlertRecord, operator: str) -> AlertRecord:
        record.acknowledged_at = datetime.now()
        record.acknowledged_by = operator
        self.db.commit()
        self.db.refresh(record)
        return record

    def reopen(self, record: AlertRecord) -> AlertRecord:
        record.acknowledged_at = None
        record.acknowledged_by = None
        self.db.commit()
        self.db.refresh(record)
        return record

    def open_count(self) -> int:
        stmt = select(func.count(AlertRecord.id)).where(AlertRecord.acknowledged_at.is_(None))
        return int(self.db.execute(stmt).scalar() or 0)

    def evaluate(self, measurement: Measurement, zone: Optional[Zone]) -> list[AlertRecord]:
        """拿一条采集记录比对所有生效规则，返回本次新产生的告警"""
        if zone is None:
            return []

        triggered: list[AlertRecord] = []
        rules = [
            rule
            for rule in self.list_rules(zone_id=zone.id)
            if rule.enabled and rule.metric in ALERT_METRICS
        ]

        for rule in rules:
            value = getattr(measurement, rule.metric, None)
            if value is None:
                continue
            if not self._out_of_range(value, rule):
                continue

            if not self._reached_trigger_count(rule, measurement, value):
                continue

            # 同规则近期的未确认告警算同一次事件，只更新不新增
            recent = self._recent_open_alert(rule, measurement)
            if recent is not None:
                recent.value = value
                recent.triggered_at = datetime.now()
                recent.message = self._build_message(rule, zone, value)
                self.db.commit()
                continue

            record = AlertRecord(
                rule_id=rule.id,
                zone_id=zone.id,
                device_id=measurement.device_id,
                metric=rule.metric,
                severity=rule.severity,
                value=value,
                lower_limit=rule.lower_limit,
                upper_limit=rule.upper_limit,
                message=self._build_message(rule, zone, value),
                triggered_at=datetime.now(),
            )
            self.db.add(record)
            triggered.append(record)

        if triggered:
            self.db.commit()
        return triggered

    def _recent_open_alert(
        self, rule: AlertRule, measurement: Measurement
    ) -> Optional[AlertRecord]:
        window_start = datetime.now() - timedelta(minutes=5)
        stmt = (
            select(AlertRecord)
            .where(
                AlertRecord.rule_id == rule.id,
                AlertRecord.device_id == measurement.device_id,
                AlertRecord.acknowledged_at.is_(None),
                AlertRecord.triggered_at >= window_start,
            )
            .order_by(AlertRecord.triggered_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    @staticmethod
    def _build_message(rule: AlertRule, zone: Zone, value: float) -> str:
        label = ALERT_METRICS[rule.metric]
        if rule.lower_limit is not None and rule.upper_limit is not None:
            condition = f"正常范围 {rule.lower_limit} ~ {rule.upper_limit}"
        elif rule.upper_limit is not None:
            condition = f"正常上限 {rule.upper_limit}"
        else:
            condition = f"正常下限 {rule.lower_limit}"
        return f"{zone.name} {label}越界：实测 {round(value, 3)}，{condition}"

    @staticmethod
    def _out_of_range(value: float, rule: AlertRule) -> bool:
        if rule.lower_limit is not None and value < rule.lower_limit:
            return True
        if rule.upper_limit is not None and value > rule.upper_limit:
            return True
        return False

    def _reached_trigger_count(
        self, rule: AlertRule, measurement: Measurement, value: float
    ) -> bool:
        need = max(1, rule.trigger_count)
        if need == 1:
            return True

        stmt = (
            select(Measurement)
            .where(
                Measurement.device_id == measurement.device_id,
                Measurement.measured_at <= measurement.measured_at,
            )
            .order_by(Measurement.measured_at.desc())
            .limit(need)
        )
        history = list(self.db.execute(stmt).scalars().all())

        streak = 1  # 当前这条已确认越界
        for item in history:
            old_value = getattr(item, rule.metric, None)
            if old_value is None:
                break
            if not self._out_of_range(old_value, rule):
                break
            streak += 1
            if streak >= need:
                return True
        return False
