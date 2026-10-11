from pathlib import Path
import ast, hashlib, json, sys

BASE = "ae9187bc15193fe340e77a88d9d400f51ec798dec638ac435aca1f2862c14cfe"
TARGET = "0580cb1632eed1142a6b01580898c3736a1d7c9a65b4dbdf277699fd821dc803"
PATH = "mpmath/libmp/libelefun.py"
QUAL = "exponential_series"

NEW = '''    if x < 0 or type != 2 or prec >= EXP_SERIES_U_CUTOFF:
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
'''

def manifest(root):
    root = Path(root)
    items = []
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        items.append({
            "path": p.relative_to(root).as_posix(),
            "bytes": len(b),
            "sha256": hashlib.sha256(b).hexdigest(),
        })
    mb = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(mb).hexdigest(), items, mb

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    p = root / PATH
    text = p.read_text()
    lines = text.splitlines(True)
    tree = ast.parse(text)
    hits = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == QUAL]
    if len(hits) != 1:
        raise RuntimeError((QUAL, len(hits)))
    n = hits[0]
    a, b = n.body[0].lineno - 1, n.body[-1].end_lineno
    old = "".join(lines[a:b])
    lines[a:b] = [NEW]
    out = "".join(lines)
    compile(out, str(p), "exec")
    p.write_text(out)
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest drift: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "saved": len(old.encode()) - len(NEW.encode()),
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
        "changed": [[PATH, QUAL]],
    }

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1]), indent=2))
