"""ORM mapping for every SIYANA table. The SQL source of truth is db/migrations."""
from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSONB, list: JSONB}


class IngestRun(Base):
    __tablename__ = "ingest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AtaChapter(Base):
    __tablename__ = "ata_chapters"
    code: Mapped[str] = mapped_column(String(4), primary_key=True)
    chapter: Mapped[str] = mapped_column(String(2), index=True)
    title: Mapped[str] = mapped_column(Text)
    system: Mapped[str] = mapped_column(Text)


class Tail(Base):
    __tablename__ = "tails"
    registration: Mapped[str] = mapped_column(String(16), primary_key=True)
    aircraft_type: Mapped[str] = mapped_column(String(32), index=True)
    operator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="serviceable")
    in_fleet: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Snag(Base):
    __tablename__ = "snags"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tail: Mapped[str | None] = mapped_column(String(16), ForeignKey("tails.registration"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    source_doc_id: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    norm_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ata_code: Mapped[str | None] = mapped_column(String(4), ForeignKey("ata_chapters.code"), nullable=True, index=True)
    ata_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    defect_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    part_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    aircraft_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_runs.id"), nullable=True)


class DefectEvent(Base):
    __tablename__ = "defect_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    snag_id: Mapped[int] = mapped_column(ForeignKey("snags.id"), index=True)
    tail: Mapped[str | None] = mapped_column(String(16), ForeignKey("tails.registration"), nullable=True, index=True)
    ata_code: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(2), default="S1")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_order_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    signature_id: Mapped[int | None] = mapped_column(ForeignKey("signatures.id"), nullable=True, index=True)


class Signature(Base):
    __tablename__ = "signatures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ata_code: Mapped[str] = mapped_column(String(4), index=True)
    aircraft_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    canonical: Mapped[str] = mapped_column(Text)
    member_snag_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    count: Mapped[int] = mapped_column(Integer)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signature_id: Mapped[int] = mapped_column(ForeignKey("signatures.id"), index=True)
    status: Mapped[str] = mapped_column(String(8), default="DRAFT", index=True)
    body: Mapped[dict] = mapped_column(JSONB)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    engineer_name: Mapped[str] = mapped_column(Text)
    licence_number: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(8))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(16), index=True)
    model_version: Mapped[str] = mapped_column(Text)
    input_sha256: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    source_ids: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RulPrediction(Base):
    __tablename__ = "rul_predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tail: Mapped[str] = mapped_column(String(16), ForeignKey("tails.registration"), index=True)
    engine_pos: Mapped[int] = mapped_column(Integer)
    unit_id: Mapped[int] = mapped_column(Integer)
    dataset: Mapped[str] = mapped_column(String(8))
    predicted_rul: Mapped[float] = mapped_column(Float)
    series: Mapped[list] = mapped_column(JSONB)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bay(Base):
    __tablename__ = "bays"
    id: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    capable_ata: Mapped[list[str]] = mapped_column(ARRAY(String(2)))
    available_from: Mapped[int] = mapped_column(Integer, default=0)


class Engineer(Base):
    __tablename__ = "engineers"
    id: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    licences: Mapped[list[str]] = mapped_column(ARRAY(String(8)))
    shift_hours: Mapped[int] = mapped_column(Integer)


class MaintTask(Base):
    __tablename__ = "maint_tasks"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    tail: Mapped[str] = mapped_column(String(16), ForeignKey("tails.registration"), index=True)
    ata_code: Mapped[str] = mapped_column(String(4))
    est_hours: Mapped[int] = mapped_column(Integer)
    due_by: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer)
    licence_required: Mapped[str] = mapped_column(String(8))
    description: Mapped[str] = mapped_column(Text)
    defect_event_id: Mapped[int | None] = mapped_column(ForeignKey("defect_events.id"), nullable=True)


class ScheduleRun(Base):
    __tablename__ = "schedule_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    objective: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solve_seconds: Mapped[float] = mapped_column(Float)
    horizon_hours: Mapped[int] = mapped_column(Integer)
    assignments: Mapped[list] = mapped_column(JSONB)
    licence_shortage: Mapped[list] = mapped_column(JSONB)
    baseline: Mapped[dict] = mapped_column(JSONB)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NazarFinding(Base):
    __tablename__ = "nazar_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_sha256: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[list] = mapped_column(JSONB)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Utilisation(Base):
    __tablename__ = "utilisation"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    icao24: Mapped[str] = mapped_column(String(8), index=True)
    callsign: Mapped[str | None] = mapped_column(String(12), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    baro_altitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_ground: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_runs.id"), nullable=True)


class RecurrenceLabel(Base):
    __tablename__ = "recurrence_labels"
    pair_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snag_a: Mapped[int] = mapped_column(ForeignKey("snags.id"))
    snag_b: Mapped[int] = mapped_column(ForeignKey("snags.id"))
    stratum: Mapped[str] = mapped_column(String(16))
    label: Mapped[int] = mapped_column(Integer)
    labeller: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
