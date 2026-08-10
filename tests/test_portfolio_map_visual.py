from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from unittest import mock

from tools import render_portfolio_map
from tools.portfolio_map_contract import read_portfolio_map


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / render_portfolio_map.SOURCE_PATH
SVG = ROOT / render_portfolio_map.SVG_PATH
MANIFEST = ROOT / render_portfolio_map.MANIFEST_PATH
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
FROZEN_OUTPUT_SHA256 = {
    render_portfolio_map.SVG_PATH: (
        "8e3d2657b382381fa6e41aee739d015cdcb0c0eb83fed62c85ed591506a4c039"
    ),
    render_portfolio_map.MANIFEST_PATH: (
        "a4cd96e3f4571b48323b0de3dcae5be53c4c69c128add013a9f5bec11d73d213"
    ),
}


class PortfolioMapVisualTests(unittest.TestCase):
    def test_bundle_is_byte_reproducible(self) -> None:
        bundle = render_portfolio_map.build_bundle(ROOT)
        self.assertEqual(
            set(bundle),
            {
                render_portfolio_map.SVG_PATH,
                render_portfolio_map.MANIFEST_PATH,
            },
        )
        self.assertEqual(bundle[render_portfolio_map.SVG_PATH], SVG.read_bytes())
        self.assertEqual(
            bundle[render_portfolio_map.MANIFEST_PATH],
            MANIFEST.read_bytes(),
        )

    def test_renderer_rejects_contracts_outside_the_reviewed_canvas(self) -> None:
        portfolio = read_portfolio_map(SOURCE)
        first_project = portfolio.projects[0]
        first_theme = portfolio.themes[0]
        incompatible_contracts = [
            replace(portfolio, projects=portfolio.projects[:-1]),
            replace(portfolio, themes=tuple(reversed(portfolio.themes))),
            replace(
                portfolio,
                projects=(
                    replace(first_project, theme_ids=("bogus-theme",)),
                    *portfolio.projects[1:],
                ),
            ),
            replace(portfolio, title="W" * 80),
            replace(portfolio, subtitle="W" * 100),
            replace(portfolio, scope="W" * 120),
            replace(
                portfolio,
                themes=(
                    replace(first_theme, label="W" * 40),
                    *portfolio.themes[1:],
                ),
            ),
            replace(
                portfolio,
                themes=(
                    replace(first_theme, description="W" * 120),
                    *portfolio.themes[1:],
                ),
            ),
        ]
        for field, maximum in (
            ("name", 48),
            ("domain", 64),
            ("language", 48),
            ("focus", 80),
            ("evidence_surface", 90),
            ("claim_boundary", 90),
        ):
            incompatible_contracts.append(
                replace(
                    portfolio,
                    projects=(
                        replace(first_project, **{field: "W" * maximum}),
                        *portfolio.projects[1:],
                    ),
                )
            )

        for incompatible in incompatible_contracts:
            with self.subTest(incompatible=incompatible):
                with self.assertRaises(render_portfolio_map.RenderError):
                    render_portfolio_map._render_svg(incompatible)

    def test_writer_rolls_back_both_outputs_if_manifest_publish_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            old_svg = b"<svg>previous</svg>\n"
            old_manifest = b'{"state":"previous"}\n'
            (assets / Path(render_portfolio_map.SVG_PATH).name).write_bytes(
                old_svg
            )
            (
                assets / Path(render_portfolio_map.MANIFEST_PATH).name
            ).write_bytes(old_manifest)
            bundle = {
                render_portfolio_map.SVG_PATH: b"<svg>next</svg>\n",
                render_portfolio_map.MANIFEST_PATH: b'{"state":"next"}\n',
            }
            original_replace = os.replace
            manifest_name = Path(
                render_portfolio_map.MANIFEST_PATH
            ).name
            injected = False

            def replace_with_manifest_failure(
                source: str,
                destination: str,
                *,
                src_dir_fd: int | None = None,
                dst_dir_fd: int | None = None,
            ) -> None:
                nonlocal injected
                if (
                    not injected
                    and destination == manifest_name
                    and ".portfolio-map-stage-" in source
                ):
                    injected = True
                    raise OSError("injected manifest publication failure")
                original_replace(
                    source,
                    destination,
                    src_dir_fd=src_dir_fd,
                    dst_dir_fd=dst_dir_fd,
                )

            with mock.patch.object(
                render_portfolio_map.os,
                "replace",
                side_effect=replace_with_manifest_failure,
            ):
                with self.assertRaisesRegex(
                    render_portfolio_map.RenderError,
                    r"\Aoutput transaction failed\Z",
                ):
                    render_portfolio_map._write_bundle(root, bundle)

            self.assertTrue(injected)
            self.assertEqual(
                (
                    assets / Path(render_portfolio_map.SVG_PATH).name
                ).read_bytes(),
                old_svg,
            )
            self.assertEqual(
                (
                    assets / Path(
                        render_portfolio_map.MANIFEST_PATH
                    ).name
                ).read_bytes(),
                old_manifest,
            )
            self.assertEqual(
                sorted(path.name for path in assets.iterdir()),
                sorted(
                    (
                        Path(render_portfolio_map.SVG_PATH).name,
                        Path(render_portfolio_map.MANIFEST_PATH).name,
                    )
                ),
            )

    def test_documented_check_is_read_only_and_succeeds(self) -> None:
        before = {path: path.read_bytes() for path in (SVG, MANIFEST)}
        completed = subprocess.run(
            [sys.executable, "tools/render_portfolio_map.py", "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "portfolio map: PASS (verified SVG + exact manifest)\n",
        )
        self.assertEqual(
            before,
            {path: path.read_bytes() for path in (SVG, MANIFEST)},
        )

    def test_manifest_binds_sources_output_and_every_card_claim(self) -> None:
        portfolio = read_portfolio_map(SOURCE)
        manifest = json.loads(MANIFEST.read_bytes())
        visual = SVG.read_bytes()

        self.assertEqual(manifest["format"], render_portfolio_map.FORMAT)
        self.assertEqual(
            manifest["check_command"],
            render_portfolio_map.CHECK_COMMAND,
        )
        self.assertEqual(
            [record["path"] for record in manifest["sources"]],
            list(render_portfolio_map.SOURCE_PATHS),
        )
        for record in manifest["sources"]:
            payload = (ROOT / record["path"]).read_bytes()
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(
                record["sha256"],
                hashlib.sha256(payload).hexdigest(),
            )
        self.assertEqual(manifest["outputs"], [{
            "bytes": len(visual),
            "media_type": "image/svg+xml",
            "path": render_portfolio_map.SVG_PATH,
            "sha256": hashlib.sha256(visual).hexdigest(),
        }])
        self.assertEqual(
            manifest["map"]["semantic_sha256"],
            portfolio.semantic_sha256,
        )
        self.assertEqual(
            manifest["map"]["project_count"],
            len(portfolio.projects),
        )
        self.assertFalse(
            manifest["claim_boundary"]["contains_benchmark_results"]
        )
        self.assertFalse(manifest["claim_boundary"]["remote_state_is_live"])
        self.assertEqual(
            manifest["map"]["projects"],
            [
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
        )

    def test_svg_exposes_all_projects_themes_refs_and_boundaries(self) -> None:
        portfolio = read_portfolio_map(SOURCE)
        root = ET.fromstring(SVG.read_bytes())
        project_nodes = {
            element.attrib["data-project-id"]: element
            for element in root.iter()
            if "data-project-id" in element.attrib
        }
        theme_nodes = {
            element.attrib["data-theme-id"]: element
            for element in root.iter()
            if "data-theme-id" in element.attrib
        }
        visible = "".join(root.itertext())

        self.assertEqual(
            set(project_nodes),
            {project.identifier for project in portfolio.projects},
        )
        self.assertEqual(
            set(theme_nodes),
            {theme.identifier for theme in portfolio.themes},
        )
        for project in portfolio.projects:
            with self.subTest(project=project.identifier):
                node = project_nodes[project.identifier]
                self.assertEqual(
                    node.attrib["data-repository"],
                    project.repository,
                )
                self.assertEqual(
                    node.attrib["data-commit-oid"],
                    project.commit_oid,
                )
                self.assertEqual(
                    node.attrib["data-theme-ids"],
                    ",".join(project.theme_ids),
                )
                for value in (
                    project.name,
                    project.domain,
                    project.focus,
                    project.evidence_surface,
                    project.claim_boundary,
                    project.commit_oid[:12],
                ):
                    self.assertIn(value, visible)

    def test_svg_is_accessible_fixed_canvas_sanitized_and_self_contained(
        self,
    ) -> None:
        payload = SVG.read_bytes()
        visual = payload.decode("utf-8", errors="strict")
        root = ET.fromstring(payload)

        self.assertEqual(root.tag, f"{{{SVG_NAMESPACE}}}svg")
        self.assertEqual(root.attrib["viewBox"], render_portfolio_map.VIEWBOX)
        self.assertEqual(root.attrib["role"], "img")
        labelled = root.attrib["aria-labelledby"].split()
        identifiers = {
            element.attrib["id"]
            for element in root.iter()
            if "id" in element.attrib
        }
        self.assertEqual(len(labelled), 2)
        self.assertTrue(set(labelled).issubset(identifiers))
        for pattern in render_portfolio_map.SECRET_PATTERNS:
            self.assertIsNone(pattern.search(visual))
        for forbidden in (
            str(ROOT),
            "/home/",
            "/Users/",
            "\\Users\\",
            "file://",
            "localhost",
            "<script",
            "<image",
            "<foreignObject",
            "<iframe",
            "<object",
            "<embed",
            " href=",
            " src=",
            "url(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, visual)

    def test_readme_embeds_real_map_and_reproduction_command(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contract = (
            ROOT / "docs" / "portfolio-map-contract.md"
        ).read_text(encoding="utf-8")

        self.assertIn(render_portfolio_map.SVG_PATH, readme)
        self.assertIn(render_portfolio_map.MANIFEST_PATH, readme)
        self.assertIn(render_portfolio_map.CHECK_COMMAND, readme)
        self.assertIn(render_portfolio_map.CHECK_COMMAND, contract)

    def test_generated_files_match_reviewed_hashes(self) -> None:
        for relative_path, expected in FROZEN_OUTPUT_SHA256.items():
            with self.subTest(path=relative_path):
                self.assertEqual(
                    hashlib.sha256(
                        (ROOT / relative_path).read_bytes()
                    ).hexdigest(),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()