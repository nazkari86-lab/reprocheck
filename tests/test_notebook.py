import json
from pathlib import Path

from reprocheck.audit import run_audit
from reprocheck.notebook import audit_notebook
from reprocheck.render import render_html


def test_detects_pipeline_and_execution_risks(tmp_path: Path):
    path = tmp_path / "risk.ipynb"
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 2,
                        "source": "X = scaler.fit_transform(data)",
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": "X_train, X_test = train_test_split(X)\nmodel.fit(X_test, y_test)",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    result = audit_notebook(path)
    assert {finding["code"] for finding in result.findings} == {
        "non_monotonic_notebook_execution",
        "preprocessing_before_split",
        "fit_on_test_data",
        "random_seed_not_detected",
    }


def test_reports_unparsed_cells_and_renders_notebook_summary(tmp_path: Path):
    notebook = tmp_path / "syntax.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "source": "context"},
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "source": ["np.random.seed(7)\n", "broken ("],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": "(factory()[0])()",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    notebook_audit = audit_notebook(notebook)
    assert notebook_audit.has_random_seed is True
    assert notebook_audit.code_cells == 2
    assert [item["code"] for item in notebook_audit.findings] == ["unparsed_notebook_cells"]

    report_path = tmp_path / "report.md"
    report_path.write_text("No metric claim here.", encoding="utf-8")
    report = run_audit(report_path=report_path, notebook_path=notebook)
    output = tmp_path / "audit.html"
    render_html(report, output)
    html = output.read_text(encoding="utf-8")
    assert "Code cells: <b>2</b>" in html
    assert "seed detected: <b>yes</b>" in html


def test_model_validation_data_is_not_mislabeled_as_fit_on_test(tmp_path: Path):
    path = tmp_path / "validation.ipynb"
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": (
                            "random.seed(7)\n"
                            "model.fit(X_train, y_train, validation_data=(X_test, y_test))"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = audit_notebook(path)
    assert "fit_on_test_data" not in {item["code"] for item in result.findings}
