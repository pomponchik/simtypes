from simtypes import NaturalNumber, check


def test_basic_isinstance():
    """Direct isinstance recognizes positive ints as NaturalNumber and rejects zero, negatives, and the sampled string input."""
    assert isinstance(5, NaturalNumber)
    assert isinstance(1, NaturalNumber)

    assert not isinstance(0, NaturalNumber)
    assert not isinstance(-1, NaturalNumber)
    assert not isinstance("5", NaturalNumber)


def test_basic_check():
    """check accepts positive integers as NaturalNumber and rejects zero, negatives, and the sampled string input through the public API."""
    assert check(5, NaturalNumber)
    assert check(1, NaturalNumber)

    assert not check(0, NaturalNumber)
    assert not check(-1, NaturalNumber)
    assert not check("5", NaturalNumber)
