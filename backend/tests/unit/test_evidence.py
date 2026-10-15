import json
import shutil
from pathlib import Path

import pytest

from projectlens.tracking.evidence import (
    CriterionInput,
    LinkInput,
    assess_task,
    assess_without_snapshot,
    evaluate_criterion,
)


def make_snapshot(*, partial=False):
    return {
        "files": [
            {"path": "src/a.py", "language": "python", "file_class": "source", "analysis_status": "analyzed"},
            {"path": "src/b.py", "language": "python", "file_class": "source", "analysis_status": "analyzed_with_diagnostics"},
            {"path": "src/broken.py", "language": "python", "file_class": "source", "analysis_status": "parse_failed"},
            {"path": "src/large.py", "language": "python", "file_class": "source", "analysis_status": "skipped_size_limit"},
            {"path": "src/locked.py", "language": "python", "file_class": "source", "analysis_status": "unreadable"},
            {"path": "docs/readme.md", "language": None, "file_class": "documentation", "analysis_status": "scanned"},
        ],
        "dependency_edges": [{"source": "src/a.py", "target": "src/b.py", "import_line": 4, "evidence_lines": [4]}],
        "cycles": [["src/a.py", "src/b.py"]],
        "external_imports": [], "unresolved_imports": [],
        "metrics": {"comment_markers": {
            "total": 3, "by_kind": {"TODO": 2, "FIXME": 1},
            "by_file": {
                "src/a.py": {"TODO": 1, "FIXME": 0, "total": 1, "available": True},
                "src/b.py": {"TODO": 1, "FIXME": 1, "total": 2, "available": True},
                "src/broken.py": {"TODO": 0, "FIXME": 0, "total": 0, "available": False},
            }, "unavailable_files": ["src/broken.py"],
        }}, "diagnostics": [], "partial": partial, "schema_version": "1", "projectlens_format": "projectlens-analysis",
    }


def criterion(kind, **params):
    return CriterionInput(1, kind, params)


@pytest.mark.parametrize("kind,params", [
    ("file_exists", {"path": "./src/a.py"}),
    ("path_has_files", {"prefix": "src/", "min_count": 2, "language": "python"}),
    ("import_edge_exists", {"source": "src/a.py", "target": "src/b.py"}),
    ("not_in_cycle", {"path": "docs/readme.md"}),
    ("max_todo_markers", {"path": "src/a.py", "max": 1}),
    ("no_analysis_failures", {"path": "src/a.py"}),
])
def test_each_kind_met(kind, params):
    assert evaluate_criterion(make_snapshot(), CriterionInput(1, kind, params)).outcome == "met"


@pytest.mark.parametrize("kind,params", [
    ("file_exists", {"path": "absent.py"}),
    ("path_has_files", {"prefix": "missing/"}),
    ("import_edge_exists", {"source": "src/a.py", "target": "docs/readme.md"}),
    ("not_in_cycle", {"path": "src/a.py"}),
    ("max_todo_markers", {"path": "src/b.py", "max": 1}),
    ("no_analysis_failures", {"path": "src/broken.py"}),
])
def test_each_kind_unmet(kind, params):
    assert evaluate_criterion(make_snapshot(), CriterionInput(1, kind, params)).outcome == "unmet"


@pytest.mark.parametrize("kind,params", [
    ("file_exists", {"path": "absent.py"}),
    ("path_has_files", {"prefix": "missing/"}),
    ("import_edge_exists", {"source": "src/a.py", "target": "src/broken.py"}),
    ("not_in_cycle", {"path": "absent.py"}),
    ("max_todo_markers", {"path": "src/broken.py", "max": 1}),
    ("no_analysis_failures", {"path": "missing/"}),
    ("manual_attestation", {}),
])
def test_each_kind_unknown(kind, params):
    assert evaluate_criterion(make_snapshot(partial=True), CriterionInput(1, kind, params)).outcome == "unknown"


@pytest.mark.parametrize("kind,params", [
    ("file_exists", {}), ("file_exists", {"path": "../secret"}),
    ("path_has_files", {"prefix": "src", "min_count": 1}),
    ("path_has_files", {"prefix": "src/", "min_count": 0}),
    ("path_has_files", {"prefix": "src/", "min_count": 100001}),
    ("path_has_files", {"prefix": "/src/"}),
    ("import_edge_exists", {"source": "src/a.py", "target": "../b.py"}),
    ("import_edge_exists", {"source": "/src/a.py", "target": "src/b.py"}),
    ("not_in_cycle", {"path": "C:\\src\\a.py"}),
    ("max_todo_markers", {"path": "src/a.py", "max": -1}),
    ("max_todo_markers", {"path": "src/../a.py", "max": 2}),
    ("no_analysis_failures", {"path": "../src/"}),
    ("manual_attestation", {"path": "src/a.py"}),
    ("unknown_kind", {}),
])
def test_invalid_params_are_unknown_invalid_criterion(kind, params):
    result = evaluate_criterion(make_snapshot(), CriterionInput("bad", kind, params))
    assert result.outcome == "unknown"
    assert result.reason.startswith("invalid_criterion: ")


def test_status_unknown_and_partial_rules():
    data = make_snapshot()
    assert evaluate_criterion(data, criterion("file_exists", path="src/broken.py")).outcome == "unknown"
    assert evaluate_criterion(data, criterion("file_exists", path="missing.py")).outcome == "unmet"
    assert evaluate_criterion(make_snapshot(partial=True), criterion("file_exists", path="missing.py")).outcome == "unknown"
    assert evaluate_criterion(make_snapshot(partial=True), criterion("not_in_cycle", path="src/broken.py")).outcome == "unknown"
    # Any known count above the maximum proves unmet despite unavailable remainder.
    data["metrics"]["comment_markers"]["by_file"]["src/broken.py"]["total"] = 3
    assert evaluate_criterion(data, criterion("max_todo_markers", path="src/", max=2)).outcome == "unmet"
    # A covered healthy subset can prove path_has_files even in a partial snapshot.
    assert evaluate_criterion(make_snapshot(partial=True), criterion("path_has_files", prefix="src/", min_count=1)).outcome == "met"


def test_estimate_rounding_confidence_and_unknown_exclusion():
    criteria = [criterion("file_exists", path="src/a.py"), criterion("file_exists", path="src/broken.py"),
                criterion("file_exists", path="src/broken.py")]
    result = assess_task(make_snapshot(), manual_status="IN_PROGRESS", criteria=criteria, links=[])
    assert result.estimated_percent == 100.0
    assert result.confidence == "low"  # one evaluated, two unknown
    assert len(result.unknown_criteria) == 2
    rounded = assess_task(make_snapshot(), manual_status="TODO", links=[], criteria=[
        criterion("file_exists", path="src/a.py"), criterion("file_exists", path="missing.py"),
        criterion("file_exists", path="src/b.py"),
    ])
    assert rounded.estimated_percent == 66.7
    assert rounded.confidence == "high"


@pytest.mark.parametrize("met,unmet,unknown,partial,expected", [
    (3, 0, 0, False, "high"), (2, 0, 0, False, "medium"), (2, 0, 1, False, "medium"),
    (1, 0, 2, False, "low"), (3, 0, 0, True, "medium"), (2, 0, 1, True, "low"),
    (1, 1, 0, False, "medium"),
])
def test_confidence_matrix(met, unmet, unknown, partial, expected):
    criteria = [criterion("file_exists", path="src/a.py") for _ in range(met)]
    criteria += [criterion("file_exists", path="missing.py") for _ in range(unmet)]
    criteria += [criterion("file_exists", path="src/broken.py") for _ in range(unknown)]
    assert assess_task(make_snapshot(partial=partial), manual_status="TODO", criteria=criteria, links=[]).confidence == expected


def test_empty_links_attestation_and_no_snapshot():
    result = assess_task(make_snapshot(), manual_status="TODO", criteria=[], links=[LinkInput("src/a.py")])
    assert result.state == "insufficient_evidence" and result.estimated_percent is None
    assert any("not completion evidence" in item for item in result.reasons)
    criteria = [CriterionInput("m", "manual_attestation", {}, attested=True), criterion("file_exists", path="src/a.py")]
    result = assess_task(make_snapshot(), manual_status="DONE", criteria=criteria, links=[])
    assert result.estimated_percent == 100.0
    assert result.attestations == {"attested": 1, "total": 1}
    assert result.criteria_results[0].outcome == "unknown"
    assert result.divergence is None
    no_snapshot = assess_without_snapshot("BLOCKED", criteria, [LinkInput("src/a.py")])
    assert no_snapshot.state == "no_snapshot" and no_snapshot.estimated_percent is None
    assert no_snapshot.manual_status == "BLOCKED"


def test_divergence_directions_and_non_divergence():
    unmet = [criterion("file_exists", path="missing.py")]
    complete = [criterion("file_exists", path="src/a.py") for _ in range(3)]
    assert assess_task(make_snapshot(), manual_status="DONE", criteria=unmet, links=[]).divergence == "done_but_unmet"
    assert assess_task(make_snapshot(), manual_status="TODO", criteria=complete, links=[]).divergence == "evidence_complete_but_not_done"
    assert assess_task(make_snapshot(), manual_status="BLOCKED", criteria=complete, links=[]).divergence == "evidence_complete_but_not_done"
    assert assess_task(make_snapshot(), manual_status="IN_PROGRESS", criteria=complete, links=[]).divergence is None
    assert assess_task(make_snapshot(), manual_status="TODO", criteria=complete[:1], links=[]).divergence is None


def test_manual_status_validation():
    with pytest.raises(ValueError):
        assess_without_snapshot("DONE-ish", [], [])


def test_determinism_tuple_inputs_and_json_serializable():
    one = make_snapshot()
    two = {**one, "files": tuple(reversed(one["files"])), "dependency_edges": tuple(one["dependency_edges"]), "cycles": tuple(tuple(x) for x in one["cycles"])}
    criteria = [criterion("path_has_files", prefix="src/", min_count=1), criterion("not_in_cycle", path="src/a.py")]
    links = [LinkInput("src/")]
    first = assess_task(one, manual_status="TODO", criteria=criteria, links=links, snapshot_meta={"id": 8, "commit_sha": "abc"}).to_dict()
    second = assess_task(two, manual_status="TODO", criteria=criteria, links=links, snapshot_meta={"id": 8, "commit_sha": "abc"}).to_dict()
    assert first == second
    json.dumps(first)
    assert first["criteria_results"][1]["evidence"] == ["src/a.py", "src/b.py"]
    assert first["context"][0]["analyzed_file_count"] == 2


def test_pipeline_snapshot(tmp_path):
    from projectlens.analysis.models import AnalysisOptions
    from projectlens.analysis.pipeline import analyze

    fixture = Path(__file__).parents[1] / "fixtures" / "sample_repo"
    root = tmp_path / "sample_repo"
    shutil.copytree(fixture, root)
    result = analyze(AnalysisOptions(root_path=str(root))).to_dict()
    assert evaluate_criterion(result, criterion("file_exists", path="src/pkg/left.py")).outcome == "met"
    assert evaluate_criterion(result, criterion("not_in_cycle", path="src/pkg/left.py")).outcome == "unmet"
    assert evaluate_criterion(result, criterion("max_todo_markers", path="broken.py", max=1)).outcome == "unknown"
    assert evaluate_criterion(result, criterion("no_analysis_failures", path="broken.py")).outcome == "unmet"
