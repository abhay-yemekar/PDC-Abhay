BASE = "FORMULAQSOLUTIONS"

def _circular_slice(start: int, length: int) -> str:
    L = len(BASE)
    return "".join(BASE[(start + k) % L] for k in range(length))

def build_diamond(n: int) -> list[str]:
    if n < 1:
        return []
    m = n if n % 2 == 1 else n + 1
    mid = m // 2

    lines, start = [], 0
    for i in range(m):
        width = 2 * i + 1 if i <= mid else 2 * (m - 1 - i) + 1
        raw = _circular_slice(start, width)
        pad = (m - width) // 2
        lines.append(" " * pad + raw)
        start = (start + 1) % len(BASE)
    return lines

def as_block(n: int) -> str:
    return "\n".join(build_diamond(n))
