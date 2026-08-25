def is_prime(n: int) -> bool
    if not isinstance(n, int):
        raise ValueError("n must be an integer.")

    if n <= 1:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    divisor = 3
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 2

    return True


def sum_of_primes(numbers: list[int]) -> int:
    if not isinstance(numbers, list):
        raise TypeError("numbers must be a list.")

    total = 0
    for number in numbers:
        if not isinstance(number, int):
            raise ValueError("All elements in numbers must be integers.")
        if is_prime(number):
            total += number

    return total
