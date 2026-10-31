def compute_total(items):
    return sum(x * 2 for x in items)


def render(items):
    parts = [str(x) for x in items]
    joined = ",".join(parts)
    return joined
