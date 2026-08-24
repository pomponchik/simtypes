import pytest

from simtypes import from_string

try:
    from typing import assert_type  # type: ignore[attr-defined, unused-ignore]
except ImportError:  # pragma: no cover
    from typing_extensions import assert_type


@pytest.mark.mypy_testing
def test_none_deserialization_return_types():
    """
    assert_type checks exact return types: None for None and type(None), and int for int.

    Runtime checks confirm the None singleton for both None targets and 1 for int.
    """
    bare_none_result = assert_type(from_string('null', None), None)
    none_type_result = assert_type(from_string('None', type(None)), None)
    int_result = assert_type(from_string('1', int), int)

    assert bare_none_result is None
    assert none_type_result is None
    assert int_result == 1
