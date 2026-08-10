from __future__ import annotations

from dataclasses import dataclass, field
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from .audit import run_audit
from .batch import load_project_manifest
from .version import __version__


PACKAGE_ROOT = Path(__file__).parent
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PROJECT_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_PROJECT_FILES = 300
JOB_TTL_SECONDS = 10 * 60
MAX_ACTIVE_JOBS = 4


@dataclass
class AuditJob:
    status: str = "queued"
    stages: dict[str, dict[str, object]] = field(default_factory=dict)
    result: dict[str, object] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)


_jobs: dict[str, AuditJob] = {}
_jobs_lock = threading.Lock()

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


@app.post("/api/audit/jobs", status_code=202)
async def create_audit_job(
    report: UploadFile | None = File(None),
    notebook: UploadFile | None = File(None),
    predictions: UploadFile | None = File(None),
    metrics: UploadFile | None = File(None),
    detections: UploadFile | None = File(None),
    train: UploadFile | None = File(None),
    test: UploadFile | None = File(None),
    project_files: list[UploadFile] = File(default=[]),
    report_selector: str = Form(""),
    metrics_selector: str = Form(""),
    label_column: str = Form(""),
    group_column: str = Form(""),
    identity_columns: str = Form(""),
    text_column: str = Form(""),
    near_threshold: float | None = Form(None),
    near_method: str = Form(""),
    positive_label: str = Form(""),
    prediction_task: str = Form(""),
    average: str = Form(""),
    tolerance: float | None = Form(None),
):
    upload_started = time.perf_counter()
    root = Path(tempfile.mkdtemp(prefix="reprocheck-job-"))
    try:
        with _jobs_lock:
            active_jobs = sum(job.status in {"queued", "running"} for job in _jobs.values())
        if active_jobs >= MAX_ACTIVE_JOBS:
            raise HTTPException(429, "Сервер уже выполняет максимальное число аудитов")
        manual_paths = {
            "report": await _store(report, root, "report"),
            "notebook": await _store(notebook, root, "notebook"),
            "predictions": await _store(predictions, root, "predictions"),
            "metrics": await _store(metrics, root, "metrics"),
            "detections": await _store(detections, root, "detections"),
            "train": await _store(train, root, "train"),
            "test": await _store(test, root, "test"),
        }
        stored_project = await _store_project_files(project_files, root)
        inferred, project_extras, inference_source, manifest_options = _infer_project_roles(
            stored_project
        )
        paths = {role: manual_paths[role] or inferred.get(role) for role in manual_paths}
        if paths["report"] is None:
            raise HTTPException(
                422,
                "В папке не найден научный отчёт. Добавьте report.md/report.pdf "
                "или загрузите отчёт в отдельное поле.",
            )
        if (paths["train"] is None) != (paths["test"] is None):
            raise HTTPException(400, "Train и test нужно загружать вместе")

        selected_project_paths = {path for path in inferred.values()}
        extras = [item for item in project_extras if item[1] not in selected_project_paths]
        role_summary = [
            {
                "role": role,
                "filename": path.name,
                "source": "manual" if manual_paths[role] is not None else inference_source,
            }
            for role, path in paths.items()
            if path is not None
        ]
        role_summary.extend(
            {"role": role, "filename": path.name, "source": "project_artifact"}
            for role, path in extras
        )

        job_id = uuid4().hex
        input_file_count = len(stored_project) + sum(
            path is not None for path in manual_paths.values()
        )
        job = AuditJob(
            stages={
                "files": {
                    "stage": "files",
                    "state": "completed",
                    "message": (
                        f"Загружено: {input_file_count}; зафиксировано: {len(role_summary)}; "
                        f"распознано ролей: {len(paths) - list(paths.values()).count(None)}"
                    ),
                    "files": role_summary,
                    "input_file_count": input_file_count,
                    "project_file_count": len(stored_project),
                    "inference_source": inference_source,
                    "experiment_id": manifest_options.get("experiment_id"),
                    "experiment_count": manifest_options.get("experiment_count"),
                    "duration_ms": (time.perf_counter() - upload_started) * 1000,
                }
            }
        )
        _prune_jobs()
        with _jobs_lock:
            _jobs[job_id] = job

        kwargs: dict[str, Any] = {
            "report_path": paths["report"],
            "report_selector": report_selector or manifest_options.get("report_selector"),
            "notebook_path": paths["notebook"],
            "predictions_path": paths["predictions"],
            "metrics_path": paths["metrics"],
            "metrics_selector": metrics_selector or manifest_options.get("metrics_selector"),
            "detections_path": paths["detections"],
            "train_path": paths["train"],
            "test_path": paths["test"],
            "label_column": label_column or manifest_options.get("label_column"),
            "group_column": group_column or manifest_options.get("group_column"),
            "identity_columns": (
                _split_columns(identity_columns)
                if identity_columns
                else manifest_options.get("identity_columns")
            ),
            "text_column": text_column or manifest_options.get("text_column"),
            "near_threshold": (
                near_threshold
                if near_threshold is not None
                else manifest_options.get("near_threshold", 0.8)
            ),
            "near_method": (
                near_method or manifest_options.get("near_method", "hybrid_lexical_v1")
            ),
            "positive_label": positive_label or manifest_options.get("positive_label"),
            "prediction_task": (
                prediction_task or manifest_options.get("prediction_task", "classification")
            ),
            "average": average or manifest_options.get("average", "auto"),
            "tolerance": (
                tolerance if tolerance is not None else manifest_options.get("tolerance", 0.005)
            ),
            "extra_artifacts": extras,
        }
        worker = threading.Thread(
            target=_execute_audit_job,
            args=(job_id, root, kwargs),
            name=f"reprocheck-{job_id[:8]}",
            daemon=True,
        )
        worker.start()
        return {"job_id": job_id, "status": "queued", "stages": list(job.stages.values())}
    except HTTPException:
        shutil.rmtree(root, ignore_errors=True)
        raise
    except (UnicodeDecodeError, ValueError) as error:
        shutil.rmtree(root, ignore_errors=True)
        raise HTTPException(422, str(error)) from error
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


@app.get("/api/audit/jobs/{job_id}")
def get_audit_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Audit job не найден или уже удалён")
        return _job_snapshot(job_id, job)


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
    if upload is None or not upload.filename:
        return None
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Файл {role} превышает 20 MB")
    filename = Path(upload.filename or "").name
    if not filename or filename in {".", ".."}:
        raise HTTPException(400, f"Некорректное имя файла {role}")
    path = root / "manual" / role / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


async def _store_project_files(uploads: list[UploadFile], root: Path) -> list[Path]:
    if len(uploads) > MAX_PROJECT_FILES:
        raise HTTPException(413, f"В папке больше {MAX_PROJECT_FILES} файлов")
    stored: list[Path] = []
    seen: set[Path] = set()
    total_bytes = 0
    for upload in uploads:
        raw_name = (upload.filename or "").replace("\\", "/")
        relative = Path(raw_name)
        if (
            not raw_name
            or relative.is_absolute()
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise HTTPException(400, "Папка содержит небезопасный путь файла")
        destination = root / "project" / relative
        if destination in seen:
            raise HTTPException(400, f"Повторяющийся файл проекта: {relative}")
        content = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Файл {relative} превышает 20 MB")
        total_bytes += len(content)
        if total_bytes > MAX_PROJECT_UPLOAD_BYTES:
            raise HTTPException(413, "Папка проекта превышает 100 MB")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        seen.add(destination)
        stored.append(destination)
    return stored


def _infer_project_roles(
    files: list[Path],
) -> tuple[dict[str, Path], list[tuple[str, Path]], str, dict[str, Any]]:
    if not files:
        return {}, [], "manual", {}
    available = {path.resolve(): path for path in files}
    inferred: dict[str, Path] = {}
    custom_artifacts: dict[str, Path] = {}
    source = "filename_rules"
    manifest_options: dict[str, Any] = {}
    manifests = [path for path in files if path.name.lower() == "reprocheck.json"]
    selected_manifest: Path | None = None
    if manifests:
        manifest = sorted(manifests, key=lambda path: (len(path.parts), str(path).lower()))[0]
        selected_manifest = manifest
        try:
            payload = load_project_manifest(manifest)
            experiment = payload["experiments"][0]
            for role in (
                "report",
                "notebook",
                "predictions",
                "metrics",
                "detections",
                "train",
                "test",
            ):
                value = experiment.get(role)
                if isinstance(value, str):
                    candidate = (manifest.parent / value).resolve()
                    if candidate not in available:
                        raise ValueError(f"manifest artifact is absent from upload: {value}")
                    inferred[role] = available[candidate]
            option_keys = {
                "report_selector",
                "metrics_selector",
                "label_column",
                "group_column",
                "identity_columns",
                "text_column",
                "near_threshold",
                "near_method",
                "positive_label",
                "prediction_task",
                "average",
                "tolerance",
            }
            manifest_options = {
                key: value for key, value in experiment.items() if key in option_keys
            }
            manifest_options["experiment_id"] = experiment["id"]
            manifest_options["experiment_count"] = len(payload["experiments"])
            for role, value in experiment.get("artifacts", {}).items():
                candidate = (manifest.parent / value).resolve()
                if candidate not in available:
                    raise ValueError(f"manifest artifact is absent from upload: {value}")
                custom_artifacts[role] = available[candidate]
            source = "reprocheck.json"
        except (IndexError, KeyError, OSError, TypeError) as error:
            raise ValueError(f"cannot read project manifest: {error}") from error

    rules: dict[str, tuple[set[str], set[str]]] = {
        "report": (
            {"report.md", "report.txt", "report.rst", "report.pdf", "report.docx", "paper.md"},
            {"report", "paper", "summary"},
        ),
        "notebook": (
            {"analysis.ipynb", "experiment.ipynb", "notebook.ipynb"},
            {"notebook", "experiment", "analysis"},
        ),
        "predictions": (
            {"predictions.csv", "prediction.csv", "preds.csv"},
            {"prediction", "predictions", "preds", "inference"},
        ),
        "metrics": (
            {"metrics.json", "metrics.csv", "scores.json", "scores.csv"},
            {"metric", "metrics", "scores"},
        ),
        "detections": ({"detections.json", "detection.json"}, {"detection", "detections", "coco"}),
        "train": ({"train.csv", "train_split.csv"}, {"train"}),
        "test": ({"test.csv", "test_split.csv"}, {"test"}),
    }
    suffixes = {
        "report": {".md", ".txt", ".rst", ".pdf", ".docx", ".json", ".ipynb"},
        "notebook": {".ipynb"},
        "predictions": {".csv"},
        "metrics": {".json", ".csv"},
        "detections": {".json"},
        "train": {".csv"},
        "test": {".csv"},
    }
    used = set(inferred.values()) | set(custom_artifacts.values())
    for role in ("report", "notebook", "train", "test", "predictions", "metrics", "detections"):
        if source == "reprocheck.json":
            break
        if role in inferred:
            continue
        exact_names, tokens = rules[role]
        candidates: list[tuple[int, str, Path]] = []
        for path in files:
            if path in used or path.suffix.lower() not in suffixes[role]:
                continue
            name = path.name.lower()
            stem_tokens = set(name.replace("-", "_").replace(".", "_").split("_"))
            score = 100 if name in exact_names else 20 if stem_tokens & tokens else 0
            if score:
                candidates.append((-score, str(path).lower(), path))
        if candidates:
            selected = sorted(candidates)[0][2]
            inferred[role] = selected
            used.add(selected)

    if "report" not in inferred and "notebook" in inferred:
        inferred["report"] = inferred["notebook"]

    ignored_parts = {".git", ".venv", "node_modules", "outputs", "dist", "build", "__pycache__"}
    nested_project_roots = {
        manifest.parent for manifest in manifests if manifest != selected_manifest
    }
    generic_extras = [
        path
        for path in sorted(files, key=lambda item: str(item).lower())
        if path not in used
        and not ignored_parts.intersection(path.parts)
        and not any(root == path.parent or root in path.parents for root in nested_project_roots)
    ]
    extras = sorted(custom_artifacts.items())
    extras.extend(
        (f"project_{index:03d}", path)
        for index, path in enumerate(generic_extras[: max(0, 40 - len(extras))])
    )
    return inferred, extras, source, manifest_options


def _execute_audit_job(job_id: str, root: Path, kwargs: dict[str, Any]) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        job.status = "running"

    def progress(stage: str, state: str, detail: dict[str, object]) -> None:
        with _jobs_lock:
            current = _jobs.get(job_id)
            if current is not None:
                previous = current.stages.get(stage, {})
                previous_started = previous.get("_started_at")
                started_at = (
                    time.perf_counter()
                    if state == "started"
                    else (
                        float(previous_started)
                        if isinstance(previous_started, int | float)
                        else time.perf_counter()
                    )
                )
                event = {"stage": stage, "state": state, **detail, "_started_at": started_at}
                if state == "completed":
                    event["duration_ms"] = (time.perf_counter() - started_at) * 1000
                current.stages[stage] = event

    try:
        report = run_audit(**kwargs, progress_callback=progress)
        with _jobs_lock:
            job = _jobs[job_id]
            job.result = report.to_dict()
            job.status = "completed"
    except Exception as error:
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is not None:
                job.error = str(error)
                job.status = "failed"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _job_snapshot(job_id: str, job: AuditJob) -> dict[str, object]:
    stage_order = ("files", "claims", "evidence", "matching", "certificate")
    stages = [
        {key: value for key, value in job.stages[stage].items() if not key.startswith("_")}
        for stage in stage_order
        if stage in job.stages
    ]
    return {
        "job_id": job_id,
        "status": job.status,
        "stages": stages,
        "result": job.result if job.status == "completed" else None,
        "error": job.error,
    }


def _prune_jobs() -> None:
    cutoff = time.monotonic() - JOB_TTL_SECONDS
    with _jobs_lock:
        stale = [
            job_id
            for job_id, job in _jobs.items()
            if job.status in {"completed", "failed"} and job.created_at < cutoff
        ]
        for job_id in stale:
            del _jobs[job_id]


def _split_columns(value: str) -> list[str] | None:
    columns = [item.strip() for item in value.split(",") if item.strip()]
    return columns or None
