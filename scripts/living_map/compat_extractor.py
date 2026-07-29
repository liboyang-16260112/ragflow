"""
Extraction of Python backward-compatibility registrations with canonical
replacement metadata.

The backward-compat module (``api/apps/backward_compat.py``) defines two
blueprints:

* ``manager`` — registered at ``/api/v1``
* ``legacy_v1_manager`` — registered at ``/v1``

Each deprecated route has a docstring that explicitly lists the old and new
paths.  We parse those docstrings to extract the canonical replacement
information alongside the route facts.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Optional

from scripts.living_map.route_facts import (
    RouteFact,
    normalize_quart_path,
    make_diagnostic,
)

# Matches "New path: METHOD /path" in docstrings
_DOCSTRING_REPLACEMENT_RE = re.compile(
    r"New\s+path:\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(/\S+)",
    re.IGNORECASE,
)


def extract_compatibility_routes(
    repo_root: Path,
) -> list[RouteFact]:
    """Extract compatibility-route facts from the backward-compat module.

    Returns an empty list if the file cannot be read.
    """
    filepath = repo_root / "api" / "apps" / "backward_compat.py"
    if not filepath.is_file():
        return []

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    rel_path = str(_repo_relative(filepath, repo_root))
    visitor = _CompatVisitor(rel_path)
    visitor.visit(tree)

    # Merge aliases: each route fact from backward_compat is tagged as
    # visibility=compatibility and includes canonical_replacement in
    # the diagnostic / metadata.
    return visitor.facts


class _CompatVisitor(ast.NodeVisitor):
    """Walk backward_compat.py and collect deprecated route facts."""

    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.facts: list[RouteFact] = []
        self._current_bp: str = "manager"  # default

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_route(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_route(node)
        self.generic_visit(node)

    def _check_route(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for deco in node.decorator_list:
            if not self._is_route(deco):
                continue
            route_info = self._extract_args(deco)
            if route_info is None:
                continue
            path, methods = route_info
            doc = ast.get_docstring(node) or ""

            prefix = "/api/v1" if self._current_bp == "manager" else "/v1"
            raw = prefix + path if path.startswith("/") else prefix + "/" + path
            raw = raw.rstrip("/") or "/"
            norm = normalize_quart_path(raw)

            # Extract canonical replacement from docstring
            replacement = None
            dm = _DOCSTRING_REPLACEMENT_RE.search(doc)
            if dm:
                replacement = f"{dm.group(1).upper()} {dm.group(2)}"

            # Build diagnostic for compat route
            diag_lines = [f"Compatibility route (deprecated)."]
            if replacement:
                diag_lines.append(f"Canonical replacement: {replacement}")
            diag = " ".join(diag_lines)

            for method in methods:
                f = RouteFact(
                    method=method.upper(),
                    original_path=raw,
                    normalized_path=norm,
                    runtime="python",
                    source_file=self.rel_path,
                    handler_symbol=node.name,
                    line_number=node.lineno,
                    methods=[m.upper() for m in methods],
                    diagnostic=diag,
                )
                self.facts.append(f)

    def _is_route(self, node: ast.expr) -> bool:
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        return (
            isinstance(func, ast.Attribute)
            and func.attr == "route"
        )

    def _extract_args(
        self, node: ast.Call
    ) -> Optional[tuple[str, list[str]]]:
        args = node.args
        keywords = {kw.arg: kw.value for kw in node.keywords}

        path: Optional[str] = None
        if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
            path = args[0].value
        if path is None:
            rule_node = keywords.get("rule")
            if (
                rule_node is not None
                and isinstance(rule_node, ast.Constant)
                and isinstance(rule_node.value, str)
            ):
                path = rule_node.value

        if path is None:
            return None

        methods: list[str] = ["GET"]
        methods_node = keywords.get("methods")
        if (
            methods_node is not None
            and isinstance(methods_node, ast.List)
        ):
            ms = []
            for elt in methods_node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    ms.append(elt.value)
            if ms:
                methods = ms

        return path, methods


def _repo_relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path
