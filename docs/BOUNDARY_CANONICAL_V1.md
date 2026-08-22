# XSMB Quant — Canonical Boundary V1

## Responsibility

This repository is the product/application plane. It may consume canonical quantitative datasets, model artifacts and contracts from Quant Engine, but it must not fork the canonical data/forensic rules or become a second Quant Engine.

## Allowed responsibilities

- Product-facing API/UI/service behavior.
- Controlled consumption of admitted Quant Engine artifacts.
- Product configuration and presentation.
- Thin adapters to canonical quantitative outputs.

## Forbidden duplication

- Independent historical collectors that compete with Quant Engine canonical ingestion.
- Independent canonical dataset definitions.
- Independent EV semantics.
- Independent forensic promotion rules.
- Hidden model/data transformations that bypass lineage.

## Target structure

- `app/` — product application.
- `adapters/` — Quant Engine input/output adapters.
- `contracts/` — product-consumption contracts only.
- `tests/` — product and contract tests.
- `docs/` — product documentation.

Any legacy code outside these boundaries is retained until dependency-audited and migrated.
