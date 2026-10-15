import itertools

import pytest

from projectlens.app.db.task_status import ALLOWED_TRANSITIONS, InvalidTransition, validate_transition


def test_all_ordered_status_pairs_follow_the_transition_matrix():
    statuses = tuple(ALLOWED_TRANSITIONS)
    for source, target in itertools.product(statuses, repeat=2):
        if source == target or target in ALLOWED_TRANSITIONS[source]:
            assert validate_transition(source, target) is None
        else:
            with pytest.raises(InvalidTransition) as raised:
                validate_transition(source, target)
            assert raised.value.from_status == source
            assert raised.value.to_status == target
