from __future__ import annotations

from dataclasses import dataclass
import os

import psycopg


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_artifacts (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    http_status INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    byte_length BIGINT NOT NULL,
    parser_version TEXT NOT NULL,
    raw_bytes BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_id, content_sha256)
);

CREATE TABLE IF NOT EXISTS raw_artifact_provenance (
    raw_artifact_id BIGINT PRIMARY KEY REFERENCES raw_artifacts(id),
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    parser_version TEXT NOT NULL,
    evidence_state TEXT NOT NULL DEFAULT 'EVIDENCE_BOUND',
    promotion_state TEXT NOT NULL DEFAULT 'DENY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass(frozen=True)
class PersistenceResult:
    raw_artifact_id: int
    content_sha256: str
    inserted: bool


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL_MISSING")
    return value


def persist_raw_artifact(capture, parser_version: str) -> PersistenceResult:
    with psycopg.connect(_database_url(), sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute(
                """
                INSERT INTO raw_artifacts
                (source_id, source_url, retrieved_at, http_status, content_type,
                 content_sha256, byte_length, parser_version, raw_bytes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (source_id, content_sha256) DO NOTHING
                RETURNING id
                """,
                (
                    capture.source_id,
                    capture.url,
                    capture.retrieved_at,
                    capture.http_status,
                    capture.content_type,
                    capture.content_sha256,
                    capture.byte_length,
                    parser_version,
                    capture.raw_bytes,
                ),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "SELECT id FROM raw_artifacts WHERE source_id=%s AND content_sha256=%s",
                    (capture.source_id, capture.content_sha256),
                )
                existing = cur.fetchone()
                if existing is None:
                    raise RuntimeError("RAW_ARTIFACT_INSERTION_LOST")
                artifact_id = int(existing[0])
                inserted = False
            else:
                artifact_id = int(row[0])
                inserted = True

            cur.execute(
                """
                INSERT INTO raw_artifact_provenance
                (raw_artifact_id, source_id, source_url, content_sha256,
                 parser_version, evidence_state, promotion_state)
                VALUES (%s,%s,%s,%s,%s,'EVIDENCE_BOUND','DENY')
                ON CONFLICT (raw_artifact_id) DO NOTHING
                """,
                (
                    artifact_id,
                    capture.source_id,
                    capture.url,
                    capture.content_sha256,
                    parser_version,
                ),
            )
        conn.commit()
    return PersistenceResult(artifact_id, capture.content_sha256, inserted)


def read_raw_artifact(raw_artifact_id: int) -> dict:
    """Read back the immutable raw artifact needed for durability verification."""
    with psycopg.connect(_database_url(), sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source_id, source_url, content_sha256, byte_length, raw_bytes
                FROM raw_artifacts
                WHERE id=%s
                """,
                (raw_artifact_id,),
            )
            row = cur.fetchone()
    if not row:
        raise RuntimeError("RAW_ARTIFACT_NOT_FOUND")
    return {
        "source_id": row[0],
        "source_url": row[1],
        "content_sha256": row[2],
        "byte_length": int(row[3]),
        "raw_bytes": bytes(row[4]),
    }
