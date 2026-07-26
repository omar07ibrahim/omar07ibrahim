"""Strict contract for the source-derived portfolio navigation map."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, NoReturn, cast


FORMAT: Final = "omar.portfolio_map.v1"
MAX_INPUT_BYTES: Final = 64 * 1024
PROJECT_COUNT: Final = 7
THEME_IDS: Final = (
    "bounded-inputs",
    "deterministic-replay",
    "independent-verification",
    "claim-boundaries",
)
MAX_TEXT_LENGTH: Final = 120

_ROOT_FIELDS: Final = frozenset(
    {"format", "projects", "scope", "subtitle", "themes", "title"}
)
_PROJECT_FIELDS: Final = frozenset(
    {
        "claim_boundary",
        "commit_oid",
        "default_branch",
        "domain",
        "evidence_surface",
        "focus",
        "id",
        "language",
        "name",
        "repository",
        "themes",
        "url",
    }
)
_THEME_FIELDS: Final = frozenset({"description", "id", "label"})
_IDENTIFIER = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_REPOSITORY = re.compile(
    r"omar07ibrahim/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9_])?\Z"
)
_COMMIT_OID = re.compile(r"[0-9a-f]{40}\Z")


class MapErrorCode(StrEnum):
    INVALID_FILE = "invalid_file"
    INPUT_TOO_LARGE = "input_too_large"
    INVALID_ENCODING = "invalid_encoding"
    INVALID_JSON = "invalid_json"
    DUPLICATE_KEY = "duplicate_key"
    INVALID_SHAPE = "invalid_shape"
    INVALID_VALUE = "invalid_value"


class MapError(ValueError):
    """Stable redacted validation error."""

    __slots__ = ("code",)

    def __init__(self, code: MapErrorCode) -> None:
        self.code = code
        super().__init__(f"portfolio_map_error:{code.value}")


class _DuplicateKey(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Theme:
    identifier: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class Project:
    identifier: str
    name: str
    repository: str
    url: str
    language: str
    domain: str
    focus: str
    evidence_surface: str
    claim_boundary: str
    default_branch: str
    commit_oid: str
    theme_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioMap:
    title: str
    subtitle: str
    scope: str
    themes: tuple[Theme, ...]
    projects: tuple[Project, ...]
    canonical_bytes: bytes

    @property
    def semantic_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


def _fail(code: MapErrorCode) -> NoReturn:
    raise MapError(code) from None


def _pairs_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _decode(payload: bytes | str) -> dict[str, object]:
    if type(payload) is bytes:
        if len(payload) > MAX_INPUT_BYTES:
            _fail(MapErrorCode.INPUT_TOO_LARGE)
        text: str | None = None
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            pass
        if text is None:
            _fail(MapErrorCode.INVALID_ENCODING)
    elif type(payload) is str:
        encoded: bytes | None = None
        try:
            encoded = payload.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            pass
        if encoded is None:
            _fail(MapErrorCode.INVALID_ENCODING)
        if len(encoded) > MAX_INPUT_BYTES:
            _fail(MapErrorCode.INPUT_TOO_LARGE)
        text = payload
    else:
        _fail(MapErrorCode.INVALID_SHAPE)

    failure: MapErrorCode | None = None
    value: object = None
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except _DuplicateKey:
        failure = MapErrorCode.DUPLICATE_KEY
    except (json.JSONDecodeError, ValueError, RecursionError):
        failure = MapErrorCode.INVALID_JSON
    if failure is not None:
        _fail(failure)
    if type(value) is not dict:
        _fail(MapErrorCode.INVALID_SHAPE)
    return cast(dict[str, object], value)


def _object(value: object, fields: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict:
        _fail(MapErrorCode.INVALID_SHAPE)
    result = cast(dict[str, object], value)
    if frozenset(result) != fields:
        _fail(MapErrorCode.INVALID_SHAPE)
    return result


def _list(
    value: object,
    *,
    minimum: int,
    maximum: int,
) -> list[object]:
    if type(value) is not list:
        _fail(MapErrorCode.INVALID_SHAPE)
    result = cast(list[object], value)
    if not minimum <= len(result) <= maximum:
        _fail(MapErrorCode.INVALID_VALUE)
    return result


def _text(value: object, *, maximum: int = MAX_TEXT_LENGTH) -> str:
    if type(value) is not str or not 1 <= len(value) <= maximum:
        _fail(MapErrorCode.INVALID_VALUE)
    if value != value.strip() or any(ord(character) < 32 for character in value):
        _fail(MapErrorCode.INVALID_VALUE)
    return value


def _identifier(value: object) -> str:
    result = _text(value, maximum=48)
    if _IDENTIFIER.fullmatch(result) is None:
        _fail(MapErrorCode.INVALID_VALUE)
    return result


def _canonical_document(
    *,
    title: str,
    subtitle: str,
    scope: str,
    themes: tuple[Theme, ...],
    projects: tuple[Project, ...],
) -> dict[str, object]:
    return {
        "format": FORMAT,
        "projects": [
            {
                "claim_boundary": project.claim_boundary,
                "commit_oid": project.commit_oid,
                "default_branch": project.default_branch,
                "domain": project.domain,
                "evidence_surface": project.evidence_surface,
                "focus": project.focus,
                "id": project.identifier,
                "language": project.language,
                "name": project.name,
                "repository": project.repository,
                "themes": list(project.theme_ids),
                "url": project.url,
            }
            for project in projects
        ],
        "scope": scope,
        "subtitle": subtitle,
        "themes": [
            {
                "description": theme.description,
                "id": theme.identifier,
                "label": theme.label,
            }
            for theme in themes
        ],
        "title": title,
    }


def decode_portfolio_map(payload: bytes | str) -> PortfolioMap:
    """Decode an immutable map while rejecting implicit or unknown fields."""

    document = _object(_decode(payload), _ROOT_FIELDS)
    if document["format"] != FORMAT:
        _fail(MapErrorCode.INVALID_VALUE)
    title = _text(document["title"], maximum=80)
    subtitle = _text(document["subtitle"], maximum=100)
    scope = _text(document["scope"], maximum=180)

    themes: list[Theme] = []
    theme_ids: set[str] = set()
    for raw_theme in _list(
        document["themes"],
        minimum=len(THEME_IDS),
        maximum=len(THEME_IDS),
    ):
        item = _object(raw_theme, _THEME_FIELDS)
        identifier = _identifier(item["id"])
        if identifier in theme_ids:
            _fail(MapErrorCode.INVALID_VALUE)
        theme_ids.add(identifier)
        themes.append(
            Theme(
                identifier=identifier,
                label=_text(item["label"], maximum=40),
                description=_text(item["description"], maximum=120),
            )
        )
    if tuple(theme.identifier for theme in themes) != THEME_IDS:
        _fail(MapErrorCode.INVALID_VALUE)

    projects: list[Project] = []
    project_ids: set[str] = set()
    project_names: set[str] = set()
    repositories: set[str] = set()
    for raw_project in _list(
        document["projects"],
        minimum=PROJECT_COUNT,
        maximum=PROJECT_COUNT,
    ):
        item = _object(raw_project, _PROJECT_FIELDS)
        identifier = _identifier(item["id"])
        name = _text(item["name"], maximum=48)
        repository = _text(item["repository"], maximum=100)
        if (
            identifier in project_ids
            or name.casefold() in project_names
            or repository in repositories
            or _REPOSITORY.fullmatch(repository) is None
            or ".." in repository
        ):
            _fail(MapErrorCode.INVALID_VALUE)
        project_ids.add(identifier)
        project_names.add(name.casefold())
        repositories.add(repository)

        url = _text(item["url"], maximum=160)
        if url != f"https://github.com/{repository}":
            _fail(MapErrorCode.INVALID_VALUE)
        branch = _text(item["default_branch"], maximum=100)
        commit_oid = _text(item["commit_oid"], maximum=40)
        if branch != "main" or _COMMIT_OID.fullmatch(commit_oid) is None:
            _fail(MapErrorCode.INVALID_VALUE)

        project_themes = tuple(
            _identifier(value)
            for value in _list(
                item["themes"],
                minimum=1,
                maximum=len(THEME_IDS),
            )
        )
        if (
            len(set(project_themes)) != len(project_themes)
            or not set(project_themes).issubset(theme_ids)
        ):
            _fail(MapErrorCode.INVALID_VALUE)
        projects.append(
            Project(
                identifier=identifier,
                name=name,
                repository=repository,
                url=url,
                language=_text(item["language"], maximum=48),
                domain=_text(item["domain"], maximum=64),
                focus=_text(item["focus"], maximum=80),
                evidence_surface=_text(item["evidence_surface"], maximum=90),
                claim_boundary=_text(item["claim_boundary"], maximum=90),
                default_branch=branch,
                commit_oid=commit_oid,
                theme_ids=project_themes,
            )
        )

    frozen_themes = tuple(themes)
    frozen_projects = tuple(projects)
    canonical = (
        json.dumps(
            _canonical_document(
                title=title,
                subtitle=subtitle,
                scope=scope,
                themes=frozen_themes,
                projects=frozen_projects,
            ),
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")
    return PortfolioMap(
        title=title,
        subtitle=subtitle,
        scope=scope,
        themes=frozen_themes,
        projects=frozen_projects,
        canonical_bytes=canonical,
    )


def read_portfolio_map(path: Path) -> PortfolioMap:
    """Read one bounded regular file without following a leaf symlink."""

    flags = os.O_RDONLY
    for name in ("O_CLOEXEC", "O_NOFOLLOW"):
        value = getattr(os, name, None)
        if value is None:
            _fail(MapErrorCode.INVALID_FILE)
        flags |= value
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            _fail(MapErrorCode.INVALID_FILE)
        if status.st_size > MAX_INPUT_BYTES:
            _fail(MapErrorCode.INPUT_TOO_LARGE)
        chunks: list[bytes] = []
        remaining = MAX_INPUT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(16 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > MAX_INPUT_BYTES:
            _fail(MapErrorCode.INPUT_TOO_LARGE)
    except MapError:
        raise
    except OSError:
        _fail(MapErrorCode.INVALID_FILE)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return decode_portfolio_map(payload)
