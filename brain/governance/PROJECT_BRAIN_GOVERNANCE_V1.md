# PROJECT_BRAIN Governance Contract V1

Project_Brain_AI participates from the first data-foundation step as a governance/policy layer.

## Brain permissions

The Brain may:

- OBSERVE source, calendar, schema and provenance state;
- VALIDATE contract and policy conditions;
- ENFORCE DENY/ALLOW promotion policy;
- emit evidence and policy decisions.

The Brain may **not**:

- invent a prize value;
- infer `NON_DRAW_DAY` from missing data;
- silently repair or overwrite canonical data;
- select one conflicting source variant without evidence;
- mutate production/runtime truth;
- bypass a failed validation gate.

## Promotion rule

Canonical promotion requires all mandatory gates to pass:

`RAW provenance -> FULL_27 schema -> calendar state -> source/day identity -> quorum/conflict check -> Brain policy -> evidence`

Any failed or unresolved gate produces:

`promotion = DENY`

## Separation

Project_Brain_AI is a governor, not the source of truth. FULL_27 source evidence remains authoritative; TAIL_27 and all Quant/AI features are derived representations.
