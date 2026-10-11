from pathlib import Path
import ast, hashlib, json, sys

BASE = "bab0e710a20ac41743feadf3a979e2c9d8d08fd621a42e4799ba658badb7ef37"
TARGET = "9cbaa7546f02a00ea1fffc90be3973d8ee09944d448a2441e2cf1d801c22c538"
SELECT = [
    ("sympy/core/intfunc.py", "integer_log"),
    ("sympy/simplify/simplify.py", "dotprodsimp.<locals>.count_ops_alg"),
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

def _find(root, rel, target):
    p = Path(root) / rel
    text = p.read_text()
    lines = text.splitlines(True)
    tree = ast.parse(text)
    hits = []
    stack = []
    class V(ast.NodeVisitor):
        def visit_ClassDef(self, n):
            q = (stack[-1][0] + (".<locals>." if stack[-1][1] == "func" else ".") + n.name) if stack else n.name
            stack.append((q, "class"))
            self.generic_visit(n)
            stack.pop()
        def visit_FunctionDef(self, n):
            q = (stack[-1][0] + (".<locals>." if stack[-1][1] == "func" else ".") + n.name) if stack else n.name
            if q == target:
                hits.append(n)
            stack.append((q, "func"))
            self.generic_visit(n)
            stack.pop()
        visit_AsyncFunctionDef = visit_FunctionDef
    V().visit(tree)
    if len(hits) != 1:
        raise RuntimeError((rel, target, len(hits)))
    return p, lines, hits[0]

def patch(root, rel, target):
    p, lines, n = _find(root, rel, target)
    a = n.body[0].lineno - 1
    b = n.body[-1].end_lineno
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
    cuts = [(rel, qual, patch(root, rel, qual)) for rel, qual in SELECT]
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest drift: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "saved": sum(x[2] for x in cuts),
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
        "cuts": cuts,
    }

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1]), indent=2))
