from datetime import date, datetime
from json import dumps
from math import inf, isnan
from typing import Any

import pytest
from full_match import match

from simtypes import from_string


def test_value_is_not_string():
    """Reject non-string input with ValueError before deserialization, for both parsed and passthrough target types."""
    with pytest.raises(ValueError, match=match('You can only pass a string as a string. You passed int.')):
        from_string(5, int)

    with pytest.raises(ValueError, match=match('You can only pass a string as a string. You passed int.')):
        from_string(5, str)


def test_type_is_not_type():
    """Reject non-type expected_type arguments with ValueError, including integers and string annotations that are API misuse rather than names to resolve."""
    with pytest.raises(ValueError, match=match('The type must be a valid type object.')):
        from_string('lol', 5)

    with pytest.raises(ValueError, match=match('The type must be a valid type object.')):
        from_string('kek', 'int')


def test_not_supported_data_type():
    """A custom unsupported target class raises the unsupported-type TypeError; the message names the class and includes the supported-types help text."""
    class SuperType:
        pass

    with pytest.raises(TypeError, match=match('Serialization of the type SuperType you passed is not supported. Supported types: int, float, bool, list, dict, tuple.')):
        from_string('kek', SuperType)


def test_get_string_value():
    """Explicit str deserialization returns valid string input unchanged."""
    assert from_string('kek', str) == 'kek'
    assert from_string('lol', str) == 'lol'


def test_get_int_value():
    """
    from_string(..., int) parses decimal integer strings, including negatives, leading zeroes, and underscores.

    Non-integer text, float-looking strings, the string "True", and empty strings raise the integer-specific TypeError.
    """
    assert from_string('1', int) == 1
    assert from_string('1000', int) == 1000
    assert from_string('1000000000000', int) == 1000000000000
    assert from_string('0', int) == 0
    assert from_string('000', int) == 0
    assert from_string('-15', int) == -15
    assert from_string('-1000000000000', int) == -1000000000000
    assert from_string('-100_0000000000', int) == -1000000000000
    assert from_string('-0100_0000000000', int) == -1000000000000

    with pytest.raises(TypeError, match=match('The string "kek" cannot be interpreted as an integer.')):
        from_string('kek', int)

    with pytest.raises(TypeError, match=match('The string "1.0" cannot be interpreted as an integer.')):
        from_string('1.0', int)

    with pytest.raises(TypeError, match=match('The string "True" cannot be interpreted as an integer.')):
        from_string('True', int)

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as an integer.')):
        from_string('', int)


def test_get_float_value():
    """
    Float parsing accepts decimal and integer-shaped strings with underscores, the sampled inf/NaN spellings, and Unicode infinity symbols.

    The string "True", empty strings, and non-numeric text raise the floating-point TypeError.
    """
    assert from_string('1.0', float) == 1.0
    assert from_string('1000.0', float) == 1000.0
    assert from_string('1000000000000.0', float) == 1000000000000.0
    assert from_string('0.0', float) == 0.0
    assert from_string('000.0', float) == 0.0
    assert from_string('-15.0', float) == -15.0
    assert from_string('-1000000000000.0', float) == -1000000000000.0
    assert from_string('-100_0000000000.0', float) == -1000000000000.0
    assert from_string('-0100_0000000000.0', float) == -1000000000000.0

    assert from_string('1', float) == 1.0
    assert from_string('1000', float) == 1000.0
    assert from_string('1000000000000', float) == 1000000000000.0
    assert from_string('0', float) == 0.0
    assert from_string('000', float) == 0.0
    assert from_string('-15', float) == -15.0
    assert from_string('-1000000000000', float) == -1000000000000.0
    assert from_string('-100_0000000000', float) == -1000000000000.0
    assert from_string('-0100_0000000000', float) == -1000000000000.0

    assert from_string('inf', float) == inf
    assert from_string('-inf', float) == -inf
    assert from_string('INF', float) == inf
    assert from_string('-INF', float) == -inf
    assert from_string('∞', float) == inf
    assert from_string('+∞', float) == inf
    assert from_string('-∞', float) == -inf

    assert isnan(from_string('nan', float))
    assert isnan(from_string('NaN', float))
    assert isnan(from_string('NAN', float))

    with pytest.raises(TypeError, match=match('The string "True" cannot be interpreted as a floating point number.')):
        from_string('True', float)

    with pytest.raises(TypeError, match=match('The string "kek" cannot be interpreted as a floating point number.')):
        from_string('kek', float)

    with pytest.raises(TypeError, match=match('The string "non" cannot be interpreted as a floating point number.')):
        from_string('non', float)

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a floating point number.')):
        from_string('', float)


def test_get_bool_value():
    """
    Boolean deserialization accepts only the exact string tokens "yes", "True", "true", "False", "false", and "no".

    Empty, unknown, or near-match strings raise the boolean-specific TypeError.
    """
    assert from_string('yes', bool) == True
    assert from_string('True', bool) == True
    assert from_string('true', bool) == True

    assert from_string('False', bool) == False
    assert from_string('false', bool) == False
    assert from_string('no', bool) == False

    with pytest.raises(TypeError, match=match('The string "kek" cannot be interpreted as a boolean value.')):
        from_string('kek', bool)

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a boolean value.')):
        from_string('', bool)

    with pytest.raises(TypeError, match=match('The string "nono" cannot be interpreted as a boolean value.')):
        from_string('nono', bool)


def test_get_list_value(list_type, subscribable_dict_type, subscribable_list_type):
    """
    JSON arrays decode into bare and typed lists, including nested typed lists and lists of parameterized dicts.

    Malformed JSON, wrong element types, and mismatched nested collection types raise the standardized list TypeError.
    """
    assert from_string('[]', list_type) == []
    assert from_string('[1, 2, 3]', list_type) == [1, 2, 3]
    assert from_string('[]', subscribable_list_type[int]) == []
    assert from_string('[]', subscribable_list_type[str]) == []

    assert from_string('[1, 2, 3]', subscribable_list_type[int]) == [1, 2, 3]
    assert from_string('["lol", "kek"]', subscribable_list_type[str]) == ["lol", "kek"]

    assert from_string('[["lol", "kek"], ["lol", "kek"]]', subscribable_list_type[subscribable_list_type[str]]) == [["lol", "kek"], ["lol", "kek"]]
    assert from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_list_type[subscribable_dict_type[str, str]]) == [{'lol': 'kek'}, {'lol': 'kek'}]

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a list of the specified format.')):
        from_string('', list_type)

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a list of the specified format.')):
        from_string('', subscribable_list_type[int])

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a list of the specified format.')):
        from_string('', subscribable_list_type[str])

    with pytest.raises(TypeError, match=match('The string "[1, 2, "3"]" cannot be interpreted as a list of the specified format.')):
        from_string('[1, 2, "3"]', subscribable_list_type[int])

    with pytest.raises(TypeError, match=match('The string "[1, 2, "3"]" cannot be interpreted as a list of the specified format.')):
        from_string('[1, 2, "3"]', subscribable_list_type[str])

    with pytest.raises(TypeError, match=match('The string "[1, 2, "3"" cannot be interpreted as a list of the specified format.')):
        from_string('[1, 2, "3"', subscribable_list_type[str])

    with pytest.raises(TypeError, match=match('The string "[["lol", "kek"], ["lol", "kek"]]" cannot be interpreted as a list of the specified format.')):
        from_string('[["lol", "kek"], ["lol", "kek"]]', subscribable_list_type[subscribable_list_type[int]])

    with pytest.raises(TypeError, match=match('The string "[["lol", "kek"], ["lol", "kek"]]" cannot be interpreted as a list of the specified format.')):
        from_string('[["lol", "kek"], ["lol", "kek"]]', subscribable_list_type[subscribable_dict_type[int, int]])

    with pytest.raises(TypeError, match=match('The string "[{"lol": "kek"}, {"lol": "kek"}]" cannot be interpreted as a list of the specified format.')):
        from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_list_type[subscribable_dict_type[str, int]])

    with pytest.raises(TypeError, match=match('The string "[{"lol": "kek"}, {"lol": "kek"}]" cannot be interpreted as a list of the specified format.')):
        from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_list_type[subscribable_dict_type[int, str]])

    with pytest.raises(TypeError, match=match('The string "[{"lol": "kek"}, {"lol": "kek"}]" cannot be interpreted as a list of the specified format.')):
        from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_list_type[subscribable_list_type[str]])


def test_get_tuple_value(tuple_type, subscribable_tuple_type, subscribable_dict_type):
    """
    JSON arrays decode into bare, fixed-length, variadic, and nested typed tuples, including parameterized dict elements.

    Malformed input, wrong arity, and nested type errors raise the standardized tuple TypeError.
    """
    assert from_string('[]', tuple_type) == ()
    assert from_string('[1, 2, 3]', tuple_type) == (1, 2, 3)
    assert from_string('[]', subscribable_tuple_type[int, ...]) == ()
    assert from_string('[]', subscribable_tuple_type[str, ...]) == ()

    assert from_string('[1, 2, 3]', subscribable_tuple_type[int, ...]) == (1, 2, 3)
    assert from_string('["lol", "kek"]', subscribable_tuple_type[str, ...]) == ("lol", "kek")
    assert from_string('[1, 2, 3]', subscribable_tuple_type[int, int, int]) == (1, 2, 3)
    assert from_string('["lol", "kek"]', subscribable_tuple_type[str, str]) == ("lol", "kek")

    assert from_string('[["lol", "kek"], ["lol", "kek"]]', subscribable_tuple_type[subscribable_tuple_type[str, str], subscribable_tuple_type[str, str]]) == (("lol", "kek"), ("lol", "kek"))
    assert from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_tuple_type[subscribable_dict_type[str, str], subscribable_dict_type[str, str]]) == ({'lol': 'kek'}, {'lol': 'kek'})

    assert from_string('[["lol", "kek"], ["lol", "kek"]]', subscribable_tuple_type[subscribable_tuple_type[str, str], ...]) == (("lol", "kek"), ("lol", "kek"))
    assert from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_tuple_type[subscribable_dict_type[str, str], ...]) == ({'lol': 'kek'}, {'lol': 'kek'})

    with pytest.raises(TypeError, match=match('The string "[]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[]', subscribable_tuple_type[int])

    with pytest.raises(TypeError, match=match('The string "[]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[]', subscribable_tuple_type[str])

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a tuple of the specified format.')):
        from_string('', tuple_type)

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a tuple of the specified format.')):
        from_string('', subscribable_tuple_type[int])

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a tuple of the specified format.')):
        from_string('', subscribable_tuple_type[str])

    with pytest.raises(TypeError, match=match('The string "[1, 2, "3"]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[1, 2, "3"]', subscribable_tuple_type[int])

    with pytest.raises(TypeError, match=match('The string "[1, 2, "3"]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[1, 2, "3"]', subscribable_tuple_type[str])

    with pytest.raises(TypeError, match=match('The string "[1, 2, "3"" cannot be interpreted as a tuple of the specified format.')):
        from_string('[1, 2, "3"', subscribable_tuple_type[str])

    with pytest.raises(TypeError, match=match('The string "[["lol", "kek"], ["lol", "kek"]]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[["lol", "kek"], ["lol", "kek"]]', subscribable_tuple_type[subscribable_tuple_type[int]])

    with pytest.raises(TypeError, match=match('The string "[["lol", "kek"], ["lol", "kek"]]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[["lol", "kek"], ["lol", "kek"]]', subscribable_tuple_type[subscribable_dict_type[int, int]])

    with pytest.raises(TypeError, match=match('The string "[{"lol": "kek"}, {"lol": "kek"}]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_tuple_type[subscribable_dict_type[str, int]])

    with pytest.raises(TypeError, match=match('The string "[{"lol": "kek"}, {"lol": "kek"}]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_tuple_type[subscribable_dict_type[int, str]])

    with pytest.raises(TypeError, match=match('The string "[{"lol": "kek"}, {"lol": "kek"}]" cannot be interpreted as a tuple of the specified format.')):
        from_string('[{"lol": "kek"}, {"lol": "kek"}]', subscribable_tuple_type[subscribable_tuple_type[str]])


def test_get_dict_value(dict_type, subscribable_list_type, subscribable_dict_type):
    """
    JSON objects decode into bare and parameterized dicts when keys and values satisfy the annotations.

    JSON string keys are not coerced to int, so non-empty int-key dict hints fail; invalid JSON, value mismatches, and bad nested values raise the standardized dict TypeError.
    """
    assert from_string('{}', dict_type) == {}
    assert from_string('{"lol": "kek"}', dict_type) == {'lol': 'kek'}
    assert from_string('{}', subscribable_dict_type[int, int]) == {}
    assert from_string('{}', subscribable_dict_type[str, str]) == {}
    assert from_string('{}', subscribable_dict_type[int, str]) == {}
    assert from_string('{}', subscribable_dict_type[str, int]) == {}

    assert from_string('{"1": 1, "2": 2, "3": 3}', subscribable_dict_type[str, int]) == {"1": 1, "2": 2, "3": 3}
    assert from_string('{"lol": "kek"}', subscribable_dict_type[str, str]) == {"lol": "kek"}
    assert from_string('{"lol": 1, "kek": 2}', subscribable_dict_type[str, int]) == {"lol": 1, "kek": 2}

    assert from_string('{"kek": ["lol", "kek"]}', subscribable_dict_type[str, subscribable_list_type[str]]) == {"kek": ["lol", "kek"]}
    assert from_string('{"123": [{"lol": "kek"}, {"lol": "kek"}]}', subscribable_dict_type[str, subscribable_list_type[subscribable_dict_type[str, str]]]) == {"123": [{"lol": "kek"}, {"lol": "kek"}]}
    assert from_string('{"123": [{"lol": 1}, {"lol": 2}]}', subscribable_dict_type[str, subscribable_list_type[subscribable_dict_type[str, int]]]) == {"123": [{"lol": 1}, {"lol": 2}]}

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a dict of the specified format.')):
        from_string('', dict_type)

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a dict of the specified format.')):
        from_string('', subscribable_dict_type[int, int])

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a dict of the specified format.')):
        from_string('', subscribable_dict_type[int, str])

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a dict of the specified format.')):
        from_string('', subscribable_dict_type[str, str])

    with pytest.raises(TypeError, match=match('The string "" cannot be interpreted as a dict of the specified format.')):
        from_string('', subscribable_dict_type[str, int])

    with pytest.raises(TypeError, match=match('The string "{" cannot be interpreted as a dict of the specified format.')):
        from_string('{', subscribable_dict_type[str, int])

    with pytest.raises(TypeError, match=match('The string "}" cannot be interpreted as a dict of the specified format.')):
        from_string('}', subscribable_dict_type[str, int])

    with pytest.raises(TypeError, match=match('The string "}" cannot be interpreted as a dict of the specified format.')):
        from_string('}', subscribable_dict_type[int, int])

    with pytest.raises(TypeError, match=match('The string "}" cannot be interpreted as a dict of the specified format.')):
        from_string('}', dict_type)

    with pytest.raises(TypeError, match=match('The string "{1: 1}" cannot be interpreted as a dict of the specified format.')):
        from_string('{1: 1}', subscribable_dict_type[int, str])

    with pytest.raises(TypeError, match=match('The string "{1: 1}" cannot be interpreted as a dict of the specified format.')):
        from_string('{1: 1}', subscribable_dict_type[str, int])

    with pytest.raises(TypeError, match=match('The string "{"lol": "kek"}" cannot be interpreted as a dict of the specified format.')):
        from_string('{"lol": "kek"}', subscribable_dict_type[str, int])

    with pytest.raises(TypeError, match=match('The string "{"lol": "kek"}" cannot be interpreted as a dict of the specified format.')):
        from_string('{"lol": "kek"}', subscribable_dict_type[int, str])

    with pytest.raises(TypeError, match=match('The string "{"lol": "kek"" cannot be interpreted as a dict of the specified format.')):
        from_string('{"lol": "kek"', subscribable_dict_type[str, str])

    with pytest.raises(TypeError, match=match('The string "{"lol": "kek"}" cannot be interpreted as a dict of the specified format.')):
        from_string('{"lol": "kek"}', subscribable_dict_type[int, int])

    with pytest.raises(TypeError, match=match('The string "{"lol": ["kek"]}" cannot be interpreted as a dict of the specified format.')):
        from_string('{"lol": ["kek"]}', subscribable_dict_type[str, subscribable_list_type[int]])

    with pytest.raises(TypeError, match=match('The string "{"lol": {"kek": "kek"}}" cannot be interpreted as a dict of the specified format.')):
        from_string('{"lol": {"kek": "kek"}}', subscribable_dict_type[str, subscribable_dict_type[int, str]])


@pytest.mark.parametrize(
    'string',
    [
        '{"lol": "kek"}',
        '1',
        'kek',
    ],
)
def test_get_any(string):
    """from_string with Any returns input strings unchanged, even when they look like JSON or numbers."""
    assert from_string(string, Any) == string


def test_deserialize_date():
    """
    Scalar ISO dates deserialize like date.fromisoformat.

    Invalid scalar dates raise the date-specific TypeError.
    """
    isoformatted_date = date(2026, 1, 22).isoformat()

    assert from_string(isoformatted_date, date) == date.fromisoformat(isoformatted_date)

    with pytest.raises(TypeError, match=match('The string "kek" cannot be interpreted as a date object.')):
        from_string('kek', date)


def test_deserialize_datetetime():
    """
    ISO datetime strings deserialize like datetime.fromisoformat.

    Invalid scalar datetime strings raise the datetime-specific TypeError.
    """
    isoformatted_datetime = datetime.now().isoformat()

    assert from_string(isoformatted_datetime, datetime) == datetime.fromisoformat(isoformatted_datetime)

    with pytest.raises(TypeError, match=match('The string "kek" cannot be interpreted as a datetime object.')):
        from_string('kek', datetime)


def test_deserialize_subscribable_collections_with_datetimes(subscribable_list_type, subscribable_tuple_type, subscribable_dict_type):
    """Typed list, tuple, and dict hints deserialize ISO datetime strings in elements and dict keys or values; dict keys or values annotated as str remain strings."""
    isoformatted_datetime = datetime.now().isoformat()

    assert from_string(dumps([isoformatted_datetime]), subscribable_list_type[datetime]) == [datetime.fromisoformat(isoformatted_datetime)]
    assert from_string(dumps([isoformatted_datetime]), subscribable_tuple_type[datetime]) == (datetime.fromisoformat(isoformatted_datetime),)
    assert from_string(dumps([isoformatted_datetime]), subscribable_tuple_type[datetime, ...]) == (datetime.fromisoformat(isoformatted_datetime),)
    assert from_string(dumps({isoformatted_datetime: isoformatted_datetime}), subscribable_dict_type[datetime, datetime]) == {datetime.fromisoformat(isoformatted_datetime): datetime.fromisoformat(isoformatted_datetime)}
    assert from_string(dumps({isoformatted_datetime: isoformatted_datetime}), subscribable_dict_type[datetime, str]) == {datetime.fromisoformat(isoformatted_datetime): isoformatted_datetime}
    assert from_string(dumps({isoformatted_datetime: isoformatted_datetime}), subscribable_dict_type[str, datetime]) == {isoformatted_datetime: datetime.fromisoformat(isoformatted_datetime)}


def test_deserialize_subscribable_collections_with_dates(subscribable_list_type, subscribable_tuple_type, subscribable_dict_type):
    """Typed list, tuple, and dict hints deserialize ISO date strings in elements and dict keys or values; dict keys or values annotated as str remain strings."""
    isoformatted_date = date(2026, 1, 22).isoformat()

    assert from_string(dumps([isoformatted_date]), subscribable_list_type[date]) == [date.fromisoformat(isoformatted_date)]
    assert from_string(dumps([isoformatted_date]), subscribable_tuple_type[date]) == (date.fromisoformat(isoformatted_date),)
    assert from_string(dumps([isoformatted_date]), subscribable_tuple_type[date, ...]) == (date.fromisoformat(isoformatted_date),)
    assert from_string(dumps({isoformatted_date: isoformatted_date}), subscribable_dict_type[date, date]) == {date.fromisoformat(isoformatted_date): date.fromisoformat(isoformatted_date)}
    assert from_string(dumps({isoformatted_date: isoformatted_date}), subscribable_dict_type[date, str]) == {date.fromisoformat(isoformatted_date): isoformatted_date}
    assert from_string(dumps({isoformatted_date: isoformatted_date}), subscribable_dict_type[str, date]) == {isoformatted_date: date.fromisoformat(isoformatted_date)}


def test_wrong_collection_content(subscribable_list_type, subscribable_tuple_type, subscribable_dict_type, dict_type, list_type, tuple_type):  # noqa: PLR0915, PLR0913
    """Invalid JSON collection shapes, nested collection mismatches, bad element/key/value types, and failed date/datetime conversions raise the relevant collection TypeError."""
    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps([123]), subscribable_list_type[date])

    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps([123]), subscribable_list_type[datetime])

    with pytest.raises(TypeError, match=match('The string "[null]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps([None]), subscribable_list_type[datetime])

    with pytest.raises(TypeError, match=match('The string "[null]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps([None]), subscribable_list_type[date])

    with pytest.raises(TypeError, match=match('The string "["123"]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps(['123']), subscribable_list_type[date])

    with pytest.raises(TypeError, match=match('The string "["123"]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps(['123']), subscribable_list_type[datetime])


    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([123]), subscribable_tuple_type[date])

    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([123]), subscribable_tuple_type[datetime])

    with pytest.raises(TypeError, match=match('The string "[null]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([None]), subscribable_tuple_type[datetime])

    with pytest.raises(TypeError, match=match('The string "[null]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([None]), subscribable_tuple_type[date])

    with pytest.raises(TypeError, match=match('The string "["123"]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps(['123']), subscribable_tuple_type[datetime])

    with pytest.raises(TypeError, match=match('The string "["123"]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps(['123']), subscribable_tuple_type[date])


    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([123]), subscribable_tuple_type[date, ...])

    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([123]), subscribable_tuple_type[datetime, ...])

    with pytest.raises(TypeError, match=match('The string "[null]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([None]), subscribable_tuple_type[datetime, ...])

    with pytest.raises(TypeError, match=match('The string "[null]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([None]), subscribable_tuple_type[date, ...])

    with pytest.raises(TypeError, match=match('The string "["123"]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps(['123']), subscribable_tuple_type[datetime, ...])

    with pytest.raises(TypeError, match=match('The string "["123"]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps(['123']), subscribable_tuple_type[date, ...])


    with pytest.raises(TypeError, match=match('The string "{"kek": 123}" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps({'kek': 123}), subscribable_tuple_type[date])

    with pytest.raises(TypeError, match=match('The string "{"kek": 123}" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps({'kek': 123}), subscribable_tuple_type[date, ...])

    with pytest.raises(TypeError, match=match('The string "{"kek": 123}" cannot be interpreted as a list of the specified format.')):
        from_string(dumps({'kek': 123}), subscribable_list_type[date])


    with pytest.raises(TypeError, match=match('The string "[{"kek": "lol"}]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps([{'kek': 'lol'}]), subscribable_list_type[subscribable_dict_type[str, int]])

    with pytest.raises(TypeError, match=match('The string "[{"kek": "lol"}]" cannot be interpreted as a list of the specified format.')):
        from_string(dumps([{'kek': 'lol'}]), subscribable_list_type[subscribable_list_type[int]])


    with pytest.raises(TypeError, match=match('The string "[{"kek": "lol"}]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([{'kek': 'lol'}]), subscribable_tuple_type[subscribable_dict_type[str, int]])

    with pytest.raises(TypeError, match=match('The string "[{"kek": "lol"}]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([{'kek': 'lol'}]), subscribable_tuple_type[subscribable_list_type[int]])

    with pytest.raises(TypeError, match=match('The string "[{"kek": "lol"}]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([{'kek': 'lol'}]), subscribable_tuple_type[subscribable_list_type[int], ...])

    with pytest.raises(TypeError, match=match('The string "[{"kek": "lol"}]" cannot be interpreted as a tuple of the specified format.')):
        from_string(dumps([{'kek': 'lol'}]), subscribable_tuple_type[subscribable_dict_type[str, int], ...])


    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps([123]), subscribable_dict_type[int, int])

    with pytest.raises(TypeError, match=match('The string "["123"]" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps(['123']), subscribable_dict_type[int, int])

    with pytest.raises(TypeError, match=match('The string "{"123": "123"}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({123: '123'}), subscribable_dict_type[int, int])

    with pytest.raises(TypeError, match=match('The string "{"123": 123}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': 123}), subscribable_dict_type[int, int])

    with pytest.raises(TypeError, match=match('The string "{"123": {"123": "123"}}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': {123: '123'}}), subscribable_dict_type[str, subscribable_dict_type[int, int]])

    with pytest.raises(TypeError, match=match('The string "{"123": [123, 123]}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': [123, 123]}), subscribable_dict_type[str, subscribable_dict_type[int, int]])

    with pytest.raises(TypeError, match=match('The string "{"123": {"123": "123"}}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': {123: '123'}}), subscribable_dict_type[str, subscribable_list_type[int]])


    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps([123]), subscribable_dict_type[int, date])

    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps([123]), subscribable_dict_type[int, datetime])

    with pytest.raises(TypeError, match=match('The string "{"123": "123"}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({123: '123'}), subscribable_dict_type[int, datetime])

    with pytest.raises(TypeError, match=match('The string "{"123": "123"}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({123: '123'}), subscribable_dict_type[datetime, str])

    with pytest.raises(TypeError, match=match('The string "{"123": "123"}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({123: '123'}), subscribable_dict_type[int, date])

    with pytest.raises(TypeError, match=match('The string "{"123": "123"}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({123: '123'}), subscribable_dict_type[date, str])

    with pytest.raises(TypeError, match=match('The string "{"123": null}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': None}), subscribable_dict_type[int, datetime])

    with pytest.raises(TypeError, match=match('The string "{"123": null}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': None}), subscribable_dict_type[int, date])

    with pytest.raises(TypeError, match=match('The string "{"123": 123}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': 123}), subscribable_dict_type[int, datetime])

    with pytest.raises(TypeError, match=match('The string "{"123": 123}" cannot be interpreted as a dict of the specified format.')):
        from_string(dumps({'123': 123}), subscribable_dict_type[int, date])


    with pytest.raises(TypeError, match=match('The string "123" cannot be interpreted as a dict of the specified format.')):
        from_string('123', dict_type)

    with pytest.raises(TypeError, match=match('The string "[123]" cannot be interpreted as a dict of the specified format.')):
        from_string('[123]', dict_type)

    with pytest.raises(TypeError, match=match('The string "123" cannot be interpreted as a list of the specified format.')):
        from_string('123', list_type)

    with pytest.raises(TypeError, match=match('The string "123" cannot be interpreted as a tuple of the specified format.')):
        from_string('123', tuple_type)
