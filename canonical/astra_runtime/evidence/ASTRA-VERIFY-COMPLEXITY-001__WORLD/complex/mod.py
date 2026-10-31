"""Two functions, one flat and one not."""


def flat(values):
    return sum(values)


def nested(values):
    total = 0
    for value in values:
        if value > 0:
            for inner in range(value):
                if inner % 2:
                    total += inner
    return total
