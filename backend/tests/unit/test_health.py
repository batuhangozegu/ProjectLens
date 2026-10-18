from projectlens.analysis.health import compute_health
from projectlens.analysis.models import DependencyEdge, FileRecord


def base_inputs():
    files = [FileRecord(f"src/{i}.py", "python", "python_source", 100, "analyzed") for i in range(4)]
    metrics = {"test_matching": {"sources_total": 2, "sources_with_matching_test": 1},
               "comment_markers": {"total": 1, "unavailable_files": []}, "physical_loc": {"total": 400}}
    return files, [], [], [], metrics


def component(result, key):
    return next(item for item in result["components"] if item["id"] == key)


def test_component_boundaries_and_saturation():
    files, edges, cycles, unresolved, metrics = base_inputs()
    assert component(compute_health(files, edges, cycles, unresolved, metrics, False), "cycles")["score"] == 100
    cycles[:] = [[f"src/{i}.py" for i in range(4)]]
    assert component(compute_health(files, edges, cycles, unresolved, metrics, False), "cycles")["score"] == 0
    cycles[:] = [["src/0.py"]]
    assert component(compute_health(files, edges, cycles, unresolved, metrics, False), "cycles")["score"] == 0
    unresolved[:] = [{"module": "x"}, {"module": "y"}]
    edges[:] = [DependencyEdge("src/0.py", "src/1.py", 1), DependencyEdge("src/2.py", "src/3.py", 1)]
    assert component(compute_health(files, edges, cycles, unresolved, metrics, False), "unresolved_imports")["score"] == 0
    unresolved.append({"module": "z"})
    assert component(compute_health(files, edges, cycles, unresolved, metrics, False), "unresolved_imports")["score"] == 0
    unresolved.clear()
    assert component(compute_health(files, edges, cycles, unresolved, metrics, False), "unresolved_imports")["score"] == 100


def test_todo_density_saturation_and_test_score():
    files, edges, cycles, unresolved, metrics = base_inputs()
    metrics["comment_markers"]["total"] = 8
    health = compute_health(files, edges, cycles, unresolved, metrics, False)
    assert component(health, "todo_density")["score"] == 0
    assert component(health, "test_presence")["score"] == 50


def test_each_component_can_be_unavailable_and_overall_needs_two():
    files, edges, cycles, unresolved, metrics = base_inputs()
    metrics["test_matching"]["sources_total"] = 0
    metrics["comment_markers"]["unavailable_files"] = ["x.py"]
    result = compute_health(files, edges, cycles, unresolved, metrics, False)
    assert component(result, "test_presence")["available"] is False
    assert component(result, "todo_density")["available"] is False
    result = compute_health([], edges, cycles, unresolved, {"test_matching": {"sources_total": 0}, "comment_markers": {"total": 0}, "physical_loc": {"total": 0}}, False)
    assert result["score"] is None and result["confidence"] == "none"
    assert all(not item["available"] for item in result["components"])


def test_weight_renormalization_levels_confidence_and_determinism():
    files, edges, cycles, unresolved, metrics = base_inputs()
    metrics["test_matching"] = {"sources_total": 1, "sources_with_matching_test": 1}
    metrics["comment_markers"]["unavailable_files"] = ["missing.py"]
    result = compute_health(files, edges, cycles, unresolved, metrics, False)
    # cycles 100, unresolved unavailable, tests 100; normalized weights .3/.3 => 100
    assert result["score"] == 100 and result["level"] == "good" and result["confidence"] == "low"
    assert result == compute_health(list(reversed(files)), edges, cycles, unresolved, metrics, False)
    complete = base_inputs()
    all_available = compute_health(*complete[:5], partial=True)
    assert all_available["confidence"] == "medium"


def test_rounding_and_input_order_independence():
    files, edges, cycles, unresolved, metrics = base_inputs()
    a = compute_health(files, edges, cycles, unresolved, metrics, False)
    b = compute_health(files[::-1], edges[::-1], cycles[::-1], unresolved[::-1], metrics, False)
    assert a == b
    assert isinstance(a["score"], float)
