#!/usr/bin/env python3
"""Render the curated portfolio navigation map from its strict contract."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import secrets
import stat
import sys
import textwrap
import unicodedata
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.portfolio_map_contract import (
    PROJECT_COUNT,
    THEME_IDS,
    PortfolioMap,
    Project,
    read_portfolio_map,
)


SOURCE_PATH: Final = "portfolio/projects.v1.json"
SVG_PATH: Final = "assets/portfolio-systems-map.svg"
MANIFEST_PATH: Final = "assets/portfolio-systems-map.manifest.json"
CHECK_COMMAND: Final = "python3 tools/render_portfolio_map.py --check"
FORMAT: Final = "omar.portfolio_map_manifest.v1"
VIEWBOX: Final = "0 0 1800 1430"
SOURCE_PATHS: Final = (
    SOURCE_PATH,
    "tools/portfolio_map_contract.py",
    "tools/render_portfolio_map.py",
)
OUTPUT_PATHS: Final = (SVG_PATH, MANIFEST_PATH)

THEME_COLORS: Final = {
    "bounded-inputs": "#0e7490",
    "deterministic-replay": "#6d28d9",
    "independent-verification": "#15803d",
    "claim-boundaries": "#b45309",
}
THEME_TINTS: Final = {
    "bounded-inputs": "#cffafe",
    "deterministic-replay": "#ede9fe",
    "independent-verification": "#dcfce7",
    "claim-boundaries": "#fef3c7",
}
SECRET_PATTERNS: Final = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|password)\s*[:=]\s*\S+"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
)


class RenderError(RuntimeError):
    """The source-derived portfolio bundle could not be verified."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _text_length(
    value: str,
    *,
    font_size: int,
    maximum: int,
    bold: bool = False,
) -> int:
    if type(value) is not str or not value:
        raise RenderError("portfolio text is not renderable")
    units = 0.0
    for character in value:
        if character.isspace():
            units += 0.34
        elif unicodedata.east_asian_width(character) in {"F", "W"}:
            units += 1.0
        elif character in "MW@#%&QO":
            units += 0.92
        elif character in "mw":
            units += 0.82
        elif character in "ilIjtfr!'.,:;|`":
            units += 0.34
        elif character.isupper():
            units += 0.70
        elif character.isdigit():
            units += 0.62
        else:
            units += 0.56
    if bold:
        units *= 1.06
    pixels = max(1, math.ceil(units * font_size))
    if pixels > maximum:
        raise RenderError("portfolio text does not fit the reviewed canvas")
    return pixels


def _fit_attributes(
    value: str,
    *,
    font_size: int,
    maximum: int,
    bold: bool = False,
) -> str:
    length = _text_length(
        value,
        font_size=font_size,
        maximum=maximum,
        bold=bold,
    )
    return f'textLength="{length}" lengthAdjust="spacingAndGlyphs"'


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def _lines(
    text: str,
    *,
    width: int,
    maximum: int,
) -> tuple[str, ...]:
    wrapped = tuple(
        textwrap.wrap(
            text,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
        )
    )
    if not wrapped or len(wrapped) > maximum:
        raise RenderError("portfolio text does not fit the reviewed canvas")
    return wrapped


def _theme_card(
    *,
    x: int,
    identifier: str,
    label: str,
    description: str,
) -> str:
    color = THEME_COLORS[identifier]
    tint = THEME_TINTS[identifier]
    description_lines = _lines(description, width=46, maximum=3)
    text = [
        f'<g data-theme-id="{_escape(identifier)}">',
        f'<rect x="{x}" y="220" width="410" height="164" rx="18" '
        f'fill="{tint}" stroke="{color}" stroke-width="2"/>',
        f'<circle cx="{x + 28}" cy="254" r="10" fill="{color}"/>',
        f'<text x="{x + 48}" y="262" class="theme-title" '
        f'{_fit_attributes(label, font_size=20, maximum=334, bold=True)}>'
        f"{_escape(label)}</text>",
    ]
    for index, line in enumerate(description_lines):
        text.append(
            f'<text x="{x + 28}" y="{306 + index * 24}" '
            f'class="theme-copy" '
            f'{_fit_attributes(line, font_size=15, maximum=354)}>'
            f"{_escape(line)}</text>"
        )
    text.append("</g>")
    return "\n".join(text)


def _theme_chips(project: Project, *, x: int, y: int) -> str:
    parts: list[str] = []
    cursor = x
    labels = {
        "bounded-inputs": "bounded",
        "deterministic-replay": "replay",
        "independent-verification": "verified",
        "claim-boundaries": "bounded claim",
    }
    widths = {
        "bounded-inputs": 76,
        "deterministic-replay": 72,
        "independent-verification": 82,
        "claim-boundaries": 104,
    }
    for identifier in project.theme_ids:
        width = widths[identifier]
        parts.extend(
            (
                f'<rect x="{cursor}" y="{y - 18}" width="{width}" '
                f'height="26" rx="13" fill="{THEME_TINTS[identifier]}"/>',
                f'<circle cx="{cursor + 13}" cy="{y - 5}" r="4" '
                f'fill="{THEME_COLORS[identifier]}"/>',
                f'<text x="{cursor + 23}" y="{y}" class="chip">'
                f'{_escape(labels[identifier])}</text>',
            )
        )
        cursor += width + 8
    return "\n".join(parts)


def _project_card(project: Project, *, x: int, y: int) -> str:
    first_theme = project.theme_ids[0]
    rail = THEME_COLORS[first_theme]
    metadata = f"{project.domain} · {project.language}"
    reference = f"{project.default_branch} · {project.commit_oid[:12]}"
    metadata_attributes = _fit_attributes(
        metadata,
        font_size=15,
        maximum=780,
    )
    reference_attributes = _fit_attributes(
        reference,
        font_size=12,
        maximum=250,
    )
    attributes = {
        "data-project-id": project.identifier,
        "data-repository": project.repository,
        "data-default-branch": project.default_branch,
        "data-commit-oid": project.commit_oid,
        "data-theme-ids": ",".join(project.theme_ids),
    }
    rendered_attributes = " ".join(
        f'{name}="{_escape(value)}"' for name, value in attributes.items()
    )
    return "\n".join(
        (
            f"<g {rendered_attributes}>",
            f'<rect x="{x}" y="{y}" width="840" height="188" rx="18" '
            'class="project-card"/>',
            f'<rect x="{x}" y="{y}" width="8" height="188" rx="4" '
            f'fill="{rail}"/>',
            f'<text x="{x + 30}" y="{y + 39}" class="project-name" '
            f'{_fit_attributes(project.name, font_size=25, maximum=780, bold=True)}>'
            f"{_escape(project.name)}</text>",
            f'<text x="{x + 30}" y="{y + 65}" class="project-meta" '
            f"{metadata_attributes}>"
            f"{_escape(project.domain)} · {_escape(project.language)}</text>",
            f'<text x="{x + 30}" y="{y + 96}" class="row-label">FOCUS</text>',
            f'<text x="{x + 154}" y="{y + 96}" class="row-value" '
            f'{_fit_attributes(project.focus, font_size=15, maximum=658)}>'
            f"{_escape(project.focus)}</text>",
            f'<text x="{x + 30}" y="{y + 124}" class="row-label">PUBLIC EVIDENCE</text>',
            f'<text x="{x + 178}" y="{y + 124}" class="row-value" '
            f'{_fit_attributes(project.evidence_surface, font_size=15, maximum=634)}>'
            f"{_escape(project.evidence_surface)}</text>",
            f'<text x="{x + 30}" y="{y + 152}" class="row-label">BOUNDARY</text>',
            f'<text x="{x + 154}" y="{y + 152}" class="boundary" '
            f'{_fit_attributes(project.claim_boundary, font_size=15, maximum=658, bold=True)}>'
            f"{_escape(project.claim_boundary)}</text>",
            f'<text x="{x + 30}" y="{y + 177}" class="ref" '
            f"{reference_attributes}>"
            f"{_escape(project.default_branch)} · "
            f"{_escape(project.commit_oid[:12])}</text>",
            _theme_chips(project, x=x + 310, y=y + 177),
            "</g>",
        )
    )


def _scope_card(portfolio: PortfolioMap, *, x: int, y: int) -> str:
    scope_lines = _lines(portfolio.scope, width=62, maximum=2)
    parts = [
        '<g data-card-kind="scope-boundary">',
        f'<rect x="{x}" y="{y}" width="840" height="188" rx="18" '
        'fill="#111827"/>',
        f'<text x="{x + 30}" y="{y + 41}" class="scope-title">'
        "HOW TO READ THIS MAP</text>",
    ]
    for index, line in enumerate(scope_lines):
        parts.append(
            f'<text x="{x + 30}" y="{y + 78 + index * 25}" '
            f'class="scope-copy" '
            f'{_fit_attributes(line, font_size=16, maximum=780)}>'
            f"{_escape(line)}</text>"
        )
    parts.extend(
        (
            f'<text x="{x + 30}" y="{y + 143}" class="scope-note">'
            "Refs are reviewed snapshots, not live remote-state attestations.</text>",
            f'<text x="{x + 30}" y="{y + 169}" class="scope-note">'
            "No benchmark score, hiring claim, or execution result is inferred.</text>",
            "</g>",
        )
    )
    return "\n".join(parts)


def _render_svg(portfolio: PortfolioMap) -> bytes:
    if (
        len(portfolio.projects) != PROJECT_COUNT
        or tuple(theme.identifier for theme in portfolio.themes) != THEME_IDS
        or tuple(THEME_COLORS) != THEME_IDS
        or tuple(THEME_TINTS) != THEME_IDS
        or any(
            type(project.theme_ids) is not tuple
            or not project.theme_ids
            or len(set(project.theme_ids)) != len(project.theme_ids)
            or not set(project.theme_ids).issubset(THEME_IDS)
            for project in portfolio.projects
        )
    ):
        raise RenderError("portfolio contract is not render-compatible")
    title_attributes = _fit_attributes(
        portfolio.title,
        font_size=38,
        maximum=1250,
        bold=True,
    )
    subtitle_attributes = _fit_attributes(
        portfolio.subtitle,
        font_size=20,
        maximum=1250,
    )
    theme_cards = "\n".join(
        _theme_card(
            x=40 + index * 430,
            identifier=theme.identifier,
            label=theme.label,
            description=theme.description,
        )
        for index, theme in enumerate(portfolio.themes)
    )
    project_cards: list[str] = []
    for index, project in enumerate(portfolio.projects):
        row, column = divmod(index, 2)
        project_cards.append(
            _project_card(
                project,
                x=40 + column * 880,
                y=420 + row * 205,
            )
        )
    project_cards.append(_scope_card(portfolio, x=920, y=1035))
    body = "\n".join(project_cards)
    semantic_sha = portfolio.semantic_sha256
    document = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1430" viewBox="{VIEWBOX}" role="img" aria-labelledby="map-title map-desc" data-format="{FORMAT}" data-semantic-sha256="{semantic_sha}">
  <title id="map-title">{_escape(portfolio.title)}</title>
  <desc id="map-desc">A source-derived navigation map of seven public AI systems projects, their evidence surfaces, recurring engineering themes, pinned default-branch refs, and explicit claim boundaries.</desc>
  <style>
    .background {{ fill: #f8fafc; }}
    .header {{ fill: #0f172a; }}
    .title {{ fill: #f8fafc; font: 700 38px Inter, "Segoe UI", Arial, sans-serif; }}
    .subtitle {{ fill: #cbd5e1; font: 400 20px Inter, "Segoe UI", Arial, sans-serif; }}
    .digest-label {{ fill: #94a3b8; font: 600 12px "SFMono-Regular", Consolas, monospace; letter-spacing: 0.8px; }}
    .digest {{ fill: #e2e8f0; font: 400 14px "SFMono-Regular", Consolas, monospace; }}
    .metric-label {{ fill: #cbd5e1; font: 700 11px Inter, "Segoe UI", Arial, sans-serif; letter-spacing: 1px; text-anchor: middle; }}
    .metric-value {{ fill: #ffffff; font: 700 30px Inter, "Segoe UI", Arial, sans-serif; text-anchor: middle; }}
    .section {{ fill: #0f172a; font: 700 22px Inter, "Segoe UI", Arial, sans-serif; }}
    .section-note {{ fill: #64748b; font: 400 15px Inter, "Segoe UI", Arial, sans-serif; }}
    .theme-title {{ fill: #0f172a; font: 700 20px Inter, "Segoe UI", Arial, sans-serif; }}
    .theme-copy {{ fill: #334155; font: 400 15px Inter, "Segoe UI", Arial, sans-serif; }}
    .project-card {{ fill: #ffffff; stroke: #d7e0ec; stroke-width: 2; }}
    .project-name {{ fill: #0f172a; font: 700 25px Inter, "Segoe UI", Arial, sans-serif; }}
    .project-meta {{ fill: #475569; font: 500 15px Inter, "Segoe UI", Arial, sans-serif; }}
    .row-label {{ fill: #64748b; font: 700 11px Inter, "Segoe UI", Arial, sans-serif; letter-spacing: 0.8px; }}
    .row-value {{ fill: #1e293b; font: 500 15px Inter, "Segoe UI", Arial, sans-serif; }}
    .boundary {{ fill: #9a3412; font: 600 15px Inter, "Segoe UI", Arial, sans-serif; }}
    .ref {{ fill: #64748b; font: 400 12px "SFMono-Regular", Consolas, monospace; }}
    .chip {{ fill: #334155; font: 600 11px Inter, "Segoe UI", Arial, sans-serif; }}
    .scope-title {{ fill: #ffffff; font: 700 20px Inter, "Segoe UI", Arial, sans-serif; }}
    .scope-copy {{ fill: #e2e8f0; font: 500 16px Inter, "Segoe UI", Arial, sans-serif; }}
    .scope-note {{ fill: #94a3b8; font: 400 14px Inter, "Segoe UI", Arial, sans-serif; }}
    .footer {{ fill: #dbeafe; stroke: #60a5fa; stroke-width: 2; }}
    .footer-title {{ fill: #075985; font: 700 16px Inter, "Segoe UI", Arial, sans-serif; }}
    .footer-copy {{ fill: #334155; font: 400 14px Inter, "Segoe UI", Arial, sans-serif; }}
  </style>
  <rect class="background" width="1800" height="1430"/>
  <rect class="header" x="32" y="28" width="1736" height="158" rx="24"/>
  <text class="title" x="76" y="84" {title_attributes}>{_escape(portfolio.title)}</text>
  <text class="subtitle" x="76" y="122" {subtitle_attributes}>{_escape(portfolio.subtitle)}</text>
  <text class="digest-label" x="76" y="153">CONTRACT SEMANTIC SHA-256</text>
  <text class="digest" x="290" y="153">{semantic_sha}</text>
  <g data-metric="projects">
    <rect x="1410" y="58" width="140" height="92" rx="18" fill="#164e63"/>
    <text class="metric-label" x="1480" y="86">PROJECTS</text>
    <text class="metric-value" x="1480" y="127">{len(portfolio.projects)}</text>
  </g>
  <g data-metric="themes">
    <rect x="1570" y="58" width="140" height="92" rx="18" fill="#4c1d95"/>
    <text class="metric-label" x="1640" y="86">THEMES</text>
    <text class="metric-value" x="1640" y="127">{len(portfolio.themes)}</text>
  </g>
  <text class="section" x="40" y="210">Recurring engineering constraints</text>
  {theme_cards}
  <text class="section" x="40" y="414">Selected public systems</text>
  <text class="section-note" x="430" y="414">Evidence surface + explicit boundary + pinned default-branch snapshot</text>
  {body}
  <rect class="footer" x="40" y="1260" width="1720" height="120" rx="18"/>
  <text class="footer-title" x="70" y="1300">SOURCE-DERIVED NAVIGATION, NOT A SCORECARD</text>
  <text class="footer-copy" x="70" y="1331">Generated from portfolio/projects.v1.json. Every card preserves one public evidence surface and one non-goal.</text>
  <text class="footer-copy" x="70" y="1358">Reproduce: {CHECK_COMMAND} · exact sources and output SHA-256 are bound in the adjacent manifest.</text>
</svg>
"""
    return document.encode("utf-8")


def _source_records(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for relative_path in SOURCE_PATHS:
        payload = (root / relative_path).read_bytes()
        records.append(
            {
                "bytes": len(payload),
                "path": relative_path,
                "sha256": _sha256(payload),
            }
        )
    return records


def build_bundle(root: Path) -> dict[str, bytes]:
    """Build the complete output bundle without mutating the repository."""

    portfolio = read_portfolio_map(root / SOURCE_PATH)
    visual = _render_svg(portfolio)
    manifest = {
        "check_command": CHECK_COMMAND,
        "claim_boundary": {
            "description": portfolio.scope,
            "contains_benchmark_results": False,
            "remote_state_is_live": False,
        },
        "format": FORMAT,
        "map": {
            "project_count": len(portfolio.projects),
            "projects": [
                {
                    "claim_boundary": project.claim_boundary,
                    "commit_oid": project.commit_oid,
                    "default_branch": project.default_branch,
                    "evidence_surface": project.evidence_surface,
                    "id": project.identifier,
                    "repository": project.repository,
                    "theme_ids": list(project.theme_ids),
                }
                for project in portfolio.projects
            ],
            "semantic_sha256": portfolio.semantic_sha256,
            "theme_count": len(portfolio.themes),
            "theme_ids": [theme.identifier for theme in portfolio.themes],
        },
        "outputs": [
            {
                "bytes": len(visual),
                "media_type": "image/svg+xml",
                "path": SVG_PATH,
                "sha256": _sha256(visual),
            }
        ],
        "schema_version": 1,
        "sources": _source_records(root),
    }
    bundle = {
        SVG_PATH: visual,
        MANIFEST_PATH: _json_bytes(manifest),
    }
    _scan_bundle(bundle, root)
    return bundle


def _scan_bundle(bundle: Mapping[str, bytes], root: Path) -> None:
    if set(bundle) != {SVG_PATH, MANIFEST_PATH}:
        raise RenderError("generated output inventory is not exact")
    forbidden = (
        str(root),
        "/home/",
        "/Users/",
        "\\Users\\",
        "file://",
        "localhost",
    )
    for relative_path, payload in bundle.items():
        text = payload.decode("utf-8", errors="strict")
        for token in forbidden:
            if token in text:
                raise RenderError("generated output contains host-local data")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise RenderError("generated output contains secret-like data")
        if relative_path == SVG_PATH:
            lowered = text.casefold()
            for surface in (
                "<script",
                "<image",
                "<foreignobject",
                "<iframe",
                "<object",
                "<embed",
                " href=",
                " src=",
                "url(",
            ):
                if surface in lowered:
                    raise RenderError(
                        "generated SVG contains an external-resource surface"
                    )


def _fingerprint(status: os.stat_result) -> tuple[int, ...]:
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _assert_assets_binding(root_fd: int, assets_fd: int) -> None:
    visible = os.stat("assets", dir_fd=root_fd, follow_symlinks=False)
    pinned = os.fstat(assets_fd)
    if (
        not stat.S_ISDIR(visible.st_mode)
        or not stat.S_ISDIR(pinned.st_mode)
        or (visible.st_dev, visible.st_ino)
        != (pinned.st_dev, pinned.st_ino)
    ):
        raise RenderError("output directory binding changed")


def _target_fingerprint(
    assets_fd: int,
    name: str,
) -> tuple[int, ...] | None:
    try:
        status = os.stat(name, dir_fd=assets_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(status.st_mode):
        raise RenderError("output target must be a regular file")
    return _fingerprint(status)


def _snapshot_target(
    assets_fd: int,
    name: str,
) -> tuple[bytes, int, tuple[int, ...]] | None:
    initial = _target_fingerprint(assets_fd, name)
    if initial is None:
        return None
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        dir_fd=assets_fd,
    )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _fingerprint(opened) != initial:
            raise RenderError("output target binding changed")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        completed = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    visible = _target_fingerprint(assets_fd, name)
    if visible != initial or _fingerprint(completed) != initial:
        raise RenderError("output target changed during snapshot")
    return b"".join(chunks), stat.S_IMODE(completed.st_mode), initial


def _stage_payload(
    assets_fd: int,
    *,
    label: str,
    payload: bytes,
    mode: int,
) -> str:
    descriptor: int | None = None
    name = ""
    for _ in range(32):
        name = f".portfolio-map-{label}.{secrets.token_hex(12)}"
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_CLOEXEC
                | os.O_NOFOLLOW,
                0o600,
                dir_fd=assets_fd,
            )
            break
        except FileExistsError:
            continue
    if descriptor is None:
        raise RenderError("could not allocate a private output stage")
    completed = False
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short output stage write")
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
        completed = True
    finally:
        os.close(descriptor)
        if not completed:
            try:
                os.unlink(name, dir_fd=assets_fd)
            except FileNotFoundError:
                pass
    return name


def _cleanup_asset_names(assets_fd: int, names: Iterable[str]) -> bool:
    clean = True
    for name in tuple(names):
        try:
            os.unlink(name, dir_fd=assets_fd)
        except FileNotFoundError:
            continue
        except OSError:
            clean = False
    return clean


def _write_bundle(root: Path, bundle: Mapping[str, bytes]) -> None:
    if set(bundle) != set(OUTPUT_PATHS) or any(
        type(bundle[path]) is not bytes for path in OUTPUT_PATHS
    ):
        raise RenderError("generated output inventory is not exact")

    root_fd: int | None = None
    assets_fd: int | None = None
    stages: dict[str, str] = {}
    backups: dict[str, str] = {}
    snapshots: dict[str, tuple[int, ...] | None] = {}
    published: list[str] = []
    failure: str | None = None
    try:
        root_fd = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        try:
            os.mkdir("assets", mode=0o755, dir_fd=root_fd)
        except FileExistsError:
            pass
        assets_fd = os.open(
            "assets",
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=root_fd,
        )
        _assert_assets_binding(root_fd, assets_fd)

        for relative_path in OUTPUT_PATHS:
            name = Path(relative_path).name
            snapshot = _snapshot_target(assets_fd, name)
            snapshots[name] = None if snapshot is None else snapshot[2]
            stages[name] = _stage_payload(
                assets_fd,
                label=f"stage-{name}",
                payload=bundle[relative_path],
                mode=0o644,
            )
            if snapshot is not None:
                backups[name] = _stage_payload(
                    assets_fd,
                    label=f"backup-{name}",
                    payload=snapshot[0],
                    mode=snapshot[1],
                )
        os.fsync(assets_fd)

        for relative_path in OUTPUT_PATHS:
            name = Path(relative_path).name
            _assert_assets_binding(root_fd, assets_fd)
            if _target_fingerprint(assets_fd, name) != snapshots[name]:
                raise RenderError("output target changed before publication")
            os.replace(
                stages[name],
                name,
                src_dir_fd=assets_fd,
                dst_dir_fd=assets_fd,
            )
            del stages[name]
            published.append(name)
            os.fsync(assets_fd)
            committed = _snapshot_target(assets_fd, name)
            if (
                committed is None
                or committed[0] != bundle[relative_path]
                or committed[1] != 0o644
            ):
                raise RenderError("published output verification failed")
        _assert_assets_binding(root_fd, assets_fd)
    except (OSError, RenderError):
        failure = "output transaction failed"
        if assets_fd is not None:
            rollback_clean = True
            for name in reversed(published):
                try:
                    backup = backups.pop(name, None)
                    if backup is None:
                        os.unlink(name, dir_fd=assets_fd)
                    else:
                        os.replace(
                            backup,
                            name,
                            src_dir_fd=assets_fd,
                            dst_dir_fd=assets_fd,
                        )
                except OSError:
                    rollback_clean = False
            if rollback_clean:
                rollback_clean = _cleanup_asset_names(
                    assets_fd,
                    (*stages.values(), *backups.values()),
                )
                try:
                    os.fsync(assets_fd)
                except OSError:
                    rollback_clean = False
            else:
                _cleanup_asset_names(assets_fd, stages.values())
            if not rollback_clean:
                failure = "output transaction failed; rollback incomplete"
    else:
        assert assets_fd is not None
        cleanup_clean = _cleanup_asset_names(assets_fd, backups.values())
        try:
            os.fsync(assets_fd)
        except OSError:
            cleanup_clean = False
        if not cleanup_clean:
            failure = "output transaction committed; cleanup incomplete"
    finally:
        if assets_fd is not None:
            os.close(assets_fd)
        if root_fd is not None:
            os.close(root_fd)

    if failure is not None:
        raise RenderError(failure) from None


def _check_bundle(root: Path, bundle: Mapping[str, bytes]) -> None:
    mismatches: list[str] = []
    for relative_path, expected in sorted(bundle.items()):
        target = root / relative_path
        try:
            status = target.lstat()
        except FileNotFoundError:
            mismatches.append(relative_path)
            continue
        if (
            not stat.S_ISREG(status.st_mode)
            or target.is_symlink()
            or target.read_bytes() != expected
        ):
            mismatches.append(relative_path)
    if mismatches:
        raise RenderError(
            "generated artifact drift:" + ",".join(mismatches)
        )


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write or verify the source-derived portfolio map."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parse_args(argv)
    try:
        bundle = build_bundle(ROOT)
        if arguments.write:
            _write_bundle(ROOT, bundle)
            action = "wrote"
        else:
            _check_bundle(ROOT, bundle)
            action = "verified"
    except (OSError, RenderError) as error:
        print(f"portfolio map: FAIL ({error})", file=os.sys.stderr)
        return 1
    print(f"portfolio map: PASS ({action} SVG + exact manifest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
