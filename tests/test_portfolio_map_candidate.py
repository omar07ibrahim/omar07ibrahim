from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from tools import render_portfolio_map, verify_portfolio_map_candidate
from tools.portfolio_map_contract import read_portfolio_map


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / render_portfolio_map.SOURCE_PATH


def manifest_bytes(value: object) -> bytes:
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


class PortfolioMapCandidateTests(unittest.TestCase):
    def write_bundle(
        self,
        directory: Path,
        bundle: dict[str, bytes],
    ) -> None:
        for relative_path, payload in bundle.items():
            (directory / Path(relative_path).name).write_bytes(payload)

    def assert_candidate_error(
        self,
        directory: Path,
        reason: str,
    ) -> None:
        with self.assertRaises(
            verify_portfolio_map_candidate.CandidateError
        ) as raised:
            verify_portfolio_map_candidate.verify(directory)
        self.assertEqual(str(raised.exception), reason)

    def test_exact_production_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_bundle(
                directory,
                render_portfolio_map.build_bundle(ROOT),
            )

            verify_portfolio_map_candidate.verify(directory)

    def test_augmented_svg_and_recomputed_manifest_fail_replay(self) -> None:
        bundle = render_portfolio_map.build_bundle(ROOT)
        visual = bundle[render_portfolio_map.SVG_PATH].replace(
            b"</svg>\n",
            b'<text x="1" y="1">UNREVIEWED ADDITION</text>\n</svg>\n',
        )
        self.assertNotEqual(visual, bundle[render_portfolio_map.SVG_PATH])
        manifest = json.loads(
            bundle[render_portfolio_map.MANIFEST_PATH]
        )
        manifest["outputs"][0]["bytes"] = len(visual)
        manifest["outputs"][0]["sha256"] = hashlib.sha256(
            visual
        ).hexdigest()
        bundle[render_portfolio_map.SVG_PATH] = visual
        bundle[render_portfolio_map.MANIFEST_PATH] = manifest_bytes(manifest)

        portfolio = read_portfolio_map(SOURCE)
        self.assertEqual(
            verify_portfolio_map_candidate._decode_manifest(
                bundle[render_portfolio_map.MANIFEST_PATH]
            ),
            verify_portfolio_map_candidate._expected_manifest(
                visual=visual,
                portfolio=portfolio,
            ),
        )
        verify_portfolio_map_candidate._verify_svg(visual, portfolio)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_bundle(directory, bundle)
            self.assert_candidate_error(
                directory,
                "svg_renderer_replay_mismatch",
            )

    def test_semantically_equal_manifest_must_match_renderer_bytes(self) -> None:
        bundle = render_portfolio_map.build_bundle(ROOT)
        compact = (
            json.dumps(
                json.loads(bundle[render_portfolio_map.MANIFEST_PATH]),
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("ascii")
        self.assertNotEqual(
            compact,
            bundle[render_portfolio_map.MANIFEST_PATH],
        )
        bundle[render_portfolio_map.MANIFEST_PATH] = compact

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_bundle(directory, bundle)
            self.assert_candidate_error(
                directory,
                "manifest_renderer_replay_mismatch",
            )

    def test_swapped_and_extra_bundle_members_fail_closed(self) -> None:
        bundle = render_portfolio_map.build_bundle(ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            swapped = {
                render_portfolio_map.SVG_PATH: bundle[
                    render_portfolio_map.MANIFEST_PATH
                ],
                render_portfolio_map.MANIFEST_PATH: bundle[
                    render_portfolio_map.SVG_PATH
                ],
            }
            self.write_bundle(directory, swapped)
            self.assert_candidate_error(directory, "invalid_manifest")

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_bundle(directory, bundle)
            (directory / "unexpected.txt").write_bytes(b"unexpected\n")
            self.assert_candidate_error(
                directory,
                "bundle_inventory_mismatch",
            )

    def test_unreviewed_source_ref_fails_closed(self) -> None:
        portfolio = read_portfolio_map(SOURCE)
        mutated = replace(
            portfolio,
            projects=(
                replace(portfolio.projects[0], commit_oid="0" * 40),
                *portfolio.projects[1:],
            ),
        )
        bundle = render_portfolio_map.build_bundle(ROOT)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_bundle(directory, bundle)
            with mock.patch.object(
                verify_portfolio_map_candidate,
                "read_portfolio_map",
                return_value=mutated,
            ):
                self.assert_candidate_error(
                    directory,
                    "immutable_project_refs_mismatch",
                )


if __name__ == "__main__":
    unittest.main()
