from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.portfolio_map_contract import (
    MAX_INPUT_BYTES,
    MapError,
    MapErrorCode,
    decode_portfolio_map,
    read_portfolio_map,
)


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "portfolio" / "projects.v1.json"
FROZEN_SEMANTIC_SHA256 = (
    "84b732e27f3f82ce0035a27b7393678235449eb57cbda42d603115b95c3f80eb"
)


def document() -> dict[str, object]:
    return json.loads(MAP_PATH.read_bytes())


def encoded(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


class PortfolioMapContractTests(unittest.TestCase):
    def assert_error(
        self,
        payload: bytes | str,
        code: MapErrorCode,
    ) -> None:
        with self.assertRaises(MapError) as raised:
            decode_portfolio_map(payload)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(
            str(raised.exception),
            f"portfolio_map_error:{code.value}",
        )
        self.assertIsNone(raised.exception.__context__)

    def test_committed_map_is_bounded_canonical_and_profile_linked(self) -> None:
        portfolio = read_portfolio_map(MAP_PATH)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(len(portfolio.projects), 7)
        self.assertEqual(len(portfolio.themes), 4)
        self.assertEqual(
            portfolio.semantic_sha256,
            FROZEN_SEMANTIC_SHA256,
        )
        self.assertLessEqual(len(MAP_PATH.read_bytes()), MAX_INPUT_BYTES)
        self.assertEqual(
            decode_portfolio_map(portfolio.canonical_bytes),
            portfolio,
        )
        for project in portfolio.projects:
            with self.subTest(project=project.identifier):
                self.assertIn(project.url, readme)
                self.assertEqual(len(project.commit_oid), 40)

    def test_key_order_and_formatting_do_not_change_semantic_digest(self) -> None:
        baseline = read_portfolio_map(MAP_PATH)
        reformatted = json.dumps(
            document(),
            ensure_ascii=False,
            indent=7,
            sort_keys=False,
        )

        self.assertEqual(
            decode_portfolio_map(reformatted).semantic_sha256,
            baseline.semantic_sha256,
        )

    def test_duplicate_unknown_missing_and_type_alias_fail_closed(self) -> None:
        self.assert_error(
            '{"format":"omar.portfolio_map.v1",'
            '"format":"omar.portfolio_map.v1"}',
            MapErrorCode.DUPLICATE_KEY,
        )

        unknown = document()
        unknown["unreviewed"] = True
        self.assert_error(encoded(unknown), MapErrorCode.INVALID_SHAPE)

        missing = document()
        del missing["scope"]
        self.assert_error(encoded(missing), MapErrorCode.INVALID_SHAPE)

        boolean_projects = document()
        boolean_projects["projects"] = True
        self.assert_error(
            encoded(boolean_projects),
            MapErrorCode.INVALID_SHAPE,
        )

    def test_repository_ref_url_and_theme_integrity_are_exact(self) -> None:
        mutations: list[dict[str, object]] = []

        bad_url = document()
        bad_url["projects"][0]["url"] = "https://example.invalid/project"
        mutations.append(bad_url)

        bad_oid = document()
        bad_oid["projects"][0]["commit_oid"] = "deadbeef"
        mutations.append(bad_oid)

        duplicate_repo = document()
        duplicate_repo["projects"][1]["repository"] = (
            duplicate_repo["projects"][0]["repository"]
        )
        duplicate_repo["projects"][1]["url"] = (
            duplicate_repo["projects"][0]["url"]
        )
        mutations.append(duplicate_repo)

        unknown_theme = document()
        unknown_theme["projects"][0]["themes"] = ["not-declared"]
        mutations.append(unknown_theme)

        duplicate_theme = document()
        duplicate_theme["themes"].append(duplicate_theme["themes"][0])
        mutations.append(duplicate_theme)

        traversal_branch = document()
        traversal_branch["projects"][0]["default_branch"] = "../main"
        mutations.append(traversal_branch)

        invalid_repository = document()
        invalid_repository["projects"][0]["repository"] = "./repo"
        invalid_repository["projects"][0]["url"] = "https://github.com/./repo"
        mutations.append(invalid_repository)

        fifth_theme = document()
        fifth_theme["themes"].append({
            "description": "A syntactically complete but undeclared theme.",
            "id": "extra-theme",
            "label": "Extra theme",
        })
        mutations.append(fifth_theme)

        eighth_project = document()
        additional = dict(eighth_project["projects"][0])
        additional.update({
            "commit_oid": "1" * 40,
            "id": "eighth-project",
            "name": "Eighth project",
            "repository": "omar07ibrahim/eighth-project",
            "url": "https://github.com/omar07ibrahim/eighth-project",
        })
        eighth_project["projects"].append(additional)
        mutations.append(eighth_project)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_error(
                    encoded(mutation),
                    MapErrorCode.INVALID_VALUE,
                )

    def test_v1_default_branch_is_the_exact_rendered_main_snapshot(self) -> None:
        for invalid in (
            "main/",
            "main//x",
            "main/.hidden",
            "main/x.lock",
            "develop",
        ):
            value = document()
            value["projects"][0]["default_branch"] = invalid
            with self.subTest(branch=invalid):
                self.assert_error(
                    encoded(value),
                    MapErrorCode.INVALID_VALUE,
                )

    def test_bytes_encoding_and_leaf_file_boundary_are_fail_closed(self) -> None:
        self.assert_error(
            b" " * (MAX_INPUT_BYTES + 1),
            MapErrorCode.INPUT_TOO_LARGE,
        )
        self.assert_error(b"\xff", MapErrorCode.INVALID_ENCODING)
        self.assert_error("[]", MapErrorCode.INVALID_SHAPE)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.json"
            target.write_bytes(MAP_PATH.read_bytes())
            link = root / "map.json"
            link.symlink_to(target)

            with self.assertRaises(MapError) as symlinked:
                read_portfolio_map(link)
            self.assertEqual(
                symlinked.exception.code,
                MapErrorCode.INVALID_FILE,
            )
            self.assertNotIn(temporary, str(symlinked.exception))

            oversized = root / "oversized.json"
            with oversized.open("wb") as stream:
                stream.truncate(MAX_INPUT_BYTES + 1)
            with self.assertRaises(MapError) as too_large:
                read_portfolio_map(oversized)
            self.assertEqual(
                too_large.exception.code,
                MapErrorCode.INPUT_TOO_LARGE,
            )


if __name__ == "__main__":
    unittest.main()
