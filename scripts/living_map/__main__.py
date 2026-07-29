#!/usr/bin/env python3
"""
Living-map documentation generation entry point.

Usage::

    python scripts/living_map/generate.py          # generate all views
    python scripts/living_map/check.py             # non-mutating drift check

These commands are discoverable from the repo root and are designed to run
without starting any runtime services.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_on_path() -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))


def cmd_generate() -> int:
    """Generate and write all living-map inventory views."""
    _ensure_on_path()

    from scripts.living_map.python_extractor import extract_python_routes
    from scripts.living_map.go_extractor import extract_go_routes
    from scripts.living_map.compat_extractor import extract_compatibility_routes
    from scripts.living_map.manifest_schema import load_manifest
    from scripts.living_map.manifest_loader import generate_inventory, validate_all, write_generated_views

    manifest_path = _REPO_ROOT / "scripts" / "living_map" / "manifest.json"
    output_dir = _REPO_ROOT / "docs" / "living-map" / "generated"

    errors = validate_all(_REPO_ROOT, manifest_path)
    if errors:
        print("Validation errors detected (generation continues):")
        for err in errors:
            print(f"  - {err}")
        print()

    py_facts = extract_python_routes(_REPO_ROOT)
    go_facts = extract_go_routes(_REPO_ROOT)
    compat_facts = extract_compatibility_routes(_REPO_ROOT)
    all_facts = py_facts + go_facts + compat_facts

    print(f"Extracted {len(py_facts)} Python routes, {len(go_facts)} Go routes,"
          f" {len(compat_facts)} compatibility routes ({len(all_facts)} total)")

    if manifest_path.is_file():
        manifest = load_manifest(manifest_path)
        print(f"Loaded {len(manifest)} manifest entries")
        inventory = generate_inventory(all_facts, manifest)
        write_generated_views(inventory, output_dir)
        print(f"Generated views written to {output_dir}")
        print(f"  Public: {len(inventory['public'])} routes")
        print(f"  Maintainer: {len(inventory['maintainer'])} routes")
        print(f"  Parity entries: {len(inventory['parity'])}")
    else:
        # First run: generate inventory without manifest, mark all as unclassified
        print("No manifest found — generating skeleton inventory with unclassified routes")
        from scripts.living_map.manifest_loader import generate_inventory as gen_inv
        inventory = gen_inv(all_facts, [])
        write_generated_views(inventory, output_dir)
        print(f"Skeleton views written to {output_dir}")

    return 0


def cmd_check() -> int:
    """Run non-mutating drift check."""
    _ensure_on_path()

    from scripts.living_map.manifest_loader import check_mode

    drifts = check_mode(_REPO_ROOT)
    if drifts:
        print(f"DRIFT DETECTED ({len(drifts)} issues):")
        for d in drifts:
            print(f"  - {d}")
        return 1
    else:
        print("OK — no drift detected")
        return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Living-map generation and validation")
    parser.add_argument(
        "command",
        nargs="?",
        default="generate",
        choices=["generate", "check"],
        help="Action: generate (default) or check",
    )
    args = parser.parse_args()

    if args.command == "check":
        sys.exit(cmd_check())
    else:
        sys.exit(cmd_generate())
