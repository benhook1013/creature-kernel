"""Disposable CK-KICK-010 walking-skeleton host."""

from .diagnostics import Diagnostic, Phase, Severity, ValidationError, ValidationResult
from .resolver import resolve, resolve_document, resolve_file, resolve_json, validate_and_resolve

__all__ = [
    "Diagnostic",
    "Phase",
    "Severity",
    "ValidationError",
    "ValidationResult",
    "resolve",
    "resolve_document",
    "resolve_file",
    "resolve_json",
    "validate_and_resolve",
]
