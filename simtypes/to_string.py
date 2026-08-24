from datetime import date, datetime
from json import dumps
from typing import Any, NoReturn

from simtypes.errors import NonRoundTrippableKeyError

JSON_DUMPS_KEY_TYPES = (str, int, float, bool, type(None))
SUPPORTED_SCALAR_TYPES = (*JSON_DUMPS_KEY_TYPES, date, datetime)


def raise_type_error_for_unsupported_value(value: Any) -> NoReturn:
    raise TypeError(
        f'Serialization of the type {type(value).__name__} is not supported. '
        'Supported types: str, int, float, bool, NoneType, date, datetime, list, tuple, dict.',
    )


def check_collection(value: Any, strict_json_dict: bool) -> None:
    value_type = type(value)
    if any(value_type is scalar_type for scalar_type in SUPPORTED_SCALAR_TYPES):
        return
    if value_type is list or value_type is tuple:
        for element in value:
            check_collection(element, strict_json_dict)
        return
    if value_type is not dict:
        raise_type_error_for_unsupported_value(value)

    for key, element in value.items():
        key_type = type(key)
        if key_type is not str:
            if not any(key_type is json_key_type for json_key_type in JSON_DUMPS_KEY_TYPES):
                raise TypeError(
                    f'Dictionary key {key!r} of type {key_type.__name__} cannot be serialized to JSON.',
                )
            if strict_json_dict:
                raise NonRoundTrippableKeyError(
                    f'Dictionary key {key!r} of type {key_type.__name__} cannot be serialized without changing '
                    'its type. Pass strict_json_dict=False to allow lossy serialization.',
                )
        check_collection(element, strict_json_dict)


def to_string(value: Any, *, strict_json_dict: bool = True) -> str:
    if type(strict_json_dict) is not bool:
        raise TypeError('strict_json_dict must be a bool.')

    value_type = type(value)

    if value_type is str or value_type is int or value_type is float or value_type is bool:
        return str(value)
    if value_type is type(None):
        return 'None'
    if value_type is date or value_type is datetime:
        return str(value.isoformat())

    if value_type is list or value_type is tuple or value_type is dict:
        check_collection(value, strict_json_dict)
        return dumps(value, default=lambda temporal_value: temporal_value.isoformat())

    raise_type_error_for_unsupported_value(value)
