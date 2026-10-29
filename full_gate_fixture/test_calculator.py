import sys
sys.path.insert(0, '.')
from calculator import add, subtract, calculate_total


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(5, 3) == 2


def test_calculate_total():
    assert calculate_total([1, 2, 3]) == 6
