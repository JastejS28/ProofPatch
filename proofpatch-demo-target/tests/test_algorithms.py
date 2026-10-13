from algorithms import contains_duplicate


def test_duplicate_exists():
    assert contains_duplicate(
        [1, 2, 3, 2]
    ) is True


def test_no_duplicate():
    assert contains_duplicate(
        [1, 2, 3, 4]
    ) is False