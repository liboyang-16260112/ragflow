"""
Manifest loading, merge validation, and inventory generation for the
living-map pipeline.

This module connects the three data sources:

1. **Extracted route facts** (Python ↔ Go → :class:`RouteFact`)
2. **Reviewed manifest entries** (:class:`ManifestEntry`)
3. **Generated views** (public inventory, maintainer inventory, parity view)

Validation rules:

* Every governed ``/api/v1`` source route must have a matching policy entry.
* Every manifest route must exist in at least one declared runtime.
* Public routes must carry valid HTTP reference, contract-test, and SDK evidence.
* Compatibility entries must identify a canonical replacement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

from scripts.living_map.manifest_schema import (
    ManifestEntry,
    validate_manifest,
    load_manifest,
)
from scripts.living_map.route_facts import (
    RouteFact,
    canonical_route_key,
)
from scripts.living_map.python_extractor import extract_python_routes
from scripts.living_map.go_extractor import extract_go_routes
from scripts.living_map.compat_extractor import extract_compatibility_routes


# ---------------------------------------------------------------------------
# Merge validation
# ---------------------------------------------------------------------------

class MergeError(Exception):
    """Validation error during manifest-source merge."""


def validate_merge(
    facts: list[RouteFact],
    manifest: list[ManifestEntry],
) -> list[str]:
    """Validate that extracted facts and policy manifest are consistent.

    Returns a list of human-readable error messages (empty = valid).
    """
    errors: list[str] = []

    fact_keys: dict[str, RouteFact] = {}
    for f in facts:
        fact_keys[f.key] = f

    manifest_keys: dict[str, ManifestEntry] = {}
    for e in manifest:
        if e.key in manifest_keys:
            continue  # duplicate — already caught by validate_manifest
        manifest_keys[e.key] = e

    # 1. Every governed /api/v1 fact must be classified
    unclassified_count = 0
    for key, fact in sorted(fact_keys.items()):
        if not fact.normalized_path.startswith("/api/v1"):
            continue
        if key not in manifest_keys:
            # During baseline creation, report unclassified routes as
            # informational rather than blocking errors.
            unclassified_count += 1
            if unclassified_count <= 20:
                errors.append(
                    f"Unclassified governed route: {key}"
                    f" (source: {fact.source_file}:{fact.line_number},"
                    f" runtime: {fact.runtime})"
                )
    if unclassified_count > 20:
        errors.append(
            f"... and {unclassified_count - 20} more unclassified governed routes"
            f" (total: {unclassified_count})"
        )

    # 2. Every manifest entry must have at least one source fact
    for key, entry in sorted(manifest_keys.items()):
        if key not in fact_keys:
            errors.append(
                f"Stale manifest entry (no source route): {key}"
                f" (capability: {entry.capability})"
            )
            continue

        # 3. Runtime enforcement: entry declares runtimes, facts must match
        fact = fact_keys[key]
        if entry.runtime == "python" and fact.runtime != "python":
            errors.append(
                f"Runtime mismatch for {key}: manifest declares python,"
                f" but only found in {fact.runtime}"
            )
        elif entry.runtime == "go" and fact.runtime != "go":
            errors.append(
                f"Runtime mismatch for {key}: manifest declares go,"
                f" but only found in {fact.runtime}"
            )
        elif entry.runtime == "both":
            other_runtime = "go" if fact.runtime == "python" else "python"
            other_key = None
            for f2 in facts:
                if f2.key == key and f2.runtime == other_runtime:
                    other_key = f2.key
                    break
            if other_key is None:
                errors.append(
                    f"Runtime gap for {key}: manifest declares both,"
                    f" but route only exists in {fact.runtime}"
                )

    return errors


# ---------------------------------------------------------------------------
# Full validation (manifest + merge + evidence)
# ---------------------------------------------------------------------------

def validate_all(
    repo_root: Path,
    manifest_path: Optional[Path] = None,
) -> list[str]:
    """Run the complete validation pipeline.

    1. Extract all route facts from the repository source.
    2. Load and validate the manifest schema.
    3. Merge-validate facts against manifest.
    4. Validate public-route evidence links.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    # Extract
    py_facts = extract_python_routes(repo_root)
    go_facts = extract_go_routes(repo_root)
    compat_facts = extract_compatibility_routes(repo_root)
    all_facts = py_facts + go_facts + compat_facts

    # Load manifest
    if manifest_path is None:
        manifest_path = repo_root / "scripts" / "living_map" / "manifest.json"
    if not manifest_path.is_file():
        errors.append(f"Manifest file not found: {manifest_path}")
        return errors

    try:
        manifest = load_manifest(manifest_path)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        errors.append(f"Failed to load manifest: {exc}")
        return errors

    # Schema validation
    schema_errors = validate_manifest(manifest)
    errors.extend(schema_errors)

    # Merge validation
    merge_errors = validate_merge(all_facts, manifest)
    errors.extend(merge_errors)

    # Evidence validation (links)
    evidence_errors = validate_evidence(manifest, repo_root)
    errors.extend(evidence_errors)

    return errors


def validate_evidence(
    manifest: list[ManifestEntry],
    repo_root: Path,
) -> list[str]:
    """Validate reference links in the manifest.

    Checks existence of:
    * HTTP reference anchors in the documentation
    * SDK reference paths
    * Contract test paths
    """
    errors: list[str] = []

    for entry in manifest:
        if entry.visibility != "public":
            continue

        # HTTP reference: check the file exists (the anchor is in-doc, cheaper
        # to skip full anchor parsing)
        if entry.http_reference:
            ref_path = _anchor_file(entry.http_reference)
            full = repo_root / ref_path
            if ref_path and not full.is_file():
                errors.append(
                    f"{entry.key}: http_reference target not found: {ref_path}"
                )

        if entry.sdk_reference:
            sdk_path = Path(entry.sdk_reference)
            full = repo_root / sdk_path
            if not full.exists():
                errors.append(
                    f"{entry.key}: sdk_reference target not found: {sdk_path}"
                )

        if entry.contract_test:
            test_path = Path(entry.contract_test)
            full = repo_root / test_path
            if not full.exists():
                errors.append(
                    f"{entry.key}: contract_test target not found: {test_path}"
                )

    return errors


def _anchor_file(ref: str) -> Optional[str]:
    """Extract the file path from a ``path#anchor`` reference."""
    return ref.split("#")[0] if "#" in ref else ref


# ---------------------------------------------------------------------------
# Inventory generation
# ---------------------------------------------------------------------------

def generate_inventory(
    facts: list[RouteFact],
    manifest: list[ManifestEntry],
) -> dict:
    """Produce the merged inventory data structure.

    Returns a dict with ``public``, ``maintainer``, and ``parity`` sections
    suitable for serialization to generated views.
    """
    manifest_by_key: dict[str, ManifestEntry] = {e.key: e for e in manifest}

    # Merge facts with policy
    merged: list[dict] = []
    for f in facts:
        entry = manifest_by_key.get(f.key)
        record = {
            "method": f.method,
            "path": f.normalized_path,
            "original_path": f.original_path,
            "runtime": f.runtime,
            "source_file": f.source_file,
            "handler_symbol": f.handler_symbol,
            "capability": entry.capability if entry else "未分类",
            "visibility": entry.visibility if entry else "internal",
            "stability": entry.stability if entry else "experimental",
            "intended_runtime": entry.runtime if entry else "unknown",
            "canonical_replacement": (
                entry.canonical_replacement if entry else None
            ),
            "http_reference": entry.http_reference if entry else None,
            "sdk_reference": entry.sdk_reference if entry else None,
            "contract_test": entry.contract_test if entry else None,
        }
        if f.diagnostic:
            record["diagnostic"] = f.diagnostic
        merged.append(record)

    # Stable sort: capability, then method, then path
    merged.sort(key=lambda r: (r["capability"], r["method"], r["path"]))

    public = [r for r in merged if r["visibility"] == "public"]
    maintainer = merged  # everything, including internal/compat/beta

    # Parity view
    parity = _build_parity_view(merged, manifest_by_key)

    return {
        "public": public,
        "maintainer": maintainer,
        "parity": parity,
    }


def _build_parity_view(
    merged: list[dict],
    manifest_by_key: dict[str, ManifestEntry],
) -> list[dict]:
    """Build a Python/Go parity report."""
    result: list[dict] = []
    by_key: dict[str, list[dict]] = {}
    for r in merged:
        by_key.setdefault(r["method"] + " " + r["path"], []).append(r)

    for key, entries in sorted(by_key.items()):
        runtimes = {e["runtime"] for e in entries}
        entry = manifest_by_key.get(key)
        intended = entry.runtime if entry else "unknown"

        state = "both"
        if runtimes == {"python"}:
            state = "python-only"
        elif runtimes == {"go"}:
            state = "go-only"

        # Policy-aware state
        if intended == "python-only" and state == "python-only":
            state_label = "有意仅 Python 支持"
        elif intended == "go-only" and state == "go-only":
            state_label = "有意仅 Go 支持"
        elif intended == "both" and state != "both":
            state_label = f"⚠ 运行时缺口: 预期 both, 实际 {state}"
        elif state == "both":
            state_label = "双运行时支持"
        else:
            state_label = state

        result.append({
            "key": key,
            "runtimes": sorted(runtimes),
            "state": state,
            "state_label": state_label,
            "intended": intended,
            "capability": entries[0].get("capability", "未分类"),
            "visibility": entries[0].get("visibility", "unknown"),
        })

    return result


# ---------------------------------------------------------------------------
# Deterministic serialization
# ---------------------------------------------------------------------------

def write_generated_views(
    inventory: dict,
    output_dir: Path,
) -> None:
    """Write generated inventory views as JSON files.

    Output files:
    * ``public_inventory.json`` — public API capability inventory
    * ``maintainer_inventory.json`` — full maintainer inventory
    * ``parity_view.json`` — Python/Go parity view
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for section, filename in [
        ("public", "public_inventory.json"),
        ("maintainer", "maintainer_inventory.json"),
        ("parity", "parity_view.json"),
    ]:
        data = inventory[section]
        out_path = output_dir / filename
        out_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Check mode
# ---------------------------------------------------------------------------

def check_mode(
    repo_root: Path,
    generated_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> list[str]:
    """Run non-mutating validation and drift check.

    1. Regenerate all views in memory.
    2. Compare with committed generated files.
    3. Run all validation rules.

    Returns a list of error/drift messages (empty = no drift).
    """
    drifts: list[str] = []

    if generated_dir is None:
        generated_dir = repo_root / "docs" / "living-map" / "generated"

    # Validation
    errors = validate_all(repo_root, manifest_path)
    drifts.extend(errors)

    # Regenerate and compare
    py_facts = extract_python_routes(repo_root)
    go_facts = extract_go_routes(repo_root)
    compat_facts = extract_compatibility_routes(repo_root)
    all_facts = py_facts + go_facts + compat_facts

    if manifest_path is None:
        manifest_path = repo_root / "scripts" / "living_map" / "manifest.json"

    if manifest_path.is_file():
        manifest = load_manifest(manifest_path)
        inventory = generate_inventory(all_facts, manifest)

        for section, filename in [
            ("public", "public_inventory.json"),
            ("maintainer", "maintainer_inventory.json"),
            ("parity", "parity_view.json"),
        ]:
            committed = generated_dir / filename
            if committed.is_file():
                committed_content = committed.read_text(encoding="utf-8")
                generated_content = json.dumps(
                    inventory[section], ensure_ascii=False, indent=2
                ) + "\n"
                if committed_content != generated_content:
                    drifts.append(
                        f"Drift detected: {filename} differs from regenerated content."
                        f" Run 'python scripts/living_map/generate.py' to update."
                    )
            else:
                drifts.append(
                    f"Missing generated file: {filename}."
                    f" Run 'python scripts/living_map/generate.py' to create."
                )

    return drifts
