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

The reviewed semantic SHA-256 of version 1 is:

```text
e7c9ae9b5e0344bed4ad72c40a8524ab46df7afa7896c8a7240b582e35ef61be
```

The strict standard-library decoder rejects duplicate, missing, and unknown
fields; malformed repository URLs or refs; undeclared theme relationships;
oversized input; invalid UTF-8; and leaf symlinks. Canonical semantic bytes make
formatting and JSON object-key order irrelevant while preserving the reviewed
project and theme order used by the renderer.

The future SVG generated from this contract will remain a curated navigation
diagram. It will not turn pinned metadata into an attestation that a remote
branch has not advanced, and it will not invent screenshots, benchmark scores,
or execution results.
