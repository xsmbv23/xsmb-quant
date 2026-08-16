"""L0 source ingestion adapters.

Adapters capture raw bytes first. Parsing is downstream and never replaces the
raw artifact. All adapter output is candidate evidence until provenance,
calendar and quorum gates pass.
"""
