from pathlib import Path
import hashlib, io, json, tokenize

BASE = "0145aceb14e86c89ab4a2b52bfc581d92650ed7bed4905ef98918434bc7c4f1d"
TARGET = "9da2ae566f6faa2db8ccaaac3b60423feb790115952c386a68df2c09ff140abc"

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
    saved = 0
    touched = 0
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        lines = b.splitlines(keepends=True)
        string_lines = set()
        for t in tokenize.tokenize(io.BytesIO(b).readline):
            if t.type == tokenize.STRING:
                string_lines.update(range(t.start[0], t.end[0] + 1))
        nb = b"".join(
            line
            for line_number, line in enumerate(lines, 1)
            if line.strip() or line_number in string_lines
        )
        if nb != b:
            compile(nb.decode("utf-8"), str(p), "exec")
            p.write_bytes(nb)
            saved += len(b) - len(nb)
            touched += 1
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {
        "manifest": after,
        "touched_python_files": touched,
        "saved_bytes": saved,
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
    }

if __name__ == "__main__":
    import sys
    print(json.dumps(apply(sys.argv[1]), indent=2))
