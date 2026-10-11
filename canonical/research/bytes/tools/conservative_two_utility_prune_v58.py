from pathlib import Path
import ast, hashlib, json

BASE = "5af543694a726b13666f7dbff68417eb8d4f600dc4d0e244c3e16e17ee6a2da3"
TARGET = "409dd682c47e2a25acc2915af689650757f02cf828826a9854d06c0e386bb1c1"
SELECT = [
    ("mpmath/libmp/libmpf.py", "strict_normalize"),
    ("mpmath/libmp/libmpf.py", "mpf_frexp"),
]

def manifest(root):
    root = Path(root)
    items = []
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        items.append({"path": p.relative_to(root).as_posix(), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    mb = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(mb).hexdigest(), items, mb

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    cuts = []
    for rel, qual in SELECT:
        p = root / rel
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
        n = hits[0]
        a, b = n.body[0].lineno - 1, n.body[-1].end_lineno
        ind = " " * n.body[0].col_offset
        old = "".join(lines[a:b])
        new = ind + 'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
        lines[a:b] = [new]
        out = "".join(lines)
        compile(out, str(p), "exec")
        p.write_text(out)
        cuts.append((rel, qual, len(old.encode()) - len(new.encode())))
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {"manifest": after, "saved": sum(x[2] for x in cuts), "raw_python_source_bytes": sum(x["bytes"] for x in items), "cuts": cuts}

if __name__ == "__main__":
    import sys
    print(json.dumps(apply(sys.argv[1]), indent=2))
