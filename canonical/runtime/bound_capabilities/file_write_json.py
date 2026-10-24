#!/usr/bin/env python3
"""Write a JSON document to a repository-local file. Python stdlib, nothing else.

`file_write_text` gave the registry a producer for text, and with it a chain could
start.  But a JSON file is not a text file that happens to look like JSON: the
promise `json.file.available` makes is that a downstream consumer can PARSE it, and
bytes that round-trip do not establish that.  Twenty-two capabilities in the registry
declare a `json_path` input and before this none of them could be fed by a chain --
goal_compilation_benchmark_v1 records the consequence in its own commentary:
EXT_JQ_TABLE cannot select the capability it should because nothing produces
`json.file.available`, and "the honest fix for those two is to add a capability that
produces the missing effect, not to change the compiler."

So the proof here is stronger than a byte comparison.  The bytes are written, read
back, compared, and then PARSED -- and the parsed value is compared to what the
caller stated, so a document that parses to something other than what was asked for
is refused rather than reported as written.

The document slot is named `spec` because capability_type_surface_v1.type_of derives
a slot's type FROM ITS NAME and `spec` is a name it already knows to be JSON_TEXT.
Naming it `content` would type it STRING, and the composer's binder fills STRING from
whatever text a sentence states -- so a request stating plain text was routed here and
refused.  Declaring the type truthfully makes the existing type checker refuse the
mismatch before any side effect rather than after one.
"""
from __future__ import annotations
import hashlib
import json
import pathlib


def _safe(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    root = pathlib.Path(root).resolve()
    content = args.get("spec")
    output_path = _safe(root, args.get("output_path"))
    if content is None or (isinstance(content, str) and content.strip() == ""):
        raise RuntimeError("CONTENT_REQUIRED")
    if not output_path.name or output_path.is_dir():
        raise RuntimeError("OUTPUT_PATH_REQUIRED")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except Exception as exc:
            raise RuntimeError("CONTENT_NOT_VALID_JSON:%s" % type(exc).__name__) from exc
    else:
        parsed = content
    raw = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    check = output_path.read_bytes()
    if check != raw:
        raise RuntimeError("WRITE_DID_NOT_ROUNDTRIP")
    try:
        reread = json.loads(check.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("WRITTEN_FILE_NOT_VALID_JSON:%s" % type(exc).__name__) from exc
    if reread != parsed:
        raise RuntimeError("WRITTEN_JSON_DOES_NOT_MATCH_STATED")
    return {
        "adapter": "file_write_json",
        "output_path": str(output_path.relative_to(root)),
        "output_bytes": len(check),
        "output_sha256": hashlib.sha256(check).hexdigest(),
        "output_verified": True,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "json_parsed": True,
        "json_top_level_type": type(parsed).__name__,
    }
