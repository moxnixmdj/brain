from pathlib import Path
import ast, hashlib, json, sys

BASE = "bdc69baf4e75991e6b5abd1ec271886c43a02ac08a422656374f19122ffb9bd0"
TARGET = "719e9d956c4b24f54474ebd0dea30fe3e2352e6037743ec5a07b911cdec071e2"

FAIL_CLOSED = [
    ("mpmath/libmp/libmpf.py", "mpf_sum"),
    ("mpmath/libmp/libmpf.py", "round_int"),
    ("mpmath/libmp/libmpf.py", "from_str"),
    ("mpmath/libmp/libmpf.py", "mpf_mod"),
    ("mpmath/ctx_mp_python.py", "_mpc.__pow__"),
    ("mpmath/ctx_mp_python.py", "PythonMPContext._wrap_specfun"),
    ("mpmath/ctx_mp_python.py", "_mpc.__add__"),
    ("mpmath/ctx_mp_python.py", "_mpc.__sub__"),
    ("mpmath/ctx_mp_python.py", "_mpc.__div__"),
    ("mpmath/libmp/libmpf.py", "to_int"),
]

REPAIR = ("sympy/printing/str.py", "StrPrinter._print_Rational")

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

def repair_rational_printer(root):
    rel, qual = REPAIR
    p, text, lines, n = _find(root, rel, qual)
    a, b = n.body[0].lineno - 1, n.body[-1].end_lineno
    ind = " " * n.body[0].col_offset
    old = "".join(lines[a:b])
    new = (
        ind + "if expr.q == 1:\n"
        + ind + "    return str(expr.p)\n"
        + ind + "else:\n"
        + ind + '    if self._settings.get("sympy_integers", False):\n'
        + ind + '        return "S(%s)/%s" % (expr.p, expr.q)\n'
        + ind + '    return "%s/%s" % (expr.p, expr.q)\n'
    )
    lines[a:b] = [new]
    out = "".join(lines)
    compile(out, str(p), "exec")
    p.write_text(out)
    return len(new.encode()) - len(old.encode())

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    cuts = [(rel, q, fail_close(root, rel, q)) for rel, q in FAIL_CLOSED]
    repair_delta = repair_rational_printer(root)
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "fail_closed_saved_bytes": sum(x[2] for x in cuts),
        "repair_added_bytes": repair_delta,
        "net_saved_bytes": sum(x[2] for x in cuts) - repair_delta,
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
        "cuts": cuts,
        "repair": REPAIR,
    }

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1]), indent=2))
