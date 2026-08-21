"""module_a: some types and a helper function, plus one unrelated function
that should never show up in a slice of order_total()."""

TAX_RATE = 0.08


class Item:
    def __init__(self, name: str, price: float):
        self.name = name
        self.price = price

    def display_price(self) -> str:
        return f"${self.price:.2f}"


class Cart:
    def __init__(self):
        self.items: list[Item] = []

    def add(self, item: Item) -> None:
        self.items.append(item)

    def subtotal(self) -> float:
        return sum(i.price for i in self.items)


def format_currency(amount: float) -> str:
    return f"${amount:.2f}"


def unrelated_utility(x: int, y: int) -> int:
    """Not reachable from order_total() — should never appear in its slice."""
    return x * y + 7
