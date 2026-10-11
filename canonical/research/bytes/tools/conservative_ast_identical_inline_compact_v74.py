from pathlib import Path
import ast, collections, hashlib, io, json, re, tokenize

BASE = "20e5e5154a06ce58225594f0c2ad76fcc8abe7177b72803898a6aafaad45e849"
TARGET = "b0b5024dbd831e104d25373dc2bc2c14feed5892624d3cae4d5100bfaa1eb18f"
PATTERNS = (
    (re.compile(rb"[ \t]*([,;:])[ \t]*"), rb"\1"),
    (re.compile(rb"[ \t]*([\(\[\{])[ \t]*"), rb"\1"),
    (re.compile(rb"[ \t]*([\)\]\}])[ \t]*"), rb"\1"),
    (re.compile(rb"[ \t]*([+\-*/%@<>=|&^~]+)[ \t]*"), rb"\1"),
)

def manifest(root):
    root = Path(root)
    items = []
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        items.append({"path": p.relative_to(root).as_posix(), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    mb = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(mb).hexdigest(), items, mb

def _ast(source):
    return ast.dump(ast.parse(source, type_comments=True), include_attributes=False)

def _candidate(b):
    lines = b.splitlines(keepends=True)
    protected = collections.defaultdict(list)
    for t in tokenize.tokenize(io.BytesIO(b).readline):
        if t.type not in (tokenize.STRING, tokenize.COMMENT):
            continue
        sl, sc = t.start
        el, ec = t.end
        if sl == el:
            protected[sl].append((sc, ec))
        else:
            protected[sl].append((sc, len(lines[sl - 1].rstrip(b"\r\n"))))
            for ln in range(sl + 1, el):
                protected[ln].append((0, len(lines[ln - 1].rstrip(b"\r\n"))))
            protected[el].append((0, ec))
    out = []
    for ln, line in enumerate(lines, 1):
        if line.endswith(b"\r\n"):
            content, newline = line[:-2], b"\r\n"
        elif line.endswith(b"\n"):
            content, newline = line[:-1], b"\n"
        elif line.endswith(b"\r"):
            content, newline = line[:-1], b"\r"
        else:
            content, newline = line, b""
        indent_end = re.match(rb"^[ \t]*", content).end()
        intervals = [(0, indent_end)] + sorted(protected.get(ln, ()))
        merged = []
        for a, z in intervals:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], z))
            else:
                merged.append((a, z))
        parts = []
        pos = 0
        for a, z in merged:
            if pos < a:
                segment = content[pos:a]
                for pattern, replacement in PATTERNS:
                    segment = pattern.sub(replacement, segment)
                parts.append(segment)
            parts.append(content[a:z])
            pos = z
        if pos < len(content):
            segment = content[pos:]
            for pattern, replacement in PATTERNS:
                segment = pattern.sub(replacement, segment)
            parts.append(segment)
        out.append(b"".join(parts) + newline)
    return b"".join(out)

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    changed = rejected = saved = 0
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        nb = _candidate(b)
        if nb == b:
            continue
        try:
            compile(nb.decode("utf-8"), str(p), "exec")
            if _ast(b.decode("utf-8")) != _ast(nb.decode("utf-8")):
                raise ValueError("AST drift")
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
    return {
        "manifest": after,
        "changed_python_files": changed,
        "rejected_candidate_files": rejected,
        "saved_bytes": saved,
        "raw_python_source_bytes": sum(x["bytes"] for x in items),
    }

if __name__ == "__main__":
    import sys
    print(json.dumps(apply(sys.argv[1]), indent=2))