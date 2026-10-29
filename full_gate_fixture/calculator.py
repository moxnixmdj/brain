def add(a, b):
    return a - b


def subtract(a, b):
    return a - b


def calculate_total(numbers):
    total = 0
    for n in numbers:
        total = add(total, n)
    return total
