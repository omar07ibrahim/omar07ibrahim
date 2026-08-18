# Profile README rendering lab

This directory contains inert, single-variable fixtures for comparing GitHub's
repository README renderer with the embedded profile README renderer.

Safety constraints:

- no scripts, event handlers, forms, navigation overlays, or external requests;
- no animation, `foreignObject`, embedded HTML, or CSS inside SVG assets;
- bounded content and at most two levels of nesting;
- stop testing if a fixture affects navigation, creates a clickable overlay, or
  causes noticeable resource pressure.

Candidate severity:

- `L0`: normal rendering;
- `L1`: unusual but contained inside the README;
- `L2`: large but contained effect; visually interesting, not a bug by itself;
- `L3`: document overflow, trusted-UI displacement, or content escaping the
  README boundary;
- `STOP`: interactive overlay, navigation impact, code execution, or load spike.

