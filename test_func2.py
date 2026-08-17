"""Unit tests for the is_prime function in func2.ipynb."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def is_prime():
    """Load is_prime from the notebook code cells."""
    notebook_path = Path(__file__).with_name("func2.ipynb")
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    namespace = {}
    for cell in notebook["cells"]:
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            exec(source, namespace)

    return namespace["is_prime"]


@pytest.mark.parametrize("value", [-10, -1, 0, 1])
def test_is_prime_returns_false_for_values_less_than_or_equal_to_one(
    is_prime,
    value,
):
    assert is_prime(value) is False


def test_is_prime_returns_true_for_two(is_prime):
    assert is_prime(2) is True


@pytest.mark.parametrize("value", [4, 10, 100])
def test_is_prime_returns_false_for_even_numbers_greater_than_two(
    is_prime,
    value,
):
    assert is_prime(value) is False


@pytest.mark.parametrize("value", [9, 15, 25])
def test_is_prime_returns_false_for_odd_composite_numbers(is_prime, value):
    assert is_prime(value) is False


@pytest.mark.parametrize("value", [3, 11, 97])
def test_is_prime_returns_true_for_odd_prime_numbers(is_prime, value):
    assert is_prime(value) is True


@pytest.mark.parametrize("value", ["7", 7.0, None])
def test_is_prime_raises_value_error_for_non_integer_values(is_prime, value):
    with pytest.raises(ValueError, match="n must be an integer"):
        is_prime(value)
