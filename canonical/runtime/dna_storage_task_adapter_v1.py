"""Donor-free task adapter for the Brain DNA storage codec.

Converts only explicit task-visible instructions and artifact declarations into
bounded codec operations. It performs no model calls, network access, or hidden
benchmark lookup. Ambiguous contracts fail closed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import ast
import json
import pathlib
import re
import shutil
from typing import Any, Sequence

from canonical.runtime import dna_storage_codec_v1 as codec

SCHEMA = "PROJECT_BRAIN_DNA_STORAGE_TASK_ADAPTER_V1"
MODEL_DEPENDENCY_COUNT = 0
NETWORK_DEPENDENCY_COUNT = 0

_ABS_PATH = re.compile(r"(?<![A-Za-z0-9_.-])(/(?:root|data|app|workspace|results|output|outputs)(?:/[A-Za-z0-9_.{}-]+)+)")
_FILENAME = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.{}-]+\.(?:dna|fa|fasta|bin|dat|txt|py|json|csv))(?![A-Za-z0-9_.-])", re.I)
_INPUT_WORDS = ("input", "source", "payload", "original", "read from", "decode from", "encode from")
_OUTPUT_WORDS = ("output", "save", "write", "emit", "produce", "store in", "store to", "result")
_ENCODE_WORDS = ("encode", "encoding", "bytes to dna", "store as dna", "dna storage", "oligo")
_DECODE_WORDS = ("decode", "decoding", "recover", "reconstruct", "dna to bytes", "restore")
_SOURCE_WORDS = ("implement", "implementation", "write a codec", "create a codec", "source file", "python script")


class DNAStorageTaskAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class CodecTaskPlan:
    mode: str
    input_path: str | None
    output_path: str
    artifact_roots: tuple[str, ...]
    evidence: tuple[str, ...]


def _uniq(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    for raw in values:
        value = str(raw).strip().rstrip(".,;:)")
        if value and value not in out:
            out.append(value)
    return out


def _paths(instruction: str) -> list[str]:
    return _uniq([m.group(1) for m in _ABS_PATH.finditer(str(instruction))])


def _artifact_roots(artifacts: Sequence[str] | None) -> list[str]:
    out = []
    for raw in artifacts or ():
        value = str(raw).strip()
        if not value.startswith("/"):
            raise DNAStorageTaskAdapterError("ARTIFACT_PATH_NOT_ABSOLUTE")
        out.append(value.rstrip("/") or "/")
    return _uniq(out)


def _under(path: str, root: str) -> bool:
    p = pathlib.PurePosixPath(path)
    r = pathlib.PurePosixPath(root)
    return p == r or r in p.parents


def _is_outputish(path: str, artifact_roots: Sequence[str]) -> bool:
    low = path.lower()
    if low.startswith(("/root/results/", "/results/", "/output/", "/outputs/")):
        return True
    return any(_under(path, root) for root in artifact_roots)


def _score_near_words(text: str, token: str, words: Sequence[str]) -> int:
    low = text.lower()
    pos = low.find(token.lower())
    if pos < 0:
        return 0
    window = low[max(0, pos - 90): pos + len(token) + 90]
    return sum(1 for word in words if word in window)


def _mode(instruction: str, output_paths: Sequence[str]) -> tuple[str, list[str]]:
    low = instruction.lower()
    scores = {
        "encode": sum(low.count(x) for x in _ENCODE_WORDS),
        "decode": sum(low.count(x) for x in _DECODE_WORDS),
        "source": sum(low.count(x) for x in _SOURCE_WORDS),
    }
    if any(str(p).lower().endswith(".py") for p in output_paths):
        scores["source"] += 3
    if scores["encode"] > 0 and scores["decode"] > 0:
        if any(x in low for x in ("round trip", "roundtrip", "encode and decode", "encoding and decoding")):
            return "roundtrip", ["VISIBLE_ROUNDTRIP_LANGUAGE"]
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    if not ranked or ranked[0][1] <= 0:
        raise DNAStorageTaskAdapterError("TASK_MODE_UNRESOLVED")
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        raise DNAStorageTaskAdapterError("TASK_MODE_AMBIGUOUS")
    return ranked[0][0], ["VISIBLE_MODE_LANGUAGE:" + ranked[0][0]]


def _relative_output_name(instruction: str, mode: str) -> str | None:
    candidates = _uniq([m.group(1) for m in _FILENAME.finditer(instruction)])
    if not candidates:
        return None
    scored = sorted(
        ((_score_near_words(instruction, name, _OUTPUT_WORDS), name) for name in candidates),
        key=lambda x: (-x[0], x[1]),
    )
    if scored[0][0] > 0:
        return scored[0][1]
    preferred = {
        "encode": (".dna", ".fa", ".fasta", ".txt"),
        "decode": (".bin", ".dat", ".txt"),
        "source": (".py",),
    }.get(mode, ())
    hits = [name for name in candidates if name.lower().endswith(preferred)]
    return hits[0] if len(hits) == 1 else None


def resolve_plan(instruction: str, artifacts: Sequence[str] | None = None) -> CodecTaskPlan:
    if not isinstance(instruction, str) or not instruction.strip():
        raise DNAStorageTaskAdapterError("INSTRUCTION_REQUIRED")
    roots = _artifact_roots(artifacts)
    visible_paths = _paths(instruction)
    explicit_outputs = [p for p in visible_paths if _is_outputish(p, roots)]
    mode, evidence = _mode(instruction, explicit_outputs)

    output_candidates = list(explicit_outputs)
    artifact_files = [p for p in roots if pathlib.PurePosixPath(p).suffix]
    output_candidates.extend(p for p in artifact_files if p not in output_candidates)

    if not output_candidates:
        artifact_dirs = [p for p in roots if not pathlib.PurePosixPath(p).suffix]
        basename = _relative_output_name(instruction, mode)
        if len(artifact_dirs) == 1 and basename:
            output_candidates.append(str(pathlib.PurePosixPath(artifact_dirs[0]) / basename))
            evidence.append("OUTPUT_DERIVED_FROM_VISIBLE_BASENAME_AND_ARTIFACT_DIR")
        elif mode == "source" and len(artifact_dirs) == 1:
            output_candidates.append(str(pathlib.PurePosixPath(artifact_dirs[0]) / "dna_storage_codec.py"))
            evidence.append("SOURCE_DEFAULT_WITHIN_AUTHORITATIVE_ARTIFACT_DIR")

    output_candidates = _uniq(output_candidates)
    if len(output_candidates) != 1:
        raise DNAStorageTaskAdapterError("OUTPUT_PATH_AMBIGUOUS_OR_MISSING")
    output_path = output_candidates[0]

    if mode == "source":
        return CodecTaskPlan(mode, None, output_path, tuple(roots), tuple(evidence))

    input_candidates = [p for p in visible_paths if p != output_path and not _is_outputish(p, roots)]
    scored_inputs = sorted(
        ((_score_near_words(instruction, p, _INPUT_WORDS), p) for p in input_candidates),
        key=lambda x: (-x[0], x[1]),
    )
    if not scored_inputs:
        raise DNAStorageTaskAdapterError("INPUT_PATH_MISSING")
    best_score = scored_inputs[0][0]
    best = [p for score, p in scored_inputs if score == best_score]
    if best_score <= 0 and len(input_candidates) != 1:
        raise DNAStorageTaskAdapterError("INPUT_PATH_AMBIGUOUS")
    if len(best) != 1:
        raise DNAStorageTaskAdapterError("INPUT_PATH_AMBIGUOUS")
    input_path = best[0]
    if input_path == output_path:
        raise DNAStorageTaskAdapterError("INPUT_OUTPUT_PATH_COLLISION")
    return CodecTaskPlan(mode, input_path, output_path, tuple(roots), tuple(evidence))


def execute_plan(plan: CodecTaskPlan) -> dict[str, Any]:
    out = pathlib.Path(plan.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if plan.mode == "encode":
        result = codec.encode_file(plan.input_path or "", out)
    elif plan.mode == "decode":
        result = codec.decode_file(plan.input_path or "", out)
    elif plan.mode == "roundtrip":
        encoded = out.with_suffix(out.suffix + ".dna")
        encode_receipt = codec.encode_file(plan.input_path or "", encoded)
        result = codec.decode_file(encoded, out)
        result["encode_receipt"] = encode_receipt
    elif plan.mode == "source":
        source = pathlib.Path(codec.__file__)
        shutil.copyfile(source, out)
        ast.parse(out.read_text(encoding="utf-8"), filename=str(out))
        result = {
            "schema": codec.SCHEMA,
            "status": "PASS__DNA_STORAGE_SOURCE_MATERIALIZED",
            "output_path": str(out),
            "model_dependency_count": 0,
            "network_dependency_count": 0,
        }
    else:
        raise DNAStorageTaskAdapterError("UNSUPPORTED_MODE")
    return {
        "schema": SCHEMA,
        "status": "PASS__DNA_STORAGE_TASK_CONTRACT_EXECUTED",
        "plan": asdict(plan),
        "result": result,
        "model_dependency_count": 0,
        "network_dependency_count": 0,
    }


def execute_contract(instruction: str, artifacts: Sequence[str] | None = None) -> dict[str, Any]:
    return execute_plan(resolve_plan(instruction, artifacts))


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("request_json")
    args = parser.parse_args(list(argv) if argv is not None else None)
    request = json.loads(pathlib.Path(args.request_json).read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise DNAStorageTaskAdapterError("REQUEST_OBJECT_REQUIRED")
    result = execute_contract(request.get("instruction", ""), request.get("artifacts") or [])
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
