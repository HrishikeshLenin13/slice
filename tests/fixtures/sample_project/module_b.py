from tests.fixtures.sample_project.module_a import Cart, TAX_RATE, format_currency


def order_total(cart: Cart) -> str:
    """The slicing target used throughout the tests. Its true dependency
    closure is: Cart (type + subtotal call), TAX_RATE (global), and
    format_currency (callee) — nothing from unrelated_utility()."""
    subtotal = cart.subtotal()
    total = subtotal * (1 + TAX_RATE)
    return format_currency(total)


def checkout(cart: Cart) -> str:
    """A caller of order_total(), used to test caller inclusion."""
    return order_total(cart)


HANDLERS = {
    "total": order_total,
    "checkout": checkout,
}


def dynamic_dispatch(action: str, cart: Cart) -> str:
    """Deliberately unsound: the real call target depends on a runtime
    string, so static analysis cannot enumerate it. Slice must flag this
    function rather than silently omit the true dependency (whichever
    HANDLERS entry gets picked at runtime)."""
    handler = HANDLERS[action]
    return handler(cart)


def reflective_call(cart: Cart, method_name: str) -> float:
    """Also deliberately unsound: getattr() with a runtime name."""
    method = getattr(cart, method_name)
    return method()
