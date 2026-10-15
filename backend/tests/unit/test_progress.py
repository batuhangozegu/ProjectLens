import json
import random

import pytest

from projectlens.tracking.progress import (
    PROGRESS_FORMULA_VERSION,
    STATUSES,
    TaskProgressInput,
    compute_progress,
)


@pytest.mark.parametrize(
    ("status", "expected_state", "expected_percent"),
    [
        ("TODO", "not_started", 0.0),
        ("IN_PROGRESS", "in_progress", 0.0),
        ("DONE", "complete", 100.0),
        ("BLOCKED", "not_started", 0.0),
    ],
)
def test_single_status(status, expected_state, expected_percent):
    result = compute_progress([TaskProgressInput(status)])
    assert result.total == 1
    assert result.remaining == (0 if status == "DONE" else 1)
    assert result.counts == {key: int(key == status) for key in STATUSES}
    assert result.completed == int(status == "DONE")
    assert result.state == expected_state
    assert result.percent_complete == expected_percent
    assert result.has_blocked is (status == "BLOCKED")


def test_empty_has_explicit_empty_state_and_null_percent():
    result = compute_progress([])
    assert result.total == result.remaining == result.completed == 0
    assert result.percent_complete is None
    assert result.state == "empty"
    assert result.counts == dict.fromkeys(STATUSES, 0)


def test_all_done_none_done_and_mixed_blocked():
    assert compute_progress([TaskProgressInput("DONE")] * 3).state == "complete"
    none_done = compute_progress([TaskProgressInput("TODO"), TaskProgressInput("BLOCKED")])
    assert none_done.percent_complete == 0.0
    assert none_done.state == "not_started"
    mixed = compute_progress(
        [TaskProgressInput("DONE"), TaskProgressInput("TODO"), TaskProgressInput("BLOCKED")]
    )
    assert mixed.percent_complete == 33.3
    assert mixed.remaining == 2
    assert mixed.has_blocked


def test_in_progress_earns_no_partial_credit():
    result = compute_progress([TaskProgressInput("DONE"), TaskProgressInput("IN_PROGRESS")])
    assert result.percent_complete == 50.0
    assert result.completed == 1


@pytest.mark.parametrize(
    ("done", "total", "expected"),
    [(1, 3, 33.3), (2, 3, 66.7), (1, 8, 12.5), (1, 16, 6.3), (1, 6, 16.7)],
)
def test_exact_half_up_rounding(done, total, expected):
    tasks = [TaskProgressInput("DONE")] * done + [TaskProgressInput("TODO")] * (total - done)
    assert compute_progress(tasks).percent_complete == expected


def test_large_task_count_uses_exact_ratio_before_rounding():
    tasks = [TaskProgressInput("DONE")] * 333_333 + [TaskProgressInput("TODO")] * 666_667
    assert compute_progress(tasks).percent_complete == 33.3


def test_unknown_status_raises_clear_value_error():
    with pytest.raises(ValueError, match="Unknown task status 'PENDING'.*TODO.*BLOCKED"):
        compute_progress([TaskProgressInput("PENDING")])


def test_breakdowns_sort_labels_and_put_missing_label_last():
    result = compute_progress(
        [
            TaskProgressInput("DONE", category="zeta", section="Part 2"),
            TaskProgressInput("TODO", category=None, section=None),
            TaskProgressInput("BLOCKED", category="alpha", section="Part 1"),
            TaskProgressInput("IN_PROGRESS", category="alpha", section="Part 1"),
        ]
    )
    assert list(result.breakdown_by_category) == ["alpha", "zeta", "(uncategorized)"]
    assert list(result.breakdown_by_section) == ["Part 1", "Part 2", "(no section)"]
    assert result.breakdown_by_category["alpha"].counts["BLOCKED"] == 1
    assert result.breakdown_by_category["(uncategorized)"].total == 1
    assert result.breakdown_by_section["(no section)"].total == 1


def test_to_dict_json_safe_versioned_and_input_order_independent():
    tasks = [
        TaskProgressInput("DONE", "b", "S2"),
        TaskProgressInput("BLOCKED", None, "S1"),
        TaskProgressInput("IN_PROGRESS", "a", None),
    ]
    first = compute_progress(tasks).to_dict()
    assert first["formula_version"] == PROGRESS_FORMULA_VERSION == "1"
    assert json.loads(json.dumps(first)) == first
    shuffled = list(tasks)
    random.Random(19).shuffle(shuffled)
    assert compute_progress(shuffled).to_dict() == first


def test_accepts_generator_without_mutating_items():
    source = (TaskProgressInput(status) for status in ("DONE", "TODO"))
    assert compute_progress(source).total == 2
