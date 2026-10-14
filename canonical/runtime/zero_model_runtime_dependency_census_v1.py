#!/usr/bin/env python3
"""Zero-model producer-cognition dependency census (fail-closed, AST-derived).

Purpose: discharge the *inventory* half of the donor-requalification requirements
(`FULL_RUNTIME_DEPENDENCY_INVENTORY_COMPLETE`, `MODEL_DEPENDENCY_COUNT_*`,
`ONLINE_TEACHER_CALL_COUNT_*`) demanded by
canonical/verification/CAPABILITY_TRANSFER_V2_DONOR_AUTHORITY_INVALIDATION_20261011_V1.json
and GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.

It enumerates every Python source under the given roots and classifies each file:
  IMPORT_LEVEL_MODEL_DEPENDENCY  -- imports a model SDK / inference runtime module
  CALL_LEVEL_MODEL_DEPENDENCY    -- string/argument evidence of a model endpoint,
                                    chat-completions route, or local inference binary
  STRING_REFERENCE_ONLY          -- model vocabulary appears only in non-call strings
                                    (task names, documentation, verifier fixtures)
  CLEAN                          -- none of the above

This census proves INVENTORY, not credit.  A credited producer path is admissible
only if every file it transitively imports is CLEAN or STRING_REFERENCE_ONLY.
Nothing here grants capability, acceptance, ownership, or terminal credit.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_ZERO_MODEL_RUNTIME_DEPENDENCY_CENSUS_V1"

MODEL_MODULES = {
    "openai", "anthropic", "llama_cpp", "vllm", "transformers", "litellm", "ollama",
    "google.generativeai", "google.genai", "mistralai", "cohere", "together", "groq",
    "replicate", "huggingface_hub", "sentence_transformers", "langchain", "langchain_openai",
    "langchain_anthropic", "llama_index", "dspy", "instructor", "guidance", "outlines",
    "mlx_lm", "ctransformers", "exllamav2", "tgi", "text_generation", "sglang", "lmdeploy",
}
# Tensor frameworks are not model cognition by themselves, but any model *load* through
# them is.  They are reported separately so the auditor can inspect call sites.
TENSOR_MODULES = {"torch", "tensorflow", "jax", "onnxruntime", "keras", "safetensors"}

ENDPOINT_RE = re.compile(
    r"(api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|openrouter\.ai|"
    r"api\.together\.(xyz|ai)|api\.groq\.com|api\.mistral\.ai|api\.cohere\.(ai|com)|"
    r"/v1/chat/completions|/v1/completions|/v1/messages|/api/generate|/api/chat)",
    re.I,
)
LOCAL_RUNTIME_RE = re.compile(
    r"\b(llama-server|llama\.cpp|llama_cpp|llama-cli|ollama\s+(run|serve)|vllm\.entrypoints|"
    r"python\s+-m\s+vllm|text-generation-launcher|sglang\.launch_server|lmdeploy\s+serve|"
    r"[A-Za-z0-9_./-]+\.gguf|PROJECT_BRAIN_[A-Z0-9_]*MODEL)\b",
    re.I,
)
# Identifier-level evidence: constants/classes naming a local inference stack or weights.
IDENTIFIER_RE = re.compile(r"(LLAMA_CPP|GGUF|VLLM|OLLAMA|QWEN|DEEPSEEK|MISTRAL|GEMMA)", re.I)
SELF_NAME = "zero_model_runtime_dependency_census_v1.py"
MODEL_VOCAB_RE = re.compile(
    r"\b(qwen|llama|deepseek|mistral|mixtral|gemma|phi-?\d|gpt-?\d|claude|opus|sonnet|haiku|"
    r"gemini|grok|chat_?completion|llm|open[-_ ]?weight)\b",
    re.I,
)
CALL_NAMES_RE = re.compile(
    r"\b(chat\.completions\.create|messages\.create|responses\.create|generate_content|"
    r"Llama\(|AutoModelForCausalLM|pipeline\(\s*['\"]text-generation|completion\(|ChatCompletion)",
)


def _git_blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}".encode("ascii") + b"\0")
    h.update(data)
    return h.hexdigest()


def _top_module(name: str) -> str:
    return name.split(".")[0]


def classify_file(path: Path, root: Path) -> dict:
    data = path.read_bytes()
    rec: dict = {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "git_blob_sha": _git_blob_sha(data),
        "classification": "CLEAN",
        "model_module_imports": [],
        "tensor_module_imports": [],
        "endpoint_or_route_strings": [],
        "local_inference_runtime_strings": [],
        "model_call_names": [],
        "model_identifiers": [],
        "model_vocabulary_string_lines": 0,
        "parse_error": None,
    }
    try:
        tree = ast.parse(data.decode("utf-8", errors="replace"))
    except SyntaxError as exc:  # fail closed: unparseable == unknown == not clean
        rec["parse_error"] = f"{type(exc).__name__}:{exc.lineno}"
        rec["classification"] = "PARSE_ERROR_FAILS_CLOSED"
        return rec

    strings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                if mod in MODEL_MODULES or _top_module(mod) in MODEL_MODULES:
                    rec["model_module_imports"].append({"line": node.lineno, "module": mod})
                elif _top_module(mod) in TENSOR_MODULES:
                    rec["tensor_module_imports"].append({"line": node.lineno, "module": mod})
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if mod in MODEL_MODULES or _top_module(mod) in MODEL_MODULES:
                rec["model_module_imports"].append({"line": node.lineno, "module": mod})
            elif _top_module(mod) in TENSOR_MODULES:
                rec["tensor_module_imports"].append({"line": node.lineno, "module": mod})
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append((getattr(node, "lineno", 0), node.value))
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef)) and IDENTIFIER_RE.search(node.name):
            rec["model_identifiers"].append({"line": node.lineno, "name": node.name})
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and IDENTIFIER_RE.search(node.id):
            rec["model_identifiers"].append({"line": node.lineno, "name": node.id})

    text = data.decode("utf-8", errors="replace")
    for m in CALL_NAMES_RE.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        rec["model_call_names"].append({"line": line, "name": m.group(0)})

    for lineno, s in strings:
        if ENDPOINT_RE.search(s):
            rec["endpoint_or_route_strings"].append({"line": lineno, "match": ENDPOINT_RE.search(s).group(0)})
        if LOCAL_RUNTIME_RE.search(s):
            rec["local_inference_runtime_strings"].append({"line": lineno, "match": LOCAL_RUNTIME_RE.search(s).group(0)})
        if MODEL_VOCAB_RE.search(s):
            rec["model_vocabulary_string_lines"] += 1

    if rec["model_module_imports"]:
        rec["classification"] = "IMPORT_LEVEL_MODEL_DEPENDENCY"
    elif rec["endpoint_or_route_strings"] or rec["local_inference_runtime_strings"] or rec["model_call_names"]:
        rec["classification"] = "CALL_LEVEL_MODEL_DEPENDENCY"
    elif rec["model_identifiers"] and rec["model_vocabulary_string_lines"]:
        # Named inference constants plus model vocabulary in strings == operative model stack.
        rec["classification"] = "IDENTIFIER_LEVEL_MODEL_DEPENDENCY"
    elif rec["model_vocabulary_string_lines"] or rec["tensor_module_imports"] or rec["model_identifiers"]:
        rec["classification"] = "STRING_REFERENCE_ONLY"
    return rec


def run_census(root: Path, surfaces: list[str]) -> dict:
    files: list[dict] = []
    for surface in surfaces:
        base = root / surface
        if not base.exists():
            files.append({"path": surface, "classification": "SURFACE_MISSING_FAILS_CLOSED"})
            continue
        for p in sorted(base.rglob("*.py")):
            if "__pycache__" in p.parts or p.name == SELF_NAME:
                continue
            files.append(classify_file(p, root))

    counts: dict[str, int] = {}
    for f in files:
        counts[f["classification"]] = counts.get(f["classification"], 0) + 1

    dependent = [f for f in files if f["classification"] in (
        "IMPORT_LEVEL_MODEL_DEPENDENCY", "CALL_LEVEL_MODEL_DEPENDENCY", "IDENTIFIER_LEVEL_MODEL_DEPENDENCY",
        "PARSE_ERROR_FAILS_CLOSED", "SURFACE_MISSING_FAILS_CLOSED")]
    return {
        "schema": SCHEMA,
        "surfaces": surfaces,
        "file_count": len(files),
        "classification_counts": dict(sorted(counts.items())),
        "model_dependent_file_count": len(dependent),
        "model_dependent_files": [
            {k: v for k, v in f.items() if k in (
                "path", "git_blob_sha", "classification", "model_module_imports",
                "endpoint_or_route_strings", "local_inference_runtime_strings", "model_call_names",
                "model_identifiers", "parse_error")}
            for f in dependent
        ],
        "credited_producer_path_rule": (
            "A CREDITED PRODUCER PATH IS ADMISSIBLE ONLY IF EVERY FILE IT TRANSITIVELY IMPORTS IS "
            "CLEAN OR STRING_REFERENCE_ONLY__EVERY FILE LISTED IN model_dependent_files IS QUARANTINED "
            "FROM CREDITED PRODUCER COGNITION UNTIL DELETED OR PROVED NON-LOAD-BEARING"
        ),
        "census_proves": "RUNTIME_DEPENDENCY_INVENTORY_FOR_THE_SCANNED_SURFACES_ONLY",
        "census_does_not_prove": [
            "ZERO_MODEL_COGNITION_IN_HISTORICAL_RECEIPTS",
            "TRANSITIVE_IMPORT_CLOSURE_OF_ANY_SPECIFIC_CREDITED_ROUTE",
            "BEHAVIOR_PRESERVATION_AFTER_DONOR_REMOVAL",
            "ANY_CAPABILITY_ACCEPTANCE_OWNERSHIP_OR_TERMINAL_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--surface", action="append", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    surfaces = args.surface or ["canonical/runtime", "execution_guard"]
    out = run_census(root, surfaces)
    payload = json.dumps(out, indent=1, sort_keys=False)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if out["model_dependent_file_count"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
