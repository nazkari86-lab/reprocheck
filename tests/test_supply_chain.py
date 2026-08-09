import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTION_REFERENCE = re.compile(r"^\s*(?:-\s+)?uses:\s+([^\s#]+)", re.MULTILINE)
IMMUTABLE_ACTION = re.compile(r"^[^/\s]+/[^@\s]+@[0-9a-f]{40}$")


def test_workflows_pin_external_actions_to_commit_sha():
    paths = [ROOT / "action.yml", *(ROOT / ".github/workflows").glob("*.yml")]
    references = {
        path.relative_to(ROOT).as_posix(): ACTION_REFERENCE.findall(
            path.read_text(encoding="utf-8")
        )
        for path in paths
    }
    assert all(references.values())
    for path, action_references in references.items():
        for reference in action_references:
            if reference.startswith("./"):
                continue
            assert IMMUTABLE_ACTION.fullmatch(reference), f"mutable action in {path}: {reference}"


def test_release_attests_every_published_asset_with_minimal_required_permissions():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for permission in (
        "contents: write",
        "id-token: write",
        "attestations: write",
        "artifact-metadata: write",
    ):
        assert permission in workflow
    for subject in (
        "dist/reprocheck-${{ env.PACKAGE_VERSION }}-py3-none-any.whl",
        "dist/reprocheck-${{ env.PACKAGE_VERSION }}.tar.gz",
        "dist/SHA256SUMS",
    ):
        assert subject in workflow
    assert "python -m pip_audit -r requirements-ci.txt --progress-spinner off" in workflow
