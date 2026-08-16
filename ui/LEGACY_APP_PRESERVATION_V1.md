# Legacy `app.py` preservation contract

The legacy interface is a presentation contract and must be preserved in full while the core is replaced behind it.

Reference artifact:

- filename: `app.py`
- size: `92,490` bytes
- SHA-256: `a0a9498f0370167b1681e371828d26294cdab850b55332738ca267f06801f01b`

## Locked rule

Do not redesign the UI while rebuilding the data/core layers.

Preserve:

- tabs and navigation;
- buttons and controls;
- labels and status areas;
- tables/charts/text outputs;
- user workflow and presentation semantics.

Replace only the implementation behind the UI through explicit service adapters.

The original file is retained as a user-provided source artifact outside Git source control until it is injected into the new repository byte-for-byte. The SHA above is the preservation anchor.
