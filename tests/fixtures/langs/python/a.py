class A:
    """doc"""

    def m(self, x: int) -> int:
        return x + 1


def f() -> int:
    return A().m(1)
