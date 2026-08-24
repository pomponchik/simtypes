<details>
  <summary>ⓘ</summary>

[![Downloads](https://static.pepy.tech/badge/simtypes/month)](https://pepy.tech/project/simtypes)
[![Downloads](https://static.pepy.tech/badge/simtypes)](https://pepy.tech/project/simtypes)
[![Coverage Status](https://coveralls.io/repos/github/mutating/simtypes/badge.svg?branch=main)](https://coveralls.io/github/mutating/simtypes?branch=main)
[![Lines of code](https://sloc.xyz/github/mutating/simtypes/?category=code)](https://github.com/boyter/scc/)
[![Hits-of-Code](https://hitsofcode.com/github/mutating/simtypes?branch=main&label=Hits-of-Code&exclude=docs/)](https://hitsofcode.com/github/mutating/simtypes/view?branch=main)
[![Test-Package](https://github.com/mutating/simtypes/actions/workflows/tests_and_coverage.yml/badge.svg)](https://github.com/mutating/simtypes/actions/workflows/tests_and_coverage.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/simtypes.svg)](https://pypi.python.org/pypi/simtypes)
[![PyPI version](https://badge.fury.io/py/simtypes.svg)](https://badge.fury.io/py/simtypes)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/mutating/simtypes)

</details>

![logo](https://raw.githubusercontent.com/mutating/simtypes/develop/docs/assets/logo_2.svg)

Python type checking tools are usually very complex. In this case, we have thrown out almost all the places where there is a lot of complexity, and left only the most obvious and necessary things for runtime use.


## Table of contents

- [**Why?**](#why)
- [**Installation**](#installation)
- [**Type checking**](#type-checking)
- [**Special types**](#special-types)
- [**String deserialization**](#string-deserialization)
- [**String serialization**](#string-serialization)


## Why?

It's been a long time since static type checking tools like [`mypy`](https://github.com/python/mypy) for `Python` have been available, and they've become very complex. The typing system has also become noticeably more complicated, providing us with more and more new types of annotations, new syntax and other tools. It seems that `Python` devs procrastinate endlessly, postponing all the really important [`CPython`](https://github.com/python/cpython) improvements in order to add more garbage to [`typing`](https://docs.python.org/3/library/typing.html).

A separate difficulty arises for those who try to use type annotations at runtime. Many data types make sense only in the context of static validation, and there is no way to verify these aspects at runtime. And some checks, although theoretically possible, would be extremely expensive. For example, to verify the validity of annotation `List[int]` in relation to a list, you would need to iterate over all its elements to make sure that none of them violates the contract from the annotation.

So, why do we need this package? There is only one function where you can pass a type or a type annotation + a specific value, and you will find out if one corresponds to the other. That's it! You can use this feature as a support when creating runtime type checking tools, however, we do not offer these tools here. You decide for yourself whether to wrap this function in syntactic sugar like decorators with automatic type checking.

Also, we are not trying to cover the whole chasm of semantics that, for example, `mypy` can track. Our approach is to make type checking as stupid as possible. This is the only way to avoid the stupid typing games that complex tools impose on us.

What exactly does this library support:

- The basis of everything is the simplest type checking via [`isinstance`](https://docs.python.org/3/library/functions.html#isinstance). If you don't use any special types from [`typing`](https://docs.python.org/3/library/typing.html), expect direct type matching.
- [`Union`](https://docs.python.org/3/library/typing.html#typing.Union) support. You can combine the two types through a logical OR.
- Checking the [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional) type and `None` as an annotation.
- Using [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) annotation.

And that's what's not here:

- Supports types with complex semantics from the [`typing`](https://docs.python.org/3/library/typing.html) module.
- Checking the contents of collections. In normal mode, collections are checked only for the base type (in strict mode, the contents for some base collections are also checked).
- Support for string annotations.

If you need more complex semantics, use static validation tools. If you need strange and expensive runtime checks that try to confuse static semantics by adding thousands of exceptions, use other runtime tools. Use this library if you need a MINIMUM.


## Installation

You can install [`simtypes`](https://pypi.python.org/pypi/simtypes) using pip:

```bash
pip install simtypes
```

You can also quickly try out this and other packages without having to install using [instld](https://github.com/pomponchik/instld).


## Type checking

Import the `check` function:

```python
from simtypes import check
```

And pass there two arguments, a value + a type or type annotation:

```python
print(check(1, int))
#> True
print(check(1, str))
#> False
print(check(1, Any))
#> True
print(check('kek', Any))
#> True
print(check(1, List))
#> False
print(check([1], List))
#> True
print(check([1], List[int]))
#> True
print(check(['kek'], List[int]))  # Attention! The content of the list is not checked in normal mode.
#> True
print(check(1, Optional[int]))
#> True
print(check(None, Optional[int]))
#> True
print(check(1, Optional[str]))
#> False
print(check(1, None))
#> False
print(check(None, None))
#> True
```

> ↑ As you can see, the function returns `True` or `False`, depending on whether the value matches its annotation.

In normal mode, the contents of collections are not checked. However, if strict mode is activated, the contents of lists, dicts and tuples will also start to be checked:

```python
print(check(['kek'], List[str], strict=True))
#> True
print(check({'lol': 'kek'}, Dict[str, str], strict=True))
#> True
print(check([1, 2, 3], List[str], strict=True))
#> False
print(check({'lol': 123}, Dict[str, str], strict=True))
#> False
print(check((1, 2, 3), Tuple[int, int, int], strict=True))
#> True
print(check((1, 2, 3), Tuple[int, ...], strict=True))
#> True
print(check((1, 2, "text"), Tuple[int, ...], strict=True))
#> False
```

Mock objects are skipped during verification by default. If you want to disable this, use `pass_mocks=False`:

```python
from unittest.mock import Mock, MagicMock

print(check(Mock(), str))
#> True
print(check(MagicMock(), int))
#> True

print(check(Mock(), str, pass_mocks=False))
#> False
print(check(MagicMock(), int, pass_mocks=False))
#> False
```


## Special types

Some non-trivial runtime checks can be shifted to the type system. This library offers several additional types, which can be checked for membership via the check function:

- `NaturalNumber` — as the name implies, only objects of type `int` greater than zero will be checked for this type.
- `NonNegativeInt` — the same as `NaturalNumber`, but `0` is also a valid value.

Here are some usage examples:

```python
from simtypes import NaturalNumber, NonNegativeInt

print(check(13, NaturalNumber))
#> True
print(check(0, NaturalNumber))
#> False
print(check(13, NonNegativeInt))
#> True
print(check(0, NonNegativeInt))
#> True
print(check(-11, NonNegativeInt))
#> False
```

In addition to other types, simtypes supports an extended type of sentinels from the [`denial`](https://github.com/mutating/denial/) library. In short, this is an extended `None`, for cases when we need to distinguish between situations where a value is undefined and situations where it is defined as undefined. Similar to `None`, objects of the `InnerNoneType` class can be used as type hints for themselves:

```python
from denial import InnerNoneType

print(check(InnerNoneType('key'), InnerNoneType('key')))
#> True
```


## String deserialization

The library also provides basic deserialization. Conversion of strings into several basic types in various combinations is supported:

- `str` - any string can be interpreted as a `str` type.
- `None` or `type(None)` - the strings `"null"` and `"None"` are interpreted as `None`.
- `int` - any integers.
- `float` - any floating-point numbers, including infinities and [`NaN`](https://en.wikipedia.org/wiki/NaN).
- `bool` - the strings `"yes"`, `"True"`, and `"true"` are interpreted as `True`, while `"no"`, `"False"`, or `"false"` are interpreted as `False`.
- `date` or `datetime` - strings representing, respectively, dates or dates + time in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format.
- `list` - lists in [`JSON`](https://en.wikipedia.org/wiki/JSON) format are expected.
- `tuple` - lists in [`JSON`](https://en.wikipedia.org/wiki/JSON) format are expected.
- `dict` - dicts in [`JSON`](https://en.wikipedia.org/wiki/JSON) format are expected.

Examples:

```python
from simtypes import from_string

# ints
print(from_string('13', int))
#> 13
print(from_string('-13', int))
#> -13

# floats
print(from_string('13', float))
#> 13.0
print(from_string('13.5', float))
#> 13.5
print(from_string('nan', float))
#> nan
print(from_string('∞', float))
#> inf
print(from_string('-∞', float))
#> -inf
print(from_string('inf', float))
#> inf
print(from_string('-inf', float))
#> -inf

# strings
print(from_string('I am the danger', str))
#> "I am the danger"
print(from_string('I am the danger', Any))  # Any is interpreted as a string.
#> "I am the danger"

# None
print(from_string('null', None))
#> None
print(from_string('None', type(None)))
#> None

# bools
print(from_string('yes', bool))
#> True
print(from_string('no', bool))
#> False
print(from_string('True', bool))
#> True

# dates and datetimes
from datetime import datetime, date

print(from_string('2026-01-27', date))
#> 2026-01-27
print(from_string('2026-01-27 01:47:29.982044', datetime))
#> 2026-01-27 01:47:29.982044

# collections
print(from_string('[1, 2, 3]', list[int]))
#> [1, 2, 3]
print(from_string('[1, 2, 3]', tuple[int, ...]))
#> (1, 2, 3)
print(from_string('{"123": [1, 2, 3]}', dict[str, tuple[int, ...]]))
#> {'123': (1, 2, 3)}
```

> 👀 If the passed string cannot be interpreted as an object of the specified type, a `TypeError` exception will be raised.


## String serialization

The library also provides basic serialization. The `to_string` function is the reverse operation for `from_string`: it converts supported Python values into strings.

The following exact types are supported:

- `str` - strings are returned unchanged.
- `NoneType` - `None` is converted to the string `"None"`.
- `int` - integers use their standard Python string representation.
- `float` - floating-point numbers use their standard Python string representation, including infinities, [`NaN`](https://en.wikipedia.org/wiki/NaN), and negative zero.
- `bool` - boolean values are converted to `"True"` or `"False"`.
- `date` or `datetime` - dates and datetimes are converted to [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) strings.
- `list` - lists are converted to [`JSON`](https://en.wikipedia.org/wiki/JSON) arrays.
- `tuple` - tuples are converted to [`JSON`](https://en.wikipedia.org/wiki/JSON) arrays.
- `dict` - dictionaries with exact string keys are converted to [`JSON`](https://en.wikipedia.org/wiki/JSON) objects.

Inside collections, `None` becomes `null`, boolean values use the JSON spelling, and `date` and `datetime` values become ISO-formatted JSON strings. Subclasses of supported types and all other types raise `TypeError`.

The full function signature is:

```python
def to_string(value: Any, *, strict_json_dict: bool = True) -> str:
    ...
```

Examples:

```python
from datetime import date, datetime
from typing import Dict, List, Tuple

from simtypes import NonRoundTrippableKeyError, from_string, to_string

# scalars
print(to_string('text'))
#> text
print(to_string(13))
#> 13
print(to_string(True))
#> True
print(to_string(None))
#> None
print(to_string(date(2026, 1, 22)))
#> 2026-01-22
print(to_string(datetime(2026, 1, 22, 3, 4, 5)))
#> 2026-01-22T03:04:05

# collections
value = {
    'items': (1, None),
    'dates': [date(2026, 1, 22)],
}

print(to_string(value))
#> {"items": [1, null], "dates": ["2026-01-22"]}

# round-trip
integer = 13
print(from_string(to_string(integer), int))
#> 13

items = [(1, 2), (3, 4)]
items_type = List[Tuple[int, ...]]
print(from_string(to_string(items), items_type))
#> [(1, 2), (3, 4)]

temporal = {'dates': [date(2026, 1, 22)]}
temporal_type = Dict[str, List[date]]
print(from_string(to_string(temporal), temporal_type))
#> {'dates': [datetime.date(2026, 1, 22)]}

# dictionary keys
try:
    to_string({1: 'value'})
except NonRoundTrippableKeyError as error:
    print(error)
#> Dictionary key 1 of type int cannot be serialized without changing its type. Pass strict_json_dict=False to allow lossy serialization.

serialized = to_string({1: 'value'}, strict_json_dict=False)
print(serialized)
#> {"1": "value"}
print(from_string(serialized, Dict[str, str]))
#> {'1': 'value'}
```

For round-trip, retain the complete expected type, including generic arguments, and pass it to `from_string`. The serialized text contains no type information: the same JSON array can represent a Python list or tuple. A round-trip through `Any` preserves only values whose exact type is `str`, because `from_string(..., Any)` returns the serialized text unchanged.

By default, dictionaries accept only exact string keys. Pass `strict_json_dict=False` to allow `int`, `float`, `bool`, and `None` keys. These keys are converted to JSON property names, so their original types are not preserved. Different Python keys may also produce duplicate JSON property names; the serialized text retains the duplicates, but `from_string` retains only the last value. Other key types, including `date` and `datetime`, raise `TypeError` in both modes.

> 👀 There are two additional round-trip limitations:
>
> - `NaN` must be compared semantically because `NaN != NaN`. The sign of `-0.0` is preserved.
> - Datetime serialization preserves calendar and time fields, microseconds, and UTC offsets that are zero or at least one second in magnitude. A nonzero subsecond offset becomes zero during deserialization without changing the wall time. ISO strings do not preserve `fold` or a `tzinfo` object's identity or custom name.
