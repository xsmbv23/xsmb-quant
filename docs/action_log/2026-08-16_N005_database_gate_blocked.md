# N005 — Database Persistence Gate / Fail-Closed Result

**Actor:** GPT-5.6 Luna

## Objective

Verify immutable raw-artifact persistence against `xsmb_runtime_db` from the Render runtime using TLS-required PostgreSQL.

## Implementation

- Added `psycopg[binary]` to `requirements.txt`.
- Docker build was corrected to install `requirements.txt`.
- Added `storage/raw_artifacts.py` with:
  - TLS-required connection;
  - immutable `raw_artifacts` table;
  - unique `(source_id, content_sha256)` idempotency key;
  - provenance table;
  - raw bytes stored unchanged;
  - `EVIDENCE_BOUND` + `DENY` default states.
- Added gated runtime persistence path in `foundation_gate.py`.

## Runtime result

The persistence gate was deliberately enabled in Render. The application reached the persistence boundary and failed with:

`DATABASE_URL_MISSING`

This is the correct Fosennic result: the system did **not** continue while raw evidence could not be durably persisted.

## Governance

`PROMOTION = DENY`.

`RAW_ARTIFACT_PERSISTENCE = BLOCKED / UNKNOWN`.

The temporary persistence flag was returned to `0` so the public foundation service does not remain in a failing startup state.

## Important finding

The `xsmb-quant` Render service currently does not expose a `DATABASE_URL` environment variable to the runtime. The PostgreSQL instance exists and is available, but the service-to-database credential binding is not present in the service environment.

No database credential or password is written to the repository or action logs.

## Next action

N005B — provision the Render service's `DATABASE_URL` secret from the existing `xsmb_runtime_db` connection configuration, with TLS required, then rerun the gated persistence verification. Do not proceed to additional source adapters until read-after-write evidence exists.
