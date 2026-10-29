"""Validate CSV files against a JSON schema of column rules."""
from .core import validate_rows, validate_file, Violation

__version__ = "0.1.0"
__all__ = ["validate_rows", "validate_file", "Violation"]
