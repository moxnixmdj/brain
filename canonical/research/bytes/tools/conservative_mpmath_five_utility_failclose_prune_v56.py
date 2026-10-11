from pathlib import Path
import ast, hashlib, json, sys

BASE = "a401c2d9595af738a360f9df69da3162c4663e1624917e3d5d6a2b6bcd2ba3ef"
TARGET = "589f1dea175b4e541634ca6bcf252db889507da4a9fd318acb5d684fa297221c"

FAIL_CLOSED = [
    ("mpmath/libmp/libmpf.py", "from_bstr"),
    ("mpmath/libmp/libmpf.py", "mpf_rand"),
    ("mpmath/libmp/libmpf.py", "mpf_min_max"),
    ("mpmath/libmp/libmpf.py", "to_rational"),
    ("mpmath/libmp/libmpf.py", "from_Decimal"),
]

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

def fail_close(root, rel, qual):
    p, text, lines, n = _find(root, rel, qual)
    a, b = n.body[0].lineno - 1, n.body[-1].end_lineno
    ind = " " * n.body[0].col_offset
    old = "".join(lines[a:b])
    new = ind + 'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
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
    cuts = [(rel, q, fail_close(root, rel, q)) for rel, q in FAIL_CLOSED]
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "saved_raw_python_bytes": sum(x[2] for x in cuts),
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
        "cuts": cuts,
    }

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1]), indent=2))
