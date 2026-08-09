from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

from .models import NotebookAudit


SEED_PATTERNS = (
    re.compile(r"\brandom_state\s*="),
    re.compile(r"\b(?:np\.)?random\.seed\s*\("),
    re.compile(r"\btorch\.manual_seed\s*\("),
)


def audit_notebook(path: Path) -> NotebookAudit:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cells = payload.get("cells", [])
    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    sources = [_source_text(cell.get("source", "")) for cell in code_cells]
    combined = "\n".join(sources)
    counts = [cell.get("execution_count") for cell in code_cells]
    numeric_counts = [count for count in counts if isinstance(count, int)]
    duplicate_counts = sorted(
        count for count, amount in Counter(numeric_counts).items() if amount > 1
    )
    monotonic = numeric_counts == sorted(numeric_counts) and not duplicate_counts
    has_seed = any(pattern.search(combined) for pattern in SEED_PATTERNS)
    findings: list[dict[str, object]] = []

    if numeric_counts and not monotonic:
        findings.append(
            {
                "severity": "medium",
                "code": "non_monotonic_notebook_execution",
                "message": "Notebook cells have duplicate or non-monotonic execution counts.",
            }
        )

    calls = _collect_calls(sources)
    has_training = any(name.endswith((".fit", ".fit_transform")) for _, name, _ in calls)
    split_positions = [position for position, name, _ in calls if name.endswith("train_test_split")]
    fit_positions = [
        position for position, name, _ in calls if name.endswith((".fit", ".fit_transform"))
    ]
    if split_positions and fit_positions and min(fit_positions) < min(split_positions):
        findings.append(
            {
                "severity": "high",
                "code": "preprocessing_before_split",
                "message": "A fit/fit_transform call appears before train_test_split in notebook order.",
            }
        )

    test_fit_calls = [
        name
        for _, name, arguments in calls
        if name.endswith((".fit", ".fit_transform"))
        and any(
            "test" in argument.casefold()
            and not argument.casefold().startswith(("validation_data=", "validation_split="))
            for argument in arguments
        )
    ]
    if test_fit_calls:
        findings.append(
            {
                "severity": "high",
                "code": "fit_on_test_data",
                "message": "A fit/fit_transform call receives a variable whose name contains 'test'.",
            }
        )

    findings.extend(_dataflow_findings(sources))

    if has_training and not has_seed:
        findings.append(
            {
                "severity": "medium",
                "code": "random_seed_not_detected",
                "message": "Training code was detected, but no common random-seed declaration was found.",
            }
        )

    syntax_errors = sum(1 for source in sources if not _is_parseable(source))
    if syntax_errors:
        findings.append(
            {
                "severity": "low",
                "code": "unparsed_notebook_cells",
                "message": f"{syntax_errors} code cells could not be parsed as standalone Python.",
            }
        )

    return NotebookAudit(
        filename=path.name,
        total_cells=len(cells),
        code_cells=len(code_cells),
        executed_code_cells=len(numeric_counts),
        has_random_seed=has_seed,
        execution_order_monotonic=monotonic,
        duplicate_execution_counts=duplicate_counts,
        findings=findings,
    )


def _collect_calls(sources: list[str]) -> list[tuple[int, str, list[str]]]:
    calls: list[tuple[int, str, list[str]]] = []
    for cell_index, source in enumerate(sources):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node.func)
                arguments = [ast.unparse(argument) for argument in node.args]
                arguments.extend(
                    f"{keyword.arg or '**'}={ast.unparse(keyword.value)}"
                    for keyword in node.keywords
                )
                calls.append((cell_index * 1_000_000 + node.lineno, name, arguments))
    return calls


def _dataflow_findings(sources: list[str]) -> list[dict[str, object]]:
    trees = []
    for source in sources:
        try:
            trees.append(ast.parse(source))
        except SyntaxError:
            continue
    function_sinks = _function_fit_parameters(trees)
    taint: dict[str, set[str]] = {}
    risky_calls: list[str] = []
    for tree in trees:
        for statement in tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(statement, ast.Assign):
                _propagate_assignment(statement.targets, statement.value, taint)
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                _propagate_assignment([statement.target], statement.value, taint)
            for node in ast.walk(statement):
                if not isinstance(node, ast.Call):
                    continue
                name = _call_name(node.func)
                argument_taint = [_expression_taint(argument, taint) for argument in node.args]
                if name.endswith((".fit", ".fit_transform")):
                    direct_test_name = any(
                        "test" in ast.unparse(argument).casefold() for argument in node.args
                    )
                    if not direct_test_name and any("test" in tags for tags in argument_taint):
                        risky_calls.append(name)
                elif name in function_sinks and any(
                    index < len(argument_taint) and "test" in argument_taint[index]
                    for index in function_sinks[name]
                ):
                    risky_calls.append(name)
    if not risky_calls:
        return []
    return [
        {
            "severity": "high",
            "code": "fit_on_test_dataflow",
            "message": (
                "Static data-flow links test-derived data to a training fit call: "
                + ", ".join(sorted(set(risky_calls)))
                + "."
            ),
        }
    ]


def _function_fit_parameters(trees: list[ast.Module]) -> dict[str, set[int]]:
    sinks: dict[str, set[int]] = {}
    for tree in trees:
        for function in (node for node in tree.body if isinstance(node, ast.FunctionDef)):
            parameters = [argument.arg for argument in function.args.args]
            aliases: dict[str, set[int]] = {name: {index} for index, name in enumerate(parameters)}
            used: set[int] = set()
            for statement in function.body:
                if isinstance(statement, ast.Assign):
                    indexes = _parameter_indexes(statement.value, aliases)
                    for target in statement.targets:
                        for name in _target_names(target):
                            aliases[name] = indexes
                for node in ast.walk(statement):
                    if isinstance(node, ast.Call) and _call_name(node.func).endswith(
                        (".fit", ".fit_transform")
                    ):
                        for argument in node.args:
                            used.update(_parameter_indexes(argument, aliases))
            if used:
                sinks[function.name] = used
    return sinks


def _propagate_assignment(
    targets: list[ast.expr], value: ast.expr, taint: dict[str, set[str]]
) -> None:
    if isinstance(value, ast.Call) and _call_name(value.func).endswith("train_test_split"):
        flat_targets = [name for target in targets for name in _target_names(target)]
        for index, name in enumerate(flat_targets):
            taint[name] = {"test" if index % 2 else "train"}
        return
    tags = _expression_taint(value, taint)
    for target in targets:
        for name in _target_names(target):
            inferred = {"test"} if "test" in name.casefold() else set()
            taint[name] = tags | inferred


def _target_names(node: ast.expr) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [name for element in node.elts for name in _target_names(element)]
    return []


def _expression_taint(node: ast.AST, taint: dict[str, set[str]]) -> set[str]:
    tags: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            tags.update(taint.get(child.id, set()))
    return tags


def _parameter_indexes(node: ast.AST, aliases: dict[str, set[int]]) -> set[int]:
    indexes: set[int] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            indexes.update(aliases.get(child.id, set()))
    return indexes


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _is_parseable(source: str) -> bool:
    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


def _source_text(source: str | list[str]) -> str:
    return "".join(source) if isinstance(source, list) else source
