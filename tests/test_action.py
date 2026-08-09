from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_composite_action_passes_inputs_through_environment():
    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    audit_step = action.split("- name: Audit project", 1)[1]

    assert "REPROCHECK_MANIFEST: ${{ inputs.manifest }}" in audit_step
    assert "REPROCHECK_OUTPUT_DIR: ${{ inputs.output-dir }}" in audit_step
    run_script = audit_step.split("run: >-", 1)[1]
    assert "${{ inputs.manifest }}" not in run_script
    assert "${{ inputs.output-dir }}" not in run_script
    assert '"$REPROCHECK_MANIFEST"' in run_script
    assert '"$REPROCHECK_OUTPUT_DIR"' in run_script


def test_release_attests_sbom_with_packages_and_checksums():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "make runtime-sbom" in workflow
    assert "make dependency-audit" in workflow
    assert workflow.count("reprocheck-sbom.cdx.json") >= 3
    assert "dist/reprocheck-sbom.cdx.json" in workflow
