from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import DATABASE_URL

class Base(DeclarativeBase):
    pass

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor: Mapped[str] = mapped_column(String(200), default="anonymous")
    action: Mapped[str] = mapped_column(String(120), index=True)
    object_type: Mapped[str] = mapped_column(String(80), default="")
    object_id: Mapped[str] = mapped_column(String(200), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")

class CaseRecord(Base):
    __tablename__ = "analysis_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor: Mapped[str] = mapped_column(String(200), default="anonymous")
    question: Mapped[str] = mapped_column(Text)
    target_id: Mapped[str] = mapped_column(String(200), default="")
    top_candidate: Mapped[str] = mapped_column(Text, default="")
    top_score: Mapped[float] = mapped_column(Float, default=0.0)
    result_json: Mapped[str] = mapped_column(Text, default="{}")


class VisionEventRecord(Base):
    __tablename__ = "vision_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    camera_id: Mapped[str] = mapped_column(String(200), index=True)
    equipment_id: Mapped[str] = mapped_column(String(200), index=True, default="")
    severity: Mapped[str] = mapped_column(String(40), index=True, default="warning")
    rule_id: Mapped[str] = mapped_column(String(160), default="")
    event_type: Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    snapshot_path: Mapped[str] = mapped_column(Text, default="")
    detections_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

class VisionReviewRecord(Base):
    __tablename__ = "vision_review_queue"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    camera_id: Mapped[str] = mapped_column(String(200), index=True)
    equipment_id: Mapped[str] = mapped_column(String(200), index=True, default="")
    image_path: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), index=True, default="pending")
    detections_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

class IngestSnapshot(Base):
    __tablename__ = "ingest_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    catalog_json: Mapped[str] = mapped_column(Text, default="[]")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db() -> None:
    Base.metadata.create_all(engine)

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def log_audit(actor: str, action: str, payload: dict[str, Any] | None = None, object_type: str = "", object_id: str = "") -> None:
    with SessionLocal() as s:
        s.add(AuditEvent(timestamp=utcnow(), actor=actor, action=action, object_type=object_type, object_id=object_id, payload_json=json.dumps(payload or {}, ensure_ascii=False, default=str)))
        s.commit()

def save_case(actor: str, question: str, target_id: str | None, top_candidate: str | None, top_score: float | None, result: dict[str, Any]) -> int:
    with SessionLocal() as s:
        row = CaseRecord(created_at=utcnow(), actor=actor, question=question, target_id=target_id or "", top_candidate=top_candidate or "", top_score=float(top_score or 0), result_json=json.dumps(result, ensure_ascii=False, default=str))
        s.add(row); s.commit(); s.refresh(row); return int(row.id)

def save_snapshot(file_count: int, table_count: int, chunk_count: int, catalog: list[dict]) -> int:
    with SessionLocal() as s:
        row = IngestSnapshot(created_at=utcnow(), file_count=file_count, table_count=table_count, chunk_count=chunk_count, catalog_json=json.dumps(catalog, ensure_ascii=False, default=str))
        s.add(row); s.commit(); s.refresh(row); return int(row.id)

def recent_cases(limit: int = 50) -> list[dict[str, Any]]:
    with SessionLocal() as s:
        rows = s.scalars(select(CaseRecord).order_by(CaseRecord.id.desc()).limit(limit)).all()
        return [{"id": r.id, "created_at": r.created_at.isoformat(), "actor": r.actor, "question": r.question, "target_id": r.target_id, "top_candidate": r.top_candidate, "top_score": r.top_score} for r in rows]

def recent_audit(limit: int = 100) -> list[dict[str, Any]]:
    with SessionLocal() as s:
        rows = s.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)).all()
        return [{"id": r.id, "timestamp": r.timestamp.isoformat(), "actor": r.actor, "action": r.action, "object_type": r.object_type, "object_id": r.object_id, "payload": json.loads(r.payload_json or "{}") } for r in rows]


def save_vision_event(camera_id: str, equipment_id: str, severity: str, rule_id: str, event_type: str, message: str, snapshot_path: str, detections: list[dict], metadata: dict[str, Any] | None = None) -> int:
    with SessionLocal() as s:
        row = VisionEventRecord(
            created_at=utcnow(), camera_id=camera_id, equipment_id=equipment_id, severity=severity, rule_id=rule_id,
            event_type=event_type, message=message, snapshot_path=snapshot_path,
            detections_json=json.dumps(detections or [], ensure_ascii=False, default=str),
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
        )
        s.add(row); s.commit(); s.refresh(row); return int(row.id)

def recent_vision_events(limit: int = 50) -> list[dict[str, Any]]:
    with SessionLocal() as s:
        rows = s.scalars(select(VisionEventRecord).order_by(VisionEventRecord.id.desc()).limit(limit)).all()
        return [{
            "id": r.id, "created_at": r.created_at.isoformat(), "camera_id": r.camera_id, "equipment_id": r.equipment_id,
            "severity": r.severity, "rule_id": r.rule_id, "event_type": r.event_type, "message": r.message,
            "snapshot_path": r.snapshot_path, "detections": json.loads(r.detections_json or "[]"),
            "metadata": json.loads(r.metadata_json or "{}"),
        } for r in rows]

def save_review_item(camera_id: str, equipment_id: str, image_path: str, detections: list[dict], metadata: dict[str, Any] | None = None) -> int:
    with SessionLocal() as s:
        row = VisionReviewRecord(
            created_at=utcnow(), camera_id=camera_id, equipment_id=equipment_id, image_path=image_path, status="pending",
            detections_json=json.dumps(detections or [], ensure_ascii=False, default=str),
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
        )
        s.add(row); s.commit(); s.refresh(row); return int(row.id)

def recent_review_items(limit: int = 50) -> list[dict[str, Any]]:
    with SessionLocal() as s:
        rows = s.scalars(select(VisionReviewRecord).order_by(VisionReviewRecord.id.desc()).limit(limit)).all()
        return [{
            "id": r.id, "created_at": r.created_at.isoformat(), "camera_id": r.camera_id, "equipment_id": r.equipment_id,
            "image_path": r.image_path, "status": r.status, "detections": json.loads(r.detections_json or "[]"),
            "metadata": json.loads(r.metadata_json or "{}"),
        } for r in rows]
