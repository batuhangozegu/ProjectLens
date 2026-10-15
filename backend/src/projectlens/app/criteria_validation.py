"""Strict validation and normalization for acceptance criterion parameters."""

from __future__ import annotations

from typing import Any

from projectlens.app.path_validation import normalize_file_path, normalize_task_path

KINDS = {
    "file_exists", "path_has_files", "import_edge_exists", "not_in_cycle",
    "max_todo_markers", "no_analysis_failures", "manual_attestation",
}


def validate_criterion_params(kind: str, params: Any) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError("unknown acceptance criterion kind")
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    result = dict(params)

    def keys(required: set[str], optional: set[str] | None = None) -> None:
        optional = optional or set()
        if not required <= result.keys() or not result.keys() <= required | optional:
            raise ValueError("params contain missing or unknown keys")

    def integer(name: str, minimum: int, maximum: int) -> None:
        value = result[name]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")

    def short_string(name: str) -> None:
        value = result[name]
        if not isinstance(value, str) or len(value) > 40:
            raise ValueError(f"{name} must be a string of at most 40 characters")

    if kind == "file_exists":
        keys({"path"}); result["path"] = normalize_file_path(result["path"])
    elif kind == "path_has_files":
        keys({"prefix"}, {"min_count", "language", "file_class"})
        if not isinstance(result["prefix"], str):
            raise ValueError("prefix must end with '/'")
        result["prefix"] = normalize_task_path(result["prefix"])
        if not result["prefix"].endswith("/"):
            raise ValueError("prefix must end with '/'")
        result["min_count"] = result.get("min_count", 1)
        integer("min_count", 1, 100000)
        for key in ("language", "file_class"):
            if key in result:
                short_string(key)
    elif kind == "import_edge_exists":
        keys({"source", "target"})
        result["source"] = normalize_file_path(result["source"])
        result["target"] = normalize_file_path(result["target"])
    elif kind == "not_in_cycle":
        keys({"path"}); result["path"] = normalize_file_path(result["path"])
    elif kind == "max_todo_markers":
        keys({"path", "max"})
        result["path"] = normalize_task_path(result["path"])
        integer("max", 0, 1000000)
    elif kind == "no_analysis_failures":
        keys({"path"}); result["path"] = normalize_task_path(result["path"])
    else:
        keys(set())
    return result
