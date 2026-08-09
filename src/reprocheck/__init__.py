"""ReproCheck public package API."""

from typing import TYPE_CHECKING

from .claims import extract_claims, extract_table_claims
from .version import __version__

if TYPE_CHECKING:
    from .audit import run_audit
    from .batch import run_project_check

__all__ = [
    "__version__",
    "extract_claims",
    "extract_table_claims",
    "run_audit",
    "run_project_check",
]


def __getattr__(name: str) -> object:
    if name == "run_audit":
        from .audit import run_audit

        return run_audit
    if name == "run_project_check":
        from .batch import run_project_check

        return run_project_check
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
