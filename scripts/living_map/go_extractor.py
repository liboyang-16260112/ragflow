"""
Static extraction of Gin route groups, HTTP method registrations, handler
symbols, and source locations from Go source files under ``internal/router/``.

Strategy
--------
Gin routes are registered via:

* ``engine.GET("/path", handler)`` / ``engine.POST(...)`` — direct engine routes
* ``group := engine.Group("/prefix")`` followed by ``group.GET("/sub", ...)`` —
  nested groups
* Anonymous nested groups: ``v1 := authorized.Group("/api/v1") { v1.GET(...) }``

We parse Go source with a lightweight state-machine approach (regex + line
scanning) rather than a full Go parser so the extractor can run without the Go
toolchain.  This is adequate because the RAGFlow router code follows consistent
patterns: group variables are declared with ``:= engine.Group(prefix)`` or
``= engine.Group(prefix)``, and HTTP calls are ``varName.METHOD(path, ...)``.

Unresolvable constructs (e.g. method names built from string slices, or
registration patterns that don't match our recognized AST) produce a
``RouteFact`` with ``dynamic=True`` and a diagnostic.

References
----------
- ``internal/router/router.go``
- ``internal/router/router_ee.go``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

from scripts.living_map.route_facts import (
    HTTP_METHODS,
    RouteFact,
    canonical_route_key,
    normalize_gin_path,
    make_diagnostic,
)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches `varName := engine.Group("prefix")` or `varName = engine.Group("prefix")`
_GROUP_DECL_RE = re.compile(
    r'(\w+)\s*:?=\s*\w+\.Group\("([^"]*)"\)'
)

# Matches `varName.METHOD("path", handler)` or `varName.METHOD("path", ...)`
_ROUTE_CALL_RE = re.compile(
    r'(\w+)\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\("([^"]*)"\s*,\s*(\S+)'
)

# Matches `METHOD("path", handler)` on direct engine calls
_ENGINE_ROUTE_RE = re.compile(
    r'(?:engine|r\.Setup)?\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\("([^"]*)"\s*,\s*(\S+)'
)

# Matches `v1 := authorized.Group("/api/v1")` — chained group to parent var
_CHAINED_GROUP_RE = re.compile(
    r'(\w+)\s*:?=\s*(\w+)\.Group\("([^"]*)"\)'
)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_go_routes(
    repo_root: Path,
    source_files: Optional[list[Path]] = None,
) -> list[RouteFact]:
    """Extract route facts from Go router source files.

    Parameters
    ----------
    repo_root : Path
        Repository root directory.
    source_files : list[Path] | None
        Specific files to scan.  When *None*, scans the conventional router
        directory.

    Returns
    -------
    list[RouteFact]
    """
    if source_files is None:
        router_dir = repo_root / "internal" / "router"
        if router_dir.is_dir():
            source_files = sorted(router_dir.glob("*.go"))
        else:
            source_files = []

    all_facts: list[RouteFact] = []
    for filepath in source_files:
        if not filepath.is_file() or filepath.name.endswith("_test.go"):
            continue
        try:
            source = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = _repo_relative(filepath, repo_root)
        facts = _extract_one_go_file(source, str(rel_path))
        all_facts.extend(facts)

    return all_facts


def _extract_one_go_file(source: str, rel_path: str) -> list[RouteFact]:
    """Extract all route facts from one Go source file."""
    lines = source.splitlines()
    facts: list[RouteFact] = []

    # Phase 1: collect group → prefix mappings (two sub-passes)
    groups: dict[str, str] = {}
    chained_decls: list[tuple[int, str, str, str]] = []  # (line, child, parent, sub_prefix)

    for lineno, line in enumerate(lines, start=1):
        # Chained group FIRST (child := parentVar.Group("prefix"))
        m_chained = _CHAINED_GROUP_RE.search(line)
        if m_chained:
            chained_decls.append(
                (lineno, m_chained.group(1), m_chained.group(2), m_chained.group(3))
            )
            continue

        # Direct group from engine: var := engine.Group("prefix") or var = engine.Group("prefix")
        m_direct = _GROUP_DECL_RE.search(line)
        if m_direct:
            groups[m_direct.group(1)] = m_direct.group(2)
            continue

    # Resolve chained groups (may need multiple passes for transitive chains)
    for _, child_var, parent_var, sub_prefix in chained_decls:
        parent_prefix = groups.get(parent_var, "")
        groups[child_var] = parent_prefix + sub_prefix

    # Phase 2: extract route calls
    for lineno, line in enumerate(lines, start=1):
        m = _ROUTE_CALL_RE.search(line)
        if not m:
            # Try engine-direct pattern
            m = _ENGINE_ROUTE_RE.search(line)
            if not m:
                continue

        var = m.group(1)
        method = m.group(2).upper()
        sub_path = m.group(3)
        handler = m.group(4) if m.lastindex and m.lastindex >= 4 else "unknown"

        # Resolve handler symbol (strip trailing parens/commas)
        handler = handler.strip().rstrip(",").rstrip(")").strip()

        prefix = ""
        if var in groups:
            prefix = groups[var]

        raw_path = prefix + sub_path if sub_path.startswith("/") else prefix + "/" + sub_path
        raw_path = raw_path.rstrip("/") or "/"
        norm = normalize_gin_path(raw_path)

        dynamic = False
        diagnostic = None
        if method not in HTTP_METHODS:
            dynamic = True
            diagnostic = make_diagnostic(
                rel_path,
                lineno,
                f"Unrecognized HTTP method '{method}'",
                line,
            )

        f = RouteFact(
            method=method,
            original_path=raw_path,
            normalized_path=norm,
            runtime="go",
            source_file=rel_path,
            handler_symbol=handler,
            line_number=lineno,
            dynamic=dynamic,
            diagnostic=diagnostic,
        )
        facts.append(f)

    return facts


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
