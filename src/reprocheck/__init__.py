"""ReproCheck public package API."""

from typing import TYPE_CHECKING

from .claims import extract_claims, extract_table_claims
from .version import __version__

if TYPE_CHECKING:
    from .audit import run_audit
    from .batch import run_project_check
    from .leakage import TextMatch, TextMatchSearch, find_text_matches, text_similarity
    from .signing import generate_keypair, sign_certificate, verify_certificate_signature

__all__ = [
    "__version__",
    "extract_claims",
    "extract_table_claims",
    "generate_keypair",
    "run_audit",
    "run_project_check",
    "sign_certificate",
    "TextMatch",
    "TextMatchSearch",
    "find_text_matches",
    "text_similarity",
    "verify_certificate_signature",
]


def __getattr__(name: str) -> object:
    if name == "run_audit":
        from .audit import run_audit

        return run_audit
    if name == "run_project_check":
        from .batch import run_project_check

        return run_project_check
    if name in {"generate_keypair", "sign_certificate", "verify_certificate_signature"}:
        from . import signing

        return getattr(signing, name)
    if name in {"TextMatch", "TextMatchSearch", "find_text_matches", "text_similarity"}:
        from . import leakage

        return getattr(leakage, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
