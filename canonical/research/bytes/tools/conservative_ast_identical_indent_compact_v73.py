from pathlib import Path
import ast, hashlib, io, json, re, tokenize

BASE = "9da2ae566f6faa2db8ccaaac3b60423feb790115952c386a68df2c09ff140abc"
TARGET = "20e5e5154a06ce58225594f0c2ad76fcc8abe7177b72803898a6aafaad45e849"

def manifest(root):
    root = Path(root)
    items = []
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        items.append({"path": p.relative_to(root).as_posix(), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    mb = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(mb).hexdigest(), items, mb

def _ast_identity(a, b):
    return ast.dump(ast.parse(a, type_comments=True), include_attributes=False) == ast.dump(ast.parse(b, type_comments=True), include_attributes=False)

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    changed = rejected = saved = 0
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        lines = b.splitlines(keepends=True)
        string_lines = set()
        for t in tokenize.tokenize(io.BytesIO(b).readline):
            if t.type == tokenize.STRING:
                string_lines.update(range(t.start[0], t.end[0] + 1))
        out = []
        for line_number, line in enumerate(lines, 1):
            if line_number not in string_lines:
                m = re.match(br"^( +)", line)
                if m:
                    n = len(m.group(1))
                    line = b"\t" * (n // 4) + b" " * (n % 4) + line[n:]
            out.append(line)
        nb = b"".join(out)
        if nb == b:
            continue
        try:
            compile(nb.decode("utf-8"), str(p), "exec")
            if not _ast_identity(b.decode("utf-8"), nb.decode("utf-8")):
                rejected += 1
                continue
        except Exception:
            rejected += 1
            continue
        p.write_bytes(nb)
        changed += 1
        saved += len(b) - len(nb)
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {"manifest": after, "changed_python_files": changed, "rejected_candidate_files": rejected, "saved_bytes": saved, "raw_python_source_bytes": sum(x["bytes"] for x in items)}

if __name__ == "__main__":
    import sys
    print(json.dumps(apply(sys.argv[1]), indent=2))
