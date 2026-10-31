"""Models."""

def line_total(item):
    return item.price_cents * item.qty
class Item:
    def __init__(self, price_cents, qty=1):
        self.price_cents = price_cents
        self.qty = qty

    def total(self):
        return self.price_cents * self.qty
