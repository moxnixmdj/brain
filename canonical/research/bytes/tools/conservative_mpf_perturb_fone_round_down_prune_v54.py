from pathlib import Path
import ast, hashlib, json, sys

BASE = "ae9187bc15193fe340e77a88d9d400f51ec798dec638ac435aca1f2862c14cfe"
TARGET = "0a4f02588b1058752991ab6156e3f28fe0514eed79ad85292c5aa39d546935f3"
PATH = "mpmath/libmp/libmpf.py"
QUAL = "mpf_perturb"
NEW = '''    if x != fone or rnd != round_down or eps_sign not in (0, 1):
        raise NotImplementedError("outside Brain bounded exact-symbolic contract")
    if eps_sign:
        return mpf_add(x, (1, MPZ_ONE, -prec, 1), prec, rnd)
    return mpf_pos(x, prec, rnd)
'''

def manifest(root):
    root = Path(root); items = []
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
    p = root / PATH
    text = p.read_text(); lines = text.splitlines(True); tree = ast.parse(text)
    hits = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == QUAL]
    if len(hits) != 1:
        raise RuntimeError((QUAL, len(hits)))
    n = hits[0]
    a, b = n.body[0].lineno - 1, n.body[-1].end_lineno
    old = "".join(lines[a:b]); lines[a:b] = [NEW]
    out = "".join(lines); compile(out, str(p), "exec"); p.write_text(out)
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest drift: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {"manifest": after, "saved": len(old.encode()) - len(NEW.encode()), "raw_python_source_bytes": sum(x["bytes"] for x in items)}

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1]), indent=2))
