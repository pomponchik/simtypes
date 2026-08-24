from datetime import date, datetime

try:
    from typing import assert_type  # type: ignore[attr-defined, unused-ignore]
except ImportError:  # pragma: no cover
    from typing_extensions import assert_type

import pytest

from simtypes import to_string


@pytest.mark.mypy_testing
def test_to_string_returns_str_for_supported_values():
    """Check statically and at runtime that to_string returns str for every supported category, including non-strict integer-key dictionaries."""
    serialization_results = [
        assert_type(to_string('value'), str),
        assert_type(to_string(1), str),
        assert_type(to_string(1.5), str),
        assert_type(to_string(True), str),
        assert_type(to_string(None), str),
        assert_type(to_string(date(2026, 1, 22)), str),
        assert_type(to_string(datetime(2026, 1, 22, 3, 4, 5)), str),
        assert_type(to_string([1, 2]), str),
        assert_type(to_string((1, 2)), str),
        assert_type(to_string({'key': 1}), str),
        assert_type(to_string({1: 'value'}, strict_json_dict=False), str),
    ]

    assert all(type(serialization_result) is str for serialization_result in serialization_results)
