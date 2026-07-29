"""
API-surface manifest schema, allowed values, canonical route-key format,
and a small valid example for the RAGFlow living-map governance layer.

The manifest overlays policy metadata onto route facts extracted from source
code.  It is the single reviewed source of truth for capability membership,
visibility, stability, and intended runtime support.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

# ---------------------------------------------------------------------------
# Allowed enum values
# ---------------------------------------------------------------------------

VISIBILITY_VALUES: tuple[str, ...] = ("public", "beta", "internal", "compatibility")
"""Every governed route MUST carry exactly one visibility classification."""

STABILITY_VALUES: tuple[str, ...] = ("stable", "experimental", "deprecated")
"""Stability of the public contract (for internal/compat routes this is advisory)."""

RUNTIME_VALUES: tuple[str, ...] = (
    "python",
    "go",
    "both",
    "python-only",
    "go-only",
)
"""Declared intended runtime(s) for the route.

- ``python`` / ``go``: only this runtime is expected.
- ``both``: the route is expected to exist in **both** Python and Go runtimes.
- ``python-only`` / ``go-only``: the route is intentionally supported in only one
  runtime and should not be flagged as a parity gap.
"""

# ---------------------------------------------------------------------------
# Canonical route-key format
# ---------------------------------------------------------------------------
# ``METHOD /normalized/path`` — e.g. ``GET /api/v1/datasets/{dataset_id}``.
# Path parameters are spelled with curly braces as produced by the shared
# normalizer (Quart ``<name>`` / ``<path:name>`` and Gin ``:name`` / ``*name``
# are all collapsed to ``{name}``).  The method is **upper-case** and the path
# is **absolute**.
#
# Duplicate canonical keys (after normalization) are rejected by validation.

CANONICAL_KEY_JOINER = " "
"""Separator between upper-case HTTP method and normalized path."""


def canonical_key(method: str, path: str) -> str:
    """Return a canonical route key from *method* and *path*."""
    return f"{method.upper().strip()} {path.rstrip('/') or '/'}"


# ---------------------------------------------------------------------------
# Manifest entry model
# ---------------------------------------------------------------------------

class ManifestEntry:
    """A single reviewed policy entry for one governed route.

    Attributes
    ----------
    method : str
        Upper-case HTTP method (e.g. ``GET``, ``POST``).
    path : str
        Normalized route path (e.g. ``/api/v1/datasets/{dataset_id}``).
    capability : str
        Human-readable Simplified Chinese capability label (e.g. "数据集管理").
    visibility : Literal["public", "beta", "internal", "compatibility"]
    stability : Literal["stable", "experimental", "deprecated"]
    runtime : Literal["python", "go", "both", "python-only", "go-only"]
    canonical_replacement : str | None
        Canonical key of the replacement route (required when
        ``visibility == "compatibility"`` and a replacement exists).
    http_reference : str | None
        Stable anchor link in the existing HTTP reference (required when
        ``visibility == "public"``).
    sdk_reference : str | None
        Python SDK surface link (required when the capability is exposed by the
        supported Python SDK).
    contract_test : str | None
        Executable or contract-test location (required when
        ``visibility == "public"``).
    notes : str | None
        Free-form maintainer notes (optional).
    """

    __slots__ = (
        "method",
        "path",
        "capability",
        "visibility",
        "stability",
        "runtime",
        "canonical_replacement",
        "http_reference",
        "sdk_reference",
        "contract_test",
        "notes",
    )

    def __init__(
        self,
        method: str,
        path: str,
        capability: str,
        visibility: str,
        stability: str,
        runtime: str,
        canonical_replacement: str | None = None,
        http_reference: str | None = None,
        sdk_reference: str | None = None,
        contract_test: str | None = None,
        notes: str | None = None,
    ) -> None:
        self.method = method.upper().strip()
        self.path = path.rstrip("/") or "/"
        self.capability = capability
        self.visibility = visibility
        self.stability = stability
        self.runtime = runtime
        self.canonical_replacement = canonical_replacement
        self.http_reference = http_reference
        self.sdk_reference = sdk_reference
        self.contract_test = contract_test
        self.notes = notes

    @property
    def key(self) -> str:
        return canonical_key(self.method, self.path)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "method": self.method,
            "path": self.path,
            "capability": self.capability,
            "visibility": self.visibility,
            "stability": self.stability,
            "runtime": self.runtime,
        }
        if self.canonical_replacement is not None:
            d["canonical_replacement"] = self.canonical_replacement
        if self.http_reference is not None:
            d["http_reference"] = self.http_reference
        if self.sdk_reference is not None:
            d["sdk_reference"] = self.sdk_reference
        if self.contract_test is not None:
            d["contract_test"] = self.contract_test
        if self.notes is not None:
            d["notes"] = self.notes
        return d


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ManifestError(Exception):
    """Validation error for the API-surface manifest."""


def _duplicate_keys(entries: list[ManifestEntry]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for e in entries:
        k = e.key
        if k in seen:
            dupes.add(k)
        seen.add(k)
    return dupes


def validate_manifest(entries: list[ManifestEntry]) -> list[str]:
    """Validate a list of manifest entries.

    Returns a (possibly empty) list of human-readable error messages.
    When the list is empty the manifest is valid.
    """
    errors: list[str] = []

    # --- duplicate canonical keys ---
    dupes = _duplicate_keys(entries)
    if dupes:
        for k in sorted(dupes):
            errors.append(f"Duplicate canonical key: {k}")

    for i, e in enumerate(entries):
        prefix = f"[{i}] {e.key}"

        if e.visibility not in VISIBILITY_VALUES:
            errors.append(
                f"{prefix}: invalid visibility '{e.visibility}'"
                f" (allowed: {', '.join(VISIBILITY_VALUES)})"
            )
        if e.stability not in STABILITY_VALUES:
            errors.append(
                f"{prefix}: invalid stability '{e.stability}'"
                f" (allowed: {', '.join(STABILITY_VALUES)})"
            )
        if e.runtime not in RUNTIME_VALUES:
            errors.append(
                f"{prefix}: invalid runtime '{e.runtime}'"
                f" (allowed: {', '.join(RUNTIME_VALUES)})"
            )

        # compatibility MUST have a canonical_replacement when a replacement exists
        if e.visibility == "compatibility" and e.canonical_replacement is None:
            errors.append(
                f"{prefix}: compatibility entry missing canonical_replacement"
            )

        # public routes require http_reference and contract_test
        if e.visibility == "public":
            if not e.http_reference:
                errors.append(
                    f"{prefix}: public route missing http_reference"
                )
            if not e.contract_test:
                errors.append(
                    f"{prefix}: public route missing contract_test"
                )

    return errors


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> list[ManifestEntry]:
    """Load a manifest from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return _dicts_to_entries(data)


def save_manifest(entries: list[ManifestEntry], path: Path) -> None:
    """Save a manifest to a JSON file with stable sorting."""
    sorted_entries = sorted(entries, key=lambda e: (e.capability, e.method, e.path))
    data = [_sort_dict(e.to_dict()) for e in sorted_entries]
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _dicts_to_entries(data: list[dict[str, Any]]) -> list[ManifestEntry]:
    return [ManifestEntry(**d) for d in data]


def _sort_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Stable key order for deterministic output."""
    field_order = (
        "method",
        "path",
        "capability",
        "visibility",
        "stability",
        "runtime",
        "canonical_replacement",
        "http_reference",
        "sdk_reference",
        "contract_test",
        "notes",
    )
    result: dict[str, Any] = {}
    for k in field_order:
        if k in d:
            result[k] = d[k]
    return result


# ---------------------------------------------------------------------------
# Small valid example (mirrors real RAGFlow routes for illustration)
# ---------------------------------------------------------------------------

EXAMPLE_ENTRIES: list[ManifestEntry] = [
    ManifestEntry(
        method="GET",
        path="/api/v1/datasets",
        capability="数据集管理",
        visibility="public",
        stability="stable",
        runtime="both",
        http_reference="references/http_api_reference.md#get-apiv1datasets",
        sdk_reference="sdk/python/ragflow_sdk/modules/dataset.py",
        contract_test="api/apps/restful_apis/dataset_api.py",
    ),
    ManifestEntry(
        method="POST",
        path="/api/v1/datasets",
        capability="数据集管理",
        visibility="public",
        stability="stable",
        runtime="both",
        http_reference="references/http_api_reference.md#post-apiv1datasets",
        sdk_reference="sdk/python/ragflow_sdk/modules/dataset.py",
        contract_test="api/apps/restful_apis/dataset_api.py",
    ),
    ManifestEntry(
        method="DELETE",
        path="/api/v1/datasets/{dataset_id}",
        capability="数据集管理",
        visibility="public",
        stability="stable",
        runtime="both",
        http_reference="references/http_api_reference.md#delete-apiv1datasetsdataset_id",
        sdk_reference="sdk/python/ragflow_sdk/modules/dataset.py",
        contract_test="api/apps/restful_apis/dataset_api.py",
    ),
    ManifestEntry(
        method="POST",
        path="/api/v1/chats/{chat_id}/completions",
        capability="会话管理",
        visibility="compatibility",
        stability="deprecated",
        runtime="python",
        canonical_replacement="POST /api/v1/chat/completions",
    ),
    ManifestEntry(
        method="GET",
        path="/api/v1/system/status",
        capability="系统管理",
        visibility="internal",
        stability="stable",
        runtime="both",
    ),
]

_ = __name__ == "__main__" and print(
    json.dumps(
        [_sort_dict(e.to_dict()) for e in EXAMPLE_ENTRIES],
        ensure_ascii=False,
        indent=2,
    )
)
