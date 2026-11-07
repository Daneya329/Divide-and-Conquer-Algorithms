
import contextlib
import io
import math
import os
import time

from algos import projectSignup as cp
from algos import lim as ks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIRS = {
    "closest": os.path.join(BASE_DIR, "datasets", "closest_pair"),
    "karatsuba": os.path.join(BASE_DIR, "datasets", "karatsuba"),
}


# ----------------------------------------------------------------------------
# Files
# ----------------------------------------------------------------------------
def natural_key(name):
    digits = "".join(ch for ch in name if ch.isdigit())
    return (int(digits) if digits else 0, name)


def list_datasets(kind):
    folder = DATASET_DIRS[kind]
    if not os.path.isdir(folder):
        return []
    files = [f for f in os.listdir(folder) if f.lower().endswith(".txt")]
    return [os.path.join(folder, f) for f in sorted(files, key=natural_key)]


def detect_kind(path):
    """'closest' if lines look like 'x y', 'karatsuba' if they hold one integer each."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = []
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
            if len(lines) >= 2:
                break
    if not lines:
        raise ValueError("The file is empty.")
    if len(lines[0].split()) == 2:
        return "closest"
    if len(lines) >= 2 and lines[0].isdigit() and lines[1].isdigit():
        return "karatsuba"
    raise ValueError("Unrecognised file format.\n"
                     "Closest pair: one 'x y' point per line.\n"
                     "Karatsuba: two integers on separate lines.")


def load_numbers(path):
    """Same parsing rules as the original Karatsuba program."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read().strip()
    lines = raw.splitlines()
    if len(lines) < 2:
        raise ValueError("The selected text file format must have two numbers on separate lines.")
    return int(lines[0].strip()), int(lines[1].strip())


def dataset_summary(path):
    """Short description used in the dataset list."""
    try:
        kind = detect_kind(path)
        if kind == "closest":
            with open(path, encoding="utf-8", errors="replace") as f:
                count = sum(1 for line in f if line.strip())
            return f"{count} pts"
        n, m = load_numbers(path)
        return f"{max(len(str(n)), len(str(m)))} dig"
    except Exception:
        return "?"


# ----------------------------------------------------------------------------
# Closest pair
# ----------------------------------------------------------------------------
class CPNode:
    __slots__ = ("id", "parent", "depth", "px", "n", "mid", "d", "children")

    def __init__(self, nid, parent, depth, px):
        self.id = nid
        self.parent = parent
        self.depth = depth
        self.px = px
        self.n = len(px)
        self.mid = px[self.n // 2] if self.n > 3 else None
        self.d = None
        self.children = []


def trace_closest_pair(points):
    """Run the ORIGINAL closest_pair while recording every recursive call.

    Returns (distance, nodes, events, seconds) where events is a list of
    ('enter' | 'exit', node) in execution order.
    """
    nodes, events, stack = [], [], []
    original = cp.closest_pair

    def recorder(px, py):
        parent = stack[-1] if stack else None
        node = CPNode(len(nodes), parent, len(stack), px)
        nodes.append(node)
        if parent is not None:
            parent.children.append(node)
        events.append(("enter", node))
        stack.append(node)
        try:
            node.d = original(px, py)
        finally:
            stack.pop()
        events.append(("exit", node))
        return node.d

    px = sorted(points, key=lambda p: p.x)
    py = sorted(points, key=lambda p: p.y)
    cp.closest_pair = recorder
    try:
        start = time.perf_counter()
        d = recorder(px, py)
        elapsed = time.perf_counter() - start
    finally:
        cp.closest_pair = original
    return d, nodes, events, elapsed


def time_closest_pair(points):
    """Plain (un-traced) run of the original algorithm, as in the original GUI."""
    start = time.perf_counter()
    px = sorted(points, key=lambda p: p.x)
    py = sorted(points, key=lambda p: p.y)
    d = cp.closest_pair(px, py)
    return d, time.perf_counter() - start


def find_pair_with_distance(points, d, tol=1e-9):
    """Locate one pair of points whose distance equals d (for highlighting only)."""
    pts = sorted(points, key=lambda p: (p.x, p.y))
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if pts[j].x - pts[i].x > d + tol:
                break
            if abs(cp.distance(pts[i], pts[j]) - d) <= tol * max(1.0, d):
                return pts[i], pts[j]
    return None


def strip_points(node):
    """Points of a sub-problem lying inside the strip |x - mid.x| < delta."""
    if node.mid is None or len(node.children) < 2:
        return [], None
    delta = min(c.d for c in node.children)
    pts = [p for p in node.px if abs(p.x - node.mid.x) < delta]
    pts.sort(key=lambda p: p.y)
    return pts, delta


# ----------------------------------------------------------------------------
# Karatsuba
# ----------------------------------------------------------------------------
class KNode:
    __slots__ = ("id", "parent", "depth", "n", "m", "result", "children", "role")

    def __init__(self, nid, parent, depth, n, m, role):
        self.id = nid
        self.parent = parent
        self.depth = depth
        self.n = n
        self.m = m
        self.role = role
        self.result = None
        self.children = []

    @property
    def is_base(self):
        return self.n < 10 or self.m < 10

    def split(self):
        """Same split rule the original karatsuba() uses (for display only)."""
        num_digits = max(len(str(self.n)), len(str(self.m)))
        half = (num_digits + 1) // 2
        s = 10 ** half
        return half, self.n // s, self.n % s, self.m // s, self.m % s


def trace_karatsuba(n, m, capture_output=True):
    """Run the ORIGINAL karatsuba() recording each call; its print() trace is captured.

    Returns (product, nodes, trace_text, seconds).
    """
    nodes, stack = [], []
    original = ks.karatsuba
    roles = ("w = a·c", "y = b·d", "z' = (a+b)(c+d)")

    def recorder(a, b, depth=0):
        parent = stack[-1] if stack else None
        role = roles[len(parent.children)] if parent is not None else "root"
        node = KNode(len(nodes), parent, depth, a, b, role)
        nodes.append(node)
        if parent is not None:
            parent.children.append(node)
        stack.append(node)
        try:
            node.result = original(a, b, depth)
        finally:
            stack.pop()
        return node.result

    buf = io.StringIO() if capture_output else open(os.devnull, "w", encoding="utf-8")
    ks.karatsuba = recorder
    try:
        with contextlib.redirect_stdout(buf):
            start = time.perf_counter()
            product = recorder(n, m, 0)
            elapsed = time.perf_counter() - start
    finally:
        ks.karatsuba = original
    text = buf.getvalue() if capture_output else ""
    buf.close()
    return product, nodes, text, elapsed


def time_karatsuba(n, m):
    """Un-traced run; the original print statements are sent to os.devnull."""
    with open(os.devnull, "w", encoding="utf-8") as sink, contextlib.redirect_stdout(sink):
        start = time.perf_counter()
        product = ks.karatsuba(n, m, depth=0)
        elapsed = time.perf_counter() - start
    return product, elapsed


# ----------------------------------------------------------------------------
# Benchmark
# ----------------------------------------------------------------------------
def benchmark_file(path, kind=None):
    kind = kind or detect_kind(path)
    name = os.path.basename(path)
    if kind == "closest":
        points = cp.load_points(path)
        d, elapsed = time_closest_pair(points)
        _, nodes, _, _ = trace_closest_pair(points)
        b0 = time.perf_counter()
        expected = cp.brute_force(points)
        brute_time = time.perf_counter() - b0
        pair = find_pair_with_distance(points, d)
        return {
            "algorithm": "Closest Pair", "file": name, "size": len(points),
            "size_label": f"{len(points)} points",
            "result": cp.format_number(d),
            "detail": f"{pair[0].show()} – {pair[1].show()}" if pair else "",
            "time_ms": elapsed * 1000, "baseline_ms": brute_time * 1000,
            "calls": len(nodes), "depth": max(nd.depth for nd in nodes),
            "verified": math.isclose(d, expected, rel_tol=1e-12, abs_tol=1e-12),
        }
    n, m = load_numbers(path)
    product, elapsed = time_karatsuba(n, m)
    _, nodes, _, _ = trace_karatsuba(n, m, capture_output=False)
    b0 = time.perf_counter()
    expected = n * m
    builtin_time = time.perf_counter() - b0
    digits = len(str(product))
    ps = str(product)
    return {
        "algorithm": "Karatsuba", "file": name, "size": max(len(str(n)), len(str(m))),
        "size_label": f"{len(str(n))}×{len(str(m))} digits",
        "result": f"{digits}-digit product",
        "detail": ps[:12] + "…" + ps[-6:] if digits > 20 else ps,
        "time_ms": elapsed * 1000, "baseline_ms": builtin_time * 1000,
        "calls": len(nodes), "depth": max(nd.depth for nd in nodes),
        "verified": product == expected,
    }
