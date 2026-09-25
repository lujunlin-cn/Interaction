"""ORM 表结构。JSON 列在 Postgres 下落 JSONB，在测试 SQLite 下落 TEXT。

设计：Session 是聚合根（World/Drama/Branch/Event/Wish/Arc 等子状态随其原子读写），
保证双域事务与恢复语义简单正确；Trace/Job/Route 等可观测性数据单独建表供查询。
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from .db import Base


class JSONFlex(TypeDecorator):
    """Postgres → JSONB；其他后端 → TEXT(JSON)。"""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


class ScenarioRow(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    draft: Mapped[dict] = mapped_column(JSONFlex)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class ScenarioVersionRow(Base):
    __tablename__ = "scenario_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32))
    snapshot: Mapped[dict] = mapped_column(JSONFlex)   # 不可变
    created_at: Mapped[int] = mapped_column(BigInteger)


class GlobalCharacterRow(Base):
    __tablename__ = "global_characters"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    data: Mapped[dict] = mapped_column(JSONFlex)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class CharacterCreationKeyRow(Base):
    """Durable idempotency mapping for Standard character creation.

    The key is client supplied and scoped to a creation operation. Keeping it
    in its own table makes retries safe across browser reloads and processes,
    unlike a React in-flight flag.
    """
    __tablename__ = "character_creation_keys"
    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    character_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[int] = mapped_column(BigInteger)


class AssetRow(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict] = mapped_column(JSONFlex)
    created_at: Mapped[int] = mapped_column(BigInteger)


class SessionRow(Base):
    """Session 聚合根：双域状态、分支、事件、愿望、篇章、预算都在这一行内原子读写。"""
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64))
    scenario_version_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    state: Mapped[dict] = mapped_column(JSONFlex)      # 完整 SessionState
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class JobRow(Base):
    __tablename__ = "generation_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    branch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    data: Mapped[dict] = mapped_column(JSONFlex)
    started_at: Mapped[int] = mapped_column(BigInteger)


class TraceSpanRow(Base):
    __tablename__ = "trace_spans"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    branch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSONFlex)
    at: Mapped[int] = mapped_column(BigInteger)


class RouteEventRow(Base):
    __tablename__ = "provider_route_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSONFlex)
    at: Mapped[int] = mapped_column(BigInteger)


class FeedbackRow(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONFlex)
    at: Mapped[int] = mapped_column(BigInteger)


# --- v0.6 Character Asset System ---

class CharacterAssetRow(Base):
    __tablename__ = "character_assets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    character_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="CANDIDATE")
    role: Mapped[str] = mapped_column(String(32), default="")
    data: Mapped[dict] = mapped_column(JSONFlex)      # CharacterAsset
    created_at: Mapped[int] = mapped_column(BigInteger)


class CharacterVersionRow(Base):
    __tablename__ = "character_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    character_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    change_type: Mapped[str] = mapped_column(String(24), default="METADATA")
    data: Mapped[dict] = mapped_column(JSONFlex)      # CharacterVersion
    created_at: Mapped[int] = mapped_column(BigInteger)


class ScenarioCharacterSnapshotRow(Base):
    __tablename__ = "scenario_character_snapshots"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_version_id: Mapped[str] = mapped_column(String(64), index=True)
    global_character_id: Mapped[str] = mapped_column(String(64), index=True)
    character_version_id: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSONFlex)      # ScenarioCharacterSnapshot
    created_at: Mapped[int] = mapped_column(BigInteger)
