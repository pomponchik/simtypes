import pytest

from simtypes import check


@pytest.mark.mypy_testing
def test_basic_positives() -> None:
    """Static typing accepts simple matching int and str check calls, and the runtime results are true."""
    assert check(5, int)
    assert check("kek", str)


@pytest.mark.mypy_testing
def test_positive_with_users_class() -> None:
    """Static typing accepts a locally defined class hint, and the runtime check is true for its instance."""
    class SomeClass:
        pass

    assert check(SomeClass(), SomeClass)


@pytest.mark.mypy_testing
def test_negative_with_users_class() -> None:
    """
    A non-instance value can be passed with a local class hint without a static typing error.

    The false runtime result is intentionally not asserted here.
    """
    class SomeClass:
        pass

    check(5, SomeClass)
