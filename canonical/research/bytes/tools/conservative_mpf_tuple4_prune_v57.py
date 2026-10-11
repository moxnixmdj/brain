from pathlib import Path
import ast, hashlib, json

BASE = "589f1dea175b4e541634ca6bcf252db889507da4a9fd318acb5d684fa297221c"
TARGET = "5af543694a726b13666f7dbff68417eb8d4f600dc4d0e244c3e16e17ee6a2da3"
PATH = "mpmath/ctx_mp_python.py"
QUAL = "_mpf.__new__"

NEW = '''def __new__(cls, val=fzero, **kwargs):
        prec, rounding = cls.context._prec_rounding
        if kwargs or type(val) is not tuple or len(val) != 4:
            raise NotImplementedError("outside Brain bounded exact-symbolic contract")
        if val not in (finf, fninf, fnan):
            sign, man, exp, bc = val
            val = normalize(sign, MPZ(man), exp, bc, prec, rounding)
        v = new(cls)
        v._mpf_ = val
        return v
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
    stack, hits = [], []

    class V(ast.NodeVisitor):
        def visit_ClassDef(self, n):
            stack.append(n.name)
            self.generic_visit(n)
            stack.pop()
        def visit_FunctionDef(self, n):
            q = ".".join(stack + [n.name])
            if q == QUAL:
                hits.append(n)
                return
            stack.append(n.name)
            self.generic_visit(n)
            stack.pop()
        visit_AsyncFunctionDef = visit_FunctionDef

    V().visit(tree)
    if len(hits) != 1:
        raise RuntimeError(f"{QUAL} identity count: {len(hits)}")
    n = hits[0]
    a = n.lineno - 1
    b = n.end_lineno
    old = "".join(lines[a:b])
    lines[a:b] = [NEW]
    out = "".join(lines)
    compile(out, str(p), "exec")
    p.write_text(out)

    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "saved": len(old.encode()) - len(NEW.encode()),
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
        "changed": [[PATH, QUAL]],
    }

if __name__ == "__main__":
    import sys
    print(json.dumps(apply(sys.argv[1]), indent=2))
