from pathlib import Path
import ast, hashlib, json

BASE = "42c3255fe51bc6e7c30afd912d3fd3aabc422742b4671eed1e7b7fc50ce290f9"
TARGET = "ea2958321bf8c5b35f6f3f6d98bee0f8498a52f51dff6826d76632e8b5a61940"
PATH = "sympy/core/intfunc.py"

class StripDocstrings(ast.NodeTransformer):
    def _strip(self, node):
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.body:
                node.body = [ast.Pass()]
        return node
    def visit_Module(self, node):
        self.generic_visit(node); return self._strip(node)
    def visit_FunctionDef(self, node):
        self.generic_visit(node); return self._strip(node)
    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node); return self._strip(node)
    def visit_ClassDef(self, node):
        self.generic_visit(node); return self._strip(node)

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
    text = p.read_text("utf-8")
    tree = ast.parse(text, type_comments=True)
    target = StripDocstrings().visit(tree)
    ast.fix_missing_locations(target)
    out = ast.unparse(target) + "\n"
    compile(out, str(p), "exec")
    parsed = ast.parse(out, type_comments=True)
    if ast.dump(parsed, include_attributes=False) != ast.dump(target, include_attributes=False):
        raise RuntimeError("post-strip AST reconstruction mismatch")
    old = len(text.encode())
    p.write_text(out, "utf-8", newline="")
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "saved_bytes": old - len(out.encode()),
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
        "changed_path": PATH,
    }

if __name__ == "__main__":
    import sys
    print(json.dumps(apply(sys.argv[1]), indent=2))
