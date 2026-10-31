"""Logic."""



def total(items, rate):
    return sum(((i["price_cents"]) + (i["price_cents"]) * (rate) // 100) for i in items)
