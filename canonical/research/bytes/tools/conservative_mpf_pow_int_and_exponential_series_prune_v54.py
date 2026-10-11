from pathlib import Path
import ast, hashlib, json, sys

BASE = "ae9187bc15193fe340e77a88d9d400f51ec798dec638ac435aca1f2862c14cfe"
TARGET = "7c52fd9d44d688c6fc10fd7797a5ba33da5c6b34ee54860cabb318bb2b00fb01"

REPLACEMENTS = {
    ("mpmath/libmp/libmpf.py", "mpf_pow_int"): '''    n = int(n)
    if n == 2:
        _, man, exp, bc = s
        if not man:
            return fzero
        man = man * man
        if man == 1:
            return (0, MPZ_ONE, exp + exp, 1)
        bc = bc + bc - 2
        bc += bctable[int(man >> bc)]
        return normalize1(0, man, exp + exp, bc, prec, rnd)
    raise NotImplementedError("outside Brain bounded exact-symbolic contract")
''',
    ("mpmath/libmp/libelefun.py", "exponential_series"): '''    if x < 0 or type != 2 or prec >= EXP_SERIES_U_CUTOFF:
        raise NotImplementedError("outside Brain bounded exact-symbolic contract")
    r = int(0.5 * prec ** 0.5)
    xmag = bitcount(x) - prec
    r = max(0, xmag + r)
    extra = 10 + 2 * max(r, -xmag)
    wp = prec + extra
    x <<= extra - r
    one = MPZ_ONE << wp
    x2 = a = x * x >> wp
    x4 = x2 * x2 >> wp
    s0 = s1 = MPZ_ZERO
    k = 2
    while a:
        a //= (k - 1) * k
        s0 += a
        k += 2
        a //= (k - 1) * k
        s1 += a
        k += 2
        a = a * x4 >> wp
    s1 = x2 * s1 >> wp
    c = s1 - s0 + one
    pshift = wp - 1
    for i in xrange(r):
        c = (c * c >> pshift) - one
    s = isqrt_fast(abs((one << wp) - c * c))
    return (c >> extra, s >> extra)
''',
}

def manifest(root):
    root = Path(root)
    items = []
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        items.append({"path": p.relative_to(root).as_posix(), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    mb = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(mb).hexdigest(), items, mb

def _find(root, rel, qual):
    p = Path(root) / rel
    text = p.read_text()
    lines = text.splitlines(True)
    tree = ast.parse(text)
    stack, hits = [], []
    class V(ast.NodeVisitor):
        def visit_ClassDef(self, n):
            stack.append(n.name); self.generic_visit(n); stack.pop()
        def visit_FunctionDef(self, n):
            q = ".".join(stack + [n.name])
            if q == qual:
                hits.append(n); return
            stack.append(n.name); self.generic_visit(n); stack.pop()
        visit_AsyncFunctionDef = visit_FunctionDef
    V().visit(tree)
    if len(hits) != 1:
        raise RuntimeError((rel, qual, len(hits)))
    return p, text, lines, hits[0]

def replace_body(root, rel, qual, new):
    p, text, lines, n = _find(root, rel, qual)
    a, b = n.body[0].lineno - 1, n.body[-1].end_lineno
    old = "".join(lines[a:b])
    lines[a:b] = [new]
    out = "".join(lines)
    compile(out, str(p), "exec")
    p.write_text(out)
    return len(old.encode()) - len(new.encode())

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    cuts = [(rel, qual, replace_body(root, rel, qual, new)) for (rel, qual), new in REPLACEMENTS.items()]
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {"manifest": after, "saved_raw_python_bytes": sum(x[2] for x in cuts), "raw_python_source_bytes": sum(x["bytes"] for x in items), "cuts": cuts}

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1]), indent=2))
