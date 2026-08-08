# Portfolio map contract

`portfolio/projects.v1.json` is the reviewed source for a compact visual map of
the selected public work in this profile. It records a navigation snapshot,
not benchmark results and not a live GitHub API response.

Each project entry binds:

- its exact public repository URL;
- the public default branch and reviewed 40-character commit object ID;
- the language, systems domain, and technical focus shown in the map;
- the evidence surface already described by the project; and
- one explicit boundary that the profile must not silently cross.

Version 1 is deliberately render-closed: it contains exactly seven project
cards on exact `main` snapshots and exactly four ordered themes
(`bounded-inputs`, `deterministic-replay`, `independent-verification`, and
`claim-boundaries`). Adding a card, palette, or different default branch
requires a reviewed contract version and layout update; it cannot silently
overflow the current canvas.

The renderer applies a deterministic glyph-width budget to every
contract-derived label and writes the reviewed width into SVG `textLength`
metadata. Long prose wraps only within fixed line and pixel budgets. A string
that cannot fit its assigned title, theme, project, or scope region stops
generation instead of being clipped or silently compressed beyond the
reviewed geometry.

The reviewed semantic SHA-256 of version 1 is:

```text
9bdb27e85a464b6d0497f6d493664398657fe951724cd1dbd21ebd8b0dabc15c
```

The strict standard-library decoder rejects duplicate, missing, and unknown
fields; malformed repository URLs or refs; undeclared theme relationships;
oversized input; invalid UTF-8; and leaf symlinks. Canonical semantic bytes make
formatting and JSON object-key order irrelevant while preserving the reviewed
project and theme order used by the renderer.

Generate the reviewed SVG intentionally with:

```bash
python3 tools/render_portfolio_map.py --write
```

Verify the committed SVG and exact manifest without writing:

```bash
python3 tools/render_portfolio_map.py --check
```

The generated SVG remains a curated navigation diagram. It does not turn
pinned metadata into an attestation that a remote branch has not advanced, and
it does not invent screenshots, benchmark scores, or execution results.
