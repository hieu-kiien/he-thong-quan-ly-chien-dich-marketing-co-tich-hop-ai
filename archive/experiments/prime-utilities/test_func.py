import importlib.util
from pathlib import Path

import pytest


FUNC_PATH = Path(__file__).with_name("func.py")


def load_func_module():
    spec = importlib.util.spec_from_file_location("func", FUNC_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


func = load_func_module()


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (1, 2, 3),
        (10, 20, 30),
        (-1, -2, -3),
        (-5, 3, -2),
        (5, -3, 2),
    ],
)
def test_add_integer_numbers(a, b, expected):
    assert func.add(a, b) == expected


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (0, 0, 0),
        (0, 7, 7),
        (7, 0, 7),
        (0, -7, -7),
    ],
)
def test_add_with_zero_edge_cases(a, b, expected):
    assert func.add(a, b) == expected


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (1.5, 2.5, 4.0),
        (-1.5, 1.5, 0.0),
        (0.1, 0.2, 0.3),
    ],
)
def test_add_float_numbers(a, b, expected):
    assert func.add(a, b) == pytest.approx(expected)


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("Hello, ", "World!", "Hello, World!"),
        ([1, 2], [3, 4], [1, 2, 3, 4]),
        ((1, 2), (3, 4), (1, 2, 3, 4)),
    ],
)
def test_add_concatenates_supported_sequence_types(a, b, expected):
    assert func.add(a, b) == expected


@pytest.mark.parametrize(
    "a, b",
    [
        (1, "2"),
        ("1", 2),
        ([1], 2),
        (None, 1),
    ],
)
def test_add_raises_type_error_for_unsupported_type_combinations(a, b):
    with pytest.raises(TypeError):
        func.add(a, b)
