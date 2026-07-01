import sys
from unittest.mock import MagicMock, Mock

try:
    from types import NoneType  # type: ignore[attr-defined]
except ImportError:
    NoneType = type(None)  # type: ignore[misc]

from collections.abc import Sequence
from typing import Any, Optional, Union

import pytest
from denial import InnerNone, InnerNoneType, SentinelType
from full_match import match

from simtypes import check


def test_none():
    """
    Bare None and NoneType annotations match only the None singleton.

    Falsy values, the string "None", and the NoneType class object itself are rejected as values.
    """
    assert check(None, None) is True
    assert check(None, NoneType) is True

    assert check(1, None) is False
    assert check('None', None) is False
    assert check(0, None) is False
    assert check(False, None) is False
    assert check(False, NoneType) is False
    assert check(0, NoneType) is False
    assert check('some string', NoneType) is False

    assert check(NoneType, NoneType) is False
    assert check(NoneType, None) is False


def test_built_in_types():
    """
    Plain bool, int, float, and str hints match exact runtime types, except for bool-as-int behavior covered elsewhere.

    String values that look convertible are rejected instead of being parsed or coerced.
    """
    assert check(True, bool)
    assert check(1, int)
    assert check(1.0, float)
    assert check('hello', str)

    assert not check(1, bool)
    assert not check('True', bool)
    assert not check(1.0, bool)
    assert not check(None, bool)
    assert not check('1', int)
    assert not check(1.0, int)
    assert not check(None, int)
    assert not check(1, str)
    assert not check(None, str)
    assert not check('1.0', float)
    assert not check(1, float)
    assert not check(None, float)


def test_any():
    """typing.Any matches all sampled values, including primitives, collections, None, and type objects."""
    assert check(True, Any)
    assert check(False, Any)
    assert check(0, Any)
    assert check('kek', Any)
    assert check(1.0, Any)
    assert check([1, 2, 3], Any)
    assert check((1, 2, 3), Any)
    assert check([True], Any)
    assert check('True', Any)
    assert check(None, Any)
    assert check(str, Any)
    assert check(-1000, Any)


@pytest.mark.skipif(sys.version_info > (3, 13), reason="Before Python 3.14, you couldn't just use Union as an annotation.")
def test_empty_union_old_pythons():
    """Before the Python 3.14 bare-Union behavior, check(None, Union) raises ValueError for an unusable annotation."""
    with pytest.raises(ValueError, match=match('Type must be a valid type object.')):
        check(None, Union)


@pytest.mark.skipif(sys.version_info < (3, 14), reason="Before Python 3.14, you couldn't just use Union as an annotation.")
def test_empty_union():
    """On Python 3.14+, bare typing.Union is valid but behaves as an empty union, not Any, and matches none of the sampled values."""
    assert not check(None, Union)
    assert not check(1, Union)
    assert not check('kek', Union)


def test_empty_optional():
    """Bare Optional is invalid: check(None, Optional) raises ValueError rather than matching None or behaving like Optional[Any]."""
    with pytest.raises(ValueError, match=match('Type must be a valid type object.')):
        check(None, Optional)


def test_union(make_union):
    """
    Parameterized unions accept values matching any member type.

    Covers both typing.Union and PEP 604 syntax, and rejects None unless it is explicitly included.
    """
    assert check(1, make_union(int, str))
    assert check('hello', make_union(int, str))
    assert check(1.0, make_union(int, float))

    assert not check(1.0, make_union(int, str))
    assert not check(None, make_union(int, str))


def test_union_recursive(make_union):
    """
    Nested unions behave the same as equivalent flattened unions.

    They accept any member type across typing.Union and | forms, and reject unrelated containers and None.
    """
    assert check(1, make_union(int, make_union(float, str)))
    assert check(1.0, make_union(int, make_union(float, str)))
    assert check('kek', make_union(int, make_union(float, str)))

    assert check(1, make_union(make_union(float, str), int))
    assert check(1.0, make_union(make_union(float, str), int))
    assert check('kek', make_union(make_union(float, str), int))

    assert not check(None, make_union(int, make_union(float, str)))
    assert not check([1, 2, 3], make_union(int, make_union(float, str)))
    assert not check(['kek'], make_union(int, make_union(float, str)))
    assert not check(('kek',), make_union(int, make_union(float, str)))
    assert not check(set(), make_union(int, make_union(float, str)))

    assert not check(None, make_union(make_union(float, str), int))
    assert not check([1, 2, 3], make_union(make_union(float, str), int))
    assert not check(['kek'], make_union(make_union(float, str), int))
    assert not check(('kek',), make_union(make_union(float, str), int))
    assert not check(set(), make_union(make_union(float, str), int))


def test_bool_is_int(make_optional, make_union):
    """bool values satisfy int annotations, including through Union, Optional, and Optional[Union[...]]."""
    assert check(True, int)
    assert check(False, int)

    assert check(True, make_union(int, str))
    assert check(True, make_union(str, int))
    assert check(False, make_union(int, str))
    assert check(False, make_union(str, int))

    assert check(False, make_optional(int))
    assert check(True, make_optional(int))

    assert check(True, make_optional(make_union(int, str)))
    assert check(False, make_optional(make_union(int, str)))


def test_optional(tuple_type, list_type, make_optional):
    """
    Optional annotations accept only None or values of the wrapped type.

    Covers typing.Optional[T], T | None, and Optional hints wrapping bare list or tuple types.
    """
    assert check(None, make_optional(int))
    assert check(1, make_optional(int))
    assert check(0, make_optional(int))
    assert check(-1000, make_optional(int))

    assert not check(1.0, make_optional(int))
    assert not check('1.0', make_optional(int))
    assert not check('kek', make_optional(int))
    assert not check('None', make_optional(int))
    assert not check([1, 2, 3], make_optional(int))
    assert not check(('kek',), make_optional(int))
    assert not check((1, 2, 3), make_optional(int))
    assert not check(set(), make_optional(int))

    assert check(None, make_optional(str))
    assert check('1', make_optional(str))
    assert check('kek', make_optional(str))
    assert check('', make_optional(str))

    assert not check(1.0, make_optional(str))
    assert not check(1, make_optional(str))
    assert not check(['kek'], make_optional(str))

    assert check([], make_optional(list_type))
    assert not check([], make_optional(tuple_type))
    assert check((), make_optional(tuple_type))
    assert check((1, 2, 3), make_optional(tuple_type))


def test_optional_union(make_union, make_optional, tuple_type):
    """
    Optional unions accept None or any inner union member across typing and PEP 604 spellings.

    This differs from ordinary unions, where None is rejected unless it is explicitly included.
    """
    assert check(None, make_optional(make_union(int, str)))
    assert check(1, make_optional(make_union(int, str)))
    assert check('kek', make_optional(make_union(int, str)))
    assert check('', make_optional(make_union(int, str)))
    assert check(-1000, make_optional(make_union(int, str)))
    assert check(0, make_optional(make_union(int, str)))
    assert check((), make_optional(make_union(int, tuple_type)))
    assert check((1, 2, 3), make_optional(make_union(int, tuple_type)))

    assert not check(1.0, make_optional(make_union(int, str)))
    assert not check([1.0], make_optional(make_union(int, str)))
    assert not check([1], make_optional(make_union(int, str)))
    assert not check(['kek'], make_optional(make_union(int, str)))
    assert not check([None], make_optional(make_union(int, str)))
    assert not check([[]], make_optional(make_union(int, str)))
    assert not check([], make_optional(make_union(int, tuple_type)))
    assert not check([1, 2, 3], make_optional(make_union(int, tuple_type)))
    assert not check([5], make_optional(make_union(int, tuple_type)))
    assert not check('kek', make_optional(make_union(int, tuple_type)))


@pytest.mark.parametrize(
    'addictional_parameters',
    [
        {},
        {'strict': True},
        {'strict': False},
    ],
)
def test_list_without_arguments(list_type, addictional_parameters):
    """
    Unsubscripted List/list annotations validate only the outer list type across strict modes.

    Mixed contents are accepted when no element type is declared.
    """
    assert check([], list_type, **addictional_parameters)
    assert check([1, 2, 3], list_type, **addictional_parameters)
    assert check(['kek', 'lol'], list_type, **addictional_parameters)
    assert check([1, 'kek', 2.0], list_type, **addictional_parameters)

    assert not check((), list_type, **addictional_parameters)
    assert not check((1, 2, 3), list_type, **addictional_parameters)
    assert not check(('kek', 'lol'), list_type, **addictional_parameters)
    assert not check((1, 'kek', 2.0), list_type, **addictional_parameters)

    assert not check(1, list_type, **addictional_parameters)
    assert not check(1.0, list_type, **addictional_parameters)
    assert not check('kek', list_type, **addictional_parameters)
    assert not check(None, list_type, **addictional_parameters)


@pytest.mark.parametrize(
    'addictional_parameters',
    [
        {},
        {'strict': True},
        {'strict': False},
    ],
)
def test_tuple_without_arguments(tuple_type, addictional_parameters):
    """
    Unsubscripted Tuple and tuple annotations validate only tuple-ness across strict modes.

    Length, nesting, and contents are ignored, while non-tuples are rejected.
    """
    assert check((), tuple_type, **addictional_parameters)
    assert check((1,), tuple_type, **addictional_parameters)
    assert check((None,), tuple_type, **addictional_parameters)
    assert check(('kek',), tuple_type, **addictional_parameters)
    assert check((('kek',),), tuple_type, **addictional_parameters)
    assert check((1, 2, 3), tuple_type, **addictional_parameters)
    assert check(('kek', 'lol'), tuple_type, **addictional_parameters)
    assert check((1, 'kek', 2.0), tuple_type, **addictional_parameters)

    assert not check([], tuple_type, **addictional_parameters)
    assert not check([1, 2, 3], tuple_type, **addictional_parameters)
    assert not check(['kek', 'lol'], tuple_type, **addictional_parameters)
    assert not check([1, 'kek', 2.0], tuple_type, **addictional_parameters)
    assert not check([(1, 2, 3)], tuple_type, **addictional_parameters)
    assert not check('(1, 2, 3)', tuple_type, **addictional_parameters)
    assert not check('kek', tuple_type, **addictional_parameters)
    assert not check(1, tuple_type, **addictional_parameters)
    assert not check(1.0, tuple_type, **addictional_parameters)
    assert not check(None, tuple_type, **addictional_parameters)


@pytest.mark.parametrize(
    'addictional_parameters',
    [
        {},
        {'strict': True},
        {'strict': False},
    ],
)
def test_set_without_arguments(set_type, addictional_parameters):
    """Unsubscripted Set/set annotations accept sets and reject non-set values regardless of strict mode."""
    assert check(set(), set_type, **addictional_parameters)
    assert check({1}, set_type, **addictional_parameters)
    assert check({None}, set_type, **addictional_parameters)
    assert check({'kek'}, set_type, **addictional_parameters)
    assert check({1, 2, 3}, set_type, **addictional_parameters)
    assert check({'lol', 'kek'}, set_type, **addictional_parameters)

    assert not check([], set_type, **addictional_parameters)
    assert not check([(1, 2, 3)], set_type, **addictional_parameters)
    assert not check('(1, 2, 3)', set_type, **addictional_parameters)
    assert not check('kek', set_type, **addictional_parameters)
    assert not check(1, set_type, **addictional_parameters)
    assert not check(1.0, set_type, **addictional_parameters)
    assert not check(None, set_type, **addictional_parameters)


@pytest.mark.parametrize(
    'addictional_parameters',
    [
        {},
        {'strict': True},
        {'strict': False},
    ],
)
def test_dict_without_arguments(dict_type, addictional_parameters):
    """
    Unsubscripted Dict/dict annotations validate only the outer dict type.

    Any real dict is accepted across strict modes, while non-dict values are rejected.
    """
    assert check({}, dict_type, **addictional_parameters)
    assert check({'lol': 'kek'}, dict_type, **addictional_parameters)
    assert check({1: 'kek'}, dict_type, **addictional_parameters)
    assert check({'lol': 1}, dict_type, **addictional_parameters)
    assert check({'lol': None}, dict_type, **addictional_parameters)
    assert check({1: None}, dict_type, **addictional_parameters)

    assert not check([], dict_type)
    assert not check(set([1, 2, 3]), dict_type, **addictional_parameters)
    assert not check(None, dict_type, **addictional_parameters)
    assert not check(1, dict_type, **addictional_parameters)
    assert not check(1.0, dict_type, **addictional_parameters)
    assert not check('{1: None}', dict_type, **addictional_parameters)
    assert not check('kek', dict_type, **addictional_parameters)
    assert not check(dict_type, dict_type, **addictional_parameters)


def test_content_of_list_not_in_strict_mode_is_not_checking(subscribable_list_type):
    """Non-strict List[int]/list[int] checks accept any list regardless of element contents."""
    assert check([], subscribable_list_type[int])
    assert check(['lol', 'kek'], subscribable_list_type[int])
    assert check([1.0, 2.0], subscribable_list_type[int])
    assert check([None, None], subscribable_list_type[int])
    assert check([None, 'kek', 1, 1.0], subscribable_list_type[int])


def test_content_of_tuple_not_in_strict_mode_is_not_checking(subscribable_tuple_type):
    """Non-strict tuple[int] and Tuple[int] checks validate only the outer tuple, ignoring element types and arity."""
    assert check((), subscribable_tuple_type[int])
    assert check(('lol', 'kek'), subscribable_tuple_type[int])
    assert check((1.0, 2.0), subscribable_tuple_type[int])
    assert check((None, None), subscribable_tuple_type[int])
    assert check((None, 'kek', 1, 1.0), subscribable_tuple_type[int])


def test_content_of_dict_not_in_strict_mode_is_not_checking(subscribable_dict_type):
    """Non-strict Dict[int, int]/dict[int, int] validation accepts any dict regardless of key and value types."""
    assert check({}, subscribable_dict_type[int, int])
    assert check({1: 'kek'}, subscribable_dict_type[int, int])
    assert check({'lol': 'kek'}, subscribable_dict_type[int, int])
    assert check({'lol': 1}, subscribable_dict_type[int, int])
    assert check({1.0: 1}, subscribable_dict_type[int, int])


@pytest.mark.skipif(sys.version_info < (3, 9), reason='Subscribing to objects became available in Python 3.9')
def test_content_of_set_not_in_strict_mode_is_not_checking():
    """Non-strict set[int] validation checks only the set origin and ignores element types."""
    assert check(set(), set[int])
    assert check(set(['lol', 'kek']), set[int])
    assert check(set([1, 'kek']), set[int])
    assert check(set([1, None]), set[int])
    assert check(set([None, None]), set[int])
    assert check(set(['1', '2']), set[int])


def test_try_to_pass_not_type_object_as_type():
    """check raises ValueError for non-type, non-annotation second arguments, including string pseudo-annotations."""
    with pytest.raises(ValueError, match=match('Type must be a valid type object.')):
        check(1, 1)

    with pytest.raises(ValueError, match=match('Type must be a valid type object.')):
        check(1, '1')

    with pytest.raises(ValueError, match=match('Type must be a valid type object.')):
        check(1, 'SomeClass')


def test_simple_isinstance():
    """check mirrors isinstance for a user-defined class, matching instances and rejecting unrelated values and class-name strings."""
    class SomeType:
        pass

    assert check(SomeType(), SomeType)

    assert check(None, SomeType) == False
    assert check(1, SomeType) == False
    assert check('SomeType', SomeType) == False
    assert check(1.5, SomeType) == False


def test_sequence():
    """Bare Sequence uses ABC membership: lists, tuples, and strings pass, while scalar non-sequences fail."""
    assert check([1, 2, 3], Sequence)
    assert check((1, 2, 3), Sequence)
    assert check('kek', Sequence)

    assert not check(1, Sequence)


@pytest.mark.skipif(sys.version_info < (3, 9), reason='Subscribing to objects became available in Python 3.9')
def test_sequence_is_not_checking_content():
    """Sequence[str] checks only the sequence origin, so integer lists and tuples still pass."""
    assert check((1, 2, 3), Sequence[str])
    assert check([1, 2, 3], Sequence[str])


def test_list_with_values_in_strict_mode(subscribable_list_type, make_union):
    """
    Strict mode recursively checks parameterized lists.

    Empty lists pass, nested unions and lists are checked, and wrong element types or non-list values fail.
    """
    assert check([], subscribable_list_type[int], strict=True)
    assert check([], subscribable_list_type[str], strict=True)

    assert check([1, 2, 3], subscribable_list_type[int], strict=True)
    assert check(['1', '2', '3'], subscribable_list_type[str], strict=True)

    assert check([1, 2, 3, 4, [1, 2, 3]], subscribable_list_type[make_union(int, subscribable_list_type[int])], strict=True)

    assert not check([1, 2, 3], subscribable_list_type[str], strict=True)
    assert not check(['1', '2', 3], subscribable_list_type[int], strict=True)
    assert not check(['1', '2', '3'], subscribable_list_type[int], strict=True)

    assert not check((1, 2, 3), subscribable_list_type[str], strict=True)
    assert not check("123", subscribable_list_type[str], strict=True)

    assert not check([1, 2, 3, 4, [1, 2, '3']], subscribable_list_type[make_union(int, subscribable_list_type[int])], strict=True)


def test_dict_with_values_in_strict_mode(subscribable_dict_type, subscribable_list_type, make_union):
    """
    Strict dict handling checks real dicts recursively.

    Every key and value annotation is validated, including nested containers and unions, while empty dicts pass.
    """
    assert check({}, subscribable_dict_type[int, int], strict=True)
    assert check({}, subscribable_dict_type[str, str], strict=True)

    assert not check('kek', subscribable_dict_type[int, int], strict=True)
    assert not check('{}', subscribable_dict_type[str, str], strict=True)

    assert check({1: 1}, subscribable_dict_type[int, int], strict=True)
    assert check({'kek': 1}, subscribable_dict_type[str, int], strict=True)
    assert check({'kek': 'lol'}, subscribable_dict_type[str, str], strict=True)
    assert check({'kek': ['lol', 'kek']}, subscribable_dict_type[str, subscribable_list_type[str]], strict=True)
    assert check({'kek': ['lol', 1, 2, 3]}, subscribable_dict_type[str, subscribable_list_type[make_union(str, int)]], strict=True)
    assert check({123: ['lol', 1, 2, 3]}, subscribable_dict_type[int, subscribable_list_type[make_union(str, int)]], strict=True)
    assert check({123: {'lol': 'kek'}}, subscribable_dict_type[int, subscribable_dict_type[str, str]], strict=True)

    assert not check({1: 'kek'}, subscribable_dict_type[int, int], strict=True)
    assert not check({1: 1}, subscribable_dict_type[str, int], strict=True)
    assert not check({123: {'lol': 123}}, subscribable_dict_type[int, subscribable_dict_type[str, str]], strict=True)
    assert not check({123: {123: 'kek'}}, subscribable_dict_type[int, subscribable_dict_type[str, str]], strict=True)
    assert not check({123: ['lol', 1, 2, 3.0]}, subscribable_dict_type[int, subscribable_list_type[make_union(str, int)]], strict=True)


def test_tuple_with_values_in_strict_mode(subscribable_tuple_type, make_union):
    """
    Strict tuple checks validate tuple contents and enforce arity for fixed-length annotations.

    Variadic tuple annotations and tuple/union nesting are checked recursively; list and string inputs are rejected.
    """
    assert not check((), subscribable_tuple_type[int], strict=True)
    assert not check((), subscribable_tuple_type[str], strict=True)
    assert check((), subscribable_tuple_type[int, ...], strict=True)
    assert check((), subscribable_tuple_type[str, ...], strict=True)

    assert not check((1), subscribable_tuple_type[int, int], strict=True)
    assert not check(('kek'), subscribable_tuple_type[str, str], strict=True)

    assert check((1, 2, 3), subscribable_tuple_type[int, ...], strict=True)
    assert check(('1', '2', '3'), subscribable_tuple_type[str, ...], strict=True)

    assert check((1, 2, 3, 4, (1, 2, 3)), subscribable_tuple_type[make_union(int, subscribable_tuple_type[int, ...]), ...], strict=True)

    assert not check((1, 2, 3), subscribable_tuple_type[str, ...], strict=True)
    assert not check(('1', '2', 3), subscribable_tuple_type[int, ...], strict=True)
    assert not check(('1', '2', '3'), subscribable_tuple_type[int, ...], strict=True)

    assert not check((1, 2, 3), subscribable_tuple_type[str, ...], strict=True)
    assert not check([1, 2, 3], subscribable_tuple_type[str, ...], strict=True)
    assert not check(['1', '2', '3'], subscribable_tuple_type[str, ...], strict=True)
    assert not check("123", subscribable_tuple_type[str, ...], strict=True)

    assert not check((1, 2, 3, 4, (1, 2, '3')), subscribable_tuple_type[make_union(int, subscribable_tuple_type[int])], strict=True)


def test_lists_are_tuples_flag_is_true_in_strict_mode(subscribable_tuple_type, subscribable_list_type, subscribable_dict_type, make_union):
    """With strict=True and lists_are_tuples=True, lists can satisfy tuple annotations recursively, including inside unions, lists, and dict values."""
    assert check(["123"], subscribable_list_type[str], strict=True, lists_are_tuples=True)
    assert check(["123"], subscribable_tuple_type[str, ...], strict=True, lists_are_tuples=True)
    assert check(("123",), subscribable_tuple_type[str, ...], strict=True, lists_are_tuples=True)

    assert check([("123", "456"), ("123", "456")], subscribable_tuple_type[subscribable_tuple_type[str, ...], ...], strict=True, lists_are_tuples=True)
    assert check([("123", "456"), ["123", "456"]], subscribable_tuple_type[subscribable_tuple_type[str, ...], ...], strict=True, lists_are_tuples=True)
    assert check([["123", "456"], ["123", "456"]], subscribable_tuple_type[subscribable_tuple_type[str, ...], ...], strict=True, lists_are_tuples=True)
    assert check((["123", "456"], ["123", "456"]), subscribable_tuple_type[subscribable_tuple_type[str, ...], ...], strict=True, lists_are_tuples=True)
    assert check((("123", "456"), ("123", "456")), subscribable_tuple_type[subscribable_tuple_type[str, ...], ...], strict=True, lists_are_tuples=True)

    assert check(["123"], make_union(subscribable_tuple_type[str, ...], int), strict=True, lists_are_tuples=True)
    assert check([1, 2, 3], make_union(subscribable_tuple_type[str, ...], subscribable_tuple_type[int, ...]), strict=True, lists_are_tuples=True)

    assert check([[1, 2, 3], [4, 5, 6]], subscribable_list_type[make_union(subscribable_tuple_type[str, ...], subscribable_tuple_type[int, ...])], strict=True, lists_are_tuples=True)
    assert check([[1, 2, 3], [4, 5, 6]], subscribable_tuple_type[subscribable_tuple_type[int, ...], ...], strict=True, lists_are_tuples=True)
    assert check(([1, 2, 3], [4, 5, 6]), subscribable_tuple_type[make_union(subscribable_tuple_type[str, ...], subscribable_tuple_type[int, ...]), ...], strict=True, lists_are_tuples=True)
    assert check({1: [1, 2, 3], 2: [4, 5, 6]}, subscribable_dict_type[int, make_union(subscribable_tuple_type[str, ...], subscribable_tuple_type[int, ...])], strict=True, lists_are_tuples=True)


@pytest.mark.parametrize(
    'strict_mode',
    [
        False,
        True,
    ],
)
@pytest.mark.parametrize(
    'addictional_parameters',
    [
        {'pass_mocks': True},
        {},
    ],
)
def test_pass_mocks_when_its_on(strict_mode, list_type, addictional_parameters):
    """With default pass_mocks or pass_mocks=True, Mock and MagicMock pass unrelated hints in both strict modes."""
    assert check(Mock(), int, strict=strict_mode, **addictional_parameters)
    assert check(Mock(), str, strict=strict_mode, **addictional_parameters)
    assert check(Mock(), list_type, strict=strict_mode, **addictional_parameters)

    assert check(MagicMock(), int, strict=strict_mode, **addictional_parameters)
    assert check(MagicMock(), str, strict=strict_mode, **addictional_parameters)
    assert check(MagicMock(), list_type, strict=strict_mode, **addictional_parameters)

    assert check(Mock(), Mock, strict=strict_mode, **addictional_parameters)
    assert check(MagicMock(), MagicMock, strict=strict_mode, **addictional_parameters)


@pytest.mark.parametrize(
    'strict_mode',
    [
        False,
        True,
    ],
)
def test_pass_mocks_when_its_off(strict_mode, list_type):
    """Disabling pass_mocks rejects mocks for unrelated hints while keeping normal Mock and MagicMock isinstance matches."""
    assert not check(Mock(), int, strict=strict_mode, pass_mocks=False)
    assert not check(Mock(), str, strict=strict_mode, pass_mocks=False)
    assert not check(Mock(), list_type, strict=strict_mode, pass_mocks=False)

    assert not check(MagicMock(), int, strict=strict_mode, pass_mocks=False)
    assert not check(MagicMock(), str, strict=strict_mode, pass_mocks=False)
    assert not check(MagicMock(), list_type, strict=strict_mode, pass_mocks=False)

    assert check(Mock(), Mock, strict=strict_mode, pass_mocks=False)
    assert check(MagicMock(), MagicMock, strict=strict_mode, pass_mocks=False)


@pytest.mark.parametrize(
    'strict_mode',
    [
        False,
        True,
    ],
)
def test_denial_sentinel(strict_mode):
    """SentinelType accepts None, InnerNone, and InnerNoneType(...) instances in both strict modes while rejecting ordinary values."""
    assert not check(123, SentinelType, strict=strict_mode)
    assert not check('None', SentinelType, strict=strict_mode)

    assert check(None, SentinelType, strict=strict_mode)
    assert check(InnerNone, SentinelType, strict=strict_mode)
    assert check(InnerNoneType(), SentinelType, strict=strict_mode)
    assert check(InnerNoneType(123), SentinelType, strict=strict_mode)
    assert check(InnerNoneType('lol'), SentinelType, strict=strict_mode)


@pytest.mark.parametrize(
    'strict_mode',
    [
        False,
        True,
    ],
)
def test_denial_innernonetype(strict_mode):
    """InnerNoneType accepts InnerNone and any InnerNoneType(...) instance while rejecting ordinary values and real None."""
    assert not check(123, InnerNoneType, strict=strict_mode)
    assert not check('None', InnerNoneType, strict=strict_mode)
    assert not check(None, InnerNoneType, strict=strict_mode)

    assert check(InnerNone, InnerNoneType, strict=strict_mode)
    assert check(InnerNoneType(), InnerNoneType, strict=strict_mode)
    assert check(InnerNoneType(123), InnerNoneType, strict=strict_mode)
    assert check(InnerNoneType('lol'), InnerNoneType, strict=strict_mode)


@pytest.mark.parametrize(
    'strict_mode',
    [
        False,
        True,
    ],
)
def test_denial_innernone(strict_mode):
    """Concrete denial sentinels match only equal sentinel values, not merely other InnerNoneType instances, regardless of strict mode."""
    assert not check(123, InnerNoneType(123), strict=strict_mode)
    assert not check('None', InnerNoneType(123), strict=strict_mode)
    assert not check(None, InnerNoneType(123), strict=strict_mode)

    assert not check(123, InnerNoneType('123'), strict=strict_mode)
    assert not check('None', InnerNoneType('123'), strict=strict_mode)
    assert not check(None, InnerNoneType('123'), strict=strict_mode)

    assert not check(123, InnerNone, strict=strict_mode)
    assert not check('None', InnerNone, strict=strict_mode)
    assert not check(None, InnerNone, strict=strict_mode)

    assert not check(InnerNoneType(), InnerNoneType(), strict=strict_mode)
    assert not check(InnerNoneType(), InnerNone, strict=strict_mode)
    assert not check(InnerNoneType(123), InnerNoneType(1234), strict=strict_mode)
    assert not check(InnerNoneType('lol'), InnerNoneType('lol-kek'), strict=strict_mode)

    assert check(InnerNone, InnerNone, strict=strict_mode)
    assert check(InnerNoneType(123), InnerNoneType(123), strict=strict_mode)
    assert check(InnerNoneType('lol'), InnerNoneType('lol'), strict=strict_mode)
