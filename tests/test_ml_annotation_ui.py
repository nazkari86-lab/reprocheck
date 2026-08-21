from __future__ import annotations

import json
from pathlib import Path

import pytest

from reprocheck.ml_annotation_ui import render_annotation_ui, write_annotation_ui


def _packet() -> dict[str, object]:
    return {
        "schema_version": "reprocheck.ml-annotation-packet.v1",
        "corpus_id": "corpus",
        "reviewer": "reviewer-a",
        "mapping_sha256": "a" * 64,
        "independent_review_required": True,
        "blocks": [{"blind_id": "B-1", "raw_text": "Accuracy: 94% </script>"}],
    }


def test_ui_is_standalone_russian_blinded_and_script_safe() -> None:
    rendered = render_annotation_ui(_packet())
    assert "Разметка научных результатов" in rendered
    assert "Экспортировать заполненный JSON" in rendered
    assert "<\\/script>" in rendered
    assert "repository_id" not in rendered
    assert "coordinator" not in rendered
    assert "localStorage" in rendered


def test_ui_writer_and_invalid_packets(tmp_path: Path) -> None:
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps(_packet()), encoding="utf-8")
    output = tmp_path / "review.html"
    write_annotation_ui(packet, output)
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    with pytest.raises(ValueError, match="already exists"):
        write_annotation_ui(packet, output)
    for mutation, message in [
        ({"schema_version": "bad"}, "unsupported"),
        ({"blocks": []}, "no blocks"),
        ({"reviewer": ""}, "no reviewer"),
    ]:
        value = {**_packet(), **mutation}
        with pytest.raises(ValueError, match=message):
            render_annotation_ui(value)
