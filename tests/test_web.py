from fastapi.testclient import TestClient

from reprocheck import web
from reprocheck.web import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_endpoint_exposes_real_traceable_audit():
    response = client.post("/api/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_review"
    assert {artifact["filename"] for artifact in payload["artifacts"]} == {
        "research_report.md",
        "model_predictions.csv",
        "train_split.csv",
        "test_split.csv",
    }
    assert {claim["status"] for claim in payload["claims"]} == {"verified", "mismatch"}
    assert payload["leakage"]["exact_overlap_test_rows"] == 1
    assert any(item["code"] == "exact_split_overlap" for item in payload["findings"])
    relations = {edge["relation"] for edge in payload["evidence_graph"]["edges"]}
    assert {"contains", "recomputes", "supports", "contradicts", "flags"} <= relations


def test_audit_endpoint():
    response = client.post(
        "/api/audit",
        files={
            "report": ("report.md", b"Accuracy: 50%", "text/markdown"),
            "predictions": (
                "predictions.csv",
                b"y_true,y_pred\n0,0\n1,0\n",
                "text/csv",
            ),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "passed"
    assert len(response.json()["certificate_sha256"]) == 64
    assert len(response.json()["evidence_graph"]["graph_sha256"]) == 64
    assert response.json()["evidence_graph"]["nodes"]


def test_regression_metrics_are_marked_scalar_and_web_uses_metadata():
    response = client.post(
        "/api/audit",
        data={"prediction_task": "regression"},
        files={
            "report": ("report.md", b"MAE: 2.5", "text/markdown"),
            "predictions": (
                "predictions.csv",
                b"y_true,y_pred\n0,2\n0,3\n",
                "text/csv",
            ),
        },
    )
    assert response.status_code == 200
    assert response.json()["claims"][0]["display_kind"] == "scalar"

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "formatMetric(claim.value, display_kind)" in script.text
    assert "percent(claim.value)" not in script.text


def test_web_exposes_interactive_evidence_explorer():
    page = client.get("/")
    script = client.get("/static/app.js")
    styles = client.get("/static/styles.css")

    assert page.status_code == script.status_code == styles.status_code == 200
    assert 'id="evidence-explorer"' in page.text
    assert 'id="evidence-svg"' in page.text
    assert 'id="node-inspector"' in page.text
    assert 'id="demo"' in page.text
    assert "semanticNeighborhood" in script.text
    assert "MAX_VISIBLE_NODES" in script.text
    assert "prefers-reduced-motion" in styles.text


def test_audit_endpoint_rejects_malformed_detection():
    response = client.post(
        "/api/audit",
        files={
            "report": ("report.md", b"mAP50: 90%", "text/markdown"),
            "detections": (
                "detections.json",
                b'{"images":[{"id":"x","ground_truth":[],"predictions":['
                b'{"class_id":0,"bbox":[0,0,1,1]}]}]}',
                "application/json",
            ),
        },
    )
    assert response.status_code == 422
    assert "confidence must be numeric" in response.json()["detail"]


def test_upload_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 10)
    response = client.post(
        "/api/audit",
        files={"report": ("report.md", b"Accuracy: 100%", "text/markdown")},
    )
    assert response.status_code == 413


def test_web_forwards_hybrid_near_duplicate_configuration():
    response = client.post(
        "/api/audit",
        data={
            "identity_columns": "id",
            "text_column": "text",
            "near_method": "hybrid_lexical_v1",
            "near_threshold": "0.8",
        },
        files={
            "report": ("report.md", b"No metric claim.", "text/markdown"),
            "train": (
                "train.csv",
                b"id,text\n1,classification accuracy on validation dataset\n",
                "text/csv",
            ),
            "test": (
                "test.csv",
                b"id,text\n2,clasification accuracy on the validation data set\n",
                "text/csv",
            ),
        },
    )
    assert response.status_code == 200
    assert response.json()["parameters"]["near_method"] == "hybrid_lexical_v1"
    assert response.json()["leakage"]["near_overlap_test_rows"] == 1
