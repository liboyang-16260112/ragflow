"""
Static extraction of Quart route decorators and dynamically assigned blueprint
prefixes *without* importing the RAGFlow application.

Strategy
--------

RAGFlow registers routes through a dynamic discovery mechanism:
``register_page()`` creates a ``Blueprint``, executes a ``*_app.py`` or
``*/restful_apis/*.py`` module while injecting the blueprint as ``page.manager``,
and then calls ``app.register_blueprint(page.manager, url_prefix=...)``.

We cannot import ``api.apps`` because that would trigger the entire application
bootstrap (database connections, Redis, settings, QuartSchema init, …).  Instead
we parse the Python source statically using the ``ast`` module:

1. **Decorator routes**: Scan for ``@manager.route(path, methods=[...])`` and
   ``@blueprint.route(path, methods=[...])`` decorators.

2. **Blueprint prefix**: The prefix is assigned dynamically inside
   ``register_page()`` (or by a ``url_prefix`` kwarg).  For the API surface we
   know the convention:

   - Modules under ``api/apps/restful_apis/`` → ``/api/v1``
   - Modules under ``api/apps/sdk/`` → ``/v1/<page_name>``
   - The backward-compat ``manager`` (``api/apps/backward_compat.py``) →
     ``/api/v1``
   - The backward-compat ``legacy_v1_manager`` →
     ``/v1``

3. **Compatibility routes**: ``api/apps/backward_compat.py`` uses two
   blueprints (``manager`` and ``legacy_v1_manager``) and each route docstring
   explicitly states the old deprecated path and the new canonical path.

Unresolvable constructs (e.g. dynamically built route strings with string
interpolation in the path, or routes registered through a loop where AST cannot
determine the final value) produce a :class:`RouteFact` with ``dynamic=True``
and a diagnostic.

References
----------
- ``api/apps/__init__.py`` — blueprint discovery & dynamic prefix assignment
- ``api/apps/backward_compat.py`` — deprecated route aliases
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from scripts.living_map.route_facts import (
    RouteFact,
    normalize_quart_path,
    make_diagnostic,
)

# ---------------------------------------------------------------------------
# Path → prefix heuristics (mirrors the pattern in api/apps/__init__.py)
# ---------------------------------------------------------------------------

# Recognised blueprint variable name → default prefix
_BLUEPRINT_PREFIX_OVERRIDES: dict[str, str] = {
    "manager": "/api/v1",
    "legacy_v1_manager": "/v1",
}


def _infer_prefix_from_filepath(filepath: Path, repo_root: Path) -> str:
    """Guess the URL prefix for a Python module based on its location."""
    try:
        rel = filepath.relative_to(repo_root)
    except ValueError:
        return "/api/v1"

    # Relative to api/apps/
    if "restful_apis" in rel.parts:
        return "/api/v1"
    if "sdk" in rel.parts:
        return "/v1/<page_name>"  # the actual prefix is dynamic; mark as heuristic
    if "backward_compat" in rel.name:
        return "/api/v1"  # backward_compat's `manager` defaults to /api/v1
    return "/api/v1"


# ---------------------------------------------------------------------------
# AST-based extraction
# ---------------------------------------------------------------------------

class _RouteVisitor(ast.NodeVisitor):
    """Walk a Python AST and collect route-fact records.

    Each visited node that represents a ``@manager.route(...)``,
    ``@blueprint.route(...)``, or ``@<var>.route(...)`` decorator yields
    one :class:`RouteFact`.
    """

    def __init__(
        self,
        source_file: str,
        blueprint_var: str,
        url_prefix: str,
    ) -> None:
        self.source_file = source_file
        self.blueprint_var = blueprint_var
        self.url_prefix = url_prefix
        self.facts: list[RouteFact] = []
        self._diag_count = 0

    # -- decorator detection -----------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_decorators(node)
        self.generic_visit(node)

    def _process_decorators(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        for deco in node.decorator_list:
            if not self._is_route_decorator(deco):
                continue
            route_info = self._extract_route_args(deco)
            if route_info is None:
                continue
            path, methods, dynamic, diag = route_info

            # Join prefix + path
            raw_path = self.url_prefix + path if path.startswith("/") else self.url_prefix + "/" + path
            raw_path = raw_path.rstrip("/") or "/"
            norm = normalize_quart_path(raw_path)

            for method in methods:
                f = RouteFact(
                    method=method.upper(),
                    original_path=raw_path,
                    normalized_path=norm,
                    runtime="python",
                    source_file=self.source_file,
                    handler_symbol=node.name,
                    line_number=node.lineno,
                    methods=[m.upper() for m in methods],
                    dynamic=dynamic,
                    diagnostic=diag,
                )
                self.facts.append(f)

    def _is_route_decorator(self, node: ast.expr) -> bool:
        """Match ``@<var>.route(...)`` patterns."""
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        if not isinstance(func, ast.Attribute):
            return False
        # func.attr == "route"
        if func.attr != "route":
            return False
        return True

    def _extract_route_args(
        self, node: ast.Call
    ) -> Optional[tuple[str, list[str], bool, Optional[str]]]:
        """Extract (path, methods, dynamic, diagnostic) from a route() call.

        Returns ``None`` when the decorator is not a route registration or
        cannot be analysed at all.
        """
        args = node.args
        keywords = {kw.arg: kw.value for kw in node.keywords}

        path: Optional[str] = None
        dynamic = False
        diag: Optional[str] = None

        # Positional path arg
        if args:
            path = self._eval_str(args[0])
            if path is None:
                dynamic = True
                diag = make_diagnostic(
                    self.source_file,
                    node.lineno,
                    "Cannot statically resolve route path",
                    ast.unparse(args[0]),
                )
                path = f"<dynamic:{self._diag_count}>"
                self._diag_count += 1

        if path is None:
            path = keywords.get("rule") and self._eval_str(keywords["rule"])
            if path is None:
                return None

        # methods kwarg
        methods: list[str] = ["GET"]
        if "methods" in keywords:
            raw = self._eval_list(keywords["methods"])
            if raw:
                methods = raw
            else:
                dynamic = True
                if diag is None:
                    diag = make_diagnostic(
                        self.source_file,
                        node.lineno,
                        "Cannot statically resolve methods list",
                        ast.unparse(keywords["methods"]),
                    )

        return path, methods, dynamic, diag

    # -- eval helpers ------------------------------------------------------

    def _eval_str(self, node: ast.expr) -> Optional[str]:
        """Return a string value from an AST expression, or None."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            dynamic_parts = [
                v for v in node.values if not isinstance(v, ast.Constant)
            ]
            if not dynamic_parts:
                # f-string with only Constant parts is still dynamic in principle
                try:
                    return ast.literal_eval(node)
                except (ValueError, SyntaxError):
                    pass
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._eval_str(node.left)
            right = self._eval_str(node.right)
            if left is not None and right is not None:
                return left + right
            return None
        return None

    def _eval_list(self, node: ast.expr) -> Optional[list[str]]:
        """Return a list of strings, or None (meaning unresolvable)."""
        if isinstance(node, ast.List):
            result: list[str] = []
            for elt in node.elts:
                v = self._eval_str(elt)
                if v is None:
                    return None
                result.append(v)
            return result
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_python_routes(
    repo_root: Path,
    source_files: Optional[list[Path]] = None,
) -> list[RouteFact]:
    """Extract route facts from Python source files in the repository.

    Parameters
    ----------
    repo_root : Path
        Repository root directory.
    source_files : list[Path] | None
        Specific files to scan.  When *None*, scans the conventional API
        directories.

    Returns
    -------
    list[RouteFact]
    """
    if source_files is None:
        source_files = _default_api_files(repo_root)

    facts: list[RouteFact] = []
    for filepath in source_files:
        if not filepath.is_file():
            continue
        try:
            source = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            continue

        rel_path = str(_repo_relative(filepath, repo_root))
        url_prefix = _infer_prefix_from_filepath(filepath, repo_root)

        # Each file typically uses a ``manager`` blueprint, but some use
        # ``legacy_v1_manager`` or custom blueprint names.  We scan for all
        # common blueprint patterns.
        for bp_var in _BLUEPRINT_PREFIX_OVERRIDES:
            prefix = _BLUEPRINT_PREFIX_OVERRIDES.get(bp_var, url_prefix)
            visitor = _RouteVisitor(rel_path, bp_var, prefix)
            visitor.visit(tree)
            facts.extend(visitor.facts)

        # Also scan with the default url_prefix deduced from filepath
        visitor = _RouteVisitor(rel_path, "manager", url_prefix)
        visitor.visit(tree)
        # Deduplicate by key (ast_visit returns one per decorator; same
        # blueprint var may match multiple visitors).
        facts = _dedupe_facts(facts)

    return facts


def _default_api_files(repo_root: Path) -> list[Path]:
    """Conventional RAGFlow API source directories."""
    dirs = [
        repo_root / "api" / "apps" / "restful_apis",
        repo_root / "api" / "apps" / "sdk",
    ]
    files: list[Path] = []
    for d in dirs:
        if d.is_dir():
            files.extend(sorted(d.glob("*.py")))
    # backward compat module
    back_compat = repo_root / "api" / "apps" / "backward_compat.py"
    if back_compat.is_file():
        files.append(back_compat)
    return files


def _repo_relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _dedupe_facts(facts: list[RouteFact]) -> list[RouteFact]:
    """Keep one fact per (key, source_file, handler_symbol) tuple."""
    seen: set[tuple[str, str, str | None]] = set()
    result: list[RouteFact] = []
    for f in facts:
        sig = (f.key, f.source_file, f.handler_symbol)
        if sig not in seen:
            seen.add(sig)
            result.append(f)
    return result
