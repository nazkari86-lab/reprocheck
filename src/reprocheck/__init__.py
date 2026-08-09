"""ReproCheck public package API."""

from typing import TYPE_CHECKING

from .claims import extract_claims, extract_table_claims
from .version import __version__

if TYPE_CHECKING:
    from .audit import run_audit

__all__ = ["__version__", "extract_claims", "extract_table_claims", "run_audit"]


def __getattr__(name: str) -> object:
    if name == "run_audit":
        from .audit import run_audit

        return run_audit
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
