"""Key-order-invariant, type-exact SHA-256 digest of a JSON document.

Reuses ``freeze``/``digest`` from canonical/research/bytes/tools/semantic_digest_v1.py: object keys
are sorted, floats are hashed by their exact hex form, and ints, floats, booleans, null, arrays,
and objects are all distinguished.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader

SOURCE = "canonical/research/bytes/tools/semantic_digest_v1.py"
SCHEMA = "PROJECT_BRAIN_JSON_SEMANTIC_DIGEST_V1"


def run(args, root):
    root = pathlib.Path(root).resolve()
    src = loader.safe_repo_path(root, args.get("input_path"))
    out = loader.safe_repo_path(root, args.get("output_path"))
    if not src.is_file() or src.suffix.lower() != ".json":
        raise RuntimeError("JSON_INPUT_REQUIRED")
    if out.suffix.lower() != ".json" or out == src:
        raise RuntimeError("DISTINCT_JSON_OUTPUT_REQUIRED")
    digest = loader.load_symbol(root, SOURCE, "digest")
    raw_in = src.read_bytes()
    value = json.loads(raw_in.decode("utf-8"), parse_constant=lambda c: (_ for _ in ()).throw(ValueError("NON_FINITE_JSON_NUMBER:" + c)))
    semantic = digest(value)
    doc = {"schema": SCHEMA, "input_path": src.relative_to(root).as_posix(), "input_sha256": hashlib.sha256(raw_in).hexdigest(),
           "semantic_digest": semantic, "top_level_type": type(value).__name__}
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    verified = json.loads(out.read_text(encoding="utf-8"))["semantic_digest"] == semantic == digest(json.loads(raw_in.decode("utf-8")))
    return {
        "adapter": "research_json_semantic_digest_v1",
        "status": "PASS" if verified else "FAIL",
        "input_path": doc["input_path"],
        "semantic_digest": semantic,
        "output_path": out.relative_to(root).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": verified,
        "research_source": SOURCE,
    }
