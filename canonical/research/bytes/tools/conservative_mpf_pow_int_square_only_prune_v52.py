from pathlib import Path
import ast, hashlib, json, sys

BASE = "bab0e710a20ac41743feadf3a979e2c9d8d08fd621a42e4799ba658badb7ef37"
TARGET = "5cfdaf054fafabd04894396739defc82fed40ec3aba24b2f1b06030421b9c62f"
PATH = "mpmath/libmp/libmpf.py"
QUAL = "mpf_pow_int"

NEW = '''    n = int(n)
    if n != 2:
        raise NotImplementedError("outside Brain bounded exact-symbolic contract")
    sign, man, exp, bc = s
    if not man:
        if s == finf or s == fninf:
            return finf
        if s == fzero:
            return fzero
        return fnan
    man = man * man
    if man == 1:
        return (0, MPZ_ONE, exp + exp, 1)
    bc = bc + bc - 2
    bc += bctable[int(man >> bc)]
    return normalize1(0, man, exp + exp, bc, prec, rnd)
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
