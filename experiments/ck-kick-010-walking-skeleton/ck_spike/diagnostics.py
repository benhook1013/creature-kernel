"""Typed diagnostics shared by the disposable walking-skeleton host.

The experiment deliberately exposes structured results so a later command
adapter can inspect diagnostics without parsing human-readable messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class Phase(str, Enum):
    VALIDATION = "validation"
    RESOLUTION = "resolution"


@dataclass(frozen=True)
class Diagnostic:
    """One deterministic, machine-readable validation or resolution result."""

    code: str
    severity: Severity
    phase: Phase
    path: str
    related_source_labels: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "phase": self.phase.value,
            "path": self.path,
            "related_source_labels": list(self.related_source_labels),
            "message": self.message,
        }


@dataclass(frozen=True)
class ValidationResult:
    """The typed result boundary consumed by future adapters."""

    diagnostics: tuple[Diagnostic, ...] = ()
    graph: Any | None = None

    @property
    def ok(self) -> bool:
        return self.graph is not None and not any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is Severity.ERROR
        )

    def require_graph(self) -> Any:
        """Return the graph or raise a typed exception with all diagnostics."""

        if not self.ok:
            raise ValidationError(self.diagnostics)
        return self.graph

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "graph": self.graph.to_dict() if self.graph is not None else None,
        }


class ValidationError(Exception):
    """Exception form for callers that prefer fail-fast validation."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]):
        self.diagnostics = diagnostics
        super().__init__(
            "; ".join(
                f"{diagnostic.code} at {diagnostic.path}"
                for diagnostic in diagnostics
            )
        )

