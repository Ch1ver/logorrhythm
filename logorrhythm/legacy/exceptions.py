"""Custom exceptions for LOGORRHYTHM protocol operations."""


class LogorrhythmError(Exception):
    """Base exception for all package errors."""


class EncodingError(LogorrhythmError):
    """Raised when encoding cannot proceed due to invalid input."""


class DecodingError(LogorrhythmError):
    """Raised when decoding fails due to malformed input or policy violations."""
