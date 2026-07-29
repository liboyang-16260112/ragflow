"""
Normalized route fact model and parameter normalization shared by extracted
Python and Go registrations.

Each :class:`RouteFact` is a language-agnostic record of a single HTTP route
discovered from source code.  It carries enough information to:

* produce canonical ``METHOD /path`` keys for manifest alignment,
* compare equivalent routes across Python and Go runtimes,
* emit accurate diagnostics when a registration cannot be resolved.

Path-parameter normalisation
----------------------------

+---------------------+----------------+-------------+
| Framework           | Syntax         | Canonical   |
+=====================+================+=============+
| Quart               | ``<name>``     | ``{name}``  |
| Quart               | ``<path:name>``| ``{name}``  |
| Gin                 | ``:name``      | ``{name}``  |
| Gin                 | ``*name``      | ``{name}``  |
+---------------------+----------------+-------------+

All four forms represent the same route-level parameter.  The extracted
*original_path* retains the framework-specific form so tooling and
diagnostics can reference the exact source line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Parameter normalisation
# ---------------------------------------------------------------------------

# Quart paths: <int:name>, <path:name>, <name>
_QUART_PARAM_RE = re.compile(r"<(?:int|path|float|uuid|string)?:?([^>]+)>")

# Gin paths: :name or *name captured from a path segment
_GIN_PARAM_RE = re.compile(r":(\w+)|\*(\w+)")


def normalize_quart_path(path: str) -> str:
    """Normalize a Quart route path to the canonical ``{param}`` form.

    >>> normalize_quart_path('/api/v1/datasets/<dataset_id>')
    '/api/v1/datasets/{dataset_id}'
    >>> normalize_quart_path('/api/v1/files/<path:file_path>')
    '/api/v1/files/{file_path}'
    """
    return _QUART_PARAM_RE.sub(r"{\1}", path)


def normalize_gin_path(path: str) -> str:
    """Normalize a Gin route path to the canonical ``{param}`` form.

    >>> normalize_gin_path('/api/v1/datasets/:dataset_id')
    '/api/v1/datasets/{dataset_id}'
    >>> normalize_gin_path('/api/v1/files/*file_path')
    '/api/v1/files/{file_path}'
    """
    return _GIN_PARAM_RE.sub(r"{\1\2}", path)


def canonical_route_key(method: str, path: str) -> str:
    """Return a stable canonical key for a normalised HTTP route.

    >>> canonical_route_key('GET', '/api/v1/datasets/{dataset_id}')
    'GET /api/v1/datasets/{dataset_id}'
    """
    return f"{method.upper().strip()} {path.rstrip('/') or '/'}"


# ---------------------------------------------------------------------------
# Route fact model
# ---------------------------------------------------------------------------

RuntimeName = Literal["python", "go"]


@dataclass
class RouteFact:
    """A single HTTP route discovered from source-code extraction.

    Attributes
    ----------
    method : str
        Upper-case HTTP method (``GET``, ``POST``, …).
    original_path : str
        Path as it appears in the source decorator / registration call.
    normalized_path : str
        Canonical path with ``{param}`` placeholders.
    runtime : RuntimeName
        ``"python"`` or ``"go"``.
    source_file : str
        Repository-relative path to the source file.
    handler_symbol : str | None
        Function or method name that handles the route, where identifiable.
    line_number : int | None
        Approximate source line, or ``None`` when not resolved.
    methods : list[str]
        All HTTP methods registered for this path at this source location
        (e.g. a single decorator with ``methods=["GET", "POST"]``).
    dynamic : bool
        ``True`` when the route registration is generated dynamically (e.g.
        ``for method in [...]``) and the extractor cannot resolve it
        statically.  Such entries are always accompanied by a diagnostic.
    diagnostic : str | None
        Human-readable diagnostic emitted when the extractor cannot fully
        resolve a registration construct.
    """

    method: str
    original_path: str
    normalized_path: str
    runtime: RuntimeName
    source_file: str
    handler_symbol: str | None = None
    line_number: int | None = None
    methods: list[str] = field(default_factory=list)
    dynamic: bool = False
    diagnostic: str | None = None

    @property
    def key(self) -> str:
        """Canonical route key used for manifest alignment."""
        return canonical_route_key(self.method, self.normalized_path)

    def __post_init__(self) -> None:
        if not self.methods:
            self.methods = [self.method]


# ---------------------------------------------------------------------------
# Shared extraction helpers
# ---------------------------------------------------------------------------

HTTP_METHODS = frozenset(
    {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
)


def is_http_method(token: str) -> bool:
    """Return ``True`` when *token* looks like an HTTP method."""
    return token.upper() in HTTP_METHODS


def make_diagnostic(
    source_file: str,
    line: int,
    reason: str,
    snippet: str | None = None,
) -> str:
    """Build a human-readable diagnostic string."""
    base = f"{source_file}:{line}: {reason}"
    if snippet:
        base += f"\n  >>> {snippet.strip()}"
    return base
