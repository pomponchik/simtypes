from collections.abc import Hashable
from datetime import date, datetime
from inspect import isclass
from json import JSONDecodeError, loads
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
    overload,
)

from simtypes import check
from simtypes.typing import ExpectedType


def convert_single_value(value: str, expected_type: Type[ExpectedType]) -> ExpectedType:  # noqa: PLR0912, PLR0911, C901
    if expected_type is type(None):
        if value in ('null', 'None'):
            return None
        raise TypeError(f'The string "{value}" cannot be interpreted as None.')

    if expected_type is str:
        return value  # type: ignore[return-value]

    if expected_type is bool:
        if value in ('True', 'true', 'yes'):
            return True  # type: ignore[return-value]
        if value in ('False', 'false', 'no'):
            return False  # type: ignore[return-value]
        raise TypeError(f'The string "{value}" cannot be interpreted as a boolean value.')

    if expected_type is int:
        try:
            return int(value)  # type: ignore[return-value]
        except ValueError as e:
            raise TypeError(f'The string "{value}" cannot be interpreted as an integer.') from e

    elif expected_type is float:
        if value in {'∞', '+∞'}:
            value = 'inf'
        elif value == '-∞':
            value = '-inf'

        try:
            return float(value)  # type: ignore[return-value]
        except ValueError as e:
            raise TypeError(f'The string "{value}" cannot be interpreted as a floating point number.') from e

    if expected_type is datetime:
        try:
            return datetime.fromisoformat(value)  # type: ignore[return-value]
        except ValueError as e:
            raise TypeError(f'The string "{value}" cannot be interpreted as a datetime object.') from e

    if expected_type is date:
        try:
            return date.fromisoformat(value)  # type: ignore[return-value]
        except ValueError as e:
            raise TypeError(f'The string "{value}" cannot be interpreted as a date object.') from e

    if not isclass(expected_type):
        raise ValueError('The type must be a valid type object.')

    raise TypeError(f'Serialization of the type {expected_type.__name__} you passed is not supported. Supported types: int, float, bool, list, dict, tuple.')


# TODO: try to abstract fix_lists(), fix_tuples() and fix_dicts() to one function
def fix_lists(collection: List[Any], type_hint_arguments: Tuple[Any, ...]) -> Optional[List[Any]]:
    if not isinstance(collection, list) or len(type_hint_arguments) >= 2:
        return None

    if not len(type_hint_arguments):
        return collection

    type_hint = type_hint_arguments[0]
    origin_type = get_origin(type_hint)
    type_hint_arguments = get_args(type_hint)

    result = []
    for element in collection:
        if any(x in (dict, list, tuple) for x in (type_hint, origin_type)):
            fixed_element = fix_iterable_types(element, type_hint_arguments, origin_type, type_hint)
            if fixed_element is None:
                return None
            result.append(fixed_element)
        elif type_hint is date or type_hint is datetime:
            if not isinstance(element, str):
                return None
            try:
                result.append(convert_single_value(element, type_hint))
            except TypeError:
                return None
        else:
            result.append(element)

    return result


def fix_tuples(collection: List[Any], type_hint_arguments: Tuple[Any, ...]) -> Optional[Tuple[Any, ...]]:  # noqa: PLR0912, PLR0911, C901
    if not isinstance(collection, list):
        return None

    if not len(type_hint_arguments):
        return tuple(collection)

    result = []

    if len(type_hint_arguments) == 2 and type_hint_arguments[1] is Ellipsis:
        type_hint = type_hint_arguments[0]
        origin_type = get_origin(type_hint)
        type_hint_arguments = get_args(type_hint)

        for element in collection:
            if any(x in (dict, list, tuple) for x in (type_hint, origin_type)):
                fixed_element = fix_iterable_types(element, type_hint_arguments, origin_type, type_hint)
                if fixed_element is None:
                    return None
                result.append(fixed_element)
            elif type_hint is date or type_hint is datetime:
                if not isinstance(element, str):
                    return None
                try:
                    result.append(convert_single_value(element, type_hint))
                except TypeError:
                    return None
            else:
                result.append(element)

    else:
        if len(collection) != len(type_hint_arguments):
            return None

        for type_hint, element in zip(type_hint_arguments, collection):
            type_hint_arguments = get_args(type_hint)
            origin_type = get_origin(type_hint)
            if any(x in (dict, list, tuple) for x in (type_hint, origin_type)):
                fixed_element = fix_iterable_types(element, type_hint_arguments, origin_type, type_hint)
                if fixed_element is None:
                    return None
                result.append(fixed_element)
            elif type_hint is date or type_hint is datetime:
                if not isinstance(element, str):
                    return None
                try:
                    result.append(convert_single_value(element, type_hint))
                except TypeError:
                    return None
            else:
                result.append(element)

    return tuple(result)


def fix_dicts(collection: List[Any], type_hint_arguments: Tuple[Any, ...]) -> Optional[Dict[Hashable, Any]]:
    if not isinstance(collection, dict) or len(type_hint_arguments) >= 3 or len(type_hint_arguments) == 1:
        return None

    if not len(type_hint_arguments):
        return collection

    key_type_hint = type_hint_arguments[0]
    value_type_hint = type_hint_arguments[1]

    result = {}
    for key, element in collection.items():
        pair = {'key': (key, key_type_hint), 'value': (element, value_type_hint)}
        pair_result = {}

        for name, meta in pair.items():
            element, type_hint = meta  # noqa: PLW2901
            origin_type = get_origin(type_hint)
            type_hint_arguments = get_args(type_hint)
            if any(x in (dict, list, tuple) for x in (type_hint, origin_type)):
                fixed_element = fix_iterable_types(element, type_hint_arguments, origin_type, type_hint)
                if fixed_element is None:
                    return None
                subresult = fixed_element
            elif type_hint is date or type_hint is datetime:
                if not isinstance(element, str):
                    return None
                try:
                    subresult = convert_single_value(element, type_hint)
                except TypeError:
                    return None
            else:
                subresult = element
            pair_result[name] = subresult

        result[pair_result['key']] = pair_result['value']

    return result


def fix_iterable_types(collection: Union[List[Any], Tuple[Any, ...], Dict[Hashable, Any]], type_hint_arguments: Tuple[Any, ...], origin_type: Any, expected_type: Any) -> Optional[Union[List[Any], Tuple[Any, ...], Dict[Hashable, Any]]]:
    if list in (origin_type, expected_type):
        result = fix_lists(collection, type_hint_arguments)  # type: ignore[arg-type]
    elif tuple in (origin_type, expected_type):
        result = fix_tuples(collection, type_hint_arguments)  # type: ignore[assignment, arg-type]
        if result is not None:
            result = tuple(result)  # type: ignore[assignment]
    elif dict in (origin_type, expected_type):
        result = fix_dicts(collection, type_hint_arguments)  # type: ignore[assignment, arg-type]
    else:
        return None  # pragma: no cover

    return result


@overload
def from_string(value: str, expected_type: None) -> None:
    ...  # pragma: no cover


@overload
def from_string(value: str, expected_type: Type[ExpectedType]) -> ExpectedType:
    ...  # pragma: no cover


def from_string(value: str, expected_type: Optional[Type[ExpectedType]]) -> Optional[ExpectedType]:
    if not isinstance(value, str):
        raise ValueError(f'You can only pass a string as a string. You passed {type(value).__name__}.')

    if expected_type is None:
        return convert_single_value(value, type(None))

    if expected_type is Any:  # type: ignore[comparison-overlap]
        return value  # type: ignore[return-value]

    origin_type = get_origin(expected_type)

    if any(x in (dict, list, tuple) for x in (expected_type, origin_type)):
        type_name = expected_type.__name__ if origin_type is None else origin_type.__name__
        error = TypeError(f'The string "{value}" cannot be interpreted as a {type_name} of the specified format.')

        try:
            result = loads(value)
        except JSONDecodeError as e:
            raise error from e

        result = fix_iterable_types(result, get_args(expected_type), origin_type, expected_type)
        if result is None:
            raise error

        if check(result, expected_type, strict=True):  # type: ignore[operator]
            return result  # type: ignore[no-any-return]
        raise error

    return convert_single_value(value, expected_type)
