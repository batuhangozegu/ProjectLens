from projectlens.analysis.models import DependencyEdge, FileRecord, TestMatchRecord
from projectlens.analysis.risk import compute_risk


def source(path="a.py", loc=0, status="analyzed"):
    return FileRecord(path, "python", "python_source", loc, status)


def run(files, *, churn=None, edges=(), cycles=(), matches=()):
    return compute_risk(files, edges, cycles, matches, churn)


def test_each_factor_boundaries_and_level_thresholds():
    files = [source(f"f{i}.py", loc) for i, loc in enumerate((499, 500, 999, 1000))]
    history = {"available": True, "_churn_by_path": {"f0.py": 3, "f1.py": 4, "f2.py": 9, "f3.py": 10}}
    result = run(files, churn=history)
    by_path = {item["path"]: item for item in result["top_risks"]}
    assert by_path["f0.py"]["points"] == 1  # untested
    assert {item["id"] for item in by_path["f1.py"]["factors"]} == {"churn", "size", "untested"}
    assert by_path["f2.py"]["points"] == 3
    assert by_path["f3.py"]["points"] == 5
    assert by_path["f3.py"]["level"] == "high"
    assert [item["path"] for item in result["top_risks"]] == ["f3.py", "f1.py", "f2.py", "f0.py"]
    assert result["counts_by_level"] == {"high": 1, "medium": 2, "low": 1, "minimal": 0}


def test_cycle_untested_fan_in_and_test_match():
    files = [source("a.py"), source("b.py")]
    edges = [DependencyEdge(f"use{i}.py", "a.py", 1) for i in range(10)]
    result = run(files, edges=edges, cycles=(("a.py", "b.py"),), matches=(TestMatchRecord("a.py", ({"path": "test_a.py", "rule": "name"},)),))
    a = next(item for item in result["top_risks"] if item["path"] == "a.py")
    assert [item["id"] for item in a["factors"]] == ["cycle", "fan_in"]
    b = next(item for item in result["top_risks"] if item["path"] == "b.py")
    assert [item["id"] for item in b["factors"]] == ["cycle", "untested"]


def test_missing_churn_determinism_tie_break_and_cap():
    files = [source(f"{index:02}.py", 500) for index in range(25)]
    first = run(files)
    second = run(list(reversed(files)))
    assert first == second
    assert first["churn_available"] is False
    assert all(all(factor["id"] != "churn" for factor in item["factors"]) for item in first["top_risks"])
    assert len(first["top_risks"]) == 20
    assert [item["path"] for item in first["top_risks"]] == [f"{index:02}.py" for index in range(20)]
    assert first["confidence"] == "medium"


def test_status_and_source_class_filtering():
    result = run([source("test.py", status="parse_failed"), FileRecord("config.py", "python", "config", 2000, "analyzed"), source("broken.py", 2000, "parse_failed")])
    assert result["counts_by_level"] == {"high": 0, "medium": 0, "low": 0, "minimal": 0}


def test_minimal_zero_points_and_fan_in_boundary():
    files = [source("tested.py")]
    edges = [DependencyEdge(f"consumer{i}.py", "tested.py", 1) for i in range(9)]
    matched = (TestMatchRecord("tested.py", ({"path": "test_tested.py", "rule": "name"},)),)
    assert run(files, edges=edges, matches=matched)["counts_by_level"]["minimal"] == 1
    edges.append(DependencyEdge("consumer9.py", "tested.py", 1))
    result = run(files, edges=edges, matches=matched)
    assert result["top_risks"][0]["factors"] == [{"id": "fan_in", "points": 1, "reason": "10 incoming local dependency edges"}]
