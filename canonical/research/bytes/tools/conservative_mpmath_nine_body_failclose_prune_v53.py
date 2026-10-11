from pathlib import Path
import ast, hashlib, json, sys

BASE = "5cfdaf054fafabd04894396739defc82fed40ec3aba24b2f1b06030421b9c62f"
TARGET = "ae9187bc15193fe340e77a88d9d400f51ec798dec638ac435aca1f2862c14cfe"

FAIL_CLOSED = [
    ("mpmath/ctx_mp_python.py", "_mpc.__eq__"),
    ("mpmath/ctx_mp_python.py", "_mpc.__new__"),
    ("mpmath/ctx_mp_python.py", "_mpc.__rmul__"),
    ("mpmath/ctx_mp_python.py", "_mpf.__rdiv__"),
    ("mpmath/ctx_mp_python.py", "_mpf.__rsub__"),
    ("mpmath/libmp/libmpf.py", "gmpy_mpf_mul_int"),
    ("mpmath/libmp/libmpf.py", "python_mpf_mul_int"),
    ("mpmath/libmp/libmpf.py", "str_to_man_exp"),
    ("mpmath/libmp/libmpf.py", "strict_normalize1"),
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
