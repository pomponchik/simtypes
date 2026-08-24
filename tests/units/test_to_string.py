import json
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple, Type, Union

import pytest
from full_match import match
from hypothesis import example, given, settings, strategies

from simtypes import NonRoundTrippableKeyError, from_string, to_string


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('', '', id='empty-string'),
        pytest.param('Hello, ☃!', 'Hello, ☃!', id='unicode-string'),
        pytest.param('\ud800', '\ud800', id='high-surrogate-string'),
        pytest.param('\udfff', '\udfff', id='low-surrogate-string'),
        pytest.param(0, '0', id='zero-int'),
        pytest.param(-13, '-13', id='negative-int'),
        pytest.param(13.5, '13.5', id='finite-float'),
        pytest.param(1.0, '1.0', id='integral-float'),
        pytest.param(-0.0, '-0.0', id='negative-zero'),
        pytest.param(float('nan'), 'nan', id='nan'),
        pytest.param(float('inf'), 'inf', id='positive-infinity'),
        pytest.param(float('-inf'), '-inf', id='negative-infinity'),
        pytest.param(True, 'True', id='true'),
        pytest.param(False, 'False', id='false'),
        pytest.param(None, 'None', id='none'),
        pytest.param(date(2026, 1, 22), '2026-01-22', id='date'),
        pytest.param(datetime(2026, 1, 22, 3, 4, 5, 6), '2026-01-22T03:04:05.000006', id='naive-datetime'),
        pytest.param(
            datetime(2026, 1, 22, 3, 4, 5, tzinfo=timezone(timedelta(hours=3))),
            '2026-01-22T03:04:05+03:00',
            id='aware-datetime',
        ),
    ],
)
@pytest.mark.parametrize('strict_json_dict', [True, False], ids=('strict', 'non-strict'))
def test_serialize_scalar(
    value: Union[str, int, float, bool, None, date, datetime],
    expected: str,
    strict_json_dict: bool,
):
    """Serialize scalars canonically under both dictionary-key policies."""
    serialized = to_string(value, strict_json_dict=strict_json_dict)

    assert type(serialized) is str
    assert serialized == expected


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param([], '[]', id='empty-list'),
        pytest.param((), '[]', id='empty-tuple'),
        pytest.param({}, '{}', id='empty-dict'),
        pytest.param([1, 'two', True, None], '[1, "two", true, null]', id='mixed-list'),
        pytest.param((1, ('two', 3)), '[1, ["two", 3]]', id='nested-tuple'),
        pytest.param({'snowman ☃': '"line\n'}, r'{"snowman \u2603": "\"line\n"}', id='escaping'),
        pytest.param(['\ud800', '\udfff'], r'["\ud800", "\udfff"]', id='surrogate-strings'),
        pytest.param({'second': 2, 'first': 1}, '{"second": 2, "first": 1}', id='dict-order'),
        pytest.param({'items': [1, {'ok': False}]}, '{"items": [1, {"ok": false}]}', id='nested-dict'),
    ],
)
def test_serialize_json_dumps_compatible_collection(
    value: Union[List[object], Tuple[object, ...], Dict[str, object]],
    expected: str,
):
    """Serialize representative json.dumps-compatible collections to exact JSON text."""
    assert to_string(value) == expected


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param([date(2026, 1, 22)], '["2026-01-22"]', id='date-in-list'),
        pytest.param((datetime(2026, 1, 22, 3, 4, 5),), '["2026-01-22T03:04:05"]', id='datetime-in-tuple'),
        pytest.param({'date': date(2026, 1, 22)}, '{"date": "2026-01-22"}', id='date-in-dict'),
        pytest.param(
            {'values': [(date(2026, 1, 22), datetime(2026, 1, 22, 3, 4, 5))]},
            '{"values": [["2026-01-22", "2026-01-22T03:04:05"]]}',
            id='deeply-nested',
        ),
        pytest.param(
            [
                datetime(
                    2026,
                    1,
                    22,
                    3,
                    4,
                    5,
                    6789,
                    tzinfo=timezone(timedelta(microseconds=1)),
                ),
            ],
            '["2026-01-22T03:04:05.006789+00:00:00.000001"]',
            id='aware-datetime-with-subsecond-offset',
        ),
    ],
)
def test_serialize_nested_temporal_values(
    value: Union[List[object], Tuple[object, ...], Dict[str, object]],
    expected: str,
):
    """Encode dates and datetimes nested in collections as quoted ISO strings."""
    assert to_string(value) == expected


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param([None], '[null]', id='list'),
        pytest.param((None,), '[null]', id='tuple'),
        pytest.param({'value': None}, '{"value": null}', id='dict'),
        pytest.param([{'value': (None,)}], '[{"value": [null]}]', id='nested'),
    ],
)
def test_none_serializes_as_null_only_inside_collections(
    value: Union[List[object], Tuple[object, ...], Dict[str, object]],
    expected: str,
):
    """Distinguish top-level None from JSON null inside every supported collection."""
    top_level_text = to_string(None)
    nested_text = to_string(value)

    assert top_level_text == 'None'
    assert nested_text == expected
    assert nested_text != top_level_text


@given(data=strategies.data())
@settings(max_examples=200, deadline=None)
def test_json_dumps_compatible_output_matches_json_dumps(data: strategies.DataObject):
    """Match json.dumps output exactly across generated json.dumps-compatible collection trees."""
    scalars = strategies.one_of(strategies.none(), strategies.booleans(), strategies.integers(), strategies.floats(), strategies.text())
    values = strategies.recursive(
        scalars,
        lambda children: strategies.one_of(
            strategies.lists(children, max_size=5),
            strategies.lists(children, max_size=5).map(tuple),
            strategies.dictionaries(strategies.text(), children, max_size=5),
        ),
        max_leaves=20,
    )
    collections = strategies.one_of(
        strategies.lists(values, max_size=8),
        strategies.lists(values, max_size=8).map(tuple),
        strategies.dictionaries(strategies.text(), values, max_size=8),
    )
    value = data.draw(collections)

    assert to_string(value) == json.dumps(value)


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param({}, '{}', id='empty'),
        pytest.param({'key': 'value'}, '{"key": "value"}', id='simple'),
        pytest.param({'outer': {'inner': 1}}, '{"outer": {"inner": 1}}', id='nested'),
    ],
)
def test_strict_json_dict_accepts_string_keys(value: Dict[str, object], expected: str):
    """Accept empty, flat, and nested dictionaries whose keys are exact strings."""
    assert to_string(value) == expected


@pytest.mark.parametrize(
    'key',
    [
        pytest.param(1, id='int'),
        pytest.param(1.5, id='float'),
        pytest.param(True, id='bool'),
        pytest.param(None, id='none'),
    ],
)
@pytest.mark.parametrize('invalid_first', [True, False], ids=('invalid-first', 'invalid-last'))
def test_strict_json_dict_rejects_supported_non_string_keys(
    key: Union[int, float, bool, None],
    invalid_first: bool,
):
    """Raise NonRoundTrippableKeyError for each supported non-string key type before and after a valid key."""
    message = (
        f'Dictionary key {key!r} of type {type(key).__name__} cannot be serialized without changing its type. '
        'Pass strict_json_dict=False to allow lossy serialization.'
    )

    dictionary = {key: 'value', 'valid': 'value'} if invalid_first else {'valid': 'value', key: 'value'}

    with pytest.raises(NonRoundTrippableKeyError, match=match(message)) as exception_info:
        to_string(dictionary)

    assert type(exception_info.value) is NonRoundTrippableKeyError


@pytest.mark.parametrize('invalid_first', [True, False], ids=('invalid-first', 'invalid-last'))
@pytest.mark.parametrize(
    ('deeply_nested', 'key'),
    [
        pytest.param(False, 1, id='one-level'),
        pytest.param(True, 1.5, id='deep'),
    ],
)
def test_strict_json_dict_rejects_nested_lossy_keys(
    deeply_nested: bool,
    key: Union[int, float],
    invalid_first: bool,
):
    """Reject and identify lossy keys in shallow and deeply nested dictionaries, regardless of insertion position."""
    message = (
        f'Dictionary key {key!r} of type {type(key).__name__} cannot be serialized without changing its type. '
        'Pass strict_json_dict=False to allow lossy serialization.'
    )
    dictionary = {key: 'value', 'valid': 'value'} if invalid_first else {'valid': 'value', key: 'value'}
    value = [{'outer': ({'inner': dictionary},)}] if deeply_nested else {'outer': dictionary}

    with pytest.raises(NonRoundTrippableKeyError, match=match(message)):
        to_string(value)


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param({1: 'value'}, '{"1": "value"}', id='int'),
        pytest.param({1.5: 'value'}, '{"1.5": "value"}', id='float'),
        pytest.param({1.0: 'value'}, '{"1.0": "value"}', id='integral-float'),
        pytest.param({-0.0: 'value'}, '{"-0.0": "value"}', id='negative-zero-float'),
        pytest.param({float('nan'): 'value'}, '{"NaN": "value"}', id='nan-float'),
        pytest.param({float('inf'): 'value'}, '{"Infinity": "value"}', id='positive-infinity-float'),
        pytest.param({float('-inf'): 'value'}, '{"-Infinity": "value"}', id='negative-infinity-float'),
        pytest.param({True: 'value'}, '{"true": "value"}', id='bool'),
        pytest.param({False: 'value'}, '{"false": "value"}', id='false-bool'),
        pytest.param({None: 'value'}, '{"null": "value"}', id='none'),
        pytest.param({'outer': {1: 'value'}}, '{"outer": {"1": "value"}}', id='nested'),
        pytest.param([({1: 'value'},)], '[[{"1": "value"}]]', id='nested-through-list-and-tuple'),
    ],
)
def test_non_strict_json_dict_accepts_lossy_keys_recursively(
    value: Union[
        List[object],
        Dict[Union[str, int, float, bool, None], object],
    ],
    expected: str,
):
    """Serialize all native lossy root-key types and integer keys through nested collection layers."""
    assert to_string(value, strict_json_dict=False) == expected


@given(strategies.one_of(strategies.integers(), strategies.floats(), strategies.booleans(), strategies.none()))
@settings(max_examples=200, deadline=None)
def test_non_strict_json_dict_key_format_matches_canonical_form(
    key: Union[int, float, bool, None],
):
    """Match json.dumps names for generated numeric, boolean, and None keys."""
    expected = json.dumps({'valid': 'value', key: 'lossy'})

    assert to_string({'valid': 'value', key: 'lossy'}, strict_json_dict=False) == expected


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param({1: 'int', '1': 'string'}, '{"1": "int", "1": "string"}', id='int-and-string'),
        pytest.param({'1': 'string', 1: 'int'}, '{"1": "string", "1": "int"}', id='string-and-int'),
        pytest.param(
            {1.0: 'float', '1.0': 'string'},
            '{"1.0": "float", "1.0": "string"}',
            id='float-and-string',
        ),
        pytest.param(
            {-0.0: 'float', '-0.0': 'string'},
            '{"-0.0": "float", "-0.0": "string"}',
            id='negative-zero-and-string',
        ),
        pytest.param(
            {float('nan'): 'float', 'NaN': 'string'},
            '{"NaN": "float", "NaN": "string"}',
            id='nan-and-string',
        ),
        pytest.param(
            {float('inf'): 'float', 'Infinity': 'string'},
            '{"Infinity": "float", "Infinity": "string"}',
            id='positive-infinity-and-string',
        ),
        pytest.param(
            {float('-inf'): 'float', '-Infinity': 'string'},
            '{"-Infinity": "float", "-Infinity": "string"}',
            id='negative-infinity-and-string',
        ),
        pytest.param(
            {True: 'bool', 'true': 'string'},
            '{"true": "bool", "true": "string"}',
            id='true-and-string',
        ),
        pytest.param(
            {False: 'bool', 'false': 'string'},
            '{"false": "bool", "false": "string"}',
            id='false-and-string',
        ),
        pytest.param(
            {None: 'none', 'null': 'string'},
            '{"null": "none", "null": "string"}',
            id='none-and-string',
        ),
        pytest.param(
            {'outer': {1: 'int', '1': 'string'}},
            '{"outer": {"1": "int", "1": "string"}}',
            id='nested-int-and-string',
        ),
    ],
)
def test_non_strict_json_dict_allows_canonical_collisions(
    value: Dict[Union[str, int, float, bool, None], object],
    expected: str,
):
    """Preserve insertion order when distinct Python keys yield duplicate JSON property names, including in nested dictionaries."""
    assert to_string(value, strict_json_dict=False) == expected


def test_integer_key_does_not_round_trip_in_non_strict_mode():
    """After non-strict serialization, reject int restoration and restore the dictionary key as str."""
    value = {1: 'value'}

    serialized = to_string(value, strict_json_dict=False)
    message = 'The string "{"1": "value"}" cannot be interpreted as a dict of the specified format.'

    with pytest.raises(TypeError, match=match(message)) as exception_info:
        from_string(serialized, Dict[int, str])

    assert type(exception_info.value) is TypeError

    restored = from_string(serialized, Dict[str, str])

    assert restored == {'1': 'value'}
    assert type(next(iter(restored))) is str
    assert restored != value


@pytest.mark.parametrize(
    'key_case',
    [
        'date',
        'datetime',
        'tuple',
        'custom-hashable',
        'string-subclass',
        'int-subclass',
        'float-subclass',
        'date-subclass',
        'datetime-subclass',
        'deceptive-bool',
        'deceptive-none',
    ],
)
@pytest.mark.parametrize('strict_json_dict', [True, False], ids=('strict', 'non-strict'))
@pytest.mark.parametrize('nested', [False, True], ids=('top-level', 'nested'))
@pytest.mark.parametrize('invalid_first', [True, False], ids=('invalid-first', 'invalid-last'))
def test_json_dict_rejects_unsupported_keys_at_any_depth_in_both_modes(
    key_case: str,
    strict_json_dict: bool,
    nested: bool,
    invalid_first: bool,
):
    """Raise built-in TypeError for representative unsupported keys across both policies, insertion positions, and tested depths."""
    class HashableObject:
        ...

    class EqualToBaseMeta(type):
        _equal_type: Type[object]

        def __eq__(cls, other: object) -> bool:
            return other is cls._equal_type

        def __hash__(cls) -> int:
            return hash(cls._equal_type)

    class StringSubclass(str, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        __slots__ = ()
        _equal_type = str

    class IntSubclass(int, metaclass=EqualToBaseMeta):
        _equal_type = int

    class FloatSubclass(float, metaclass=EqualToBaseMeta):
        _equal_type = float

    class DateSubclass(date, metaclass=EqualToBaseMeta):
        _equal_type = date

    class DatetimeSubclass(datetime, metaclass=EqualToBaseMeta):
        _equal_type = datetime

    class DeceptiveBool(metaclass=EqualToBaseMeta):
        _equal_type = bool

    class DeceptiveNone(metaclass=EqualToBaseMeta):
        _equal_type = type(None)

    keys = {
        'date': date(2026, 1, 22),
        'datetime': datetime(2026, 1, 22, 3, 4, 5),
        'tuple': (1, 2),
        'custom-hashable': HashableObject(),
        'string-subclass': StringSubclass('key'),
        'int-subclass': IntSubclass(7),
        'float-subclass': FloatSubclass(1.5),
        'date-subclass': DateSubclass(2026, 1, 22),
        'datetime-subclass': DatetimeSubclass(2026, 1, 22, 3, 4, 5),
        'deceptive-bool': DeceptiveBool(),
        'deceptive-none': DeceptiveNone(),
    }
    key = keys[key_case]
    message = f'Dictionary key {key!r} of type {type(key).__name__} cannot be serialized to JSON.'
    dictionary = {key: 'value', 'valid': 'value'} if invalid_first else {'valid': 'value', key: 'value'}
    value = [{'outer': (dictionary,)}] if nested else dictionary

    with pytest.raises(TypeError, match=match(message)) as exception_info:
        to_string(value, strict_json_dict=strict_json_dict)

    assert type(exception_info.value) is TypeError


def test_strict_json_dict_is_keyword_only():
    """Require strict_json_dict to be keyword-only."""
    with pytest.raises(
        TypeError,
        match=match('to_string() takes 1 positional argument but 2 were given'),
    ):
        to_string({}, False)  # type: ignore[misc]


@pytest.mark.parametrize(
    'flag_case',
    [
        'zero-int',
        'one-int',
        'none',
        'string',
        'deceptive-bool',
    ],
)
@pytest.mark.parametrize('value', [1, {'key': 'value'}], ids=('scalar', 'dict'))
def test_strict_json_dict_must_be_bool(
    value: Union[int, Dict[str, str]],
    flag_case: str,
):
    """Require strict_json_dict to be an exact bool for scalar and dictionary inputs."""
    class EqualToBoolMeta(type):
        def __eq__(cls, other: object) -> bool:
            return other is bool

        def __hash__(cls) -> int:
            return hash(bool)

    class DeceptiveBool(metaclass=EqualToBoolMeta):
        ...

    invalid_flags = {
        'zero-int': 0,
        'one-int': 1,
        'none': None,
        'string': 'false',
        'deceptive-bool': DeceptiveBool(),
    }

    with pytest.raises(TypeError, match=match('strict_json_dict must be a bool.')):
        to_string(value, strict_json_dict=invalid_flags[flag_case])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    'value_case',
    [
        'set',
        'bytes',
        'object',
        'str-subclass',
        'int-subclass',
        'float-subclass',
        'date-subclass',
        'datetime-subclass',
        'list-subclass',
        'tuple-subclass',
        'dict-subclass',
        'deceptive-bool',
        'deceptive-none',
    ],
)
@pytest.mark.parametrize('strict_json_dict', [True, False], ids=('strict', 'non-strict'))
def test_to_string_rejects_unsupported_top_level_value(value_case: str, strict_json_dict: bool):
    """Reject unsupported top-level values under both key policies."""
    class EqualToBaseMeta(type):
        _equal_type: Type[object]

        def __eq__(cls, other: object) -> bool:
            return other is cls._equal_type

        def __hash__(cls) -> int:
            return hash(cls._equal_type)

    class StringSubclass(str, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        __slots__ = ()
        _equal_type = str

    class IntSubclass(int, metaclass=EqualToBaseMeta):
        _equal_type = int

    class FloatSubclass(float, metaclass=EqualToBaseMeta):
        _equal_type = float

    class DateSubclass(date, metaclass=EqualToBaseMeta):
        _equal_type = date

    class DatetimeSubclass(datetime, metaclass=EqualToBaseMeta):
        _equal_type = datetime

    class ListSubclass(list, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        _equal_type = list

    class TupleSubclass(tuple, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        __slots__ = ()
        _equal_type = tuple

    class DictSubclass(dict, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        _equal_type = dict

    class DeceptiveBool(metaclass=EqualToBaseMeta):
        _equal_type = bool

    class DeceptiveNone(metaclass=EqualToBaseMeta):
        _equal_type = type(None)

    values = {
        'set': {1, 2},
        'bytes': b'bytes',
        'object': object(),
        'str-subclass': StringSubclass('value'),
        'int-subclass': IntSubclass(1),
        'float-subclass': FloatSubclass(1.5),
        'date-subclass': DateSubclass(2026, 1, 22),
        'datetime-subclass': DatetimeSubclass(2026, 1, 22, 3, 4, 5),
        'list-subclass': ListSubclass([1]),
        'tuple-subclass': TupleSubclass((1,)),
        'dict-subclass': DictSubclass({'key': 'value'}),
        'deceptive-bool': DeceptiveBool(),
        'deceptive-none': DeceptiveNone(),
    }
    value = values[value_case]
    message = (
        f'Serialization of the type {type(value).__name__} is not supported. '
        'Supported types: str, int, float, bool, NoneType, date, datetime, list, tuple, dict.'
    )

    with pytest.raises(TypeError, match=match(message)) as exception_info:
        to_string(value, strict_json_dict=strict_json_dict)

    assert type(exception_info.value) is TypeError


@pytest.mark.parametrize(
    'value_case',
    [
        'list-invalid-first',
        'list',
        'tuple-invalid-first',
        'tuple',
        'dict-invalid-first',
        'dict',
        'deep-invalid-first',
        'deep',
        'int-subclass',
        'float-subclass',
        'date-subclass',
        'datetime-subclass',
        'list-subclass',
        'tuple-subclass',
        'dict-subclass',
        'deceptive-bool',
        'deceptive-none',
    ],
)
@pytest.mark.parametrize('strict_json_dict', [True, False], ids=('strict', 'non-strict'))
def test_to_string_rejects_nested_unsupported_type(
    value_case: str,
    strict_json_dict: bool,
):
    """Reject unsupported nested values in either mode and name their exact type."""
    class EqualToBaseMeta(type):
        _equal_type: Type[object]

        def __eq__(cls, other: object) -> bool:
            return other is cls._equal_type

        def __hash__(cls) -> int:
            return hash(cls._equal_type)

    class StringSubclass(str, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        __slots__ = ()
        _equal_type = str

    class IntSubclass(int, metaclass=EqualToBaseMeta):
        _equal_type = int

    class FloatSubclass(float, metaclass=EqualToBaseMeta):
        _equal_type = float

    class DateSubclass(date, metaclass=EqualToBaseMeta):
        _equal_type = date

    class DatetimeSubclass(datetime, metaclass=EqualToBaseMeta):
        _equal_type = datetime

    class ListSubclass(list, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        _equal_type = list

    class TupleSubclass(tuple, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        __slots__ = ()
        _equal_type = tuple

    class DictSubclass(dict, metaclass=EqualToBaseMeta):  # type: ignore[misc]
        _equal_type = dict

    class DeceptiveBool(metaclass=EqualToBaseMeta):
        _equal_type = bool

    class DeceptiveNone(metaclass=EqualToBaseMeta):
        _equal_type = type(None)

    cases = {
        'list-invalid-first': ([{1, 2}, 'valid'], 'set'),
        'list': (['valid', {1, 2}], 'set'),
        'tuple-invalid-first': ((b'bytes', 'valid'), 'bytes'),
        'tuple': (('valid', b'bytes'), 'bytes'),
        'dict-invalid-first': ({'invalid': object(), 'valid': 'value'}, 'object'),
        'dict': ({'valid': 'value', 'invalid': object()}, 'object'),
        'deep-invalid-first': (
            {'outer': [{'invalid': StringSubclass('nested'), 'valid': 'value'}]},
            'StringSubclass',
        ),
        'deep': (
            {'outer': [{'valid': 'value', 'invalid': StringSubclass('nested')}]},
            'StringSubclass',
        ),
        'int-subclass': ([0, IntSubclass(7)], 'IntSubclass'),
        'float-subclass': ((0.0, FloatSubclass(1.5)), 'FloatSubclass'),
        'date-subclass': ([date(2025, 1, 1), DateSubclass(2026, 1, 22)], 'DateSubclass'),
        'datetime-subclass': (
            {'valid': datetime(2025, 1, 1), 'invalid': DatetimeSubclass(2026, 1, 22, 3, 4, 5)},
            'DatetimeSubclass',
        ),
        'list-subclass': ([[], ListSubclass([1])], 'ListSubclass'),
        'tuple-subclass': ({'valid': (), 'invalid': TupleSubclass((1,))}, 'TupleSubclass'),
        'dict-subclass': (({}, DictSubclass({'key': 'value'})), 'DictSubclass'),
        'deceptive-bool': ([False, DeceptiveBool()], 'DeceptiveBool'),
        'deceptive-none': ([None, DeceptiveNone()], 'DeceptiveNone'),
    }
    value, unsupported_type_name = cases[value_case]
    message = (
        f'Serialization of the type {unsupported_type_name} is not supported. '
        'Supported types: str, int, float, bool, NoneType, date, datetime, list, tuple, dict.'
    )

    with pytest.raises(TypeError, match=match(message)) as exception_info:
        to_string(value, strict_json_dict=strict_json_dict)

    assert type(exception_info.value) is TypeError


def test_public_to_string_api():
    """Expose callable to_string and NonRoundTrippableKeyError as a distinct TypeError subclass."""
    from simtypes.errors import (  # noqa: PLC0415
        NonRoundTrippableKeyError as NonRoundTrippableKeyErrorFromModule,
    )

    assert callable(to_string)
    assert NonRoundTrippableKeyErrorFromModule is NonRoundTrippableKeyError
    assert NonRoundTrippableKeyError is not TypeError
    assert issubclass(NonRoundTrippableKeyError, TypeError)


@given(
    strategies.one_of(
        strategies.tuples(strategies.text(), strategies.just(str)),
        strategies.tuples(strategies.integers(), strategies.just(int)),
        strategies.tuples(strategies.floats(), strategies.just(float)),
        strategies.tuples(strategies.booleans(), strategies.just(bool)),
        strategies.tuples(strategies.none(), strategies.sampled_from((None, type(None)))),
        strategies.tuples(strategies.dates(), strategies.just(date)),
        strategies.tuples(
            strategies.datetimes(
                timezones=strategies.one_of(
                    strategies.none(),
                    strategies.builds(
                        timezone,
                        strategies.builds(
                            timedelta,
                            microseconds=strategies.one_of(
                                strategies.just(0),
                                strategies.integers(min_value=-86_399_999_999, max_value=-1_000_000),
                                strategies.integers(min_value=1_000_000, max_value=86_399_999_999),
                            ),
                        ),
                    ),
                ),
            ),
            strategies.just(datetime),
        ),
    ),
)
@example(('\ud800', str))
@example(('\udfff', str))
@example((None, None))
@example((None, type(None)))
@example((-0.0, float))
@example((float('inf'), float))
@example((float('-inf'), float))
@example((float('nan'), float))
@example((datetime(2026, 1, 22, 3, 4, 5, tzinfo=timezone(timedelta(hours=3))), datetime))
@example((datetime(2026, 1, 22, 3, 4, 5, fold=1), datetime))
@settings(max_examples=200, deadline=None)
def test_round_trippable_scalar_values_serialize_canonically_and_round_trip(case):
    """Require canonical scalar text and exact-type round trips under NaN, signed-zero, and datetime equivalence rules."""
    value, expected_type = case
    serialized = to_string(value)

    if type(value) is date or type(value) is datetime:
        canonical_text = value.isoformat()
    else:
        canonical_text = str(value)

    restored = from_string(serialized, expected_type)

    assert serialized == canonical_text
    assert type(restored) is type(value)

    if type(value) is float:
        if math.isnan(value):
            assert math.isnan(restored)
        else:
            assert restored == value
        if value == 0.0:
            assert math.copysign(1.0, restored) == math.copysign(1.0, value)
    elif type(value) is datetime:
        value_fields = (
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
        )
        restored_fields = (
            restored.year,
            restored.month,
            restored.day,
            restored.hour,
            restored.minute,
            restored.second,
            restored.microsecond,
        )
        assert restored_fields == value_fields
        assert restored.utcoffset() == value.utcoffset()
    else:
        assert restored == value


def test_datetime_round_trip_preserves_fields_and_offset_but_loses_tzinfo_identity_name_and_fold():
    """Preserve datetime fields and UTC offset, but not fold, tzinfo identity, or tzinfo name."""
    original_timezone = timezone(timedelta(hours=3), 'named timezone')
    value = datetime(2026, 1, 22, 3, 4, 5, 6789, tzinfo=original_timezone, fold=1)

    restored = from_string(to_string(value), datetime)

    assert type(restored) is datetime
    assert restored.replace(tzinfo=None) == value.replace(tzinfo=None)
    assert restored.utcoffset() == value.utcoffset()
    assert restored.tzinfo is not original_timezone
    assert value.tzname() == 'named timezone'
    assert restored.tzname() == 'UTC+03:00'
    assert restored.fold == 0


@pytest.mark.parametrize('offset_microseconds', [1, 999_999, -1, -999_999])
def test_datetime_subsecond_offset_serializes_exactly_but_does_not_round_trip(
    offset_microseconds: int,
):
    """Serialize nonzero subsecond UTC offsets exactly; from_string preserves wall time but sets the offset to zero."""
    value = datetime(
        2026,
        1,
        22,
        3,
        4,
        5,
        tzinfo=timezone(timedelta(microseconds=offset_microseconds)),
    )

    serialized = to_string(value)
    restored = from_string(serialized, datetime)

    assert serialized == value.isoformat()
    assert restored.replace(tzinfo=None) == value.replace(tzinfo=None)
    assert value.utcoffset() == timedelta(microseconds=offset_microseconds)
    assert restored.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    'temporal_value',
    [
        pytest.param(date(2026, 1, 22), id='date'),
        pytest.param(
            datetime(2026, 1, 22, 3, 4, 5, 6789, tzinfo=timezone(timedelta(hours=3))),
            id='datetime',
        ),
    ],
)
def test_temporal_values_round_trip_in_every_collection(
    temporal_value: Union[date, datetime],
    subscribable_list_type,
    subscribable_tuple_type,
    subscribable_dict_type,
):
    """Round-trip exact date and datetime values through every typing and built-in collection annotation."""
    temporal_type = type(temporal_value)
    cases = (
        ([temporal_value], subscribable_list_type[temporal_type]),
        ((temporal_value,), subscribable_tuple_type[temporal_type, ...]),
        ({'value': temporal_value}, subscribable_dict_type[str, temporal_type]),
    )

    for value, expected_type in cases:
        restored = from_string(to_string(value), expected_type)

        assert type(restored) is type(value)
        assert len(restored) == len(value)

        if type(value) is dict:
            assert list(restored) == list(value)
            assert type(next(iter(restored))) is str
            restored_temporal_value = restored['value']
        else:
            restored_temporal_value = restored[0]

        assert type(restored_temporal_value) is type(temporal_value)

        if type(temporal_value) is datetime:
            temporal_fields = (
                temporal_value.year,
                temporal_value.month,
                temporal_value.day,
                temporal_value.hour,
                temporal_value.minute,
                temporal_value.second,
                temporal_value.microsecond,
            )
            restored_fields = (
                restored_temporal_value.year,
                restored_temporal_value.month,
                restored_temporal_value.day,
                restored_temporal_value.hour,
                restored_temporal_value.minute,
                restored_temporal_value.second,
                restored_temporal_value.microsecond,
            )
            assert restored_fields == temporal_fields
            assert restored_temporal_value.utcoffset() == temporal_value.utcoffset()
        else:
            assert restored_temporal_value == temporal_value


@given(data=strategies.data())
@settings(max_examples=200, deadline=None)
def test_recursive_collection_round_trip_is_independent_of_key_policy(  # noqa: C901, PLR0915
    data: strategies.DataObject,
):
    """Round-trip generated collection trees with identical text under both key policies."""
    offset_microseconds = strategies.one_of(
        strategies.just(0),
        strategies.integers(min_value=-86_399_999_999, max_value=-1_000_000),
        strategies.integers(min_value=1_000_000, max_value=86_399_999_999),
    )
    fixed_timezones = offset_microseconds.map(
        lambda microseconds: timezone(timedelta(microseconds=microseconds)),
    )
    scalar_value_strategies = {
        'str': strategies.text(),
        'int': strategies.integers(),
        'float': strategies.floats(),
        'bool': strategies.booleans(),
        'none': strategies.none(),
        'date': strategies.dates(),
        'datetime': strategies.datetimes(timezones=strategies.one_of(strategies.none(), fixed_timezones)),
    }

    def values_for_spec(spec) -> strategies.SearchStrategy[object]:
        """Build a value strategy recursively from a generated type specification."""
        if isinstance(spec, str):
            return scalar_value_strategies[spec]

        kind = spec[0]
        if kind == 'list':
            return strategies.lists(values_for_spec(spec[1]), max_size=5)
        if kind == 'tuple':
            return strategies.lists(values_for_spec(spec[1]), max_size=5).map(tuple)
        if kind == 'dict':
            return strategies.dictionaries(strategies.text(), values_for_spec(spec[1]), max_size=5)
        return strategies.tuples(values_for_spec(spec[1]), values_for_spec(spec[2]))

    def annotation_for_spec(spec):
        """Build a precise annotation recursively from a generated type specification."""
        scalar_annotations = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'none': type(None),
            'date': date,
            'datetime': datetime,
        }
        if spec in scalar_annotations:
            return scalar_annotations[spec]

        kind = spec[0]
        if kind == 'list':
            return List[annotation_for_spec(spec[1])]  # type: ignore[misc]
        if kind == 'tuple':
            return Tuple[annotation_for_spec(spec[1]), ...]
        if kind == 'dict':
            return Dict[str, annotation_for_spec(spec[1])]  # type: ignore[misc]
        return Tuple[annotation_for_spec(spec[1]), annotation_for_spec(spec[2])]  # type: ignore[misc]

    def assert_round_trip_equivalent(expected, actual):
        """Compare round-trip values recursively using the contract's exact-type rules."""
        assert type(actual) is type(expected)

        if type(expected) is float:
            if math.isnan(expected):
                assert math.isnan(actual)
            else:
                assert actual == expected
            if expected == 0.0:
                assert math.copysign(1.0, actual) == math.copysign(1.0, expected)
            return

        if type(expected) is datetime:
            expected_fields = (
                expected.year,
                expected.month,
                expected.day,
                expected.hour,
                expected.minute,
                expected.second,
                expected.microsecond,
            )
            actual_fields = (
                actual.year,
                actual.month,
                actual.day,
                actual.hour,
                actual.minute,
                actual.second,
                actual.microsecond,
            )
            assert actual_fields == expected_fields
            assert actual.utcoffset() == expected.utcoffset()
            return

        if type(expected) in (list, tuple):
            assert len(actual) == len(expected)
            for expected_element, actual_element in zip(expected, actual):
                assert_round_trip_equivalent(expected_element, actual_element)
            return

        if type(expected) is dict:
            assert list(actual) == list(expected)
            for key in expected:
                assert type(next(actual_key for actual_key in actual if actual_key == key)) is type(key)
                assert_round_trip_equivalent(expected[key], actual[key])
            return

        assert actual == expected

    scalar_specs = strategies.sampled_from(('str', 'int', 'float', 'bool', 'none', 'date', 'datetime'))
    type_specs = strategies.recursive(
        scalar_specs,
        lambda children: strategies.one_of(
            strategies.tuples(strategies.just('list'), children),
            strategies.tuples(strategies.just('tuple'), children),
            strategies.tuples(strategies.just('dict'), children),
            strategies.tuples(strategies.just('fixed_tuple'), children, children),
        ),
        max_leaves=8,
    )
    spec = data.draw(type_specs.filter(lambda candidate: isinstance(candidate, tuple)))
    value = data.draw(values_for_spec(spec))
    expected_type = annotation_for_spec(spec)

    serialized = to_string(value)
    assert to_string(value, strict_json_dict=False) == serialized

    restored = from_string(serialized, expected_type)
    assert_round_trip_equivalent(value, restored)


@given(data=strategies.data())
@settings(max_examples=200, deadline=None)
def test_dicts_with_exact_str_keys_round_trip(data: strategies.DataObject):  # noqa: C901
    """Round-trip generated dictionaries whose keys have exact type str using a precise recursive annotation for their values."""
    offset_microseconds = strategies.one_of(
        strategies.just(0),
        strategies.integers(min_value=-86_399_999_999, max_value=-1_000_000),
        strategies.integers(min_value=1_000_000, max_value=86_399_999_999),
    )
    fixed_timezones = offset_microseconds.map(
        lambda microseconds: timezone(timedelta(microseconds=microseconds)),
    )
    scalar_value_strategies = {
        'str': strategies.text(),
        'int': strategies.integers(),
        'float': strategies.floats(),
        'bool': strategies.booleans(),
        'none': strategies.none(),
        'date': strategies.dates(),
        'datetime': strategies.datetimes(timezones=strategies.one_of(strategies.none(), fixed_timezones)),
    }

    def values_for_spec(spec) -> strategies.SearchStrategy[object]:
        """Build a value strategy recursively from a generated type specification."""
        if isinstance(spec, str):
            return scalar_value_strategies[spec]

        kind = spec[0]
        if kind == 'list':
            return strategies.lists(values_for_spec(spec[1]), max_size=5)
        if kind == 'tuple':
            return strategies.lists(values_for_spec(spec[1]), max_size=5).map(tuple)
        if kind == 'dict':
            return strategies.dictionaries(strategies.text(), values_for_spec(spec[1]), max_size=5)
        return strategies.tuples(values_for_spec(spec[1]), values_for_spec(spec[2]))

    def annotation_for_spec(spec):
        """Build a precise annotation recursively from a generated type specification."""
        scalar_annotations = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'none': type(None),
            'date': date,
            'datetime': datetime,
        }
        if spec in scalar_annotations:
            return scalar_annotations[spec]

        kind = spec[0]
        if kind == 'list':
            return List[annotation_for_spec(spec[1])]  # type: ignore[misc]
        if kind == 'tuple':
            return Tuple[annotation_for_spec(spec[1]), ...]
        if kind == 'dict':
            return Dict[str, annotation_for_spec(spec[1])]  # type: ignore[misc]
        return Tuple[annotation_for_spec(spec[1]), annotation_for_spec(spec[2])]  # type: ignore[misc]

    def assert_round_trip_equivalent(expected, actual):
        """Compare round-trip values recursively using the contract's exact-type rules."""
        assert type(actual) is type(expected)

        if type(expected) is float:
            if math.isnan(expected):
                assert math.isnan(actual)
            else:
                assert actual == expected
            if expected == 0.0:
                assert math.copysign(1.0, actual) == math.copysign(1.0, expected)
            return

        if type(expected) is datetime:
            expected_fields = (
                expected.year,
                expected.month,
                expected.day,
                expected.hour,
                expected.minute,
                expected.second,
                expected.microsecond,
            )
            actual_fields = (
                actual.year,
                actual.month,
                actual.day,
                actual.hour,
                actual.minute,
                actual.second,
                actual.microsecond,
            )
            assert actual_fields == expected_fields
            assert actual.utcoffset() == expected.utcoffset()
            return

        if type(expected) in (list, tuple):
            assert len(actual) == len(expected)
            for expected_element, actual_element in zip(expected, actual):
                assert_round_trip_equivalent(expected_element, actual_element)
            return

        if type(expected) is dict:
            assert list(actual) == list(expected)
            for key in expected:
                assert type(next(actual_key for actual_key in actual if actual_key == key)) is type(key)
                assert_round_trip_equivalent(expected[key], actual[key])
            return

        assert actual == expected

    scalar_specs = strategies.sampled_from(('str', 'int', 'float', 'bool', 'none', 'date', 'datetime'))
    type_specs = strategies.recursive(
        scalar_specs,
        lambda children: strategies.one_of(
            strategies.tuples(strategies.just('list'), children),
            strategies.tuples(strategies.just('tuple'), children),
            strategies.tuples(strategies.just('dict'), children),
            strategies.tuples(strategies.just('fixed_tuple'), children, children),
        ),
        max_leaves=8,
    )
    value_spec = data.draw(type_specs)
    value = data.draw(strategies.dictionaries(strategies.text(), values_for_spec(value_spec), max_size=8))
    expected_type: Any = Dict[str, annotation_for_spec(value_spec)]  # type: ignore[misc, valid-type]

    restored = from_string(to_string(value), expected_type)

    assert_round_trip_equivalent(value, restored)


def test_dict_with_surrogate_strings_round_trips():
    """Round-trip exact surrogate string keys and values without changing their runtime types."""
    value = {chr(0xDFFF): chr(0xD800)}

    restored = from_string(to_string(value), Dict[str, str])

    assert type(restored) is dict
    assert list(restored) == list(value)
    assert type(next(iter(restored))) is str
    assert type(restored[chr(0xDFFF)]) is str
    assert restored[chr(0xDFFF)] == value[chr(0xDFFF)]


@pytest.mark.parametrize(
    ('value', 'precise_type', 'expected_erased_result'),
    [
        pytest.param([date(2026, 1, 22)], List[date], ['2026-01-22'], id='date-in-list'),
        pytest.param([(1, 2)], List[Tuple[int, ...]], [[1, 2]], id='tuple-in-list'),
        pytest.param(((1,),), Tuple[Tuple[int, ...], ...], ([1],), id='nested-tuple'),
    ],
)
def test_round_trip_requires_precise_external_type(
    value: Union[
        List[date],
        List[Tuple[int, ...]],
        Tuple[Tuple[int, ...], ...],
    ],
    precise_type: Type[object],
    expected_erased_result: Union[
        List[str],
        List[List[int]],
        Tuple[List[int], ...],
    ],
):
    """Precise annotations restore original values and types; bare container annotations lose nested type information."""
    def assert_value_and_types(expected, actual):
        """Compare values recursively while requiring exact runtime types at every level."""
        assert type(actual) is type(expected)

        if type(expected) is list or type(expected) is tuple:
            assert len(actual) == len(expected)
            for expected_element, actual_element in zip(expected, actual):
                assert_value_and_types(expected_element, actual_element)
            return

        assert actual == expected

    serialized = to_string(value)

    restored_with_precise_type = from_string(serialized, precise_type)
    restored_with_erased_type = from_string(serialized, type(value))

    assert_value_and_types(value, restored_with_precise_type)
    assert restored_with_erased_type == expected_erased_result
    assert restored_with_erased_type != value


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('2026-01-22', id='str'),
        pytest.param(1, id='int'),
        pytest.param(1.5, id='float'),
        pytest.param(True, id='bool'),
        pytest.param(None, id='none'),
        pytest.param(date(2026, 1, 22), id='date'),
        pytest.param(datetime(2026, 1, 22, 3, 4, 5), id='datetime'),
        pytest.param([1], id='list'),
        pytest.param((1,), id='tuple'),
        pytest.param({'key': 1}, id='dict'),
    ],
)
def test_any_round_trip_succeeds_only_when_original_value_is_str(
    value: Union[
        str,
        int,
        float,
        bool,
        None,
        date,
        datetime,
        List[int],
        Tuple[int, ...],
        Dict[str, int],
    ],
):
    """from_string(to_string(value), Any) restores the original value and exact type only when type(value) is str."""
    serialized = to_string(value)
    restored = from_string(serialized, Any)  # type: ignore[call-overload]

    assert type(restored) is str
    assert restored == serialized
    assert (restored == value) is (type(value) is str)


def test_round_trip_with_typing_and_builtin_annotations(
    subscribable_list_type,
    subscribable_tuple_type,
    subscribable_dict_type,
):
    """Round-trip a nested value through every available typing and built-in generic alias."""
    value = {'items': [(1, 2), (3, 4)]}
    expected_type = subscribable_dict_type[
        str,
        subscribable_list_type[subscribable_tuple_type[int, ...]],
    ]

    restored = from_string(to_string(value), expected_type)

    assert type(restored) is dict
    assert list(restored) == list(value)
    assert type(next(iter(restored))) is str

    restored_items = restored['items']
    assert type(restored_items) is list
    assert len(restored_items) == len(value['items'])

    for expected_pair, restored_pair in zip(value['items'], restored_items):
        assert type(restored_pair) is tuple
        assert len(restored_pair) == len(expected_pair)
        for expected_element, restored_element in zip(expected_pair, restored_pair):
            assert type(restored_element) is int
            assert restored_element == expected_element
