#!/usr/bin/env python3
"""Independently verify a closed portfolio-map candidate bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path
from typing import Final, NoReturn

ROOT: Final = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.portfolio_map_contract import read_portfolio_map


SOURCE_PATH: Final = "portfolio/projects.v1.json"
SOURCE_PATHS: Final = (
    SOURCE_PATH,
    "tools/portfolio_map_contract.py",
    "tools/render_portfolio_map.py",
)
SVG_NAME: Final = "portfolio-systems-map.svg"
MANIFEST_NAME: Final = "portfolio-systems-map.manifest.json"
SVG_PATH: Final = f"assets/{SVG_NAME}"
MANIFEST_PATH: Final = f"assets/{MANIFEST_NAME}"
CHECK_COMMAND: Final = "python3 tools/render_portfolio_map.py --check"
MANIFEST_FORMAT: Final = "omar.portfolio_map_manifest.v1"
VIEWBOX: Final = "0 0 1800 1430"
MAX_FILE_BYTES: Final = 256 * 1024
EXPECTED_PROJECT_REFS: Final = (
    (
        "impactdiff",
        "omar07ibrahim/impactdiff",
        "4fb56ee34b74f994d7dc3714443dfc8b25e45936",
    ),
    (
        "ssemaphore",
        "omar07ibrahim/ssemaphore",
        "6a4974d01bc5e74307fb4dee192b0b8a752e6274",
    ),
    (
        "runnelmoe",
        "omar07ibrahim/runnelmoe",
        "efaf38f10c1625d745eeb354c15ebe9b9b77611f",
    ),
    (
        "tensorkiln",
        "omar07ibrahim/tensorkiln",
        "32c078a4c07f553abce9373aeb2ff8b601f23d8f",
    ),
    (
        "falsewake",
        "omar07ibrahim/falsewake",
        "84389cda0bd7b715e166273d52640d16d84f5c4c",
    ),
    (
        "stratafold",
        "omar07ibrahim/stratafold",
        "3086247ab991571d377fd9b2b0773cd40c6a2441",
    ),
    (
        "peftlint",
        "omar07ibrahim/peftlint",
        "ee72ce7a48edbfe3df9b463cc54583a2b8a6529b",
    ),
)
SECRET_PATTERNS: Final = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password)\s*[:=]\s*\S+"
    ),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
)


class CandidateError(RuntimeError):
    """The candidate does not match its reviewed source."""


class _DuplicateKey(ValueError):
    pass


def _fail(reason: str) -> NoReturn:
    raise CandidateError(reason) from None


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fingerprint(status: os.stat_result) -> tuple[int, ...]:
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _read_regular(path: Path, *, maximum: int = MAX_FILE_BYTES) -> bytes:
    try:
        visible = os.stat(path, follow_symlinks=False)
    except OSError:
        _fail("missing_or_unreadable_file")
    if not stat.S_ISREG(visible.st_mode) or visible.st_size > maximum:
        _fail("invalid_file")
    flags = os.O_RDONLY
    for name in ("O_CLOEXEC", "O_NOFOLLOW"):
        value = getattr(os, name, None)
        if value is None:
            _fail("unsupported_file_boundary")
        flags |= value
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or _fingerprint(opened) != _fingerprint(visible)
        ):
            _fail("file_binding_changed")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        completed = os.fstat(descriptor)
    except CandidateError:
        raise
    except OSError:
        _fail("file_read_failed")
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        final = os.stat(path, follow_symlinks=False)
    except OSError:
        _fail("file_binding_changed")
    if (
        len(payload) > maximum
        or _fingerprint(completed) != _fingerprint(opened)
        or _fingerprint(final) != _fingerprint(opened)
    ):
        _fail("file_binding_changed")
    return payload


def _pairs_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _decode_manifest(payload: bytes) -> object:
    try:
        text = payload.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateKey,
        ValueError,
        RecursionError,
    ):
        _fail("invalid_manifest")


def _bundle_payloads(directory: Path) -> tuple[bytes, bytes]:
    try:
        status = os.stat(directory, follow_symlinks=False)
    except OSError:
        _fail("invalid_bundle_directory")
    if not stat.S_ISDIR(status.st_mode):
        _fail("invalid_bundle_directory")
    expected = {SVG_NAME, MANIFEST_NAME}
    try:
        with os.scandir(directory) as stream:
            entries = list(stream)
    except OSError:
        _fail("invalid_bundle_directory")
    if {entry.name for entry in entries} != expected:
        _fail("bundle_inventory_mismatch")
    for entry in entries:
        try:
            entry_status = entry.stat(follow_symlinks=False)
        except OSError:
            _fail("bundle_inventory_mismatch")
        if not stat.S_ISREG(entry_status.st_mode):
            _fail("bundle_inventory_mismatch")
    return (
        _read_regular(directory / SVG_NAME),
        _read_regular(directory / MANIFEST_NAME),
    )


def _source_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for relative_path in SOURCE_PATHS:
        payload = _read_regular(ROOT / relative_path)
        records.append(
            {
                "bytes": len(payload),
                "path": relative_path,
                "sha256": _sha256(payload),
            }
        )
    return records


def _expected_manifest(
    *,
    visual: bytes,
    portfolio: object,
) -> dict[str, object]:
    projects = portfolio.projects
    themes = portfolio.themes
    return {
        "check_command": CHECK_COMMAND,
        "claim_boundary": {
            "contains_benchmark_results": False,
            "description": portfolio.scope,
            "remote_state_is_live": False,
        },
        "format": MANIFEST_FORMAT,
        "map": {
            "project_count": len(projects),
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
                for project in projects
            ],
            "semantic_sha256": portfolio.semantic_sha256,
            "theme_count": len(themes),
            "theme_ids": [theme.identifier for theme in themes],
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
        "sources": _source_records(),
    }


def _verify_source(portfolio: object) -> None:
    actual = tuple(
        (
            project.identifier,
            project.repository,
            project.commit_oid,
        )
        for project in portfolio.projects
    )
    if actual != EXPECTED_PROJECT_REFS:
        _fail("immutable_project_refs_mismatch")
    if any(
        project.default_branch != "main"
        for project in portfolio.projects
    ):
        _fail("default_branch_mismatch")


def _verify_svg(visual: bytes, portfolio: object) -> None:
    try:
        text = visual.decode("utf-8", errors="strict")
        root = ET.fromstring(visual)
    except (UnicodeDecodeError, ET.ParseError):
        _fail("invalid_svg")
    if (
        root.tag != "{http://www.w3.org/2000/svg}svg"
        or root.attrib.get("viewBox") != VIEWBOX
        or root.attrib.get("role") != "img"
        or root.attrib.get("data-format") != MANIFEST_FORMAT
        or root.attrib.get("data-semantic-sha256")
        != portfolio.semantic_sha256
    ):
        _fail("svg_root_mismatch")

    labelled = root.attrib.get("aria-labelledby", "").split()
    identifiers = {
        element.attrib["id"]
        for element in root.iter()
        if "id" in element.attrib
    }
    if len(labelled) != 2 or not set(labelled).issubset(identifiers):
        _fail("svg_accessibility_mismatch")

    project_elements = [
        element
        for element in root.iter()
        if "data-project-id" in element.attrib
    ]
    project_nodes = {
        element.attrib["data-project-id"]: element
        for element in project_elements
    }
    if (
        len(project_nodes) != len(project_elements)
        or set(project_nodes)
        != {project.identifier for project in portfolio.projects}
    ):
        _fail("svg_project_inventory_mismatch")

    visible = "".join(root.itertext())
    for project in portfolio.projects:
        node = project_nodes[project.identifier]
        expected_attributes = {
            "data-repository": project.repository,
            "data-default-branch": project.default_branch,
            "data-commit-oid": project.commit_oid,
            "data-theme-ids": ",".join(project.theme_ids),
        }
        if any(
            node.attrib.get(name) != value
            for name, value in expected_attributes.items()
        ):
            _fail("svg_project_binding_mismatch")
        for value in (
            project.name,
            project.domain,
            project.focus,
            project.evidence_surface,
            project.claim_boundary,
            project.commit_oid[:12],
        ):
            if value not in visible:
                _fail("svg_visible_claim_mismatch")

    theme_elements = [
        element
        for element in root.iter()
        if "data-theme-id" in element.attrib
    ]
    theme_ids = [element.attrib["data-theme-id"] for element in theme_elements]
    if (
        len(theme_ids) != len(set(theme_ids))
        or set(theme_ids)
        != {theme.identifier for theme in portfolio.themes}
    ):
        _fail("svg_theme_inventory_mismatch")

    for token in (
        str(ROOT),
        "/home/",
        "/Users/",
        "\\Users\\",
        "file://",
        "localhost",
    ):
        if token in text:
            _fail("svg_host_data")
    lowered = text.casefold()
    for token in (
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
        if token in lowered:
            _fail("svg_external_resource_surface")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            _fail("svg_secret_like_data")


def verify(directory: Path) -> None:
    visual, manifest_payload = _bundle_payloads(directory)
    portfolio = read_portfolio_map(ROOT / SOURCE_PATH)
    _verify_source(portfolio)
    manifest = _decode_manifest(manifest_payload)
    if manifest != _expected_manifest(
        visual=visual,
        portfolio=portfolio,
    ):
        _fail("manifest_source_binding_mismatch")
    _verify_svg(visual, portfolio)


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify one closed portfolio-map candidate bundle."
    )
    parser.add_argument("--bundle", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parse_args(argv)
    try:
        verify(arguments.bundle)
    except (CandidateError, OSError) as error:
        print(f"portfolio candidate: FAIL ({error})", file=sys.stderr)
        return 1
    print(
        "portfolio candidate: PASS "
        "(independent source and two-file bundle verification)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
