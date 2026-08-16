"""Durable evidence sink adapter.

Runtime writes compact evidence envelopes only. The sink is fail-closed:
without DATABASE_URL it refuses to claim durability. SSL is explicitly
required for Render Postgres.
"""
from __future__ import annotations

import json
import os
from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS forensic_evidence (
    evidence_sha256 TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    envelope_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("DURABILITY_DENY:DATABASE_URL_MISSING")
    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
    return dsn


def persist_envelope(envelope: dict[str, Any]) -> None:
    # Imported lazily so the base verification path stays dependency-light.
    import psycopg

    evidence_sha = envelope.get("evidence_sha256")
    action_id = envelope.get("action_id")
    if not evidence_sha or not action_id:
        raise RuntimeError("DURABILITY_DENY:INVALID_ENVELOPE")

    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute(
                """
                INSERT INTO forensic_evidence(evidence_sha256, action_id, envelope_json)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (evidence_sha256) DO NOTHING
                """,
                (evidence_sha, action_id, json.dumps(envelope, ensure_ascii=False)),
            )
        conn.commit()


def read_envelope(evidence_sha256: str) -> dict[str, Any]:
    import psycopg

    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT envelope_json FROM forensic_evidence WHERE evidence_sha256=%s",
                (evidence_sha256,),
            )
            row = cur.fetchone()
    if not row:
        raise RuntimeError("DURABILITY_DENY:EVIDENCE_NOT_FOUND")
    return row[0]
