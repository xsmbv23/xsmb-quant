# app.py UI Preservation Contract V1

The legacy `app.py` is a presentation contract and must be preserved in full.

## Rule

The rebuild replaces the service/core layer behind the UI. It does not redesign the UI.

Preserved elements include:

- layout and component hierarchy;
- tabs and navigation;
- labels, tables, charts and status panels;
- user actions and button semantics where they can be mapped safely;
- displayed audit/forensic information.

Before backend replacement, the legacy `app.py` bytes and SHA256 must be recorded as a preservation artifact. Any intentional UI change requires a separate versioned change record.
