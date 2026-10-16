"""Deterministic SHA-256 manifest of every ``*.py`` file under a repository directory.

Reuses ``manifest`` from canonical/research/bytes/tools/conservative_algebraicnumber_prune_v42.py
(the variant copied verbatim into 41 research tools) through the import-safety gate.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader

SOURCE = "canonical/research/bytes/tools/conservative_algebraicnumber_prune_v42.py"
SCHEMA = "PROJECT_BRAIN_PYTHON_SOURCE_TREE_MANIFEST_V1"


def run(args, root):
    root = pathlib.Path(root).resolve()
    tree = loader.safe_repo_path(root, args.get("source_root"))
    out = loader.safe_repo_path(root, args.get("output_path"))
    if not tree.is_dir():
        raise RuntimeError("SOURCE_TREE_DIRECTORY_REQUIRED")
    if out.suffix.lower() != ".json":
        raise RuntimeError("JSON_OUTPUT_REQUIRED")
    manifest = loader.load_symbol(root, SOURCE, "manifest")
    digest, items, canonical_bytes = manifest(tree)
    if not items:
        raise RuntimeError("NO_PYTHON_SOURCES_UNDER_ROOT")
    doc = {
        "schema": SCHEMA,
        "root_path": tree.relative_to(root).as_posix(),
        "manifest_sha256": digest,
        "file_count": len(items),
        "total_bytes": sum(int(i["bytes"]) for i in items),
        "items": items,
    }
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    reread = json.loads(out.read_text(encoding="utf-8"))
    rebuilt = json.dumps(reread["items"], sort_keys=True, separators=(",", ":")).encode()
    verified = hashlib.sha256(rebuilt).hexdigest() == digest and rebuilt == canonical_bytes
    return {
        "adapter": "research_python_tree_manifest_v1",
        "status": "PASS" if verified else "FAIL",
        "root_path": doc["root_path"],
        "manifest_sha256": digest,
        "file_count": doc["file_count"],
        "total_bytes": doc["total_bytes"],
        "output_path": out.relative_to(root).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": verified,
        "research_source": SOURCE,
    }
