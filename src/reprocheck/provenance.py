from __future__ import annotations

import hashlib
from pathlib import Path

from .models import SourceArtifact


def describe_artifact(path: Path, role: str) -> SourceArtifact:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return SourceArtifact(role=role, filename=path.name, sha256=digest.hexdigest(), size_bytes=size)
