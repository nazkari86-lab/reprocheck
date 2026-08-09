from fastapi.testclient import TestClient

from reprocheck import web
from reprocheck.web import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
