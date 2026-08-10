from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from .audit import run_audit
from .version import __version__


PACKAGE_ROOT = Path(__file__).parent
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

app = FastAPI(title="ReproCheck", version=__version__)
app.mount("/static", StaticFiles(directory=PACKAGE_ROOT / "static"), name="static")
templates = Jinja2Templates(directory=PACKAGE_ROOT / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"version": __version__}
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/api/demo")
async def audit_demo():
    return await run_in_threadpool(_run_demo_audit)


@app.post("/api/audit")
async def audit_upload(
    report: UploadFile = File(...),
    notebook: UploadFile | None = File(None),
    predictions: UploadFile | None = File(None),
    metrics: UploadFile | None = File(None),
    detections: UploadFile | None = File(None),
    train: UploadFile | None = File(None),
    test: UploadFile | None = File(None),
    report_selector: str = Form(""),
    metrics_selector: str = Form(""),
    label_column: str = Form(""),
    group_column: str = Form(""),
    identity_columns: str = Form(""),
    text_column: str = Form(""),
    near_threshold: float = Form(0.8),
    near_method: str = Form("hybrid_lexical_v1"),
    positive_label: str = Form(""),
    prediction_task: str = Form("classification"),
    average: str = Form("auto"),
    tolerance: float = Form(0.005),
):
    if (train is None) != (test is None):
        raise HTTPException(400, "Train и test нужно загружать вместе")
    try:
        with tempfile.TemporaryDirectory(prefix="reprocheck-") as directory:
            root = Path(directory)
            paths = {
                "report": await _store(report, root, "report"),
                "notebook": await _store(notebook, root, "notebook"),
                "predictions": await _store(predictions, root, "predictions"),
                "metrics": await _store(metrics, root, "metrics"),
                "detections": await _store(detections, root, "detections"),
                "train": await _store(train, root, "train"),
                "test": await _store(test, root, "test"),
            }
            report_path = paths["report"]
            if report_path is None:
                raise HTTPException(400, "Report is required")
            result = await run_in_threadpool(
                run_audit,
                report_path=report_path,
                report_selector=report_selector or None,
                notebook_path=paths["notebook"],
                predictions_path=paths["predictions"],
                metrics_path=paths["metrics"],
                metrics_selector=metrics_selector or None,
                detections_path=paths["detections"],
                train_path=paths["train"],
                test_path=paths["test"],
                label_column=label_column or None,
                group_column=group_column or None,
                identity_columns=[
                    value.strip() for value in identity_columns.split(",") if value.strip()
                ]
                or None,
                text_column=text_column or None,
                near_threshold=near_threshold,
                near_method=near_method,
                positive_label=positive_label or None,
                prediction_task=prediction_task,
                average=average,
                tolerance=tolerance,
            )
            return result.to_dict()
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(422, str(error)) from error


def _run_demo_audit() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="reprocheck-demo-") as directory:
        root = Path(directory)
        report = root / "research_report.md"
        predictions = root / "model_predictions.csv"
        train = root / "train_split.csv"
        test = root / "test_split.csv"
        report.write_text(
            "# Glacier classifier\n\nНа тестовой выборке Accuracy: 75%.\nЗаявленная F1: 0.90.\n",
            encoding="utf-8",
        )
        predictions.write_text(
            "y_true,y_pred\n0,0\n0,1\n1,1\n1,1\n",
            encoding="utf-8",
        )
        train.write_text(
            "id,text,label\ntr-1,north glacier tile,0\ntr-2,south glacier tile,1\n",
            encoding="utf-8",
        )
        test.write_text(
            "id,text,label\nte-1,south glacier tile,1\nte-2,east glacier tile,0\n",
            encoding="utf-8",
        )
        return run_audit(
            report_path=report,
            predictions_path=predictions,
            train_path=train,
            test_path=test,
            label_column="label",
            identity_columns=["text"],
        ).to_dict()


async def _store(upload: UploadFile | None, root: Path, role: str) -> Path | None:
    if upload is None:
        return None
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Файл {role} превышает 20 MB")
    suffix = Path(upload.filename or "").suffix
    path = root / f"{role}{suffix}"
    path.write_bytes(content)
    return path
