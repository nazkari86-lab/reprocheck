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
