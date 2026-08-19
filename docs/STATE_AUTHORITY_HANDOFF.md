# STATE AUTHORITY HANDOFF — XSMB DATA PLANE

The data plane does not own logical system state.

```text
Brain current_state.json
        │
        ▼
  authority identity
        │
        ▼
xsmb-quant projection
        │
        ▼
collect / observe / preserve evidence
```

## Rules

- FULL_27 remains source truth for data only after Brain admission.
- TAIL_27 remains derived data.
- Missing data remains unknown.
- Collectors are observation-only.
- The data plane cannot promote itself.
- A local state claim conflicting with Brain is `HARD_DENY`.
- Historical action logs cannot override current Brain authority.
- Runtime is evidence, not logical-state authority.
- Layer 1 expansion remains locked until Brain authorizes the transition.

Current Brain authority identity:

```text
repository = xsmbv23/Project_Brain_AI
path = state/current_state.json
blob = f368e1b448fe34f56897257e318e46709ad268fe
protocol = 1.0
```
