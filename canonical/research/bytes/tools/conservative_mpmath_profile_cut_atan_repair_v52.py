from pathlib import Path
import ast, hashlib, json, sys

BASE = "bab0e710a20ac41743feadf3a979e2c9d8d08fd621a42e4799ba658badb7ef37"
TARGET = "c6520868f23d4509eb403bf5724c56a18a21c048ebd0e231374611615d55ee8b"

FAIL_CLOSED = [
    ("mpmath/ctx_mp_python.py", "_mpf.__rsub__"),
    ("mpmath/ctx_mp_python.py", "_mpf.__rdiv__"),
    ("mpmath/ctx_mp_python.py", "_mpc.__new__"),
    ("mpmath/ctx_mp_python.py", "_mpc.__eq__"),
    ("mpmath/ctx_mp_python.py", "_mpc.__rmul__"),
    ("mpmath/libmp/libmpf.py", "strict_normalize1"),
    ("mpmath/libmp/libmpf.py", "gmpy_mpf_mul_int"),
    ("mpmath/libmp/libmpf.py", "python_mpf_mul_int"),
    ("mpmath/libmp/libmpf.py", "str_to_man_exp"),
]

WRAP_PATH = "mpmath/ctx_mp_python.py"
WRAP_QUAL = "PythonMPContext._wrap_libmp_function"
WRAP_BODY = '        if mpf_f.__name__ == "mpf_atan":\n            def f(x, **kwargs):\n                if not hasattr(x, "_mpf_"):\n                    raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n                prec, rounding = ctx._prec_rounding\n                return ctx.make_mpf(mpf_f(x._mpf_, prec, rounding))\n        else:\n            def f(x, **kwargs):\n                raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n        return f\n'

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

def replace_body(root, rel, qual, new_body):
    p, text, lines, n = _find(root, rel, qual)
    a, b = n.body[0].lineno - 1, n.body[-1].end_lineno
    old = "".join(lines[a:b])
    lines[a:b] = [new_body]
    out = "".join(lines)
    compile(out, str(p), "exec")
    p.write_text(out)
    return len(old.encode()) - len(new_body.encode())

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    saved = []
    for rel, qual in FAIL_CLOSED:
        _, _, _, n = _find(root, rel, qual)
        indent = " " * n.body[0].col_offset
        body = indent + 'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
        saved.append([rel, qual, replace_body(root, rel, qual, body)])
    saved.append([WRAP_PATH, WRAP_QUAL, replace_body(root, WRAP_PATH, WRAP_QUAL, WRAP_BODY)])
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest drift: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
        "net_saved_bytes": sum(x[2] for x in saved),
        "changes": saved,
    }

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1]), indent=2))
