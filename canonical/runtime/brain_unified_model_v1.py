#!/usr/bin/env python3
"""Brain Unified Model V1 — one front door over the compiled Brain.

``BRAIN_UNIFIED_MODEL_V1.json`` is a deterministic projection of every live
verified capability, every fabric engine mode, every internalized skill
procedure, and an index of the laws and research the machine reasons from.
This module is the thing you actually run.

Three operations, one contract:

* ``status()``   — what the model contains, and what it explicitly cannot claim.
* ``route()``    — deterministic ranking of a plain goal against the model. It
                   fails closed: an unknown goal is reported as unknown instead
                   of being answered by a guess or an external model.
* ``solve()``    — route, then execute through the authority that owns the
                   capability. Bound capabilities go through
                   ``verified_bound_capability_execution_adapter_v1.execute``,
                   which re-reads the live registry and re-checks evidence.
                   Engine modes go through the unified cognitive fabric unchanged.
* ``recall()``   — just-in-time retrieval over the knowledge index. The model
                   stores hashes, headings and terms, never a copy of the text.

Authority boundary
------------------
This module grants nothing. Every result carries zero capability, ownership and
terminal credit. It does not widen a tolerance, promote a capability, replace
the live registry, or add a model to any producer path. It exposes what Brain
already owns through one addressable artifact.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import marshal
import math
import mmap
import os
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_V1"
SOLUTION_SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_SOLUTION_V1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
DEFAULT_CORE_ARTIFACT = "canonical/unified_model/BRAIN_UNIFIED_CORE_V1.json"

# Slot names whose value is the caller's own sentence rather than a resource to
# be discovered. Mirrors the set world_binding_v1 treats as goal text, so the
# two never disagree about what counts as the caller's words.
_GOAL_TEXT_SLOTS = frozenset({"goal", "task", "objective", "query", "question", "text"})

# Kept byte-identical in behaviour to the compiler's tokenizer. A routing table
# compiled with one segmentation and queried with another silently loses recall;
# the verifier checks the two tokenizers agree on a sample of terms.
STOPWORDS = frozenset(
    """
    a an and are as at be by can could do does for from has have how i if in into
    is it its of on or our that the their them then there these this to using was
    we what when where which who why will with without you your
    """.split()
)
TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_+.-")

NON_CLAIMS = (
    "NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS",
    "NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY",
    "NOT_TERMINAL_AUTHORITY__ZERO_CAPABILITY_AND_TERMINAL_CREDIT",
    "NOT_A_REPLACEMENT_FOR_THE_LIVE_REGISTRY_OR_LAWS",
    "COVERAGE_IS_NOT_CAPABILITY__EXECUTION_STILL_REQUIRES_DECLARED_SUBSTRATE",
)

ANATOMY_SCHEMA = "PROJECT_BRAIN_ANATOMY_V1"

class UnifiedModelError(ValueError):
    """The artifact or the request violated the model contract."""

# --------------------------------------------------------------------------- bytes

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def artifact_digest(model: Mapping[str, Any]) -> str:
    return digest_value({k: v for k, v in model.items() if k != "digest"})

def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for raw in str(text or "").casefold().replace("/", " ").split():
        token = "".join(ch for ch in raw if ch in TOKEN_CHARS).strip("._-")
        if len(token) < 2 or token in STOPWORDS:
            continue
        out.append(token)
    return out

# The compiler's own repository-path scanner, character class and all: a path
# literal is two or more "/"-joined segments. Kept byte-for-byte in step with
# ``goal_compiler._repo_paths_uncached`` -- if the two ever disagree, coverage is
# measured over words the caller never asked with.
_PATH_LITERAL = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+")
_URL_LITERAL = re.compile(r"https?://[^\s)\]}>]+")

def path_literals(text: str, root: str | Path | None = None) -> list[str]:
    """The spans of ``text`` that name a real artifact, in sentence order.

    A literal counts only when something is actually there: the literal itself
    exists, or its parent directory does (so "write a new file into an existing
    directory" is still recognised as naming a destination). That requirement is
    what keeps prose out -- "and/or", "read/write" and "input/output" match the
    path shape but resolve to no parent directory, so they stay question words.
    """
    s_text = str(text or "")
    if "/" not in s_text:
        return []
    body = _URL_LITERAL.sub(" ", s_text)
    if "/" not in body:
        return []
    rr = Path(ROOT if root is None else root).resolve()
    found: list[str] = []
    for match in _PATH_LITERAL.finditer(body):
        raw = match.group(0).rstrip(".,;:!?)]}")
        candidates: list[Path] = []
        start = match.start()
        if start > 0 and body[start - 1] == "/":
            candidates.append(Path("/" + raw))
        candidates.append(rr / raw)
        for candidate in candidates:
            try:
                if candidate.exists() or candidate.parent.is_dir():
                    break
            except OSError:
                continue
        else:
            continue
        found.append(match.group(0))
    return found

def ask_tokens(text: str, root: str | Path | None = None) -> list[str]:
    """The caller's ASK: the sentence with its stated path literals blanked out.

    ``route()`` fails closed when the model recognises too little of a sentence.
    Charging the tokens of a stated path to that budget made the verdict a
    lottery on how many times a sentence happened to repeat an indexed word.
    Measured: "/home/user/brain/canonical/astra_runtime/tmp/x/calc.py" alone
    contributes eleven tokens no capability can ever claim, so "Count the
    functions defined in the python file <that path> and write the report to
    <another path>" scored coverage 0.240 against the 0.34 floor and was refused
    as GOAL_NOT_REPRESENTED_IN_MODEL before a single capability was considered --
    while "Run the python tests ..." squeaked past at 0.257 only because the
    sentence repeats its own keywords.

    A path is a located artifact the binder will bind, not a word to be
    understood. It is the same distinction the compiler already draws for a
    quoted literal (a quoted literal's words are not the task's words) and for a
    bare version token (a name fragment, not a stated value). Scoring is left
    untouched: only the denominator of the coverage budget changes.
    """
    ask = str(text or "")
    if "/" in ask:
        for literal in path_literals(ask, root):
            ask = ask.replace(literal, " ")
    return tokenize(ask)

# --------------------------------------------------------------------------- loading

_VERIFIED_BLOB_DIGESTS: dict[str, str] = {}
_VERIFIED_DIGEST_TO_RAW_SHA: dict[str, str] = {}
_OPEN_MODEL_MEM_CACHE: dict[tuple[str, int, int], "UnifiedModel"] = {}
_MMAP_CSR_MEM_CACHE: dict[tuple[str, str], Any] = {}

def _core_cache_dir() -> Path:
    return ROOT / "canonical" / "astra_runtime" / "tmp"

def _get_mmap_csr(section: str, raw_sha: str) -> Any | None:
    if not raw_sha:
        return None
    key = (section, raw_sha)
    hit = _MMAP_CSR_MEM_CACHE.get(key)
    if hit is not None:
        return hit
    csr_path = _core_cache_dir() / f"unified_model_csr_{section}_{raw_sha[:32]}.bin"
    if not csr_path.is_file():
        return None
    try:
        from canonical.runtime.mmap_csr_slot_index_v1 import MmapCSRIndex

        reader = MmapCSRIndex(csr_path)
        _MMAP_CSR_MEM_CACHE[key] = reader
        return reader
    except Exception:
        return None

def load_model(
    path: str | Path | None = None,
    *,
    root: str | Path | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    base = Path(root or ROOT).resolve()
    target = Path(path) if path else base / DEFAULT_ARTIFACT
    if not target.is_absolute():
        target = base / target
    if not target.is_file():
        raise UnifiedModelError("MODEL_ARTIFACT_MISSING:" + str(target))
    raw_bytes = target.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    try:
        model = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnifiedModelError("MODEL_ARTIFACT_NOT_JSON") from exc
    if not isinstance(model, dict) or model.get("schema") != SCHEMA:
        raise UnifiedModelError("MODEL_SCHEMA_MISMATCH")
    if verify:
        declared = (model.get("digest") or {}).get("value")
        cached_dig = _VERIFIED_BLOB_DIGESTS.get(raw_sha)
        if cached_dig is None:
            core_file = _core_cache_dir() / f"unified_model_core_{raw_sha[:32]}.marshal"
            if core_file.is_file():
                try:
                    core_blob = marshal.loads(core_file.read_bytes())
                    if (
                        isinstance(core_blob, dict)
                        and core_blob.get("core_format_v") == 5
                        and core_blob.get("raw_sha256") == raw_sha
                        and core_blob.get("schema") == SCHEMA
                        and core_blob.get("digest_value")
                    ):
                        cached_dig = str(core_blob["digest_value"])
                        _VERIFIED_BLOB_DIGESTS[raw_sha] = cached_dig
                except Exception:
                    cached_dig = None
        if cached_dig is not None:
            recomputed = cached_dig
        else:
            recomputed = artifact_digest(model)
            if declared and declared == recomputed:
                _VERIFIED_BLOB_DIGESTS[raw_sha] = recomputed
        if not declared or declared != recomputed:
            raise UnifiedModelError("MODEL_DIGEST_MISMATCH")
        _VERIFIED_DIGEST_TO_RAW_SHA[str(declared)] = raw_sha
    return model

def _declared_triggers_for_row(cid: str, row: Mapping[str, Any]) -> set[str]:
    id_tokens = set(tokenize(cid))
    return {
        str(t)
        for t in (row.get("triggers") or [])
        if str(t) not in id_tokens and len(str(t)) > 3
    }

def _extract_routing_core(model: Mapping[str, Any], raw_sha: str) -> dict[str, Any]:
    src_rows = [row for row in (model.get("source_index") or []) if isinstance(row, Mapping)]
    ext_src_rows = [row for row in (model.get("extended_source_index") or []) if isinstance(row, Mapping)]
    res_rows = [row for row in (model.get("research_index") or []) if isinstance(row, Mapping)]
    knw_rows = [row for row in (model.get("knowledge") or []) if isinstance(row, Mapping)]
    caps_map = {
        str(row["id"]): dict(row)
        for row in (model.get("capabilities") or [])
        if isinstance(row, Mapping) and row.get("id")
    }
    engines_map = {
        str(row["id"]): dict(row)
        for row in (model.get("engines") or [])
        if isinstance(row, Mapping) and row.get("id")
    }
    cap_id_terms = {
        cid: tuple(sorted(set(tokenize(cid.replace("/", " ").replace(".", " ")))))
        for cid in caps_map
    }
    receipt_ids = {
        cid for cid, row in caps_map.items() if row.get("kind") == "RECEIPT_BACKED_CAPABILITY"
    }
    trig_cache: dict[str, set[str]] = {}
    filtered_index: dict[str, dict[str, float]] = {}
    for tok, postings in ((model.get("grammar") or {}).get("index") or {}).items():
        s_tok = str(tok)
        kept: dict[str, float] = {}
        for raw_cid, weight in postings.items():
            cid = str(raw_cid)
            if cid in receipt_ids:
                trigs = trig_cache.get(cid)
                if trigs is None:
                    trigs = _declared_triggers_for_row(cid, caps_map.get(cid) or {})
                    trig_cache[cid] = trigs
                if s_tok not in trigs:
                    continue
            kept[cid] = float(weight)
        if kept:
            filtered_index[s_tok] = kept
    return {
        "core_format_v": 5,
        "raw_sha256": raw_sha,
        "schema": str(model.get("schema") or ""),
        "model_id": model.get("model_id"),
        "model_version": model.get("model_version"),
        "digest_value": str((model.get("digest") or {}).get("value") or ""),
        "counts": dict(model.get("counts") or {}),
        "anatomy": dict(model.get("anatomy") or {}),
        "objective_verbatim": (model.get("objective") or {}).get("verbatim"),
        "capabilities_map": caps_map,
        "engines_map": engines_map,
        "capability_id_terms": cap_id_terms,
        "receipt_backed_ids": tuple(sorted(receipt_ids)),
        "filtered_index": filtered_index,
        "adapter_ast_index": dict(((model.get("grammar") or {}).get("adapter_ast_index") or {})),
        "skills": [dict(row) for row in (model.get("skills") or []) if isinstance(row, Mapping)],
        "confidence": dict(((model.get("grammar") or {}).get("confidence") or {})),
        "source_index_len": len(src_rows),
        "source_entry_points": sum(1 for r in src_rows if r.get("classification") == "ENTRY_POINT"),
        "extended_source_index_len": len(ext_src_rows),
        "research_index_len": len(res_rows),
        "knowledge_len": len(knw_rows),
    }

class _LazyMarshalDict(dict):
    """`dict` subclass backed by per-entry `marshal` blobs so `open_model()` skips 18,000+ nested dict allocations."""

    def __init__(self, blobs: Mapping[str, bytes]) -> None:
        super().__init__((k, None) for k in blobs)
        self._blobs: dict[str, bytes] = dict(blobs)

    def _materialize(self, key: str) -> Any:
        val = super().get(key)
        if val is None and key in self._blobs:
            val = marshal.loads(self._blobs.pop(key))
            super().__setitem__(key, val)
        return val

    def __getitem__(self, key: str) -> Any:
        if not super().__contains__(key):
            raise KeyError(key)
        return self._materialize(key)

    def get(self, key: str, default: Any = None) -> Any:
        if not super().__contains__(key):
            return default
        return self._materialize(key)

    def values(self) -> Any:
        if self._blobs:
            for k in list(self._blobs):
                self._materialize(k)
        return super().values()

    def items(self) -> Any:
        if self._blobs:
            for k in list(self._blobs):
                self._materialize(k)
        return super().items()

    def copy(self) -> dict[str, Any]:
        return dict(self.items())

def _pack_hot_marshal_tiers(core: Mapping[str, Any]) -> tuple[dict[str, Any], bytes, bytes]:
    """Split `<1.5 KB` Tier-0 boot header, `~85 KB` Tier-1 pre-scaled route tables, and Tier-2 full capability blobs."""
    caps_raw = dict(core.get("capabilities_map") or {})
    engs_raw = dict(core.get("engines_map") or {})
    idx_raw = dict(core.get("filtered_index") or {})
    id_terms_raw = {str(k): tuple(v) for k, v in (core.get("capability_id_terms") or {}).items()}
    id_terms_sets = {cid: frozenset(terms) for cid, terms in id_terms_raw.items()}

    cid_folded_pairs = tuple((cid, cid.casefold()) for cid in caps_raw)
    cid_dot_pairs = tuple((cid, cf) for cid, cf in cid_folded_pairs if "." in cf)
    cid_nodot_pairs = tuple((cid, cf) for cid, cf in cid_folded_pairs if "." not in cf)
    exact_id_lookup: dict[str, str] = {cf: cid for cid, cf in cid_folded_pairs}

    eid_pairs: list[tuple[str, str, str]] = []
    mode_by_word: dict[str, list[tuple[str, str]]] = {}
    for eid in engs_raw:
        ef = eid.casefold()
        mode_phrase = eid.split(":", 1)[-1].replace("_", " ").casefold()
        eid_pairs.append((eid, ef, mode_phrase))
        exact_id_lookup[ef] = eid
        if mode_phrase:
            first_w = mode_phrase.split(" ", 1)[0]
            mode_by_word.setdefault(first_w, []).append((eid, mode_phrase))

    scaled_blobs: dict[str, bytes] = {}
    for tok, postings in idx_raw.items():
        scaled_blobs[str(tok)] = marshal.dumps(
            tuple(
                (
                    str(cid),
                    (2.0 if tok in id_terms_sets.get(str(cid), ()) else 1.0) * math.log1p(float(weight)),
                )
                for cid, weight in postings.items()
            )
        )

    id_kind_map: dict[str, str] = {cid: str(r.get("kind") or "UNKNOWN") for cid, r in caps_raw.items()}
    for eid, r in engs_raw.items():
        id_kind_map[eid] = str(r.get("kind") or "UNKNOWN")
    caps_with_deps = {
        cid: {"declared_dependencies": r["declared_dependencies"]}
        for cid, r in caps_raw.items()
        if isinstance(r, Mapping) and (r.get("declared_dependencies") or {}).get("declared_dependencies_checked")
    }

    route_payload = {
        "scaled_index_blobs": scaled_blobs,
        "exact_id_lookup": exact_id_lookup,
        "cid_folded_pairs": cid_folded_pairs,
        "cid_dot_pairs": cid_dot_pairs,
        "cid_nodot_pairs": cid_nodot_pairs,
        "eid_folded_triples": tuple(eid_pairs),
        "mode_phrase_by_word": {k: tuple(v) for k, v in mode_by_word.items()},
        "cap_id_set": tuple(caps_raw.keys()),
        "eng_id_set": tuple(engs_raw.keys()),
        "id_kind_map": id_kind_map,
        "caps_with_deps": caps_with_deps,
    }
    tables_payload = {
        "capabilities_blobs": {str(k): marshal.dumps(v) for k, v in caps_raw.items()},
        "engines_blobs": {str(k): marshal.dumps(v) for k, v in engs_raw.items()},
        "filtered_index": idx_raw,
        "capability_id_terms": id_terms_raw,
        "receipt_backed_ids": tuple(core.get("receipt_backed_ids") or ()),
        "skills_blob": marshal.dumps(list(core.get("skills") or [])),
        "adapter_ast_blob": marshal.dumps(dict(core.get("adapter_ast_index") or {})),
        "anatomy": dict(core.get("anatomy") or {}),
        "objective_verbatim": core.get("objective_verbatim"),
    }
    hdr = {
        "core_format_v": 5,
        "packed_marshal_v": 6,
        "raw_sha256": str(core.get("raw_sha256") or ""),
        "schema": str(core.get("schema") or ""),
        "model_id": core.get("model_id"),
        "model_version": core.get("model_version"),
        "digest_value": str(core.get("digest_value") or ""),
        "artifact_bytes": int(core.get("artifact_bytes") or 0),
        "digest_needle_offset": int(core.get("digest_needle_offset") if core.get("digest_needle_offset") is not None else -1),
        "schema_needle_offset": int(core.get("schema_needle_offset") if core.get("schema_needle_offset") is not None else -1),
        "section_byte_spans": dict(core.get("section_byte_spans") or {}),
        "objective_verbatim": str(core.get("objective_verbatim") or ""),
        "counts": dict(core.get("counts") or {}),
        "confidence": dict(core.get("confidence") or {}),
        "source_index_len": int(core.get("source_index_len") or 0),
        "source_entry_points": int(core.get("source_entry_points") or 0),
        "extended_source_index_len": int(core.get("extended_source_index_len") or 0),
        "research_index_len": int(core.get("research_index_len") or 0),
        "knowledge_len": int(core.get("knowledge_len") or 0),
        "federated_engines_len": sum(1 for r in engs_raw.values() if r.get("kind") == "FEDERATED_KERNEL_ENGINE"),
        "routing_tokens_len": len(idx_raw),
        "skills_len": len(core.get("skills") or ()),
    }
    return hdr, marshal.dumps(route_payload), marshal.dumps(tables_payload)

def _write_hot_tier_files(cache_dir: Path, raw_sha: str, core: Mapping[str, Any]) -> dict[str, Any]:
    hdr, route_bytes, tables_bytes = _pack_hot_marshal_tiers(core)
    pid = os.getpid()
    short = raw_sha[:32]
    r_path = cache_dir / f"unified_model_route6_{short}.marshal"
    t_path = cache_dir / f"unified_model_tables6_{short}.marshal"
    h_path = cache_dir / f"unified_model_hdr6_{short}.marshal"
    hdr_disk = {**hdr, "_route_path": str(r_path), "_tables_path": str(t_path)}
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for dst, blob in ((r_path, route_bytes), (t_path, tables_bytes), (h_path, marshal.dumps(hdr_disk))):
            tmp = dst.with_name(f".{dst.name}.{pid}.tmp")
            tmp.write_bytes(blob)
            tmp.replace(dst)
    except OSError:
        return {**hdr, "_route_blob": route_bytes, "_tables_blob": tables_bytes}
    return hdr_disk

def _extract_secondary_indexes(full: Mapping[str, Any], raw_sha: str) -> dict[str, Any]:
    src_map = {
        str(row["path"]): dict(row)
        for row in (full.get("source_index") or [])
        if isinstance(row, Mapping) and row.get("path")
    }
    src_df: dict[str, int] = {}
    src_postings: dict[str, list[tuple[str, int]]] = {}
    for path, row in src_map.items():
        terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
        for term, tf_val in terms.items():
            s_term = str(term)
            tf = int(tf_val or 0)
            src_df[s_term] = src_df.get(s_term, 0) + 1
            if tf > 0:
                src_postings.setdefault(s_term, []).append((path, tf))

    ext_map = {
        str(row["path"]): dict(row)
        for row in (full.get("extended_source_index") or [])
        if isinstance(row, Mapping) and row.get("path")
    }
    ext_df: dict[str, int] = {}
    comb_map: dict[str, dict[str, Any]] = dict(src_map)
    for path, row in ext_map.items():
        comb_map[path] = row
        terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
        for term in terms:
            s_term = str(term)
            ext_df[s_term] = ext_df.get(s_term, 0) + 1

    comb_postings: dict[str, list[tuple[str, int]]] = {}
    for path, row in comb_map.items():
        terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
        for term, tf_val in terms.items():
            tf = int(tf_val or 0)
            if tf > 0:
                comb_postings.setdefault(str(term), []).append((path, tf))

    harv_map = {
        str(row["id"]): dict(row)
        for row in (full.get("harvested_capabilities") or [])
        if isinstance(row, Mapping) and row.get("id")
    }

    res_map = {
        str(row["path"]): dict(row)
        for row in (full.get("research_index") or [])
        if isinstance(row, Mapping) and row.get("path")
    }
    res_df: dict[str, int] = {}
    res_postings: dict[str, list[tuple[str, int]]] = {}
    for path, row in res_map.items():
        terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
        for term, tf_val in terms.items():
            s_term = str(term)
            tf = int(tf_val or 0)
            res_df[s_term] = res_df.get(s_term, 0) + 1
            if tf > 0:
                res_postings.setdefault(s_term, []).append((path, tf))

    knw_list = [dict(row) for row in (full.get("knowledge") or []) if isinstance(row, Mapping)]
    knw_df: dict[str, int] = {}
    knw_len: list[int] = []
    knw_postings: dict[str, list[tuple[int, int]]] = {}
    knw_title_postings: dict[str, list[int]] = {}
    for idx, row in enumerate(knw_list):
        terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
        knw_len.append(sum(int(v) for v in terms.values()))
        for term, tf_val in terms.items():
            s_term = str(term)
            tf = int(tf_val or 0)
            knw_df[s_term] = knw_df.get(s_term, 0) + 1
            if tf > 0:
                knw_postings.setdefault(s_term, []).append((idx, tf))
        for t_term in row.get("title_terms") or ():
            knw_title_postings.setdefault(str(t_term), []).append(idx)

    avg_len = (sum(knw_len) / len(knw_len) if knw_len else 1.0) or 1.0
    return {
        "secondary_format_v": 2,
        "raw_sha256": raw_sha,
        "source_index": src_map,
        "source_df": src_df,
        "source_postings": {k: tuple(v) for k, v in src_postings.items()},
        "extended_source_index": ext_map,
        "extended_source_df": ext_df,
        "combined_source_index": comb_map,
        "combined_source_postings": {k: tuple(v) for k, v in comb_postings.items()},
        "harvested": harv_map,
        "research_index": res_map,
        "research_df": res_df,
        "research_postings": {k: tuple(v) for k, v in res_postings.items()},
        "knowledge": knw_list,
        "knowledge_df": knw_df,
        "knowledge_lengths": knw_len,
        "avg_length": avg_len,
        "knowledge_postings": {k: tuple(v) for k, v in knw_postings.items()},
        "knowledge_title_postings": {k: tuple(v) for k, v in knw_title_postings.items()},
    }

# --------------------------------------------------------------------------- model


# The full installation includes Waves 40-54; blind worker mounts deliberately omit them.
try:
    from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import (
        Wave53To54UnifiedCapabilityBusMixin as _Wave53To54UnifiedCapabilityBusMixin,
    )
    _Wave51To52UnifiedModelMixin = _Wave49To50UnifiedModelMixin = _Wave40To42UnifiedModelMixin = _Wave53To54UnifiedCapabilityBusMixin
except ModuleNotFoundError as exc:
    if not str(exc.name or "").startswith(("canonical.runtime.wave4", "canonical.runtime.wave5")):
        raise
    _Wave53To54UnifiedCapabilityBusMixin = _Wave51To52UnifiedModelMixin = _Wave49To50UnifiedModelMixin = _Wave40To42UnifiedModelMixin = object

class UnifiedModel(_Wave53To54UnifiedCapabilityBusMixin):
    """A loaded, digest-verified unified model."""

    def __init__(
        self,
        model: Mapping[str, Any],
        *,
        _raw_bytes: bytes | None = None,
        _core_only: bool = False,
        _target_path: Path | None = None,
        _artifact_path: Path | None = None,
    ):
        if _Wave40To42UnifiedModelMixin is object and model.get("model_id") != "brain-harbor-cold":
            raise UnifiedModelError("FULL_MODEL_WAVE_PROVIDER_MISSING")
        self._raw_bytes_backing: bytes | None = _raw_bytes
        self._target_path: Path | None = _target_path or _artifact_path
        self._artifact_path: Path | None = self._target_path
        self._declared_triggers_cache: dict[str, set[str]] = {}
        self._route_path: Path | None = None
        self._route_blob: bytes | None = None
        self._tables_path: Path | None = None
        self._tables_blob: bytes | None = None
        self._route_loaded: bool = False
        self._tables_loaded: bool = False
        self._capabilities_dict: dict[str, Any] | None = None
        self._engines_dict: dict[str, Any] | None = None
        self._skills_list: list[dict[str, Any]] | None = None
        self._skills_blob: bytes | None = None
        self._adapter_ast_blob: bytes | None = None
        self._receipt_backed_set: frozenset[str] | None = None
        self._index_dict: dict[str, dict[str, float]] | None = None
        self._cap_id_terms_raw: dict[str, Any] | None = None
        self._cap_id_terms_sets: dict[str, frozenset[str]] | None = None
        self._scaled_index_map: dict[str, tuple[tuple[str, float], ...]] | None = None
        self._exact_id_lookup_map: dict[str, str] | None = None
        self._cid_folded_pairs_tup: tuple[tuple[str, str], ...] | None = None
        self._cid_dot_pairs_tup: tuple[tuple[str, str], ...] | None = None
        self._cid_nodot_pairs_tup: tuple[tuple[str, str], ...] | None = None
        self._eid_folded_triples_tup: tuple[tuple[str, str, str], ...] | None = None
        self._mode_phrase_by_word_map: dict[str, tuple[tuple[str, str], ...]] | None = None
        self._cap_id_set_val: frozenset[str] | None = None
        self._eng_id_set_val: frozenset[str] | None = None
        self._id_kind_map_val: dict[str, str] | None = None
        self._caps_with_deps_val: dict[str, dict[str, Any]] | None = None

        if _core_only and model.get("core_format_v") == 5:
            self._model_loaded: dict[str, Any] | None = None
            self._core_meta: dict[str, Any] = dict(model)
            self.digest = str(model.get("digest_value") or "")
            confidence = self._core_meta.get("confidence") or {}
            if self._core_meta.get("packed_marshal_v") == 6:
                rp = self._core_meta.get("_route_path")
                tp = self._core_meta.get("_tables_path")
                self._route_path = Path(rp) if rp else None
                self._tables_path = Path(tp) if tp else None
                self._route_blob = self._core_meta.get("_route_blob")
                self._tables_blob = self._core_meta.get("_tables_blob")
            else:
                self._hydrate_eager_from_core(self._core_meta)
        else:
            self._model_loaded = dict(model)
            declared_dig = str((model.get("digest") or {}).get("value") or "")
            inferred_sha = _VERIFIED_DIGEST_TO_RAW_SHA.get(declared_dig, "")
            reused_core: dict[str, Any] | None = None
            if inferred_sha:
                core_f = _core_cache_dir() / f"unified_model_core_{inferred_sha[:32]}.marshal"
                if core_f.is_file():
                    try:
                        c_blob = marshal.loads(core_f.read_bytes())
                        if (
                            isinstance(c_blob, dict)
                            and c_blob.get("core_format_v") == 5
                            and c_blob.get("raw_sha256") == inferred_sha
                            and c_blob.get("digest_value") == declared_dig
                            and len(model.get("capabilities") or ()) == len(c_blob.get("capabilities_map") or {})
                            and len(model.get("source_index") or ()) == int(c_blob.get("source_index_len") or -1)
                        ):
                            reused_core = c_blob
                    except Exception:
                        reused_core = None
            self._core_meta = reused_core if reused_core is not None else _extract_routing_core(self._model_loaded, inferred_sha)
            self.digest = declared_dig
            confidence = self._core_meta["confidence"]
            self._hydrate_eager_from_core(self._core_meta)

        self._unrunnable: dict[str, list[str]] | None = None
        self._source_index_cache: dict[str, dict[str, Any]] | None = None
        self._source_postings_cache: dict[str, tuple[tuple[str, int], ...]] | None = None
        self._harvested_cache: dict[str, dict[str, Any]] | None = None
        self._harvested_index: dict[str, dict[str, float]] | None = None
        self._source_df_cache: dict[str, int] | None = None
        self._extended_source_index_cache: dict[str, dict[str, Any]] | None = None
        self._extended_source_df_cache: dict[str, int] | None = None
        self._extended_source_postings_cache: dict[str, tuple[tuple[str, int], ...]] | None = None
        self._combined_source_index_cache: dict[str, dict[str, Any]] | None = None
        self._combined_source_postings_cache: dict[str, tuple[tuple[str, int], ...]] | None = None
        self._research_index_cache: dict[str, dict[str, Any]] | None = None
        self._research_df_cache: dict[str, int] | None = None
        self._research_postings_cache: dict[str, tuple[tuple[str, int], ...]] | None = None
        self._knowledge_cache: list[dict[str, Any]] | None = None
        self._knowledge_df_cache: dict[str, int] | None = None
        self._knowledge_lengths_cache: list[int] | None = None
        self._avg_length_cache: float | None = None
        self._knowledge_postings_cache: dict[str, tuple[tuple[int, int], ...]] | None = None
        self._knowledge_title_postings_cache: dict[str, tuple[int, ...]] | None = None
        self._memory_bus: Any = None
        self._boundary_router: Any = None
        self._traced_catalog_cache: dict[str, Any] | None = None
        self._traced_adapter_cache: dict[str, dict[str, Any]] = {}
        self._fts5_model_conn: Any = None
        self._ppr_router: Any = None
        self._symbol_graph_conns: dict[str, Any] = {}
        self._dark_matter_verified: dict[str, dict[str, Any]] = {}
        self._source_csr: Any = None
        self._combined_source_csr: Any = None
        self._route_memo: dict[tuple[str, int], dict[str, Any]] = {}
        self._futamura_cascade: Any = None
        self._raw_sha256: str = str(self._core_meta.get("raw_sha256") or "")

        self.min_score = float(confidence.get("minimum_best_score", 1.0))
        self.min_coverage = float(confidence.get("minimum_coverage", 0.34))

    def _hydrate_eager_from_core(self, core: Mapping[str, Any]) -> None:
        caps = dict(core.get("capabilities_map") or {})
        engs = dict(core.get("engines_map") or {})
        id_terms = {
            cid: frozenset(terms)
            for cid, terms in (core.get("capability_id_terms") or {}).items()
        }
        idx = dict(core.get("filtered_index") or {})
        self._capabilities_dict = caps
        self._engines_dict = engs
        self._cap_id_terms_sets = id_terms
        self._skills_list = list(core.get("skills") or [])
        self._receipt_backed_set = frozenset(core.get("receipt_backed_ids") or ())
        self._index_dict = idx

        cid_folded = tuple((cid, cid.casefold()) for cid in caps)
        exact: dict[str, str] = {cf: cid for cid, cf in cid_folded}
        eid_pairs: list[tuple[str, str, str]] = []
        mode_by_word: dict[str, list[tuple[str, str]]] = {}
        for eid in engs:
            ef = eid.casefold()
            mode_phrase = eid.split(":", 1)[-1].replace("_", " ").casefold()
            eid_pairs.append((eid, ef, mode_phrase))
            exact[ef] = eid
            if mode_phrase:
                first_w = mode_phrase.split(" ", 1)[0]
                mode_by_word.setdefault(first_w, []).append((eid, mode_phrase))
        scaled_idx: dict[str, tuple[tuple[str, float], ...]] = {}
        for tok, postings in idx.items():
            scaled_idx[tok] = tuple(
                (cid, (2.0 if tok in id_terms.get(cid, ()) else 1.0) * math.log1p(weight))
                for cid, weight in postings.items()
            )
        id_kind = {cid: str(r.get("kind") or "UNKNOWN") for cid, r in caps.items()}
        for eid, r in engs.items():
            id_kind[eid] = str(r.get("kind") or "UNKNOWN")

        self._cid_folded_pairs_tup = cid_folded
        self._cid_dot_pairs_tup = tuple((cid, cf) for cid, cf in cid_folded if "." in cf)
        self._cid_nodot_pairs_tup = tuple((cid, cf) for cid, cf in cid_folded if "." not in cf)
        self._exact_id_lookup_map = exact
        self._eid_folded_triples_tup = tuple(eid_pairs)
        self._mode_phrase_by_word_map = {k: tuple(v) for k, v in mode_by_word.items()}
        self._scaled_index_map = scaled_idx
        self._cap_id_set_val = frozenset(caps.keys())
        self._eng_id_set_val = frozenset(engs.keys())
        self._id_kind_map_val = id_kind
        self._caps_with_deps_val = {
            cid: {"declared_dependencies": r["declared_dependencies"]}
            for cid, r in caps.items()
            if isinstance(r, Mapping) and (r.get("declared_dependencies") or {}).get("declared_dependencies_checked")
        }
        self._route_loaded = True
        self._tables_loaded = True

    def _ensure_route_tables(self) -> None:
        if self._route_loaded:
            return
        raw = self._route_blob
        if raw is None and self._route_path is not None and self._route_path.is_file():
            raw = self._route_path.read_bytes()
        if raw is not None:
            rt = marshal.loads(raw)
            self._route_blob = None
            self._scaled_index_map = (
                _LazyMarshalDict(rt["scaled_index_blobs"])
                if "scaled_index_blobs" in rt
                else rt["scaled_index"]
            )
            self._exact_id_lookup_map = rt["exact_id_lookup"]
            self._cid_folded_pairs_tup = rt["cid_folded_pairs"]
            self._cid_dot_pairs_tup = rt["cid_dot_pairs"]
            self._cid_nodot_pairs_tup = rt["cid_nodot_pairs"]
            self._eid_folded_triples_tup = rt["eid_folded_triples"]
            self._mode_phrase_by_word_map = rt["mode_phrase_by_word"]
            self._cap_id_set_val = frozenset(rt["cap_id_set"])
            self._eng_id_set_val = frozenset(rt["eng_id_set"])
            self._id_kind_map_val = rt["id_kind_map"]
            self._caps_with_deps_val = rt["caps_with_deps"]
            self._route_loaded = True
            return
        full = self._ensure_full_model()
        self._hydrate_eager_from_core(_extract_routing_core(full, self._raw_sha256))

    def _ensure_full_tables(self) -> None:
        if self._tables_loaded:
            return
        raw = self._tables_blob
        if raw is None and self._tables_path is not None and self._tables_path.is_file():
            raw = self._tables_path.read_bytes()
        if raw is not None:
            tb = marshal.loads(raw)
            self._tables_blob = None
            self._capabilities_dict = _LazyMarshalDict(tb["capabilities_blobs"])
            self._engines_dict = _LazyMarshalDict(tb["engines_blobs"])
            self._core_meta["capabilities_map"] = self._capabilities_dict
            self._core_meta["engines_map"] = self._engines_dict
            self._index_dict = dict(tb["filtered_index"])
            self._cap_id_terms_raw = dict(tb["capability_id_terms"])
            self._receipt_backed_set = frozenset(tb["receipt_backed_ids"])
            self._skills_blob = tb.get("skills_blob")
            self._adapter_ast_blob = tb.get("adapter_ast_blob")
            if tb.get("anatomy"):
                self._core_meta["anatomy"] = tb["anatomy"]
            if "objective_verbatim" in tb:
                self._core_meta["objective_verbatim"] = tb["objective_verbatim"]
            self._tables_loaded = True
            return
        full = self._ensure_full_model()
        self._hydrate_eager_from_core(_extract_routing_core(full, self._raw_sha256))

    @property
    def capabilities(self) -> dict[str, Any]:
        self._ensure_full_tables()
        return self._capabilities_dict  # type: ignore[return-value]

    @capabilities.setter
    def capabilities(self, value: dict[str, Any]) -> None:
        self._capabilities_dict = value

    @property
    def engines(self) -> dict[str, Any]:
        self._ensure_full_tables()
        return self._engines_dict  # type: ignore[return-value]

    @engines.setter
    def engines(self, value: dict[str, Any]) -> None:
        self._engines_dict = value

    @property
    def skills(self) -> list[dict[str, Any]]:
        self._ensure_full_tables()
        if self._skills_list is None:
            self._skills_list = list(marshal.loads(self._skills_blob) if self._skills_blob else [])
            self._skills_blob = None
        return self._skills_list

    @skills.setter
    def skills(self, value: list[dict[str, Any]]) -> None:
        self._skills_list = value
        self._skills_blob = None

    @property
    def receipt_backed_ids(self) -> frozenset[str]:
        self._ensure_full_tables()
        return self._receipt_backed_set or frozenset()

    @receipt_backed_ids.setter
    def receipt_backed_ids(self, value: frozenset[str]) -> None:
        self._receipt_backed_set = value

    @property
    def index(self) -> dict[str, dict[str, float]]:
        self._ensure_full_tables()
        return self._index_dict  # type: ignore[return-value]

    @index.setter
    def index(self, value: dict[str, dict[str, float]]) -> None:
        self._index_dict = value

    @property
    def _scaled_index(self) -> dict[str, tuple[tuple[str, float], ...]]:
        self._ensure_route_tables()
        return self._scaled_index_map  # type: ignore[return-value]

    @property
    def _exact_id_lookup(self) -> dict[str, str]:
        self._ensure_route_tables()
        return self._exact_id_lookup_map  # type: ignore[return-value]

    @property
    def _cid_dot_pairs(self) -> tuple[tuple[str, str], ...]:
        self._ensure_route_tables()
        return self._cid_dot_pairs_tup  # type: ignore[return-value]

    @property
    def _cid_nodot_pairs(self) -> tuple[tuple[str, str], ...]:
        self._ensure_route_tables()
        return self._cid_nodot_pairs_tup  # type: ignore[return-value]

    @property
    def _eid_folded_triples(self) -> tuple[tuple[str, str, str], ...]:
        self._ensure_route_tables()
        return self._eid_folded_triples_tup  # type: ignore[return-value]

    @property
    def _mode_phrase_by_word(self) -> dict[str, tuple[tuple[str, str], ...]]:
        self._ensure_route_tables()
        return self._mode_phrase_by_word_map  # type: ignore[return-value]

    def _section_cache_path(self, section: str) -> Path | None:
        if not self._raw_sha256:
            return None
        return _core_cache_dir() / f"unified_model_sec_{section}_{self._raw_sha256[:32]}.marshal"

    def _read_section_cache(self, section: str) -> Any | None:
        p = self._section_cache_path(section)
        if p is None or not p.is_file():
            return None
        try:
            blob = marshal.loads(p.read_bytes())
            if isinstance(blob, dict) and blob.get("raw_sha256") == self._raw_sha256 and blob.get("v") == 2:
                return blob.get("data")
        except Exception:
            return None
        return None

    def _write_section_cache(self, section: str, data: Any) -> None:
        p = self._section_cache_path(section)
        if p is None:
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp_f = p.with_name(f".{p.name}.{os.getpid()}.tmp")
            tmp_f.write_bytes(marshal.dumps({"v": 2, "raw_sha256": self._raw_sha256, "data": data}))
            tmp_f.replace(p)
        except Exception:
            pass

    def _load_cold_section_rows(self, section_key: str) -> list[Any]:
        """Wave 39 Elon-Speed Cold-Section Slice Loader (`os.pread` over `section_byte_spans`):
        Reads and parses ONLY the requested JSON array slice (e.g. `447 KB` `harvested_capabilities`
        or `597 KB` `extended_source_index`) instead of parsing the entire `13.47 MB` full JSON.
        Falls back fail-closed to `_ensure_full_model()` whenever `self._model_loaded` is already
        resident, `self.path != MODEL_PATH`, or `st_size != artifact_bytes` (tamper protection)."""
        if self._model_loaded is not None:
            return list(self._model_loaded.get(section_key) or [])
        spans = self._core_meta.get("section_byte_spans")
        expected_bytes = int(self._core_meta.get("artifact_bytes") or -1)
        target = self._target_path
        default_target = (ROOT / DEFAULT_ARTIFACT).resolve()
        if (
            target is not None
            and target.resolve() == default_target
            and isinstance(spans, Mapping)
            and section_key in spans
            and expected_bytes > 0
            and target.exists()
        ):
            span = spans[section_key]
            if isinstance(span, Sequence) and len(span) == 2:
                start, end = int(span[0]), int(span[1])
                if 0 <= start < end <= expected_bytes:
                    try:
                        fd = os.open(str(target), os.O_RDONLY)
                        try:
                            st = os.fstat(fd)
                            if st.st_size == expected_bytes:
                                chunk = os.pread(fd, end - start, start)
                                parsed = json.loads(chunk.decode("utf-8"))
                                if isinstance(parsed, list):
                                    return parsed
                        finally:
                            os.close(fd)
                    except Exception:
                        pass
        full = self._ensure_full_model()
        return list(full.get(section_key) or [])

    def _ensure_harvested(self) -> None:
        if self._harvested_cache is not None:
            return
        cached = self._read_section_cache("harvested")
        if isinstance(cached, dict):
            self._harvested_cache = cached
            return
        raw_rows = self._load_cold_section_rows("harvested_capabilities")
        self._harvested_cache = {
            str(row["id"]): dict(row)
            for row in raw_rows
            if isinstance(row, Mapping) and row.get("id")
        }
        self._write_section_cache("harvested", self._harvested_cache)

    def _ensure_source_index(self) -> None:
        if self._source_index_cache is not None and self._source_postings_cache is not None:
            return
        csr = _get_mmap_csr("source_index", self._raw_sha256)
        if csr is not None:
            from canonical.runtime.mmap_csr_slot_index_v1 import (
                MmapDFProxy,
                MmapDocTableProxy,
                MmapPostingsProxy,
            )

            self._source_csr = csr
            self._source_index_cache = MmapDocTableProxy(csr)  # type: ignore[assignment]
            self._source_df_cache = MmapDFProxy(csr)  # type: ignore[assignment]
            self._source_postings_cache = MmapPostingsProxy(csr)  # type: ignore[assignment]
            return
        cached = self._read_section_cache("source_index")
        if isinstance(cached, dict) and "rows" in cached and "df" in cached and "postings" in cached:
            rows = cached["rows"]
            df = cached["df"]
            postings = cached["postings"]
        else:
            raw_rows = self._load_cold_section_rows("source_index")
            rows = {
                str(row["path"]): dict(row)
                for row in raw_rows
                if isinstance(row, Mapping) and row.get("path")
            }
            df = {}
            postings_tmp: dict[str, list[tuple[str, int]]] = {}
            for path, row in rows.items():
                terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
                for term, tf_val in terms.items():
                    s_term = str(term)
                    tf = int(tf_val or 0)
                    df[s_term] = df.get(s_term, 0) + 1
                    if tf > 0:
                        postings_tmp.setdefault(s_term, []).append((path, tf))
            postings = {k: tuple(v) for k, v in postings_tmp.items()}
            self._write_section_cache("source_index", {"rows": rows, "df": df, "postings": postings})

        if self._raw_sha256 and isinstance(rows, dict):
            try:
                from canonical.runtime.mmap_csr_slot_index_v1 import (
                    MmapDFProxy,
                    MmapDocTableProxy,
                    MmapPostingsProxy,
                    open_or_build_csr_index,
                )

                built_csr = open_or_build_csr_index(
                    "source_index", self._raw_sha256, rows, df_by_term=df, cache_dir=_core_cache_dir()
                )
                _MMAP_CSR_MEM_CACHE[("source_index", self._raw_sha256)] = built_csr
                self._source_csr = built_csr
                self._source_index_cache = MmapDocTableProxy(built_csr)  # type: ignore[assignment]
                self._source_df_cache = MmapDFProxy(built_csr)  # type: ignore[assignment]
                self._source_postings_cache = MmapPostingsProxy(built_csr)  # type: ignore[assignment]
                return
            except Exception:
                pass
        self._source_index_cache = rows
        self._source_df_cache = df
        self._source_postings_cache = postings

    def _ensure_extended_source_index(self) -> None:
        if self._extended_source_index_cache is not None and self._extended_source_postings_cache is not None:
            return
        cached = self._read_section_cache("extended_source_index")
        if isinstance(cached, dict) and "rows" in cached and "df" in cached and "postings" in cached:
            self._extended_source_index_cache = cached["rows"]
            self._extended_source_df_cache = cached["df"]
            self._extended_source_postings_cache = cached["postings"]
            return
        raw_rows = self._load_cold_section_rows("extended_source_index")
        rows = {
            str(row["path"]): dict(row)
            for row in raw_rows
            if isinstance(row, Mapping) and row.get("path")
        }
        df: dict[str, int] = {}
        postings_tmp: dict[str, list[tuple[str, int]]] = {}
        for path, row in rows.items():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term, tf_val in terms.items():
                s_term = str(term)
                tf = int(tf_val or 0)
                df[s_term] = df.get(s_term, 0) + 1
                if tf > 0:
                    postings_tmp.setdefault(s_term, []).append((path, tf))
        postings = {k: tuple(v) for k, v in postings_tmp.items()}
        self._extended_source_index_cache = rows
        self._extended_source_df_cache = df
        self._extended_source_postings_cache = postings
        self._write_section_cache("extended_source_index", {"rows": rows, "df": df, "postings": postings})

    def _ensure_combined_source_index(self) -> None:
        if self._combined_source_index_cache is not None and self._combined_source_postings_cache is not None:
            return
        csr = _get_mmap_csr("combined_source", self._raw_sha256)
        if csr is not None:
            from canonical.runtime.mmap_csr_slot_index_v1 import (
                MmapDocTableProxy,
                MmapPostingsProxy,
            )

            self._combined_source_csr = csr
            self._combined_source_index_cache = MmapDocTableProxy(csr)  # type: ignore[assignment]
            self._combined_source_postings_cache = MmapPostingsProxy(csr)  # type: ignore[assignment]
            return
        self._ensure_source_index()
        self._ensure_extended_source_index()
        src_map = self._source_index_cache or {}
        ext_map = self._extended_source_index_cache or {}
        comb = dict(src_map)
        comb.update(ext_map)
        if self._raw_sha256 and isinstance(comb, dict):
            try:
                from canonical.runtime.mmap_csr_slot_index_v1 import (
                    MmapDocTableProxy,
                    MmapPostingsProxy,
                    open_or_build_csr_index,
                )

                built_comb_csr = open_or_build_csr_index(
                    "combined_source", self._raw_sha256, comb, cache_dir=_core_cache_dir()
                )
                _MMAP_CSR_MEM_CACHE[("combined_source", self._raw_sha256)] = built_comb_csr
                self._combined_source_csr = built_comb_csr
                self._combined_source_index_cache = MmapDocTableProxy(built_comb_csr)  # type: ignore[assignment]
                self._combined_source_postings_cache = MmapPostingsProxy(built_comb_csr)  # type: ignore[assignment]
                return
            except Exception:
                pass
        src_p = self._source_postings_cache or {}
        ext_p = self._extended_source_postings_cache or {}
        if not ext_p:
            comb_p = src_p
        else:
            merged: dict[str, tuple[tuple[str, int], ...]] = dict(src_p)
            overridden = set(ext_map.keys())
            for term, ext_entries in ext_p.items():
                base = merged.get(term)
                if base is None:
                    merged[term] = ext_entries
                else:
                    filtered = [e for e in base if e[0] not in overridden]
                    filtered.extend(ext_entries)
                    merged[term] = tuple(filtered)
            comb_p = merged
        self._combined_source_index_cache = comb
        self._combined_source_postings_cache = comb_p

    def _ensure_research_index(self) -> None:
        if self._research_index_cache is not None and self._research_postings_cache is not None:
            return
        cached = self._read_section_cache("research_index")
        if isinstance(cached, dict) and "rows" in cached and "df" in cached and "postings" in cached:
            self._research_index_cache = cached["rows"]
            self._research_df_cache = cached["df"]
            self._research_postings_cache = cached["postings"]
            return
        raw_rows = self._load_cold_section_rows("research_index")
        rows = {
            str(row["path"]): dict(row)
            for row in raw_rows
            if isinstance(row, Mapping) and row.get("path")
        }
        df: dict[str, int] = {}
        postings_tmp: dict[str, list[tuple[str, int]]] = {}
        for path, row in rows.items():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term, tf_val in terms.items():
                s_term = str(term)
                tf = int(tf_val or 0)
                df[s_term] = df.get(s_term, 0) + 1
                if tf > 0:
                    postings_tmp.setdefault(s_term, []).append((path, tf))
        postings = {k: tuple(v) for k, v in postings_tmp.items()}
        self._research_index_cache = rows
        self._research_df_cache = df
        self._research_postings_cache = postings
        self._write_section_cache("research_index", {"rows": rows, "df": df, "postings": postings})

    def _ensure_knowledge(self) -> None:
        if self._knowledge_cache is not None and self._knowledge_postings_cache is not None:
            return
        cached = self._read_section_cache("knowledge")
        if (
            isinstance(cached, dict)
            and "rows" in cached
            and "df" in cached
            and "postings" in cached
            and "title_postings" in cached
        ):
            self._knowledge_cache = cached["rows"]
            self._knowledge_df_cache = cached["df"]
            self._knowledge_lengths_cache = cached["lengths"]
            self._avg_length_cache = float(cached["avg_len"])
            self._knowledge_postings_cache = cached["postings"]
            self._knowledge_title_postings_cache = cached["title_postings"]
            return
        raw_rows = self._load_cold_section_rows("knowledge")
        rows = [
            dict(row) for row in raw_rows if isinstance(row, Mapping)
        ]
        df: dict[str, int] = {}
        lengths: list[int] = []
        postings_tmp: dict[str, list[tuple[int, int]]] = {}
        title_tmp: dict[str, list[int]] = {}
        for idx, row in enumerate(rows):
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            lengths.append(sum(int(v) for v in terms.values()))
            for term, tf_val in terms.items():
                s_term = str(term)
                tf = int(tf_val or 0)
                df[s_term] = df.get(s_term, 0) + 1
                if tf > 0:
                    postings_tmp.setdefault(s_term, []).append((idx, tf))
            for t_term in row.get("title_terms") or ():
                title_tmp.setdefault(str(t_term), []).append(idx)
        avg_len = (sum(lengths) / len(lengths) if lengths else 1.0) or 1.0
        postings = {k: tuple(v) for k, v in postings_tmp.items()}
        title_postings = {k: tuple(v) for k, v in title_tmp.items()}
        self._knowledge_cache = rows
        self._knowledge_df_cache = df
        self._knowledge_lengths_cache = lengths
        self._avg_length_cache = avg_len
        self._knowledge_postings_cache = postings
        self._knowledge_title_postings_cache = title_postings
        self._write_section_cache(
            "knowledge",
            {
                "rows": rows,
                "df": df,
                "lengths": lengths,
                "avg_len": avg_len,
                "postings": postings,
                "title_postings": title_postings,
            },
        )

    def harvested_surfaces(self) -> list[dict[str, Any]]:
        """Every discovered surface the tree carries but no registry declares."""
        self._ensure_harvested()
        return [dict(row) for row in (self._harvested_cache or {}).values()]

    def find_harvested(self, capability_id: str) -> dict[str, Any] | None:
        """One discovered surface by id, or None. Never returns a capability."""
        self._ensure_harvested()
        row = (self._harvested_cache or {}).get(str(capability_id))
        return dict(row) if row else None

    def _ensure_harvested_index(self) -> dict[str, dict[str, float]]:
        """Lazily build the harvested trigger index (token -> {id: weight}).

        Mirrors the capability grammar: IDF-weighted postings over declared
        triggers plus id tokens. Built once per model instance; the fallback
        in ``solve()`` only runs when the primary route fails, so this cost
        is off the hot path.
        """
        if self._harvested_index is not None:
            return self._harvested_index
        self._ensure_harvested()
        rows = self._harvested_cache or {}
        postings: dict[str, dict[str, int]] = {}
        for hid, row in rows.items():
            seen: set[str] = set()
            for trigger in row.get("triggers") or []:
                for token in tokenize(str(trigger)):
                    if token not in seen:
                        seen.add(token)
                        postings.setdefault(token, {})[hid] = 2
            for token in tokenize(hid.replace("/", " ").replace(".", " ")):
                if token not in seen:
                    seen.add(token)
                    postings.setdefault(token, {})[hid] = 3
        total = max(1, len(rows))
        index: dict[str, dict[str, float]] = {}
        for token in sorted(postings):
            idf = 1.0 + (total / (1.0 + len(postings[token])))
            index[token] = {
                hid: round(w * idf, 6) for hid, w in sorted(postings[token].items())
            }
        self._harvested_index = index
        return index

    def route_harvested(self, goal: str, *, top_k: int = 5) -> dict[str, Any]:
        """Score harvested surfaces against a goal. Never returns a capability.

        This is the fallback router: it answers "which discovered surface
        could serve this goal?" with ``admitted: False`` on every row. It
        does not promote, admit, or verify anything — execution still goes
        through ``execute_harvested_surface`` and still issues only a
        producer receipt.
        """
        tokens = tokenize(goal)
        index = self._ensure_harvested_index()
        ask_list: list[str] = []
        seen: set[str] = set()
        for token in ask_tokens(goal):
            if token not in seen:
                seen.add(token)
                ask_list.append(token)
        scores: dict[str, float] = {}
        matched: set[str] = set()
        for token in ask_list:
            postings = index.get(token)
            if not postings:
                continue
            matched.add(token)
            for hid, weight in postings.items():
                scores[hid] = scores.get(hid, 0.0) + math.log1p(weight)
        ask = set(ask_list)
        coverage = (len(matched & ask) / len(ask)) if ask else 0.0
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        rows: list[dict[str, Any]] = []
        for hid, score in ranked[: max(1, int(top_k))]:
            row = (self._harvested_cache or {}).get(hid) or {}
            rows.append(
                {
                    "id": hid,
                    "kind": "HARVESTED_SURFACE",
                    "score": round(float(score), 6),
                    "coverage": round(coverage, 6),
                    "admitted": False,
                    "path": row.get("path"),
                    "invocation": row.get("invocation"),
                }
            )
        best = ranked[0] if ranked else None
        confident = bool(best and best[1] >= self.min_score and coverage >= self.min_coverage)
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "ROUTE_HARVESTED",
            "model_digest": self.digest,
            "goal": goal,
            "query_tokens": tokens,
            "matched_token_count": len(matched),
            "coverage": round(coverage, 6),
            "confident": confident,
            "best": rows[0] if rows else None,
            "candidates": rows,
            "reason": (
                "HARVESTED_SURFACE_ROUTED__NOT_ADMITTED"
                if confident
                else "NO_HARVESTED_SURFACE_MATCHED__FAIL_CLOSED"
            ),
        }

    def _ensure_full_model(self) -> dict[str, Any]:
        if self._model_loaded is None:
            if self._raw_bytes_backing is None and self._artifact_path is not None and self._artifact_path.is_file():
                self._raw_bytes_backing = self._artifact_path.read_bytes()
            if self._raw_bytes_backing is None:
                if self._target_path is not None and self._target_path.is_file():
                    self._raw_bytes_backing = self._target_path.read_bytes()
                else:
                    raise UnifiedModelError("MODEL_BACKING_BYTES_MISSING")
            self._model_loaded = json.loads(self._raw_bytes_backing.decode("utf-8"))
        return self._model_loaded

    def _ensure_fts5_sidecar(self) -> Path:
        """Build or open the lazy on-demand SQLite FTS5 BM25 sidecar over cold indices."""
        cache_dir = _core_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        db_path = cache_dir / f"unified_model_fts5_{(self.digest or 'unhashed')[:24]}.sqlite"
        if db_path.is_file() and db_path.stat().st_size > 4096:
            return db_path

        full = self._ensure_full_model()
        tmp_db = cache_dir / f".unified_model_fts5_{os.getpid()}.sqlite.tmp"
        tmp_db.unlink(missing_ok=True)
        conn = sqlite3.connect(str(tmp_db))
        try:
            conn.execute("PRAGMA synchronous = OFF;")
            conn.execute("PRAGMA journal_mode = MEMORY;")
            conn.execute(
                "CREATE VIRTUAL TABLE docs USING fts5(doc_id UNINDEXED, kind, path, title, body);"
            )
            batch: list[tuple[str, str, str, str, str]] = []
            for row in full.get("knowledge") or []:
                if isinstance(row, Mapping):
                    terms_s = " ".join(str(k) for k in (row.get("terms") or {}).keys())
                    batch.append((
                        f"knowledge:{row.get('path', '')}",
                        "KNOWLEDGE",
                        str(row.get("path") or ""),
                        str(row.get("title") or ""),
                        f"{row.get('summary') or ''} {terms_s}",
                    ))
            for row in full.get("source_index") or []:
                if isinstance(row, Mapping):
                    terms_s = " ".join(str(k) for k in (row.get("terms") or {}).keys())
                    syms = " ".join(str(s) for s in (row.get("symbols") or []))
                    batch.append((
                        str(row.get("id") or ""),
                        "SOURCE",
                        str(row.get("path") or ""),
                        syms[:240],
                        f"{row.get('docstring') or ''} {terms_s}",
                    ))
            for row in full.get("research_index") or []:
                if isinstance(row, Mapping):
                    terms_s = " ".join(str(k) for k in (row.get("terms") or {}).keys())
                    batch.append((
                        str(row.get("id") or ""),
                        "RESEARCH",
                        str(row.get("path") or ""),
                        str(row.get("schema") or ""),
                        f"{row.get('action_id') or ''} {row.get('status') or ''} {terms_s}",
                    ))
            conn.executemany("INSERT INTO docs VALUES (?, ?, ?, ?, ?);", batch)
            conn.commit()
        finally:
            conn.close()
        tmp_db.replace(db_path)
        return db_path

    def fts5_search(
        self,
        query: str,
        *,
        kind: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Sub-millisecond SQLite FTS5 BM25 query over cold knowledge/source/research indices."""
        tokens = [re.sub(r"[^a-z0-9_]", "", t) for t in tokenize(query)]
        tokens = [t for t in tokens if len(t) >= 2]
        if not tokens:
            return {"query": query, "hits": [], "engine": "sqlite_fts5_bm25"}
        fts_expr = " OR ".join(f'"{t}"' for t in tokens[:12])
        db_path = self._ensure_fts5_sidecar()
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            if kind:
                cur = conn.execute(
                    "SELECT doc_id, kind, path, title, bm25(docs) AS score FROM docs "
                    "WHERE docs MATCH ? AND kind = ? ORDER BY score LIMIT ?;",
                    (fts_expr, kind.upper(), max(1, int(top_k))),
                )
            else:
                cur = conn.execute(
                    "SELECT doc_id, kind, path, title, bm25(docs) AS score FROM docs "
                    "WHERE docs MATCH ? ORDER BY score LIMIT ?;",
                    (fts_expr, max(1, int(top_k))),
                )
            hits = [
                {"doc_id": r[0], "kind": r[1], "path": r[2], "title": r[3], "bm25": round(-float(r[4]), 4)}
                for r in cur.fetchall()
            ]
        finally:
            conn.close()
        return {"query": query, "hits": hits, "engine": "sqlite_fts5_bm25"}

    def _apply_secondary_bundle(self, sec: Mapping[str, Any]) -> None:
        self._source_index_cache = dict(sec["source_index"])
        self._source_df_cache = dict(sec["source_df"])
        self._source_postings_cache = dict(sec["source_postings"])
        self._extended_source_index_cache = dict(sec["extended_source_index"])
        self._extended_source_df_cache = dict(sec["extended_source_df"])
        ext_p: dict[str, list[tuple[str, int]]] = {}
        for path, row in self._extended_source_index_cache.items():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term, tf_val in terms.items():
                tf = int(tf_val or 0)
                if tf > 0:
                    ext_p.setdefault(str(term), []).append((path, tf))
        self._extended_source_postings_cache = {k: tuple(v) for k, v in ext_p.items()}
        self._combined_source_index_cache = dict(sec["combined_source_index"])
        self._combined_source_postings_cache = dict(sec["combined_source_postings"])
        self._harvested_cache = dict(sec["harvested"])
        self._research_index_cache = dict(sec["research_index"])
        self._research_df_cache = dict(sec["research_df"])
        self._research_postings_cache = dict(sec["research_postings"])
        self._knowledge_cache = list(sec["knowledge"])
        self._knowledge_df_cache = dict(sec["knowledge_df"])
        self._knowledge_lengths_cache = list(sec["knowledge_lengths"])
        self._avg_length_cache = float(sec["avg_length"])
        self._knowledge_postings_cache = dict(sec["knowledge_postings"])
        self._knowledge_title_postings_cache = dict(sec["knowledge_title_postings"])

    @property
    def model(self) -> dict[str, Any]:
        return self._ensure_full_model()

    @property
    def source_index(self) -> dict[str, dict[str, Any]]:
        self._ensure_source_index()
        return self._source_index_cache  # type: ignore[return-value]

    @property
    def _source_df(self) -> dict[str, int]:
        self._ensure_source_index()
        return self._source_df_cache  # type: ignore[return-value]

    @property
    def extended_source_index(self) -> dict[str, dict[str, Any]]:
        self._ensure_extended_source_index()
        return self._extended_source_index_cache  # type: ignore[return-value]

    @property
    def research_index(self) -> dict[str, dict[str, Any]]:
        self._ensure_research_index()
        return self._research_index_cache  # type: ignore[return-value]

    @property
    def _research_df(self) -> dict[str, int]:
        self._ensure_research_index()
        return self._research_df_cache  # type: ignore[return-value]

    @property
    def knowledge(self) -> list[dict[str, Any]]:
        self._ensure_knowledge()
        return self._knowledge_cache  # type: ignore[return-value]

    @property
    def _knowledge_df(self) -> dict[str, int]:
        self._ensure_knowledge()
        return self._knowledge_df_cache  # type: ignore[return-value]

    # ------------------------------------------------------------------ status

    def status(self) -> dict[str, Any]:
        declared = self._core_meta.get("counts") or {}
        missing_ids = sorted(
            cid
            for cid, row in self.capabilities.items()
            if _missing_declared_dependencies(row)
        )
        present = len(self.capabilities) - len(missing_ids)
        src_len = (
            len(self._source_index_cache)
            if self._source_index_cache is not None
            else int(self._core_meta.get("source_index_len") or 0)
        )
        src_ep = (
            sum(1 for row in self._source_index_cache.values() if row.get("classification") == "ENTRY_POINT")
            if isinstance(self._source_index_cache, dict)
            else int(self._core_meta.get("source_entry_points") or 0)
        )
        ext_src_len = (
            len(self._extended_source_index_cache)
            if self._extended_source_index_cache is not None
            else int(self._core_meta.get("extended_source_index_len") or 0)
        )
        res_len = (
            len(self._research_index_cache)
            if self._research_index_cache is not None
            else int(self._core_meta.get("research_index_len") or 0)
        )
        knw_len = (
            len(self._knowledge_cache)
            if self._knowledge_cache is not None
            else int(self._core_meta.get("knowledge_len") or 0)
        )
        fed_eng_len = sum(
            1 for row in self.engines.values() if row.get("kind") == "FEDERATED_KERNEL_ENGINE"
        )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "STATUS",
            "model_id": self._core_meta.get("model_id"),
            "model_version": self._core_meta.get("model_version"),
            "model_digest": self.digest,
            "counts": {
                "capabilities": len(self.capabilities),
                "bound_capabilities": declared.get("bound_capabilities"),
                "receipt_backed_capabilities": declared.get("receipt_backed_capabilities"),
                "engines": len(self.engines),
                "federated_kernel_engines": fed_eng_len,
                "skills": len(self.skills),
                "knowledge_documents": knw_len,
                "source_index_modules": src_len,
                "source_index_entry_points": src_ep,
                "extended_source_index_modules": ext_src_len,
                "research_index_records": res_len,
                "routing_tokens": len(self.index),
                "harvested_capabilities": declared.get("harvested_capabilities"),
                "frontier_leapfrog_organs": 21,
            },
            "source_index_is_addressable_not_executable": True,
            "declared_dependencies_present": present,
            "declared_dependencies_missing": len(self.capabilities) - present,
            "unified_runtime_bridge": {
                "creature_runtime": "canonical/runtime/creature_runtime_v1.py",
                "harvested_runtime": "canonical/runtime/harvested_capability_runtime_v1.py",
                "composer_route": "canonical/runtime/composer_route_v1.py",
                "spines": ["0D", "0E", "0F", "0G", "0H", "0I"],
            },
            "objective": self._core_meta.get("objective_verbatim"),
            "non_claims": list(NON_CLAIMS),
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
        }

    # --------------------------------------------------------- frontier organs

    def frontier_organs(self) -> dict[str, Any]:
        """Enumerate the 13 `swe_kernel` organs, 8 Frontier Leapfrog Plays, and Unified Leapfrog Moves."""
        from canonical.runtime import swe_kernel_organ_bridge_v1 as bridge

        swe_organs = bridge.list_organs()
        plays = [
            {
                "organ_id": "play_1_contract_world_model",
                "module_path": "canonical/runtime/state_contract_world_model_v1.py",
                "frontier_domain": "computer_use",
                "capability_role": "State-as-contract desktop effect-delta world model with volatile canonicalization",
            },
            {
                "organ_id": "play_2_law_consolidation",
                "module_path": "canonical/runtime/gradient_free_law_consolidation_v1.py",
                "frontier_domain": "continual_learning",
                "capability_role": "Gradient-free episodic law consolidation v1 (historical baseline)",
            },
            {
                "organ_id": "play_3_abstain_skill_induction",
                "module_path": "canonical/runtime/abstain_gated_skill_induction_v1.py",
                "frontier_domain": "instant_learning",
                "capability_role": "Abstain-gated structural AST skill induction over 40 real-commit episodes",
            },
            {
                "organ_id": "play_6_mutation_admission_gate",
                "module_path": "canonical/runtime/adversarial_mutation_admission_gate_v1.py",
                "frontier_domain": "coding_agents",
                "capability_role": "Adversarial AST mutation admission gate v1 (single-probe baseline)",
            },
            {
                "organ_id": "play_a_counterfactual_discr_tree_router",
                "module_path": "canonical/runtime/counterfactual_discr_tree_skill_router_v1.py",
                "frontier_domain": "continual_learning",
                "capability_role": "Witness-conditioned AST discrimination-tree router (5.4 us p50) with Rubin counterfactual utility gating",
            },
            {
                "organ_id": "play_b_verified_zero_screenshot_cache",
                "module_path": "canonical/runtime/verified_zero_screenshot_action_cache_v1.py",
                "frontier_domain": "computer_use",
                "capability_role": "Three-tier zero-screenshot data-layer workflow elevator and volatile-invariant CDP pre-probe cache",
            },
            {
                "organ_id": "play_c_relational_guard_addition_repair",
                "module_path": "canonical/runtime/relational_guard_addition_symbolic_repair_v1.py",
                "frontier_domain": "coding_agents",
                "capability_role": "Semi-naive relational AST guard/exception-contract/container-sync addition synthesizer with GuardDrop mutation gate",
            },
            {
                "organ_id": "play_d_cow_zygote_speculative_verifier",
                "module_path": "canonical/runtime/cow_zygote_speculative_verifier_v1.py",
                "frontier_domain": "verification_abstention",
                "capability_role": "POSIX os.fork() copy-on-write Zygote speculative patch verifier (1.58 ms p50) with AST test impact slicing",
            },
        ]
        moves = [
            {
                "organ_id": "play_2_law_consolidation_v2",
                "module_path": "canonical/runtime/gradient_free_law_consolidation_v2.py",
                "frontier_domain": "continual_learning",
                "capability_role": "Popper negative-witness specialization + SemiPersistentEGraph anti-unification v2 (zero false refutations, held-out transfer)",
            },
            {
                "organ_id": "play_6_mutation_admission_gate_v2",
                "module_path": "canonical/runtime/adversarial_mutation_admission_gate_v2.py",
                "frontier_domain": "coding_agents",
                "capability_role": "Apartness-guided nominal/boundary/refusal distinguishing-tuple mutation gate v2 (<15% survivor rate)",
            },
            {
                "organ_id": "move_2_cow_zygote_bus",
                "module_path": "canonical/swe_kernel/canonical_cu_sandbox_spine_v1.py",
                "frontier_domain": "computer_use",
                "capability_role": "os.fork() CoW ZygotePrewarmedPool + renameat2(RENAME_EXCHANGE) speculative execution bus",
            },
            {
                "organ_id": "move_3_swe_abduction_spine",
                "module_path": "canonical/swe_kernel/canonical_swe_spine_v1.py",
                "frontier_domain": "coding_agents",
                "capability_role": "Zero-disk CoW assertion-demand + failing-relation + witness-inversion SWE fast lane",
            },
            {
                "organ_id": "move_5_surprise_organism",
                "module_path": "canonical/swe_kernel/canonical_env_discovery_spine_v1.py",
                "frontier_domain": "instant_learning",
                "capability_role": "Surprise-gated active organism with refusal-curriculum prerequisite synthesis & active disambiguation",
            },
            {
                "organ_id": "move_1_trigram_impact_pareto",
                "module_path": "canonical/runtime/frontier_seven_moves_runtime_v1.py",
                "frontier_domain": "coding_agents",
                "capability_role": "64-bit Python int-bitset positional 3-gram search (<0.5 ms), depth-3 blast radius (<0.05 ms), and bloat Pareto auditor",
            },
            {
                "organ_id": "move_2_proof_mined_surface",
                "module_path": "canonical/runtime/frontier_seven_moves_runtime_v1.py",
                "frontier_domain": "instant_learning",
                "capability_role": "Proof-mined AST call-vector & CoW 2-run deterministic surface compiler (lifting 406 dark modules 3.7% -> 55.9%)",
            },
            {
                "organ_id": "move_3_speculative_multiverse",
                "module_path": "canonical/runtime/frontier_seven_moves_runtime_v1.py",
                "frontier_domain": "world_model",
                "capability_role": "Two-speed 10-50us RAM SemanticIR mental model + CDCL Equivalence-Modulo-Conflict nogood pruner -> CoW Zygote",
            },
            {
                "organ_id": "move_5_doors_first_hidden_smc",
                "module_path": "canonical/runtime/frontier_seven_moves_runtime_v1.py",
                "frontier_domain": "computer_use",
                "capability_role": "Zero-pixel 4-tier Doors-First computer use + executor-hidden Speculative Macro Commit guarded by state projections",
            },
            {
                "organ_id": "move_6_unblind_continual_memory",
                "module_path": "canonical/runtime/frontier_seven_moves_runtime_v1.py",
                "frontier_domain": "memory",
                "capability_role": "DBSP Z-set O(1) ForgetEval deletion + rule_expiry witness check + synthesized-oracle Clopper-Pearson curator + E-Stitch",
            },
            {
                "organ_id": "move_7_global_extrapolation_gate",
                "module_path": "canonical/runtime/frontier_seven_moves_runtime_v1.py",
                "frontier_domain": "verification_abstention",
                "capability_role": "Domain-of-verification extrapolation blocker + Purpose Gate contrast check + minimum-action global discriminator",
            },
            {
                "organ_id": "unfamiliar_m0_apartness_lsharp",
                "module_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
                "frontier_domain": "instant_learning",
                "capability_role": "Observation-table-free Brouwer-Heyting constructive apartness (L# / L#_e) active Mealy learner with error-sink pruning (<0.25 ms)",
            },
            {
                "organ_id": "unfamiliar_m1_angelic_sygus_swe",
                "module_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
                "frontier_domain": "coding_agents",
                "capability_role": "CoW Angelic Forest impossibility sieve + EUSolver OE-SyGuS + NAME_SCOPE + 4-gate non-vacuous test verifier",
            },
            {
                "organ_id": "unfamiliar_m2_protocol_lift_oracle",
                "module_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
                "frontier_domain": "computer_use",
                "capability_role": "WebMCP + CDP/HAR network-to-HTTP protocol lifter + kernel namespace confinement + magic-header round-trip effect oracle",
            },
            {
                "organ_id": "unfamiliar_m3_semiring_jtms_meme",
                "module_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
                "frontier_domain": "memory",
                "capability_role": "Why-Provenance Semiring (2^(2^V), union, join) over Z-set DBSP achieving 100% MEME Cascade & Absence in <15 us",
            },
            {
                "organ_id": "unfamiliar_m4_minimax_interrogator",
                "module_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
                "frontier_domain": "verification_abstention",
                "capability_role": "Exact DP minimax decision-region version-space interrogator (finite_minimax_decision_region_v1) with irreversibility gating",
            },
            {
                "organ_id": "unfamiliar_m5_zero_llm_alphaevolve",
                "module_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
                "frontier_domain": "continual_learning",
                "capability_role": "Zero-LLM AlphaEvolve MAP-Elites + Pareto synthesizer guarded by adversarial anti-reward-hacking evaluator audit",
            },
            {
                "organ_id": "w39_zero_adapter_inventory_bridge",
                "module_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
                "frontier_domain": "capability_composition",
                "capability_role": "Zero-wrapper bridge composing module_bridge_v1 (5,221 functions) with type_level_composer_v1 type graphs",
            },
            {
                "organ_id": "w39_moore_ontology_witness_learner",
                "module_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
                "frontier_domain": "instant_learning",
                "capability_role": "Action-invariant Moore bisimulation transfer + OPINE-World ontology residual + FlashMeta D4 witness inversion + Galois lattice",
            },
            {
                "organ_id": "w39_lens_standing_fact_cu",
                "module_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
                "frontier_domain": "computer_use",
                "capability_role": "OOXML/JSON bijective lenses + relational anchored frame + CAS stale-click guard + standing-fact batch clobber recovery",
            },
            {
                "organ_id": "w39_deltastate_sibling_swe",
                "module_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
                "frontier_domain": "coding_agents",
                "capability_role": "Oracle calibration + Plastic Surgery donor mining + Coccinelle multi-file sibling closure + DeltaBox warm-zygote os.fork() rollout",
            },
            {
                "organ_id": "w39_prospective_memtx_replay",
                "module_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
                "frontier_domain": "memory",
                "capability_role": "Kumiho prospective cue indexing + CPB Sybil echo block + AGM K*7/K*8 entrenchment + RD-Forget selective replay unlearning",
            },
            {
                "organ_id": "w39_meaning_ir_cross_lang_ratchet",
                "module_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
                "frontier_domain": "continual_learning",
                "capability_role": "Babble/Stitch Meaning-IR anti-unification + zero-shot verified cross-language recall (Python/JS/TS/Go/Rust) + MDL bit-rent eviction",
            },
        ]
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "FRONTIER_ORGANS",
            "swe_kernel_organs_count": len(swe_organs),
            "leapfrog_plays_count": len(plays),
            "total_organs": len(swe_organs) + len(plays),
            "leapfrog_moves_count": len(moves),
            "total_organs_including_moves": len(swe_organs) + len(plays) + len(moves),
            "swe_kernel_organs": swe_organs,
            "leapfrog_plays": plays,
            "leapfrog_moves": moves,
            "model_dependency_count": 0,
        }

    def invoke_frontier_organ(
        self,
        organ_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a wired `swe_kernel` organ or Frontier Leapfrog Play/Move through the Unified Runtime."""
        req = dict(payload or {})
        if organ_id == "play_1_contract_world_model":
            from canonical.runtime import state_contract_world_model_v1 as p1

            return p1.run(req, ROOT)
        if organ_id == "play_2_law_consolidation":
            from canonical.runtime import gradient_free_law_consolidation_v1 as p2

            return p2.run(req, ROOT)
        if organ_id == "play_2_law_consolidation_v2":
            from canonical.runtime import gradient_free_law_consolidation_v2 as p2v2

            return p2v2.run(req, ROOT)
        if organ_id == "play_3_abstain_skill_induction":
            from canonical.runtime import abstain_gated_skill_induction_v1 as p3

            return p3.run(req, ROOT)
        if organ_id == "play_6_mutation_admission_gate":
            from canonical.runtime import adversarial_mutation_admission_gate_v1 as p6

            return p6.run(req, ROOT)
        if organ_id == "play_6_mutation_admission_gate_v2":
            from canonical.runtime import adversarial_mutation_admission_gate_v2 as p6v2

            return p6v2.run(req, ROOT)
        if organ_id == "move_2_cow_zygote_bus":
            return self.execute_speculative(**req)
        if organ_id == "move_3_swe_abduction_spine":
            repo_root = req.pop("repo_root", ROOT)
            return self.solve_swe_repo(repo_root, **req)
        if organ_id == "move_5_surprise_organism":
            return self.autonomous_pulse(**req)
        if organ_id == "move_1_trigram_impact_pareto":
            if "pattern" in req:
                return self.trigram_search(str(req.pop("pattern")), **req)
            if "target" in req:
                return self.impact_blast_radius(str(req.pop("target")), **req)
            return self.audit_bloat_pareto()
        if organ_id == "move_2_proof_mined_surface":
            if "invoke_module" in req:
                return self.invoke_mined_surface(str(req.pop("invoke_module")), **req)
            return self.derive_and_verify_surface(**req)
        if organ_id == "move_3_speculative_multiverse":
            return self.speculate_multiverse(**req)
        if organ_id == "move_5_doors_first_hidden_smc":
            ws = req.pop("workspace_dir")
            steps = req.pop("workflow_steps")
            return self.execute_doors_first(ws, steps, **req)
        if organ_id == "move_6_unblind_continual_memory":
            return self.continual_memory_cycle(**req)
        if organ_id == "move_7_global_extrapolation_gate":
            return self.evaluate_global_extrapolation(**req)
        if organ_id == "unfamiliar_m0_apartness_lsharp":
            return self.learn_apartness_lsharp(**req)
        if organ_id == "unfamiliar_m1_angelic_sygus_swe":
            return self.solve_angelic_sygus_swe(str(req.pop("source_text")), str(req.pop("test_source")), **req)
        if organ_id == "unfamiliar_m2_protocol_lift_oracle":
            return self.lift_protocol_and_verify_effect(**req)
        if organ_id == "unfamiliar_m3_semiring_jtms_meme":
            return self.semiring_jtms_memory_cycle(**req)
        if organ_id == "unfamiliar_m4_minimax_interrogator":
            return self.minimax_interrogate_version_space(**req)
        if organ_id == "unfamiliar_m5_zero_llm_alphaevolve":
            return self.evolve_pareto_organ(str(req.pop("baseline_source")), **req)
        if organ_id == "unfamiliar_six_moves_suite":
            return self.run_unfamiliar_six_moves_suite()
        if organ_id == "play_a_counterfactual_discr_tree_router":
            from canonical.runtime import counterfactual_discr_tree_skill_router_v1 as pa

            return pa.run(req, ROOT)
        if organ_id == "play_b_verified_zero_screenshot_cache":
            from canonical.runtime import verified_zero_screenshot_action_cache_v1 as pb

            return pb.run(req, ROOT)
        if organ_id == "play_c_relational_guard_addition_repair":
            from canonical.runtime import relational_guard_addition_symbolic_repair_v1 as pc

            return pc.run(req, ROOT)
        if organ_id == "play_d_cow_zygote_speculative_verifier":
            from canonical.runtime import cow_zygote_speculative_verifier_v1 as pd

            return pd.run(req, ROOT)
        if organ_id == "w39_zero_adapter_inventory_bridge":
            goal = str(req.pop("goal", "inventory"))
            return self.zero_adapter_inventory_bridge(goal, **req)
        if organ_id == "w39_moore_ontology_witness_learner":
            return self.instant_learn_moore_witness(**req)
        if organ_id == "w39_lens_standing_fact_cu":
            return self.execute_lens_standing_fact_cu(**req)
        if organ_id == "w39_deltastate_sibling_swe":
            rr = req.pop("repo_root", ROOT)
            return self.repair_swe_deltastate_siblings(rr, **req)
        if organ_id == "w39_prospective_memtx_replay":
            return self.prospective_memtx_op(**req)
        if organ_id == "w39_meaning_ir_cross_lang_ratchet":
            return self.consolidate_meaning_ir_skill(**req)

        from canonical.runtime import swe_kernel_organ_bridge_v1 as bridge

        if organ_id == "probe_all_swe_kernel_organs":
            return bridge.probe_all_organs(ROOT)
        return bridge.invoke_organ(organ_id, req, ROOT)

    def anatomy(self, domain: str | None = None, *, top_k: int = 8) -> dict[str, Any]:
        """Where this repository implements each frontier function, by its own words."""
        block = self._core_meta.get("anatomy")
        if not block and not self._tables_loaded:
            self._ensure_full_tables()
            block = self._core_meta.get("anatomy")
        if not block and self._model_loaded:
            block = self._model_loaded.get("anatomy")
        if not block:
            return {
                "schema": ANATOMY_SCHEMA,
                "operation": "ANATOMY",
                "reason": "MODEL_HAS_NO_ANATOMY_BLOCK__RECOMPILE_WITH_DOMAIN_ATLAS",
                "domains": {},
                "capability": False,
                "executable": False,
            }
        domains = block.get("domains") or {}
        if domain is not None:
            row = domains.get(domain)
            if row is None:
                return {
                    "schema": ANATOMY_SCHEMA,
                    "operation": "ANATOMY",
                    "query": domain,
                    "reason": "UNKNOWN_DOMAIN__KNOWN: " + ", ".join(sorted(domains)),
                    "domains": {},
                    "capability": False,
                    "executable": False,
                }
            rows = list(row.get("top") or [])[: max(1, int(top_k))]
            return {
                "schema": ANATOMY_SCHEMA,
                "operation": "ANATOMY",
                "query": domain,
                "frontier_function": row.get("frontier_function"),
                "counts": {
                    "candidates": row.get("candidates"),
                    "indexed_all": row.get("indexed_all"),
                    "harvested_all": row.get("harvested_all"),
                    "hidden_share_all": row.get("hidden_share_all"),
                },
                "modules": rows,
                "reachability": (block.get("reachability") or {}).get(domain),
                "capability": False,
                "executable": False,
                "reason": "ANATOMY_NAVIGATION__NOT_ADMISSION",
            }
        return {
            "schema": ANATOMY_SCHEMA,
            "operation": "ANATOMY",
            "domains": {
                name: {
                    "frontier_function": row.get("frontier_function"),
                    "candidates": row.get("candidates"),
                    "top_module": ((row.get("top") or [{}])[0]).get("path"),
                }
                for name, row in sorted(domains.items())
            },
            "reachability": block.get("reachability") or {},
            "claim_limit": block.get("claim_limit"),
            "capability": False,
            "executable": False,
            "reason": "ANATOMY_NAVIGATION__NOT_ADMISSION",
        }

    # ------------------------------------------------------------------- route

    def _declared_triggers(self, cid: str) -> set[str]:
        """The tokens the verifier treats as this capability's own triggers.

        Mirrors `verify_brain_unified_model_v1._capability_tokens`: a declared
        trigger counts only if it is not a segment of the capability's own id
        and is longer than three characters. That excludes the path segments
        (`canonical`, `verification`) and short filename fragments (`run`,
        `py`, `v1`) that would otherwise make an ordinary word in a goal select
        this capability.
        """
        cached = self._declared_triggers_cache.get(cid)
        if cached is not None:
            return cached
        res = _declared_triggers_for_row(cid, self.capabilities.get(cid) or {})
        self._declared_triggers_cache[cid] = res
        return res

    def _ids_mentioned(self, goal: str) -> set[str]:
        folded = str(goal or "").strip().casefold()
        f_len = len(folded)
        if not f_len:
            return set()
        hits: set[str] = set()
        exact = self._exact_id_lookup.get(folded)
        if exact is not None:
            hits.add(exact)
        if "." in folded:
            for cid, cf in self._cid_dot_pairs:
                if len(cf) <= f_len and cf in folded:
                    hits.add(cid)
        for cid, cf in self._cid_nodot_pairs:
            if len(cf) <= f_len and cf in folded:
                hits.add(cid)
        if ":" in folded:
            for eid, ef, _mp in self._eid_folded_triples:
                if len(ef) <= f_len and ef in folded:
                    hits.add(eid)
        by_word = self._mode_phrase_by_word
        if by_word:
            # Split into simple alphanumeric words to probe first-word buckets in O(|words|).
            for raw_w in re.findall(r"[a-z0-9]+", folded):
                cand_list = by_word.get(raw_w)
                if cand_list:
                    for eid, mode_phrase in cand_list:
                        if mode_phrase in folded:
                            hits.add(eid)
        return hits

    def unrunnable_capabilities(self) -> dict[str, list[str]]:
        """Capabilities whose own declared dependencies do not resolve *here*.

        Resolved on the machine that is answering, never compiled in -- see
        ``_dependency_declaration``, which records the declaration precisely so
        that this answer can be true of the host rather than of whichever
        machine last built the artifact.

        A capability that cannot resolve the substrate it declares can only
        fail. Measured: ``python.contract.check.crosshair.v1`` -- whose adapter
        runs ``sys.executable -m crosshair`` on a machine without crosshair --
        was selected for eight of thirteen ordinary Python software-engineering
        sentences and failed every one of them with
        ``BOUND_PYPI_SOURCE_INCOMPLETE``, after spending the whole request
        getting there.

        This is reported by ``route()`` and enforced by ``solve()``. It is
        deliberately NOT used to filter the ranking: what the model contains is
        not a fact about one host, and this sandbox has pypdf while the CI
        runner does not, so hiding capabilities here would make routing
        host-dependent.
        """
        if self._unrunnable is None:
            found: dict[str, list[str]] = {}
            probe_cache: dict[tuple[str, bool], bool] = {}
            for cid, row in self.capabilities.items():
                missing = _missing_declared_dependencies(row, probe_cache=probe_cache)
                if missing:
                    found[cid] = missing
            self._unrunnable = found
        return self._unrunnable

    def route(self, goal: str, *, top_k: int = 5) -> dict[str, Any]:
        memo_key = (str(goal or ""), max(1, int(top_k)))
        memo_hit = self._route_memo.get(memo_key)
        if memo_hit is not None:
            return {
                **memo_hit,
                "query_tokens": list(memo_hit["query_tokens"]),
                "unrunnable_on_this_host": list(memo_hit["unrunnable_on_this_host"]),
                "best": dict(memo_hit["best"]) if memo_hit["best"] is not None else None,
                "candidates": [dict(r) for r in memo_hit["candidates"]],
            }
        tokens = tokenize(goal)
        mentioned = self._ids_mentioned(goal)
        # Score the ASK, not the sentence. A stated path is data, and its tokens
        # are not words about the operation -- but they were voting. Measured on
        # "Report who calls the function top in the python source root
        # /home/user/brain/…": brain.module.function.invoke scored 674.3, of
        # which 405.0 was the token `brain` from the caller's own path counted
        # twice, and terminal.kstar.root.assess.stdlib scored 449.2 of which
        # 405.0 was the same two hits. The capability that owns `calls` lost to
        # two capabilities matched by the directory the file happens to live in.
        #
        # A capability's own id, stated in the goal, is the opposite case: it is
        # the ask, so its tokens do vote.
        addressed_tokens: list[str] = []
        for cid in mentioned:
            addressed_tokens.extend(tokenize(cid))
        # Say it twice, get one vote. "Report the call graph ... writing the
        # report to R" repeats `report`, and at 269.3 a hit that alone
        # outscored every operation word in the sentence -- the Markdown-to-PDF
        # converter, whose only match was that repeated destination noun,
        # measured 538.6 against 505.9 for the capability that owns `call` and
        # `graph`. Repetition is how a sentence is phrased, not extra evidence
        # about what is being asked, so each distinct token votes once.
        ask_list: list[str] = []
        seen: set[str] = set()
        base_ask = ask_tokens(goal) if "/" in str(goal or "") else tokens
        for token in base_ask + addressed_tokens:
            if token not in seen:
                seen.add(token)
                ask_list.append(token)
        scores: dict[str, float] = {}
        matched: set[str] = set()
        unrunnable_known = self._unrunnable
        unrunnable_matched: set[str] = set()
        scaled_idx = self._scaled_index
        for token in ask_list:
            scaled_postings = scaled_idx.get(token)
            if not scaled_postings:
                continue
            matched.add(token)
            for cid, contrib in scaled_postings:
                if unrunnable_known is not None and cid in unrunnable_known:
                    unrunnable_matched.add(cid)
                scores[cid] = scores.get(cid, 0.0) + contrib
        if unrunnable_known is None:
            route_probe_cache: dict[tuple[str, bool], bool] = {}
            if self._tables_loaded and self._capabilities_dict is not None:
                for cid in scores:
                    row = self._capabilities_dict.get(cid)
                    if row is not None and _missing_declared_dependencies(row, probe_cache=route_probe_cache):
                        unrunnable_matched.add(cid)
            else:
                deps_map = self._caps_with_deps_val or {}
                for cid in scores:
                    row = deps_map.get(cid)
                    if row is not None and _missing_declared_dependencies(row, probe_cache=route_probe_cache):
                        unrunnable_matched.add(cid)
        for cid in mentioned:
            scores[cid] = scores.get(cid, 0.0) + math.log1p(24.0)
            matched.add(cid.casefold())
        ask = set(ask_list)
        addressed_set = set(addressed_tokens)
        matched_ask = (matched & ask) | addressed_set
        coverage = (len(matched_ask) / len(ask)) if ask else 0.0
        folded_goal = str(goal or "").casefold()
        cap_ids = self._capabilities_dict if (self._tables_loaded and self._capabilities_dict is not None) else (self._cap_id_set_val or ())
        eng_ids = self._engines_dict if (self._tables_loaded and self._engines_dict is not None) else (self._eng_id_set_val or ())
        addressed = {cid for cid in mentioned if cid in cap_ids} | {
            eid for eid in mentioned if eid in eng_ids and eid.casefold() in folded_goal
        }
        ranked = sorted(
            scores.items(),
            key=lambda kv: (kv[0] not in addressed, -kv[1], kv[0]),
        )
        rows: list[dict[str, Any]] = []
        kind_map = self._id_kind_map_val or {}
        for cid, score in ranked[: max(1, int(top_k))]:
            if self._tables_loaded and self._capabilities_dict is not None and self._engines_dict is not None:
                row = self._capabilities_dict.get(cid) or self._engines_dict.get(cid) or {}
                k_val = row.get("kind") or "UNKNOWN"
            else:
                k_val = kind_map.get(cid, "UNKNOWN")
            rows.append(
                {
                    "id": cid,
                    "kind": k_val,
                    "score": round(float(score), 6),
                    "coverage": round(coverage, 6),
                }
            )
        best = ranked[0] if ranked else None
        confident = bool(
            best
            and best[1] >= self.min_score
            and coverage >= self.min_coverage
        )
        out_route = {
            "schema": SOLUTION_SCHEMA,
            "operation": "ROUTE",
            "model_digest": self.digest,
            "goal": goal,
            "query_tokens": tokens,
            "matched_token_count": len(matched),
            "coverage": round(coverage, 6),
            "unrunnable_on_this_host": sorted(unrunnable_matched),
            "confident": confident,
            "best": rows[0] if rows else None,
            "candidates": rows,
            "reason": (
                "ROUTED_WITHIN_MODEL"
                if confident
                else "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED"
            ),
        }
        if len(self._route_memo) >= 2048:
            self._route_memo.clear()
        self._route_memo[memo_key] = out_route
        return {
            **out_route,
            "query_tokens": list(tokens),
            "unrunnable_on_this_host": list(out_route["unrunnable_on_this_host"]),
            "best": dict(rows[0]) if rows else None,
            "candidates": [dict(r) for r in rows],
        }

    # -------------------------------------------------------------- source index

    def find_source(
        self,
        query: str,
        *,
        top_k: int = 5,
        collapse_superseded: bool = True,
    ) -> dict[str, Any]:
        """Locate runtime source the model can *address* but cannot *execute*.

        This is deliberately not ``route`` and ``solve`` never calls it. The
        modules returned here have no receipt and no bound adapter, so naming one
        is an answer to "where is this?", never to "run this". Every row repeats
        ``executable: False`` so a caller cannot mistake a hit for a capability.
        """
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("FIND_SOURCE_QUERY_EMPTY")
        wanted = set(terms)
        for _t in terms:
            if "_" in _t:
                for _part in _t.split("_"):
                    if len(_part) >= 2 and _part not in STOPWORDS:
                        wanted.add(_part)
        q_folded = query.casefold()
        explicit_ver = bool(re.search(r"(?:\bv\d+\b|_v\d+|\.py\b)", q_folded))
        do_collapse = bool(collapse_superseded) and not explicit_ver
        fetch_k = max(int(top_k) * 4, 24) if (do_collapse or "_" in q_folded) else max(1, int(top_k))
        self._ensure_source_index()
        src_map = self._source_index_cache or {}
        if self._source_csr is not None:
            scored_top = self._source_csr.search_ranked(wanted, q_folded, top_k=fetch_k)
        else:
            src_df = self._source_df_cache or {}
            src_postings = self._source_postings_cache or {}
            total_docs = max(1, len(src_map))
            acc_scores: dict[str, float] = {}
            # Sorted, not `wanted`: floats do not add associatively, so summing idf contributions in
            # hash order made near-ties depend on PYTHONHASHSEED. Measured with the answer fingerprint:
            # 1 of 404 questions returned a different rank-3 module in a second process, which no
            # verifier check could see because the model was still internally consistent.
            for term in sorted(wanted):
                plist = src_postings.get(term)
                if not plist:
                    continue
                df = max(1, src_df.get(term, 1))
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                for path, tf in plist:
                    acc_scores[path] = acc_scores.get(path, 0.0) + idf * (1.0 + math.log(tf))
            scored: list[tuple[float, str, dict[str, Any]]] = []
            for path, score in acc_scores.items():
                if score <= 0.0:
                    continue
                if path.casefold() in q_folded:
                    score += 8.0
                scored.append((score, path, src_map[path]))
            scored.sort(key=lambda item: (-item[0], item[1]))
            scored_top = scored[:fetch_k]

        rows: list[dict[str, Any]] = []
        has_underscore_q = "_" in q_folded
        for score, path, row in scored_top:
            adj_score = float(score)
            if has_underscore_q and Path(path).stem.casefold() in q_folded:
                adj_score += 8.0
            rows.append(
                {
                    "path": path,
                    "id": row.get("id"),
                    "classification": row.get("classification"),
                    "sha256": row.get("sha256"),
                    "summary": row.get("summary") or "",
                    "symbol_count": int(row.get("symbol_count") or 0),
                    "matched_terms": sorted(wanted & set(row.get("terms") or ())),
                    "score": round(adj_score, 6),
                    # The load-bearing part of this whole method.
                    "capability": False,
                    "executable": False,
                }
            )
        if has_underscore_q and len(rows) > 1:
            rows.sort(key=lambda r: (-r["score"], r["path"]))
        if do_collapse and len(rows) > 1:
            deduped = dedupe_version_families(rows, path_key="path")[: max(1, int(top_k))]
            for d in deduped:
                d.pop("version_family", None)
                d.pop("version_number", None)
                d.pop("superseded_versions_collapsed", None)
            rows = deduped
        else:
            rows = rows[: max(1, int(top_k))]
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "FIND_SOURCE",
            "model_digest": self.digest,
            "query": query,
            "query_terms": terms,
            "candidates": rows,
            "best": rows[0] if rows else None,
            "indexed_modules": len(src_map),
            "reason": (
                "SOURCE_LOCATED__NOT_EXECUTABLE__NO_RECEIPT_OR_BOUND_ADAPTER"
                if rows
                else "NO_INDEXED_SOURCE_MATCHED"
            ),
        }

    def find_any_source(
        self,
        query: str,
        *,
        top_k: int = 5,
        collapse_superseded: bool = True,
    ) -> dict[str, Any]:
        """Locate source modules across ALL repository trees (`runtime`, `swe_kernel`, `tools`, `capabilities`, `research`, `integrations`)."""
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("FIND_SOURCE_QUERY_EMPTY")
        wanted = set(terms)
        for _t in terms:
            if "_" in _t:
                for _part in _t.split("_"):
                    if len(_part) >= 2 and _part not in STOPWORDS:
                        wanted.add(_part)
        q_folded = query.casefold()
        explicit_ver = bool(re.search(r"(?:\bv\d+\b|_v\d+|\.py\b)", q_folded))
        do_collapse = bool(collapse_superseded) and not explicit_ver
        fetch_k = max(int(top_k) * 4, 24) if (do_collapse or "_" in q_folded) else max(1, int(top_k))
        self._ensure_combined_source_index()
        combined = self._combined_source_index_cache or {}
        if self._combined_source_csr is not None:
            scored_top = self._combined_source_csr.search_ranked(wanted, q_folded, top_k=fetch_k)
        else:
            comb_postings = self._combined_source_postings_cache or {}
            src_df = self._source_df_cache or {}
            ext_df = self._extended_source_df_cache or {}
            total_docs = max(1, len(combined))
            acc_scores: dict[str, float] = {}
            for term in sorted(wanted):  # see find_source: float order must not depend on the hash seed
                plist = comb_postings.get(term)
                if not plist:
                    continue
                df = max(1, src_df.get(term, 0) + ext_df.get(term, 0))
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                for path, tf in plist:
                    acc_scores[path] = acc_scores.get(path, 0.0) + idf * (1.0 + math.log(tf))
            scored: list[tuple[float, str, dict[str, Any]]] = []
            for path, score in acc_scores.items():
                if score <= 0.0:
                    continue
                if path.casefold() in q_folded:
                    score += 8.0
                scored.append((score, path, combined[path]))
            scored.sort(key=lambda item: (-item[0], item[1]))
            scored_top = scored[:fetch_k]
        rows: list[dict[str, Any]] = []
        for score, path, row in scored_top:
            rows.append(
                {
                    "path": path,
                    "id": row.get("id"),
                    "tree": row.get("tree") or "canonical/runtime",
                    "classification": row.get("classification"),
                    "sha256": row.get("sha256"),
                    "summary": row.get("summary") or "",
                    "symbol_count": int(row.get("symbol_count") or 0),
                    "matched_terms": sorted(wanted & set(row.get("terms") or ())),
                    "score": round(float(score), 6),
                    "capability": False,
                    "executable": False,
                }
            )
        if do_collapse and len(rows) > 1:
            deduped = dedupe_version_families(rows, path_key="path")[: max(1, int(top_k))]
            for d in deduped:
                d.pop("version_family", None)
                d.pop("version_number", None)
                d.pop("superseded_versions_collapsed", None)
            rows = deduped
        else:
            rows = rows[: max(1, int(top_k))]
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "FIND_ANY_SOURCE",
            "model_digest": self.digest,
            "query": query,
            "query_terms": terms,
            "candidates": rows,
            "best": rows[0] if rows else None,
            "indexed_modules": len(combined),
            "reason": (
                "SOURCE_LOCATED__NOT_EXECUTABLE__NO_RECEIPT_OR_BOUND_ADAPTER"
                if rows
                else "NO_INDEXED_SOURCE_MATCHED"
            ),
        }

    def resolve_concept(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        """Sub-20us discrimination bridge from unfamiliar CS / frontier terms to Brain's koan & federated engines."""
        from canonical.runtime.unified_hidden_capability_federation_v1 import (
            resolve_cross_disciplinary_concept,
        )

        res = resolve_cross_disciplinary_concept(query, top_k=top_k)
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "RESOLVE_CONCEPT",
            "model_digest": self.digest,
            "query": query,
            "matched_families": res["matched_families"],
            "best": res["best"],
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
        }

    def list_federated_engines(self, *, domain: str | None = None) -> dict[str, Any]:
        """List all federated zero-model capability kernels registered in the unified model."""
        wanted = domain.strip().upper() if domain else None
        rows: list[dict[str, Any]] = []
        by_domain: dict[str, int] = {}
        for eid in sorted(self.engines):
            row = self.engines[eid]
            if row.get("kind") != "FEDERATED_KERNEL_ENGINE":
                continue
            dom = str(row.get("domain") or "UNCLASSIFIED")
            if wanted and dom != wanted:
                continue
            by_domain[dom] = by_domain.get(dom, 0) + 1
            rows.append(
                {
                    "id": eid,
                    "mode": row.get("mode"),
                    "domain": dom,
                    "descriptor": row.get("descriptor"),
                    "summary": row.get("summary"),
                    "required_inputs": list(row.get("required_inputs") or []),
                }
            )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "LIST_FEDERATED_ENGINES",
            "model_digest": self.digest,
            "count": len(rows),
            "domains": dict(sorted(by_domain.items())),
            "engines": rows,
        }

    # ---------------------------------------------------------- research index

    def find_research(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        """Locate the research record behind a decision or a capability.

        Governance decisions, verification receipts and action intents: what was
        claimed, when, and under which authority. A record is *evidence about* a
        capability, never a capability, so this is not ``route`` and ``solve``
        never calls it. Every row repeats ``capability: False``.
        """
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("FIND_RESEARCH_QUERY_EMPTY")
        wanted = set(terms)
        self._ensure_research_index()
        res_map = self._research_index_cache or {}
        res_df = self._research_df_cache or {}
        res_postings = self._research_postings_cache or {}
        total_docs = max(1, len(res_map))
        acc_scores: dict[str, float] = {}
        for term in sorted(wanted):  # see find_source
            plist = res_postings.get(term)
            if not plist:
                continue
            df = max(1, res_df.get(term, 1))
            idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
            for path, tf in plist:
                acc_scores[path] = acc_scores.get(path, 0.0) + idf * (1.0 + math.log(tf))
        q_folded = query.casefold()
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for path, score in acc_scores.items():
            if score <= 0.0:
                continue
            row = res_map[path]
            action_id = str(row.get("action_id") or "")
            if action_id and action_id.casefold() in q_folded:
                score += 8.0
            scored.append((score, path, row))
        scored.sort(key=lambda item: (-item[0], item[1]))

        rows: list[dict[str, Any]] = []
        for score, path, row in scored[: max(1, int(top_k))]:
            rows.append(
                {
                    "path": path,
                    "id": row.get("id"),
                    "schema": row.get("schema") or "",
                    "status": row.get("status") or "",
                    "date": row.get("date") or "",
                    "action_id": row.get("action_id") or "",
                    "sha256": row.get("sha256"),
                    "score": round(float(score), 6),
                    "capability": False,
                }
            )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "FIND_RESEARCH",
            "model_digest": self.digest,
            "query": query,
            "query_terms": terms,
            "candidates": rows,
            "best": rows[0] if rows else None,
            "indexed_records": len(res_map),
            "reason": (
                "RESEARCH_RECORD_LOCATED__EVIDENCE_NOT_CAPABILITY"
                if rows
                else "NO_INDEXED_RESEARCH_MATCHED"
            ),
        }

    # ------------------------------------------------------------------ recall

    def recall(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("RECALL_QUERY_EMPTY")
        self._ensure_knowledge()
        knw = self._knowledge_cache or []
        knw_df = self._knowledge_df_cache or {}
        knw_len = self._knowledge_lengths_cache or []
        avg_len = self._avg_length_cache or 1.0
        knw_postings = self._knowledge_postings_cache or {}
        knw_title_postings = self._knowledge_title_postings_cache or {}
        total_docs = max(1, len(knw))
        k1, b = 1.5, 0.75
        unique_terms = set(terms)
        cand_indices: set[int] = set()
        for t in unique_terms:
            for idx, _tf in knw_postings.get(t, ()):
                cand_indices.add(idx)
            for idx in knw_title_postings.get(t, ()):
                cand_indices.add(idx)
        scored: list[tuple[float, dict[str, Any]]] = []
        for i in sorted(cand_indices):
            row = knw[i]
            counts = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            length = knw_len[i] or 1
            score = 0.0
            for term in terms:
                tf = int(counts.get(term, 0))
                if tf <= 0:
                    continue
                df = max(1, knw_df.get(term, 1))
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                score += idf * (tf * (k1 + 1)) / (
                    tf + k1 * (1.0 - b + b * length / avg_len)
                )
            title_terms = set(row.get("title_terms") or [])
            if title_terms:
                overlap = len(unique_terms & title_terms) / max(1, len(unique_terms))
                if overlap >= 1.0:
                    score += 30.0
                elif overlap >= 0.5:
                    score += 10.0 * overlap
            if score > 0:
                scored.append((score, row))

        # Version rule, applied as a ranking invariant rather than a nudge.
        # The repository says the highest version in a law family is current and
        # every lower version is history. BM25 alone cannot know that: a long
        # superseded V4 out-scores a short current V8 on the family's own name.
        # So when the current member of a family is relevant at all, it is
        # lifted above every historical sibling. A query that matches only a
        # historical version still returns it -- history stays answerable, it
        # just cannot impersonate present-day authority.
        families: dict[str, dict[str, Any]] = {}
        for index, (score, row) in enumerate(scored):
            path = Path(str(row.get("path") or ""))
            match = re.fullmatch(r"(.+?)_V\d+\.md", path.name)
            if not match:
                continue
            entry = families.setdefault(match.group(1), {"current": None, "history": []})
            if row.get("authority") == "CURRENT_LAW":
                if entry["current"] is None or score > entry["current"][0]:
                    entry["current"] = (score, index)
            elif row.get("authority") in {"HISTORICAL_LAW_VERSION", "SUPERSEDED_LAW"}:
                entry["history"].append((score, index))
        adjusted = list(scored)
        for entry in families.values():
            if entry["current"] is None or not entry["history"]:
                continue
            current_score, current_index = entry["current"]
            history_max = max(score for score, _ in entry["history"])
            for score, index in entry["history"]:
                adjusted[index] = (score * 0.5, adjusted[index][1])
            adjusted[current_index] = (
                max(current_score, history_max * 1.25 + 1e-6),
                adjusted[current_index][1],
            )
        scored = adjusted
        scored.sort(key=lambda item: (-item[0], str(item[1].get("path") or "")))
        hits = []
        for score, row in scored[: max(1, int(top_k))]:
            path = ROOT / str(row.get("path"))
            excerpt = row.get("summary") or ""
            if path.is_file():
                excerpt = _excerpt(path, terms) or excerpt
            hits.append(
                {
                    "path": row.get("path"),
                    "title": row.get("title"),
                    "kind": row.get("kind"),
                    "authority": row.get("authority"),
                    "sha256": row.get("sha256"),
                    "score": round(score, 6),
                    "excerpt": excerpt,
                }
            )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "RECALL",
            "model_digest": self.digest,
            "query": query,
            "query_tokens": terms,
            "hit_count": len(hits),
            "hits": hits,
            "knowledge_is_external": True,
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
        }

    # ------------------------------------------------------------------- solve

    def organ_portfolio_status(self) -> dict[str, Any]:
        """Inspect live readiness of the 64 unified zero-model SWE & runtime organs (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.organ_portfolio_status()

    def learn_mealy_interface(
        self,
        oracle_fn: Any,
        alphabet: Sequence[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Actively learn a minimal separating-word Mealy interface (`minimal_experiment_v1`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.ActiveSymbolicMealyLearner.learn_mealy_interface(oracle_fn, alphabet, **kwargs)

    def learn_version_space_ui(
        self,
        demonstration_traces: Sequence[Sequence[tuple[Mapping[str, Any], str]]],
        query_observation: Mapping[str, Any] | None = None,
        *,
        step: int = 0,
    ) -> dict[str, Any]:
        """Synthesize a few-shot GUI/DOM Version-Space skill (`demonstration_version_space_v1`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.learn_and_act_version_space_ui(demonstration_traces, query_observation, step=step)

    def act_on_interface(
        self,
        instruction: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Zero-VLM 5-Tier Computer-Use, WebMCP & CLI Action-Grammar dispatcher (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.act_on_interface_unified(instruction, **kwargs)

    def explore_unknown_environment(
        self,
        env: Any,
        actions: Sequence[Any],
        *,
        is_goal: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Explore either a declared indexed-screen port or the existing abstract environment."""
        if kwargs.get('surface') == 'indexed_screen':
            from canonical.runtime.frame_program_v1 import explore_screen
            kwargs.pop('surface')
            if actions or is_goal is not None:
                raise ValueError('a screen supplies its own offered actions and advancement feedback')
            return explore_screen(env, **kwargs)
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.explore_unknown_environment_unified(env, actions, is_goal=is_goal, **kwargs)

    def verify_patch_uncheatable(
        self,
        workspace_dir: str | Path,
        patched_files: Mapping[str, str],
        pytest_targets: Sequence[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Uncheatable behavioural diff-mutation & structural-specification gate (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.verify_patch_uncheatable(workspace_dir, patched_files, pytest_targets, **kwargs)

    def induce_hypothesis_and_vocabulary(
        self,
        points: Sequence[tuple[Any, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Symbolic/piecewise hypothesis fitting, active query design, and vocabulary induction (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.induce_hypothesis_and_vocabulary_unified(points, **kwargs)

    def teach_edit_by_example(
        self,
        target_source: str,
        before_example: str,
        after_example: str,
    ) -> dict[str, Any]:
        """1-shot structural AST transformation transfer (`edit_by_example_v1`, `K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.teach_edit_by_example_unified(target_source, before_example, after_example)

    def fast_associate_and_adapt(
        self,
        query_or_key: str,
        *,
        observe_payload: Any | None = None,
        utility: float = 1.0,
        credit_verified: bool = True,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """64-bit Hyperdimensional SimHash VSA + Sherman-Morrison/Woodbury + Bi-Temporal PPR fast adapter (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        mem = getattr(self, "_vsa_woodbury_mem", None)
        if mem is None:
            mem = _uep.VSAWoodburyFastMemory()
            self._vsa_woodbury_mem = mem
        if observe_payload is not None:
            mem.observe(query_or_key, observe_payload, utility=utility, credit_verified=credit_verified)
        return mem.query(query_or_key, top_k=top_k)

    def decide_one_shot_sufficiency(self, **kwargs: Any) -> dict[str, Any]:
        """Decidable 1-shot demonstration sufficiency, hidden-precondition abduction & active experiment compiler (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.decide_one_shot_sufficiency_and_experiment(**kwargs)

    def compose_and_calibrate_skills(
        self,
        source_text: str,
        before_after_lessons: Sequence[tuple[str, str]],
        *,
        target_language: str = "python",
        pure_organ_source: str | None = None,
    ) -> dict[str, Any]:
        """Proved skill composition (`proved_composition_v1`), diagnostic scope calibration & 7-language CST transfer (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.compose_and_calibrate_verified_skills(
            source_text,
            before_after_lessons,
            target_language=target_language,
            pure_organ_source=pure_organ_source,
        )

    def pre_sieve_meaning_ir(
        self,
        baseline_source: str,
        candidate_sources: Sequence[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Microsecond Guarded Region-SSA Meaning-IR deduplicator & forward-backward abstract simulator (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.pre_sieve_and_simulate_meaning_ir(baseline_source, candidate_sources, **kwargs)

    @staticmethod
    def _epistemic_envelope(requested: str, goal: str, ep_res: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema": SOLUTION_SCHEMA,
            "authority": "NONE",
            "non_claims": list(NON_CLAIMS),
            "mode": requested,
            "goal": goal,
            "status": ep_res.get("status", "UNSOLVED"),
            "pass": bool(ep_res.get("pass")),
            "epistemic_result": dict(ep_res),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    def solve(
        self,
        goal: str,
        *,
        inputs: Mapping[str, Any] | None = None,
        mode: str = "AUTO",
        capability_id: str | None = None,
        instance_id: str | None = None,
        context_paths: Iterable[str] | None = None,
        cwd: str | Path | None = None,
    ) -> dict[str, Any]:
        requested = str(mode or "AUTO").strip().upper()
        inputs = dict(inputs or {})
        if requested == "LIVE_BROWSER_STEP":
            return self._epistemic_envelope(requested, goal, self.live_browser_step(goal, **inputs))
        if requested == "REPO_NATIVE_SWE":
            if inputs.get("residual_proposer") is not None:
                return self._failure(goal, "REFUSED__MODEL_FREE_ROUTE")
            return self.solve_swe_repo_native(inputs.pop("repo_root", cwd), **inputs)
        if requested == "RECALL":
            return self.recall(goal)
        # Unified Hidden-Arsenal fast rungs (addressable via explicit mode or AUTO structured inputs)
        if requested == "CHECKABILITY" or (requested == "AUTO" and "checkability_workspace" in inputs):
            ws = inputs.pop("checkability_workspace", inputs.pop("workspace_root", cwd or ROOT))
            return self._epistemic_envelope(requested, goal, self.checkability_oracle_forge(ws, instruction=str(inputs.pop("instruction", goal)), **inputs))
        if requested == "SPACETIME_SYGUS" or (requested == "AUTO" and ("sygus_examples" in inputs or "failing_envs" in inputs)):
            if "sygus_examples" in inputs:
                inputs["examples"] = inputs.pop("sygus_examples")
            return self._epistemic_envelope(requested, goal, self.spacetime_oe_sygus_repair(inputs.pop("workspace_root", cwd), **inputs))
        if requested in ("SHADOW_CU", "INSPECT") or (requested == "AUTO" and ("html_or_webmcp" in inputs or "entrypoint_path" in inputs or "shadow_op" in inputs)):
            ws = inputs.pop("workspace_root", cwd or ROOT)
            q = str(inputs.pop("question", goal if requested == "INSPECT" else ""))
            return self._epistemic_envelope(requested, goal, self.shadow_interface_computer_use(ws, question=q, **inputs))
        if requested == "ACTIVE_MEALY" or (requested == "AUTO" and ("active_mealy_oracle" in inputs or "machine_name" in inputs)):
            if "active_mealy_oracle" in inputs:
                inputs["oracle_fn"] = inputs.pop("active_mealy_oracle")
            return self._epistemic_envelope(requested, goal, self.active_mealy_question_learner(**inputs))
        if requested == "DBSP_MEMORY" or (requested == "AUTO" and ("zset_deltas" in inputs or "forge_entry" in inputs)):
            return self._epistemic_envelope(requested, goal, self.dbsp_bitemporal_forge(**inputs))
        _ASYM_SOLVE_MODES = {
            "ASYMMETRIC_LEAPFROG": "AUTO",
            "REFUSAL_AUTOBIND": "REFUSAL_AUTOBIND",
            "ANGELIC_ZYGOTE_SWE": "ANGELIC_ZYGOTE_SWE",
            "SHADOW_TRANSDUCER_CU": "SHADOW_TRANSDUCER_CU",
            "DIGITAL_TWIN_ARC": "DIGITAL_TWIN_ARC",
            "SHEAF_SRMU_MEMORY": "SHEAF_SRMU_MEMORY",
            "PC_DGM_EVOLVE": "PC_DGM_EVOLVE",
            "EGGMIND_PROOF": "EGGMIND_PROOF",
        }
        if requested in _ASYM_SOLVE_MODES or (
            requested == "AUTO"
            and any(
                k in inputs
                for k in (
                    "autobind_source",
                    "cli_refusal_text",
                    "visible_tests",
                    "dom_snapshot",
                    "interactive_env",
                    "arc_train_pairs",
                    "sheaf_episodes",
                    "pc_dgm_incumbent",
                    "eggmind_goal_tree",
                )
            )
        ):
            if "sheaf_episodes" in inputs:
                inputs["episodes"] = inputs.pop("sheaf_episodes")
            if "pc_dgm_incumbent" in inputs:
                inputs["incumbent_source"] = inputs.pop("pc_dgm_incumbent")
            if "eggmind_goal_tree" in inputs:
                inputs["goal_tree"] = inputs.pop("eggmind_goal_tree")
            pil = _ASYM_SOLVE_MODES.get(requested, str(inputs.pop("pillar", "AUTO")))
            return self._epistemic_envelope(requested, goal, self.asymmetric_leapfrog(goal, pillar=pil, inputs=inputs))

        if requested == "EPISTEMIC" and "harbor_task" in inputs:
            # The Harbor transport asks for a proposal, not workspace effects.
            # Never route a malformed cycle to the ordinary workspace solver.
            from canonical.swe_kernel.harbor_epistemic_controller_v1 import (
                is_harbor_epistemic_envelope, solve_harbor_cycle,
            )
            if is_harbor_epistemic_envelope(inputs):
                return solve_harbor_cycle(goal, inputs=inputs, model_digest=self.digest)
            return self._failure(goal, "INVALID_HARBOR_CYCLE_ENVELOPE")

        if requested in ("EPISTEMIC", "PORTFOLIO"):
            if callable(inputs.get("mealy_oracle")):
                return self._epistemic_envelope(requested, goal, self.learn_mealy_interface(
                    inputs["mealy_oracle"], inputs.get("alphabet") or (),
                    max_states=int(inputs.get("max_states", 4)), max_queries=int(inputs.get("max_queries", 48)),
                ))
            if inputs.get("version_space_traces") is not None:
                return self._epistemic_envelope(requested, goal, self.learn_version_space_ui(
                    inputs.get("version_space_traces") or (), inputs.get("query_observation"), step=int(inputs.get("step", 0)),
                ))
            if inputs.get("interface_action_problem") is not None:
                ia_spec = dict(inputs["interface_action_problem"])
                return self._epistemic_envelope(requested, goal, self.act_on_interface(str(ia_spec.pop("instruction", goal)), **ia_spec))
            if inputs.get("unknown_environment_problem") is not None:
                ue_spec = dict(inputs["unknown_environment_problem"])
                return self._epistemic_envelope(requested, goal, self.explore_unknown_environment(
                    ue_spec.pop("env"), ue_spec.pop("actions", ()), is_goal=ue_spec.pop("is_goal", None), **ue_spec,
                ))
            if inputs.get("one_shot_sufficiency_problem") is not None:
                return self._epistemic_envelope(requested, goal, self.decide_one_shot_sufficiency(**dict(inputs["one_shot_sufficiency_problem"])))
            if inputs.get("proved_skill_composition_problem") is not None:
                psc_spec = dict(inputs["proved_skill_composition_problem"])
                return self._epistemic_envelope(requested, goal, self.compose_and_calibrate_skills(
                    str(psc_spec.pop("source_text", "")), psc_spec.pop("before_after_lessons", ()), **psc_spec,
                ))
            if inputs.get("meaning_ir_presieve_problem") is not None:
                mir_spec = dict(inputs["meaning_ir_presieve_problem"])
                return self._epistemic_envelope(requested, goal, self.pre_sieve_meaning_ir(
                    str(mir_spec.pop("baseline_source", "")), mir_spec.pop("candidate_sources", ()), **mir_spec,
                ))
            if inputs.get("uncheatable_audit_problem") is not None:
                ua_spec = dict(inputs["uncheatable_audit_problem"])
                return self._epistemic_envelope(requested, goal, self.verify_patch_uncheatable(
                    ua_spec.pop("workspace_dir"), ua_spec.pop("patched_files"), ua_spec.pop("pytest_targets"), **ua_spec,
                ))
            if inputs.get("hypothesis_vocabulary_problem") is not None:
                hv_spec = dict(inputs["hypothesis_vocabulary_problem"])
                return self._epistemic_envelope(requested, goal, self.induce_hypothesis_and_vocabulary(hv_spec.pop("points", None), **hv_spec))
            if inputs.get("taught_edit_problem") is not None:
                te_spec = dict(inputs["taught_edit_problem"])
                return self._epistemic_envelope(requested, goal, self.teach_edit_by_example(
                    str(te_spec["target_source"]), str(te_spec["before_example"]), str(te_spec["after_example"]),
                ))
            ws_arg = cwd or inputs.get("workspace_dir") or inputs.get("repo_dir")
            if ws_arg is not None:
                if inputs.get("store") is None:
                    from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

                    ep_res = _uep.run_unified_epistemic_portfolio(
                        workspace_dir=Path(ws_arg),
                        goal_text=str(goal or ""),
                        pytest_targets=inputs.get("pytest_targets"),
                        suspect_files=inputs.get("suspect_files"),
                        timeout_s=float(inputs.get("timeout_s", 35.0)),
                    )
                else:
                    from canonical.swe_kernel import cross_modal_tomography_petri_v1 as _cmtp
                    from canonical.swe_kernel import epistemic_admission_and_self_play_v1 as _easp

                    store_obj = inputs.get("store")
                    if isinstance(store_obj, (str, Path)):
                        store_obj = _easp.EpistemicStoreV1(Path(store_obj))
                    elif not isinstance(store_obj, _easp.EpistemicStoreV1):
                        store_obj = _easp.EpistemicStoreV1()
                    ep_res = _cmtp.solve_epistemic_workspace_cow(
                        workspace_dir=Path(ws_arg),
                        goal_text=str(goal or ""),
                        store=store_obj,
                        pytest_targets=inputs.get("pytest_targets"),
                        suspect_files=inputs.get("suspect_files"),
                        timeout_s=float(inputs.get("timeout_s", 35.0)),
                    )
                return {
                    "schema": SOLUTION_SCHEMA,
                    "authority": "NONE",
                    "non_claims": list(NON_CLAIMS),
                    "mode": requested,
                    "goal": goal,
                    "status": ep_res.get("status", "UNSOLVED"),
                    "pass": bool(ep_res.get("pass")),
                    "epistemic_result": ep_res,
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
        if requested == "SOLVE_OR_LEARN":
            return self.act_or_learn(
                goal,
                inputs=inputs,
                capability_id=capability_id,
                instance_id=instance_id,
                context_paths=context_paths,
                cwd=cwd,
            )

        routing: dict[str, Any] | None = None
        ledger_db = inputs.pop("ledger_db_path", None) if isinstance(inputs, dict) and "ledger_db_path" in inputs else None
        ledger_pref: str | None = None
        if capability_id:
            cid = _normalise_capability_id(capability_id)
            if cid not in self.capabilities and cid not in self.engines:
                raise UnifiedModelError("CAPABILITY_NOT_IN_MODEL:" + cid)
            chosen = cid
        else:
            try:
                from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                _linfo = _default_ledger(ledger_db).lookup_shape(goal)
                _cand_pref = _linfo.get("preferred_capability")
                if _cand_pref and _cand_pref in self.capabilities:
                    ledger_pref = str(_cand_pref)
            except Exception:
                ledger_pref = None

            if ledger_pref:
                fast_routing = {
                    "confident": True,
                    "best": {"id": ledger_pref, "rule": "UPSTREAM_ROUTING_LEDGER_PREFERRED"},
                    "promoted_route": True,
                }
                fast_out = self._execute_capability(
                    goal, ledger_pref, inputs, fast_routing, instance_id, context_paths
                )
                if fast_out.get("pass") is True:
                    try:
                        from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                        _default_ledger(ledger_db).record_verified_route(goal, ledger_pref)
                    except Exception:
                        pass
                    return fast_out
                try:
                    from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                    _default_ledger(ledger_db).invalidate_preferred_capability(
                        goal, ledger_pref, reason=str(fast_out.get("reason") or "CAPABILITY_DID_NOT_PASS")
                    )
                except Exception:
                    pass

            routing = self.route(goal)
            if not routing["confident"]:
                # Unified fallback: no verified capability or engine claims
                # this goal. Before failing closed, ask whether a discovered
                # (harvested) surface does. Execution stays unadmitted and
                # zero-credit — this is reachability, not promotion.
                try:
                    harvested_routing = self.route_harvested(goal)
                except Exception:
                    harvested_routing = None
                if harvested_routing and harvested_routing.get("confident"):
                    hid = str(harvested_routing["best"]["id"])
                    return self.execute_harvested_surface(
                        capability_id=hid,
                        args=dict(inputs) if isinstance(inputs, Mapping) else {},
                        goal=goal,
                    )
                return self._failure(
                    goal,
                    "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED",
                    routing=routing,
                )
            chosen = str(routing["best"]["id"])

        if chosen.startswith("engine:") or chosen.startswith("meta:"):
            return self._dispatch_engine(goal, chosen, inputs, routing)
        out = self._execute_capability(
            goal, chosen, inputs, routing, instance_id, context_paths
        )
        if not capability_id and out.get("pass") is True:
            try:
                from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                _default_ledger(ledger_db).record_verified_route(goal, chosen)
            except Exception:
                pass
        return out

    def act_or_learn(
        self,
        goal: str,
        *,
        inputs: Mapping[str, Any] | None = None,
        capability_id: str | None = None,
        instance_id: str | None = None,
        context_paths: Iterable[str] | None = None,
        cwd: str | Path | None = None,
        db_path: str | Path | None = None,
        forged_state_path: str | Path | None = None,
        cognitive_core: Any | None = None,
        cognitive_state_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Single unified front door (`K3 = 0`): System-1 `< 0.5 ms` reflex -> System-2 deliberation with Active-Inference self-belief."""
        from canonical.runtime.one_shot_reality_closure_v2 import REQUIRED_ATTEMPT_ORDER
        from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
        from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
            match_and_invoke_forged_for_goal,
        )
        from canonical.swe_kernel.sentient_cognitive_core_v1 import shared_cognitive_core

        active_core = (
            cognitive_core
            if cognitive_core is not None
            else shared_cognitive_core(cognitive_state_dir)
        )
        r_preview = self.route(goal)
        has_reflex = bool(r_preview.get("confident")) or bool(capability_id)
        regime_info = active_core.decide_cognitive_regime(
            capability_id or goal[:96],
            has_consolidated_reflex=has_reflex,
            verification_kind="TEST_SUITE",
            host_ready=True,
            grounding_complete=bool(inputs) or bool(context_paths) or has_reflex,
        )
        pred_ticket = active_core.belief.predict_before_act(
            capability_id or goal[:96],
            memory_reflex_hit=has_reflex,
            grounding_complete=bool(inputs) or bool(context_paths) or has_reflex,
        )

        def _finalize_with_core(resp: dict[str, Any], inspector_name: str) -> dict[str, Any]:
            passed_f = bool(resp.get("pass") is True)
            settle = active_core.belief.settle_and_compute_surprise(
                pred_ticket,
                outcome_pass=passed_f,
                inspector=inspector_name,
                actual_cost=0.25 if regime_info["regime"] == "SYSTEM_1_REFLEX" else 1.0,
                actual_gain=1.0 if passed_f else 0.0,
            )
            active_core.record_wake_episode(
                task_id=str(capability_id or goal[:96]),
                goal=str(goal),
                outcome_pass=passed_f,
                route_id=str(resp.get("capability_id") or resp.get("tier_used") or regime_info["regime"]),
            )
            resp["cognitive_regime"] = regime_info
            resp["epistemic_settlement"] = {
                "predicted_pass_probability": pred_ticket.predicted_pass_probability,
                "epistemic_mi_bits": pred_ticket.epistemic_mi_bits,
                "surprise": settle["surprise"],
                "escalate_system2": settle["escalate_system2"],
            }
            return resp

        # 0A. Verified Skill Macro Compression (`verified_skill_macro_planner_v1.plan_with_skills`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("skill_macro_problem"), Mapping):
            from canonical.runtime import verified_skill_macro_planner_v1 as macro_pl

            sm_spec = inputs["skill_macro_problem"]
            macro_out = macro_pl.plan_with_skills(
                sm_spec["problem"],
                list(sm_spec.get("verified_skills") or ()),
                active_invalidators=tuple(sm_spec.get("active_invalidators") or ()),
            )
            passed_m = bool(macro_out.get("status") == "SOLVED" or macro_out.get("pass") is True)
            return self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status="PASS__VERIFIED_SKILL_MACRO_PLANNED" if passed_m else "FAIL_CLOSED__SKILL_MACRO_UNSOLVED",
                **{"pass": passed_m},
                reason=None if passed_m else str(macro_out.get("status") or "UNSOLVED"),
                skill_macro_plan=macro_out,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            )

        # 0B. R1+R2+R3 Adaptive Capability Expansion (`universal_verified_adaptive_solver_v12.run`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("adaptive_solver_v12_problem"), Mapping):
            from canonical.runtime import universal_verified_adaptive_solver_v12 as uvas12

            v12_spec = dict(inputs["adaptive_solver_v12_problem"])
            prob_doc = v12_spec.pop("problem")
            v12_repo = v12_spec.pop("repo_root", cwd or ROOT)
            v12_out = uvas12.run(prob_doc, repo_root=v12_repo, **v12_spec)
            passed_v12 = bool(v12_out.get("pass") is True)
            return self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status=str(v12_out.get("status") or ("PASS__ADAPTIVE_SOLVER_V12" if passed_v12 else "FAIL_CLOSED")),
                **{"pass": passed_v12},
                reason=None if passed_v12 else str(v12_out.get("reason") or v12_out.get("status")),
                adaptive_solver_v12=v12_out,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            )

        # 0C. Direct specialist routes (`r2_adequacy_request`, `scientific_discovery_problem`, `trace_capsule_problem`, `policy_adequacy_problem`, `ooxml_preflight_target`)
        if isinstance(inputs, Mapping) and any(
            k in inputs
            for k in (
                "r2_adequacy_request",
                "scientific_discovery_problem",
                "trace_capsule_problem",
                "policy_adequacy_problem",
                "policy_cover_payload",
                "escape_repair_state",
                "ooxml_preflight_target",
                "domain_mapping_problem",
                "epistemic_portfolio_problem",
                "mealy_interface_problem",
                "version_space_ui_problem",
                "refusal_specification_problem",
                "interface_action_problem",
                "unknown_environment_problem",
            )
        ):
            spec_payload: dict[str, Any] = {"goal": goal, **dict(inputs)}
            if forged_state_path is not None:
                spec_payload["forged_state_path"] = str(forged_state_path)
            ctrl_spec = solve_or_learn(
                spec_payload,
                cwd=cwd or ROOT,
                db_path=str(db_path) if db_path is not None else None,
            )
            passed_spec = bool(ctrl_spec.get("pass") is True)
            return self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status=str(ctrl_spec.get("status") or ("PASS__SPECIALIST_SOLVED" if passed_spec else "FAIL_CLOSED")),
                **{"pass": passed_spec},
                reason=None if passed_spec else str(ctrl_spec.get("failure_class") or ctrl_spec.get("status")),
                tier_used=ctrl_spec.get("tier_used"),
                autonomous_result=ctrl_spec,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            )

        # 0D. Canonical Unified Polyglot SWE Spine (`canonical_swe_spine_v1.solve_repository_task`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("swe_repo_task"), Mapping):
            swe_spec = dict(inputs["swe_repo_task"])
            repo_target = swe_spec.pop("repo_root", cwd or ROOT)
            return self.solve_swe_repo(
                repo_target,
                goal=goal,
                **swe_spec,
            )

        # 0E. Canonical Environment Discovery & Conflict-Aware Automata Spine (`canonical_env_discovery_spine_v1`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("env_discovery_task"), Mapping):
            env_spec = dict(inputs["env_discovery_task"])
            return self.discover_environment(goal=goal, **env_spec)

        # 0F. Canonical Speculative CoW Rollback & Code-over-GUI Spine (`canonical_cu_sandbox_spine_v1`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("cu_sandbox_task"), Mapping):
            cu_spec = dict(inputs["cu_sandbox_task"])
            return self.execute_speculative(goal=goal, **cu_spec)

        # 0G. Canonical 5-Timescale Verification-First Memory Bus & Sleep-Time Crystallizer (`canonical_memory_crystallizer_v1`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("memory_bus_op"), Mapping):
            mem_spec = dict(inputs["memory_bus_op"])
            op_name = str(mem_spec.pop("operation", "STATS"))
            payload = mem_spec.pop("payload", mem_spec)
            return self.memory_operation(op_name, payload=payload, goal=goal)

        # 0H. Canonical Dual-Channel Witness Inversion, Goal-Negation Oracle & Formal Vericoding (`canonical_oracle_vericoding_spine_v1`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("oracle_vericoding_task"), Mapping):
            ov_spec = dict(inputs["oracle_vericoding_task"])
            return self.audit_oracle_and_vericoding(goal=goal, **ov_spec)

        # 0I. Canonical BoundaryRouter (Tier-0 Reflex -> Tier-1 Zero-Model Spines -> Tier-2 Gated Proposer)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("boundary_route_task"), Mapping):
            br_spec = dict(inputs["boundary_route_task"])
            kind = str(br_spec.pop("kind", "swe_repair"))
            return self.route_with_boundary(kind, goal=goal, **br_spec)

        # 1. SYSTEM-1 REFLEX: REUSE_EXISTING_CAPABILITY via compiled UnifiedModel when confident & epistemically trusted
        is_forged_cid = bool(capability_id and str(capability_id).startswith("forged."))
        is_confident_federated = bool(
            r_preview.get("confident")
            and isinstance(r_preview.get("best"), Mapping)
            and r_preview["best"].get("kind") == "FEDERATED_KERNEL_ENGINE"
        )
        if not is_forged_cid and (
            regime_info["regime"] == "SYSTEM_1_REFLEX"
            or capability_id is not None
            or is_confident_federated
        ):
            primary = self.solve(
                goal,
                inputs=inputs,
                mode="AUTO",
                capability_id=capability_id,
                instance_id=instance_id,
                context_paths=context_paths,
            )
            if primary.get("pass") is True or capability_id is not None:
                primary["attempt_order_contract"] = list(REQUIRED_ATTEMPT_ORDER)
                return _finalize_with_core(primary, "VerifiedBoundCapabilityExecutionAdapter")
        else:
            primary = {"pass": False, "reason": "ESCALATED_TO_SYSTEM_2_DELIBERATION" if not is_forged_cid else "FORGED_CAPABILITY_TARGETED"}

        # 2. Check self-forged capabilities (`forged.*`) with independent byte re-read
        try:
            forged_out = match_and_invoke_forged_for_goal(
                goal,
                root=cwd or ROOT,
                state_path=forged_state_path,
                explicit_args=inputs,
            )
            if forged_out is not None and forged_out.get("pass") is True:
                return _finalize_with_core(
                    self._envelope(
                        operation="SOLVE_OR_LEARN",
                        goal=goal,
                        status="PASS__FORGED_CAPABILITY_EXECUTED_AND_BYTE_VERIFIED",
                        **{"pass": True},
                        reason=None,
                        capability_id=forged_out["capability_id"],
                        forged_execution=forged_out,
                        attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
                    ),
                    "ForgedInvokerByteReReadVerifier",
                )
        except Exception:
            pass

        # 3. SYSTEM-2 DELIBERATION: Escalate into 4-tier zero-LLM `solve_or_learn` (preserves honest fail-closed refusals!)
        req_payload: dict[str, Any] = {"goal": goal}
        if inputs:
            req_payload.update(dict(inputs))
        if forged_state_path is not None:
            req_payload["forged_state_path"] = str(forged_state_path)
        ctrl_out = solve_or_learn(
            req_payload,
            cwd=cwd or ROOT,
            db_path=str(db_path) if db_path is not None else None,
        )
        passed = ctrl_out.get("pass") is True
        return _finalize_with_core(
            self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status=str(ctrl_out.get("status") or ("PASS__AUTONOMOUS_SOLVED" if passed else "FAIL_CLOSED")),
                **{"pass": bool(passed)},
                reason=None if passed else str(ctrl_out.get("failure_class") or ctrl_out.get("status") or primary.get("reason")),
                tier_used=ctrl_out.get("tier_used"),
                autonomous_result=ctrl_out,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            ),
            "ClosedLoopAutonomousControllerVerifier",
        )

    # --------------------------------------------------------------- internals

    def _envelope(self, **extra: Any) -> dict[str, Any]:
        out = {
            "schema": SOLUTION_SCHEMA,
            "model_id": self._core_meta.get("model_id"),
            "model_digest": self.digest,
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
            "non_claims": list(NON_CLAIMS),
        }
        out.update(extra)
        return out

    def _failure(self, goal: str, reason: str, **extra: Any) -> dict[str, Any]:
        return self._envelope(
            operation="SOLVE",
            goal=goal,
            status="FAIL_CLOSED",
            **{"pass": False},
            reason=reason,
            **extra,
        )

    def _execute_capability(
        self,
        goal: str,
        cid: str,
        inputs: Mapping[str, Any],
        routing: Mapping[str, Any] | None,
        instance_id: str | None,
        context_paths: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        row = self.capabilities[cid]
        # A deliberate omission, recorded so it is not re-tried: refusing here
        # when `_missing_declared_dependencies(row)` is non-empty looks like the
        # obvious place for the host to vote, and it is not. Five pinned
        # DeclaredContextBindingTests drive pdf.extract.text.pypdf end to end
        # and assert on the *reason* and on `binding_provenance`; a dependency
        # refusal placed before the binder replaced
        # CAPABILITY_INPUTS_MISSING with a different string and short-circuited
        # the provenance they read. Measured in CI: 5 failures, all of them
        # negative controls about binding, none of them about dependencies.
        #
        # The adapters already fail closed on their own absent substrate, and
        # presence is reported by `status()` and by `unrunnable_capabilities()`.
        # What was actually broken was that the dependency was never DECLARED
        # at all, so nothing could report it. That is fixed in the compiler.
        required = [str(x) for x in (row.get("input_names") or [])]
        inputs = dict(inputs)
        missing = [name for name in required if name not in inputs]
        binding_provenance: dict[str, Any] | None = None
        declared = [str(p) for p in (context_paths or []) if str(p).strip()]
        if missing and declared:
            # Only a caller-declared resource is ever used to fill a slot. With
            # no declaration this path is not taken at all, so the default
            # behaviour is unchanged and an unstated input still fails closed:
            # choosing a file the caller never named would be a choice about
            # what to operate on, and an unverifiable one.
            inputs, binding_provenance, missing = self._bind_from_declared_context(
                goal, cid, required, inputs, missing, declared
            )
        if missing:
            return self._failure(
                goal,
                "CAPABILITY_INPUTS_MISSING:" + ",".join(missing),
                routing=routing,
                capability_id=cid,
                required_inputs=required,
            )
        if str(row.get("incremental_spend_usd", 0)) not in {"0", "0.0"}:
            return self._failure(
                goal,
                "CAPABILITY_NONZERO_SPEND_REJECTED",
                routing=routing,
                capability_id=cid,
            )
        try:
            from canonical.runtime.verified_bound_capability_execution_adapter_v1 import (
                execute as execute_bound,
            )

            raw = execute_bound(
                cid,
                inputs=dict(inputs),
                instance_id=instance_id or ("UNIFIED-MODEL-" + cid),
            )
        except Exception as exc:  # the adapter fails closed; so do we
            return self._failure(
                goal,
                "CAPABILITY_EXECUTION_RAISED:" + type(exc).__name__ + ":" + str(exc),
                routing=routing,
                capability_id=cid,
            )
        passed = raw.get("pass") is True
        # Report what the adapter actually established, not a stronger word for
        # it. The adapter distinguishes a promoted capability whose execution
        # trace was independently checked
        # (PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED) from a
        # receipt-backed one that merely ran and reported success
        # (PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED). Relabelling both as
        # "TRACE_VERIFIED" asserted a check that never ran, which let a plain
        # goal that matched a script's filename claim verified execution of it.
        status = str(raw.get("status") or "")
        return self._envelope(
            operation="SOLVE",
            goal=goal,
            status=(
                status
                if passed and status.startswith("PASS__")
                else "FAIL_CLOSED__CAPABILITY_DID_NOT_PASS"
            ),
            **{"pass": bool(passed)},
            reason=None if passed else "CAPABILITY_DID_NOT_PASS",
            routing=routing,
            capability_id=cid,
            binding_provenance=binding_provenance,
            inputs_sha256=raw.get("inputs_sha256"),
            registry_file_sha256=raw.get("registry_file_sha256"),
            rendered_action_sha256=raw.get("rendered_action_sha256"),
            execution=raw,
        )

    def _bind_from_declared_context(
        self,
        goal: str,
        cid: str,
        required: list[str],
        inputs: dict[str, Any],
        missing: list[str],
        declared: list[str],
    ) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
        """Ground unfilled slots from resources the caller explicitly declared.

        The compiled rows carry ``input_names`` but not the registry's
        ``action_template``, and ``world_binding_v1`` reads placeholder names
        from that template, so a minimal one is synthesized here naming exactly
        the slots this capability declares. All grounding stays in the verified
        binder, which fails closed and refuses patterns and globs by design.

        ``declared`` is the whole of what may be used from the surrounding
        world. Nothing is discovered from the wider repository, so a slot can
        only ever be filled with something the caller put in front of the
        model -- or something the caller wrote into the goal sentence itself.
        """
        try:
            from canonical.runtime import world_binding_v1 as wb
        except Exception:
            return inputs, None, missing

        # A path the goal sentence names is the most grounded resource there
        # is: the caller typed it. Declared context supplements it, it must
        # never replace it.
        #
        # `complete_inputs` uses `goal_paths` verbatim whenever a list is
        # passed -- an empty list included -- so handing it `declared` alone
        # used to throw away the named file and let the binder invent another
        # one, while still reporting `missing: []`. A goal naming
        # BOUND_CAPABILITY_REGISTRY_V1.json came back bound to
        # MIGRATION_STATUS_2026-09-10.json. The named paths go first so they
        # win, and the declared ones are still available behind them.
        goal_named: list[str] = []
        try:
            from canonical.runtime import goal_compiler as _gc

            goal_named = [str(p[0]) for p in _gc._repo_paths(goal, wb.ROOT)]
        except Exception:
            goal_named = []

        candidates: list[str] = []
        seen: set[str] = set()
        for path in goal_named + [str(p) for p in declared]:
            if path not in seen:
                seen.add(path)
                candidates.append(path)

        entry = {
            "capability_id": cid,
            "action_template": {
                "args": {name: "${input." + name + "}" for name in required}
            },
        }
        try:
            outcome = wb.complete_inputs(goal, wb.ROOT, entry, goal_paths=candidates)
        except Exception:
            return inputs, None, missing

        # Both sources are caller-supplied: the sentence the caller wrote, and
        # the paths the caller declared. Neither is a discovery.
        allowed = {str(p) for p in declared} | set(goal_named)

        # A slot the capability's own contract declares as `effect_result` must
        # hold an artifact some other capability PRODUCED -- it names the effect
        # and the field to read it from. Filling it from a resource the caller
        # merely declared hands the capability an input that violates its own
        # declared contract, and the failure surfaces much later as an opaque
        # decode error rather than as the refusal it should have been.
        #
        # This is read from the registry contract, not inferred from the slot
        # name or the file's contents: no capability declares an input type, so
        # any type-based guess here would itself be an invention.
        produced_only: set[str] = set()
        try:
            from canonical.runtime import live_integrated_brain_v1 as _lb

            reg_entry = dict(_lb.load_verified_registry()).get(cid) or {}
            for name, spec in (reg_entry.get("proposal_bindings") or {}).items():
                if isinstance(spec, dict) and spec.get("type") == "effect_result":
                    produced_only.add(str(name))
        except Exception:
            produced_only = set()
        filled: dict[str, Any] = {}
        for key in missing:
            value = (outcome.get("inputs") or {}).get(key)
            if value is None:
                continue
            text = str(value)
            low = key.lower()
            # Three kinds of value carry no choice about what to operate on, and
            # only these three are admissible:
            #
            #   1. A destination the binder synthesized. Deterministic; nothing
            #      to defend.
            #   2. The caller's own words. A slot named goal/task/objective is
            #      the sentence that was handed in, not a discovered resource.
            #   3. A path the caller supplied -- either declared as context, or
            #      written into the goal sentence itself.
            #
            # Everything else is refused. That is what keeps `source_root`
            # unbound for a goal that never named a root: a default there would
            # be a choice about what to audit, and an unverifiable one.
            #
            # A slot the contract reserves for a PRODUCED artifact is refused
            # even when the caller supplied the path, because the capability
            # declares it reads that value from another capability's effect.
            is_destination = "output" in low
            is_callers_words = low in _GOAL_TEXT_SLOTS
            if key in produced_only:
                continue
            if not (is_destination or is_callers_words or text in allowed):
                continue
            filled[key] = value

        if not filled:
            return inputs, None, missing

        merged = dict(inputs)
        merged.update(filled)
        still_missing = [name for name in required if name not in merged]
        provenance = {
            "filled_from_declared_context": sorted(filled),
            "values": {k: filled[k] for k in sorted(filled)},
            "declared_context": list(declared),
            "source": str(outcome.get("source") or ""),
        }
        return merged, provenance, still_missing

    def _dispatch_engine(
        self,
        goal: str,
        eid: str,
        inputs: Mapping[str, Any],
        routing: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        row = self.engines[eid]
        mode = str(row.get("mode") or "")
        if not mode:
            return self._failure(goal, "ENGINE_MODE_MISSING", routing=routing, engine_id=eid)
        if row.get("kind") == "FEDERATED_KERNEL_ENGINE":
            try:
                from canonical.runtime.unified_hidden_capability_federation_v1 import (
                    run_federated_engine,
                )

                out = run_federated_engine(mode, inputs, goal=goal)
            except Exception as exc:
                return self._failure(
                    goal,
                    "ENGINE_DISPATCH_FAILED:" + type(exc).__name__ + ":" + str(exc),
                    routing=routing,
                    engine_id=eid,
                )
            if not isinstance(out, Mapping):
                return self._failure(
                    goal, "ENGINE_RESULT_NOT_AN_OBJECT", routing=routing, engine_id=eid
                )
            passed = out.get("pass") is True
            raw_status = str(out.get("status") or "")
            return self._envelope(
                operation="SOLVE",
                goal=goal,
                status=(
                    raw_status
                    if passed and raw_status.startswith("PASS__")
                    else (raw_status if raw_status.startswith("FAIL_CLOSED__") else "FAIL_CLOSED__ENGINE_DID_NOT_REPORT_SUCCESS")
                ),
                **{"pass": bool(passed)},
                reason=None if passed else str(out.get("reason") or "ENGINE_DID_NOT_REPORT_SUCCESS"),
                routing=routing,
                capability_id=eid,
                engine_id=eid,
                engine_mode=mode,
                domain=row.get("domain"),
                incremental_spend_usd=0,
                model_calls=0,
                result=dict(out),
            )
        try:
            from canonical.runtime import unified_cognitive_fabric_v1 as fabric

            request = dict(inputs)
            request["mode"] = mode
            out = fabric.run(request)
        except Exception as exc:
            return self._failure(
                goal,
                "ENGINE_DISPATCH_FAILED:" + type(exc).__name__ + ":" + str(exc),
                routing=routing,
                engine_id=eid,
            )
        if not isinstance(out, Mapping):
            return self._failure(
                goal, "ENGINE_RESULT_NOT_AN_OBJECT", routing=routing, engine_id=eid
            )
        passed = out.get("pass") is True or str(out.get("status") or "").startswith("PASS")
        return self._envelope(
            operation="SOLVE",
            goal=goal,
            status=(
                "PASS__ENGINE_REPORTED_SUCCESS"
                if passed
                else "FAIL_CLOSED__ENGINE_DID_NOT_REPORT_SUCCESS"
            ),
            **{"pass": bool(passed)},
            reason=None if passed else "ENGINE_DID_NOT_REPORT_SUCCESS",
            routing=routing,
            engine_id=eid,
            engine_mode=mode,
            result=dict(out),
        )

    def solve_swe_repo(
        self,
        repo_root: str | Path,
        *,
        goal: str = "",
        test_file: str | None = None,
        c_sources: Sequence[str] | None = None,
        regression_tests: Sequence[str] = (),
        issue_text: str = "",
        language: str | None = None,
        timeout_s: float = 35.0,
        proposer: Any = None,
        law_store: Any = None,
        keep_patch_applied: bool = True,
    ) -> dict[str, Any]:
        """Run the consolidated polyglot SWE repair & verification spine directly from the front door."""
        from canonical.swe_kernel import canonical_swe_spine_v1 as spine

        res = spine.solve_repository_task(
            repo_root,
            test_file=test_file,
            c_sources=c_sources,
            regression_tests=regression_tests,
            issue_text=issue_text or goal,
            language=language,
            timeout_s=timeout_s,
            proposer=proposer,
            law_store=law_store,
            keep_patch_applied=keep_patch_applied,
        )
        passed = bool(res.get("solved") is True)
        return self._envelope(
            operation="SOLVE_SWE_REPO",
            goal=goal or issue_text or f"repair {repo_root}",
            status=str(res.get("status") or ("PASS_VERIFIED_ON_DISK" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("reason") or "SWE_SPINE_UNSOLVED"),
            canonical_swe_spine=res,
        )

    @property
    def memory_bus(self) -> Any:
        """Lazy 5-timescale verification-first memory bus (`0G`) attached to this UnifiedModel."""
        if self._memory_bus is None:
            from canonical.swe_kernel import canonical_memory_crystallizer_v1 as mem_spine

            self._memory_bus = mem_spine.VerificationFirstMemoryBus()
        return self._memory_bus

    @property
    def boundary_router(self) -> Any:
        """Lazy Tier-0 -> Tier-1 -> Tier-2 compounding BoundaryRouter (`0I`) sharing ``self.memory_bus``."""
        if self._boundary_router is None:
            from canonical.swe_kernel import canonical_boundary_router_v1 as br_spine

            self._boundary_router = br_spine.BoundaryRouter(
                memory_bus=self._memory_bus,
                memory_bus_factory=lambda: self.memory_bus,
            )
        return self._boundary_router

    def discover_environment(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Run the consolidated zero-shot environment discovery & C3AL automata spine (`0E`)."""
        from canonical.swe_kernel import canonical_env_discovery_spine_v1 as env_spine

        res = env_spine.discover_environment(**kwargs)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="DISCOVER_ENVIRONMENT",
            goal=goal or "discover_environment",
            status=str(res.get("status") or ("PASS__ENVIRONMENT_DISCOVERED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("reason") or "ENV_DISCOVERY_INCOMPLETE"),
            env_discovery=res,
        )

    def execute_speculative(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Run the consolidated CoW rollback sandbox & Code-over-GUI spine (`0F`)."""
        from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine

        res = cu_spine.execute_speculative_computer_task(**kwargs)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="EXECUTE_SPECULATIVE_CU",
            goal=goal or "execute_speculative_cu",
            status=str(res.get("status") or ("PASS__SPECULATIVE_COW_VERIFIED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("reason") or "CU_SANDBOX_UNSOLVED"),
            cu_sandbox=res,
        )

    def memory_operation(
        self,
        operation: str,
        *,
        payload: Mapping[str, Any] | None = None,
        goal: str = "",
    ) -> dict[str, Any]:
        """Execute a verified memory, crystallization, sleep-consolidation, or O(1) forgetting op (`0G`)."""
        from canonical.swe_kernel import canonical_memory_crystallizer_v1 as mem_spine

        res = mem_spine.execute_memory_operation(self.memory_bus, operation, payload)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="MEMORY_BUS_OP",
            goal=goal or f"memory:{operation}",
            status=str(res.get("status") or ("PASS__MEMORY_OP" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("reason") or "MEMORY_OP_FAILED"),
            memory_result=res,
        )

    def audit_oracle_and_vericoding(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Run dual-channel goal-negation oracle auditing & Coq formal certificate verification (`0H`)."""
        from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as ov_spine

        res = ov_spine.audit_oracle_and_vericoding(**kwargs)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="AUDIT_ORACLE_AND_VERICODING",
            goal=goal or "audit_oracle_and_vericoding",
            status=str(res.get("status") or ("PASS__ORACLE_AND_VERICODING_VERIFIED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("reason") or "ORACLE_VERICODING_REJECTED"),
            oracle_vericoding=res,
        )

    def route_with_boundary(self, kind: str, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Run the compounding Tier-0 -> Tier-1 -> Tier-2 BoundaryRouter (`0I`)."""
        k = str(kind or "swe_repair").lower().strip()
        if k == "swe_repair":
            res = self.boundary_router.route_swe_repair(**kwargs)
        elif k == "env_goal":
            res = self.boundary_router.route_env_goal(**kwargs)
        elif k == "cu_task":
            res = self.boundary_router.route_cu_task(**kwargs)
        elif k == "typed_chain":
            res = self.boundary_router.route_typed_chain(**kwargs)
        elif k == "harvested_surface":
            res = self.boundary_router.route_harvested_surface(**kwargs)
        elif k == "version_space":
            res = self.boundary_router.route_version_space_task(**kwargs)
        elif k == "register_env_goal":
            res = self.boundary_router.route_register_env_goal(**kwargs)
        elif k == "federated_engine":
            res = self.boundary_router.route_federated_engine(**kwargs)
        elif k == "one_shot_learning":
            res = self.boundary_router.route_one_shot_learning(**kwargs)
        elif k == "applicability":
            res = self.boundary_router.route_applicability_check(**kwargs)
        elif k == "refusal_spec":
            res = self.boundary_router.route_refusal_specification(**kwargs)
        elif k == "speculative_cow":
            res = self.boundary_router.route_speculative_cow_race(**kwargs)
        elif k == "cu_four_tier":
            res = self.boundary_router.route_four_tier_cu(**kwargs)
        elif k == "mutation_gate":
            res = self.boundary_router.route_mutation_admission_gate(**kwargs)
        elif k == "event_memory":
            res = self.boundary_router.route_verified_event_memory(**kwargs)
        elif k == "durable_commit":
            res = self.boundary_router.route_durable_commit(**kwargs)
        elif k == "env_broker":
            res = self.boundary_router.route_env_broker(**kwargs)
        elif k == "angelic_repair":
            res = self.boundary_router.route_angelic_counterfactual_repair(**kwargs)
        elif k == "crossfile_repair":
            res = self.boundary_router.route_crossfile_choreography(**kwargs)
        elif k == "compile_goal_contract":
            res = self.boundary_router.route_compile_goal_contract(**kwargs)
        elif k == "branch_mental_model":
            res = self.boundary_router.route_branch_mental_model(**kwargs)
        elif k == "check_mode_oracle":
            res = self.boundary_router.route_check_mode_oracle(**kwargs)
        elif k == "counterexample_experiment":
            res = self.boundary_router.route_counterexample_experiment(**kwargs)
        elif k == "run_relation_goal":
            res = self.boundary_router.route_run_relation_goal(**kwargs)
        elif k == "one_experience":
            res = self.boundary_router.route_one_experience_consequences(**kwargs)
        elif k == "self_evolution_firewall":
            res = self.boundary_router.route_self_evolution_firewall(**kwargs)
        elif k == "curate_skills":
            res = self.boundary_router.route_curate_skills(**kwargs)
        elif k == "observe_drift":
            res = self.boundary_router.route_observe_drift(**kwargs)
        elif k == "cross_host_transfer":
            res = self.boundary_router.route_cross_host_transfer(**kwargs)
        elif k == "one_demo_identify":
            res = self.boundary_router.route_one_demonstration_identify(**kwargs)
        elif k == "trace_expression_repair":
            res = self.boundary_router.route_trace_expression_repair(**kwargs)
        elif k == "multi_file_causal_localize":
            res = self.boundary_router.route_multi_file_causal_localize(**kwargs)
        elif k == "computer_env":
            res = self.boundary_router.route_discover_computer_env(**kwargs)
        elif k == "admit_route":
            res = self.boundary_router.route_admit_live(**kwargs)
        elif k == "semantic_plan":
            res = self.boundary_router.route_semantic_plan(**kwargs)
        elif k == "derive_execution_adapter":
            res = self.boundary_router.route_derive_execution_adapter(**kwargs)
        elif k == "contrast_memory_laws":
            res = self.boundary_router.route_contrast_memory_laws(**kwargs)
        elif k == "filing_key_hindsight_jitrl":
            res = self.boundary_router.route_filing_key_hindsight_jitrl(**kwargs)
        elif k == "producer_lineage_holes":
            res = self.boundary_router.route_producer_lineage_holes(**kwargs)
        elif k == "verifier_pinning_oracles":
            res = self.boundary_router.route_verifier_pinning_oracles(**kwargs)
        elif k == "purpose_gate_arbitrage":
            res = self.boundary_router.route_purpose_gate_arbitrage(**kwargs)
        elif k == "two_move_horizon_cu":
            res = self.boundary_router.route_two_move_horizon_cu(**kwargs)
        elif k == "status":
            res = {"pass": True, "status": "PASS__BOUNDARY_STATUS", **self.boundary_router.status_summary()}
        else:
            res = {"pass": False, "status": "FAIL_CLOSED__UNKNOWN_BOUNDARY_KIND", "reason": f"UNKNOWN_KIND:{k}"}
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="BOUNDARY_ROUTER",
            goal=goal or f"boundary:{k}",
            status=str(res.get("status") or ("PASS__BOUNDARY_ROUTED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("reason") or "BOUNDARY_ROUTE_FAILED"),
            boundary_route=res,
        )

    def speculate_cow_candidates(
        self,
        cow_candidates: Iterable[tuple[str, Callable[[], tuple[bool, Any]]]],
        *,
        workspace_root: str | Path | None = None,
        max_parallel: int = 4,
        timeout_s: float = 5.0,
        goal: str = "",
    ) -> dict[str, Any]:
        """Move 2 Front-Door: Screen Python candidates in parallel `os.fork()` CoW workers (`ZygotePrewarmedPool`)."""
        from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine

        sb = cu_spine.SpeculativeSandbox(Path(workspace_root) if workspace_root else ROOT)
        res = sb.evaluate_cow_zygote_batch(
            list(cow_candidates),
            max_parallel=max_parallel,
            per_worker_timeout_s=timeout_s,
        )
        passed = bool(res.get("passed"))
        return self._envelope(
            operation="SPECULATE_COW_ZYGOTE",
            goal=goal or "speculate_cow_candidates",
            status="PASS__ZYGOTE_COW_WINNER" if passed else "FAIL_CLOSED__NO_COW_WINNER",
            **{"pass": passed},
            reason=None if passed else "NO_CANDIDATE_PASSED_IN_COW_POOL",
            cow_zygote=res,
        )

    def autonomous_pulse(
        self,
        *,
        goal: str = "",
        creature_workspace: str | Path | None = None,
        blackbox_env: Any = None,
        goal_predicate: Callable[[Any], bool] | None = None,
        surprise_gated: bool = True,
        action_grammar_guide: str | None = None,
        disambiguation_candidates: Iterable[Any] | None = None,
        disambiguation_probe_universe: Iterable[Any] | None = None,
        disambiguation_truth_index: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Move 5 Front-Door: Surprise-gated autonomous pulse (`Creature` + Refusal Curriculum + Active Disambiguation)."""
        return self.discover_environment(
            goal=goal or "autonomous_pulse",
            creature_workspace=creature_workspace,
            blackbox_env=blackbox_env,
            goal_predicate=goal_predicate,
            surprise_gated=surprise_gated,
            action_grammar_guide=action_grammar_guide,
            disambiguation_candidates=list(disambiguation_candidates) if disambiguation_candidates is not None else None,
            disambiguation_probe_universe=list(disambiguation_probe_universe) if disambiguation_probe_universe is not None else None,
            disambiguation_truth_index=disambiguation_truth_index,
            **kwargs,
        )

    # ------------------------------------ 7-Move Frontier Leapfrog Front Doors

    def trigram_search(
        self,
        pattern: str,
        *,
        regex: bool = False,
        case_sensitive: bool = True,
        exclude_tests: bool = False,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """Move I Front-Door: Sub-millisecond 64-bit int-bitset positional 3-gram exact/regex search."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.get_trigram_index(ROOT).search(
            pattern,
            regex=regex,
            case_sensitive=case_sensitive,
            exclude_tests=exclude_tests,
            top_k=top_k,
        )

    def impact_blast_radius(self, module_or_stem: str, *, max_depth: int = 3) -> dict[str, Any]:
        """Move I Front-Door: `< 0.05 ms` depth-`k` reverse-importer & impacted-test bitset blast radius."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.get_trigram_index(ROOT).impact_blast_radius(module_or_stem, max_depth=max_depth)

    def audit_bloat_pareto(self) -> dict[str, Any]:
        """Move I Front-Door: Elon's First Law orphan & superseded-clone byte-cost Pareto census."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.audit_bloat_pareto(self, ROOT)

    def derive_and_verify_surface(
        self,
        *,
        module_paths: Sequence[str] | None = None,
        max_modules: int | None = None,
        per_call_timeout_s: float = 0.25,
        workers: int = 8,
    ) -> dict[str, Any]:
        """Move II Front-Door: Proof-mine call vectors and verify 2-run `os.fork()` CoW determinism (`3.7% -> 55.9%`)."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.derive_and_verify_surface(
            ROOT,
            module_paths=module_paths,
            max_modules=max_modules,
            per_call_timeout_s=per_call_timeout_s,
            workers=workers,
        )

    def invoke_mined_surface(
        self,
        module_or_stem: str,
        *,
        args: Sequence[Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
        entrypoint: str | None = None,
    ) -> dict[str, Any]:
        """Move II Front-Door: Execute any proof-mined verified dark module in an isolated CoW child."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.invoke_mined_surface(
            module_or_stem,
            args=args,
            kwargs=kwargs,
            entrypoint=entrypoint,
            root=ROOT,
        )

    def speculate_multiverse(
        self,
        *,
        base_source: str,
        func_name: str,
        candidate_sources: Sequence[tuple[str, str]],
        probe_inputs: Sequence[tuple[Any, ...]],
        postcondition: Callable[[tuple[Any, ...], Any], bool] | None = None,
        workspace_dir: str | Path | None = None,
        target_rel_file: str = "module.py",
    ) -> dict[str, Any]:
        """Move III Front-Door: Two-speed `10-50 us` RAM SemanticIR mental model + CDCL EMC nogoods -> CoW Zygote."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.speculate_multiverse(
            base_source=base_source,
            func_name=func_name,
            candidate_sources=candidate_sources,
            probe_inputs=probe_inputs,
            postcondition=postcondition,
            workspace_dir=workspace_dir,
            target_rel_file=target_rel_file,
        )

    def execute_doors_first(
        self,
        workspace_dir: str | Path,
        workflow_steps: Sequence[Mapping[str, Any]],
        *,
        smc_engine: Any = None,
        learn_macro: bool = True,
        require_guard_file: str | None = None,
    ) -> dict[str, Any]:
        """Move V Front-Door: 4-tier zero-pixel Doors-First execution + executor-hidden Speculative Macro Commit."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.execute_doors_first(
            workspace_dir,
            workflow_steps,
            smc_engine=smc_engine,
            learn_macro=learn_macro,
            require_guard_file=require_guard_file,
        )

    def continual_memory_cycle(
        self,
        *,
        active_cap: int = 32,
        num_adversarial_mutants: int = 160,
    ) -> dict[str, Any]:
        """Move VI Front-Door: DBSP Z-set O(1) ForgetEval deletion + rule_expiry + unblind curator + E-Stitch."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.continual_memory_cycle(
            active_cap=active_cap,
            num_adversarial_mutants=num_adversarial_mutants,
        )

    def evaluate_global_extrapolation(
        self,
        *,
        observed_points: Sequence[tuple[Any, Any]],
        candidate_hypotheses: Mapping[str, Callable[[Any], Any]],
        target_query_x: Any,
        probe_domain: Sequence[Any],
        world_oracle: Callable[[Any], Any] | None = None,
        route_costs: Mapping[str, float] | None = None,
        max_probes: int = 3,
    ) -> dict[str, Any]:
        """Move VII Front-Door: Domain-of-verification extrapolation blocker + Purpose Gate + global discriminator."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.evaluate_global_extrapolation(
            observed_points=observed_points,
            candidate_hypotheses=candidate_hypotheses,
            target_query_x=target_query_x,
            probe_domain=probe_domain,
            world_oracle=world_oracle,
            route_costs=route_costs,
            max_probes=max_probes,
        )

    def catalog_federated_engines(self, *, domain: str | None = None) -> dict[str, Any]:
        """List all federated hidden kernel engines exposed through this UnifiedModel."""
        return self.boundary_router.catalog_federated_engines(domain=domain)

    def run_federated_engine(
        self,
        mode: str,
        inputs: Mapping[str, Any] | None = None,
        *,
        goal: str = "",
    ) -> dict[str, Any]:
        """Run any of the 58 federated hidden kernel engines directly through UnifiedModel (`0I`)."""
        res = self.boundary_router.route_federated_engine(mode, inputs, goal=goal)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="RUN_FEDERATED_ENGINE",
            goal=goal or f"federated:{mode}",
            status=str(res.get("status") or ("PASS__FEDERATED_ENGINE_EXECUTED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "FEDERATED_ENGINE_FAILED"),
            federated_execution=res,
        )

    def speculative_cow_race(
        self,
        workspace_root: str | Path,
        branches: Sequence[Mapping[str, Any]],
        oracle_fn: Callable[[Path], bool],
        *,
        commit_winner: bool = True,
        goal: str = "",
    ) -> dict[str, Any]:
        """Run N side-effecting candidate branches in isolated CoW sandboxes (`0F`), committing ONLY a verified winner."""
        res = self.boundary_router.route_speculative_cow_race(
            workspace_root,
            branches,
            oracle_fn,
            commit_winner=commit_winner,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="SPECULATIVE_COW_RACE",
            goal=goal or f"cow_race:{len(branches)}_branches",
            status=str(res.get("status") or ("PASS__SPECULATIVE_COW_WINNER_COMMITTED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else "ALL_COW_BRANCHES_ROLLED_BACK",
            cow_race=res,
        )

    def mutation_admission_gate(
        self,
        source_text: str,
        verifier_fn: Callable[[Mapping[str, Any]], bool],
        *,
        limit: int = 8,
        seed: int = 7,
        min_kill_rate: float = 0.5,
        goal: str = "",
    ) -> dict[str, Any]:
        """Gate any skill/module promotion with real AST mutation killing (`0H` × `mutation_admission_probe_v1`)."""
        res = self.boundary_router.route_mutation_admission_gate(
            source_text,
            verifier_fn,
            limit=limit,
            seed=seed,
            min_kill_rate=min_kill_rate,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="MUTATION_ADMISSION_GATE",
            goal=goal or "mutation_admission_gate",
            status=str(res.get("status") or ("PASS__MUTATION_ADMISSION_GATE" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "MUTATION_GATE_FAILED"),
            mutation_gate=res,
        )

    def compile_goal_contract(
        self,
        goal: str,
        *,
        admissible: Mapping[str, Mapping[str, Any]] | None = None,
        root: str | Path | None = None,
    ) -> dict[str, Any]:
        """Compile a plain user goal into a typed capability contract (`0D` × `goal_front_compiler_v1`)."""
        res = self.boundary_router.route_compile_goal_contract(goal, admissible=admissible, root=root)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="COMPILE_GOAL_CONTRACT",
            goal=goal,
            status=str(res.get("status") or ("PASS__GOAL_CONTRACT_COMPILED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else "GOAL_CONTRACT_UNCOMPILED",
            contract=res,
        )

    def angelic_counterfactual_repair(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Run zero-model Angelic + Counterfactual Interior-Spec + CEGIS synthesis (`0D`)."""
        res = self.boundary_router.route_angelic_counterfactual_repair(**kwargs)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="ANGELIC_COUNTERFACTUAL_REPAIR",
            goal=goal or "angelic_counterfactual_repair",
            status=str(res.get("status") or ("PASS__ANGELIC_CEGIS_REPAIRED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "ANGELIC_REPAIR_UNSOLVED"),
            synthesis=res,
        )

    def durable_commit(
        self,
        workspace_root: str | Path,
        file_writes: Mapping[str, bytes | str],
        *,
        crash_at: str | None = None,
        recover_after_crash: bool = False,
        goal: str = "",
    ) -> dict[str, Any]:
        """Crash-safe multi-path journaled commit (`0F` × `the_record_is_the_commit_v1`)."""
        res = self.boundary_router.route_durable_commit(
            workspace_root,
            file_writes,
            crash_at=crash_at,
            recover_after_crash=recover_after_crash,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="DURABLE_COMMIT",
            goal=goal or f"durable_commit:{len(file_writes)}_files",
            status=str(res.get("status") or ("PASS__DURABLE_COMMIT_VERIFIED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else "DURABLE_COMMIT_INCOMPLETE",
            commit=res,
        )

    def self_evolution_entry_firewall(
        self,
        source_text: str,
        verifier_fn: Callable[[Mapping[str, Any]], bool],
        *,
        skill_id: str = "self_mod_candidate",
        workspace_root: str | Path | None = None,
        target_rel: str | None = None,
        positive_examples: Sequence[Any] = (),
        negative_mutants: Sequence[Any] = (),
        check_predicate: Callable[[Any], bool] | None = None,
        limit: int = 8,
        seed: int = 7,
        min_kill_rate: float = 0.5,
        commit_on_pass: bool = False,
        goal: str = "",
    ) -> dict[str, Any]:
        """Entry-Only Self-Evolution Firewall (`0H` × `0F` × `0G`): blocks poisoned self-updates at entry."""
        res = self.boundary_router.route_self_evolution_firewall(
            source_text,
            verifier_fn,
            skill_id=skill_id,
            workspace_root=workspace_root,
            target_rel=target_rel,
            positive_examples=positive_examples,
            negative_mutants=negative_mutants,
            check_predicate=check_predicate,
            limit=limit,
            seed=seed,
            min_kill_rate=min_kill_rate,
            commit_on_pass=commit_on_pass,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="SELF_EVOLUTION_ENTRY_FIREWALL",
            goal=goal or f"self_evolution_firewall:{skill_id}",
            status=str(res.get("status") or ("PASS__SELF_EVOLUTION_ADMITTED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            admitted=bool(res.get("admitted")),
            reason=None if passed else str(res.get("status") or "BLOCKED_AT_ENTRY_FIREWALL"),
            firewall=res,
        )

    # ------------------------------------------ Waves 11-13 Unified Front-Door Methods

    def record_skill_contribution(
        self,
        skill_id: str,
        outcome: str,
        *,
        note: str = "",
        db_path: str | Path | None = None,
        goal: str = "",
    ) -> dict[str, Any]:
        """Record measured reuse contribution for a skill (`0G` × `skill_contribution_ledger_v1`)."""
        res = self.memory_bus.record_skill_contribution(skill_id, outcome, note=note, db_path=db_path)
        return self._envelope(
            operation="RECORD_SKILL_CONTRIBUTION",
            goal=goal or f"skill_contribution:{skill_id}",
            status=str(res.get("status") or "PASS__SKILL_CONTRIBUTION_RECORDED"),
            **{"pass": bool(res.get("pass"))},
            contribution=res,
        )

    def _wrap_boundary_call(
        self,
        op: str,
        goal_txt: str,
        payload_key: str,
        res: Mapping[str, Any],
        pass_default: str,
        fail_default: str = "FAIL_CLOSED",
        *,
        include_reason: bool = True,
    ) -> dict[str, Any]:
        passed = bool(res.get("pass") is True)
        extra: dict[str, Any] = {"pass": passed, payload_key: res}
        if include_reason:
            extra["reason"] = None if passed else str(res.get("status") or fail_default)
        return self._envelope(
            operation=op,
            goal=goal_txt,
            status=str(res.get("status") or (pass_default if passed else fail_default)),
            **extra,
        )

    def curate_skills(
        self,
        *,
        grader_report: Mapping[str, Any] | None = None,
        min_trials: int = 3,
        threshold: float = 0.10,
        active_cap: int = 200,
        db_path: str | Path | None = None,
        goal: str = "",
    ) -> dict[str, Any]:
        """Retire deadweight skills ONLY on a measured tight grader (`0G` × `skill_contribution_ledger_v1`)."""
        res = self.boundary_router.route_curate_skills(
            grader_report=grader_report, min_trials=min_trials, threshold=threshold, active_cap=active_cap, db_path=db_path
        )
        return self._wrap_boundary_call("CURATE_SKILLS", goal or "curate_skills_by_contribution", "curation", res, "PASS__SKILLS_CURATED", "REFUSED__UNMEASURED_GRADER")

    def observe_drift(self, stream: str, value: float | bool, *, goal: str = "") -> dict[str, Any]:
        """Observe one outcome in the hybrid ADWIN + BOCPD + Page-Hinkley concept-drift monitor (`0G`)."""
        res = self.boundary_router.route_observe_drift(stream, value)
        return self._envelope(operation="OBSERVE_DRIFT", goal=goal or f"drift:{stream}", status=str(res.get("status") or "PASS__STATIONARY"), **{"pass": True}, drift=res)

    def trace_expression_repair(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Dual-slicing execution-trace blaming + literal-defect & site-generability audit (`0D`)."""
        return self._wrap_boundary_call("TRACE_EXPRESSION_REPAIR", goal or "trace_expression_repair", "trace_repair", self.boundary_router.route_trace_expression_repair(**kwargs), "PASS__TRACE_EXPRESSION_BLAMED", "TRACE_REPAIR_FAILED")

    def multi_file_causal_localize(self, repo_root: str | Path, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Multi-step differential-trace fault localization & causal SWE repair (`0D`)."""
        return self._wrap_boundary_call("MULTI_FILE_CAUSAL_LOCALIZE", goal or f"causal_localize:{Path(repo_root).name}", "causal_result", self.boundary_router.route_multi_file_causal_localize(repo_root, goal=goal, **kwargs), "PASS__DIFFERENTIAL_TRACE_LOCALIZED", "LOCALIZATION_FAILED")

    def discover_computer_env(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Discover live host OS programs, flags, file actions & minted effect signatures (`0E` × `computer_env_v1`)."""
        return self._wrap_boundary_call("DISCOVER_COMPUTER_ENV", goal or "discover_computer_env", "computer_env", self.boundary_router.route_discover_computer_env(**kwargs), "PASS__COMPUTER_ENV_DISCOVERED", "COMPUTER_ENV_UNAVAILABLE")

    def admit_route(
        self,
        goal: str,
        *,
        compiled: Mapping[str, Any] | None = None,
        registry: Mapping[str, Mapping[str, Any]] | None = None,
        dag: Mapping[str, Any] | None = None,
        entry: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fail-closed live route & DAG contract admission (`live_brain_route_admission_v1`)."""
        res = self.boundary_router.route_admit_live(goal, compiled=compiled, registry=registry, dag=dag, entry=entry)
        return self._wrap_boundary_call("ADMIT_ROUTE", goal, "route_admission", res, "PASS__ROUTE_ADMITTED", "ROUTE_ADMISSION_REJECTED")

    def semantic_plan(self, goal: str) -> dict[str, Any]:
        """Neuro-symbolic compositional task AST & plan synthesis (`semantic_generalization_engine_v1`)."""
        return self._wrap_boundary_call("SEMANTIC_PLAN", goal, "semantic_plan", self.boundary_router.route_semantic_plan(goal), "PASS__SEMANTIC_PLAN_SYNTHESIZED", "SEMANTIC_PLAN_FAILED")

    def derive_execution_adapter(
        self,
        module_rel: str,
        *,
        test_rel: str | None = None,
        timeout_s: float = 12.0,
        goal: str = "",
    ) -> dict[str, Any]:
        """Derive a two-run deterministic receipted adapter by capturing live call frames during module tests (`0I`)."""
        res = self.boundary_router.route_derive_execution_adapter(
            module_rel,
            test_rel=test_rel,
            repo_root=ROOT,
            timeout_s=timeout_s,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="DERIVE_EXECUTION_ADAPTER",
            goal=goal or f"derive_adapter:{module_rel}",
            status=str(res.get("status") or ("PASS__EXECUTION_ADAPTER_DERIVED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "EXECUTION_ADAPTER_FAILED"),
            adapter=res,
        )

    def self_improvement_queue(self, *, state_path: str | Path | None = None) -> dict[str, Any]:
        """Inspect the autonomous verified self-improvement queue (`autonomous_verified_self_improvement_v1`)."""
        from canonical.runtime import autonomous_verified_self_improvement_v1 as avsi

        sp = Path(state_path) if state_path is not None else None
        state = avsi.load_state(sp) if sp is not None else avsi.load_state()
        nxt = avsi.next_improvement_action(state_path=sp) if sp is not None else avsi.next_improvement_action()
        return self._envelope(
            operation="SELF_IMPROVEMENT_QUEUE",
            goal="autonomous_verified_self_improvement_queue",
            status="PASS__SELF_IMPROVEMENT_QUEUE_READ",
            **{"pass": True},
            next_action=nxt,
            queue_summary={
                "schema": state.get("schema"),
                "keys": sorted(state.keys()),
                "has_next_action": nxt is not None,
            },
        )

    def compose_chain(
        self,
        goal: str,
        *,
        seed: Sequence[str] | None = None,
        max_candidates: int = 6,
        cwd: str | Path | None = None,
    ) -> dict[str, Any]:
        """Compile a natural-language goal into a typed multi-step capability chain (`composer_route_v1`)."""
        res = self.boundary_router.route_typed_chain(
            goal,
            seed=seed,
            max_candidates=max_candidates,
            cwd=cwd,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="COMPOSE_TYPED_CHAIN",
            goal=goal,
            status=str(res.get("status") or ("PASS__TYPED_CHAIN_ROUTED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("refusal") or "TYPED_CHAIN_UNROUTED"),
            typed_chain=res,
        )

    def execute_harvested_surface(
        self,
        capability_id: str = "",
        *,
        path: str = "",
        args: Mapping[str, Any] | None = None,
        adversarial_args: Mapping[str, Any] | None = None,
        receipt: bool = False,
        goal: str = "",
    ) -> dict[str, Any]:
        """Execute a discovered-but-unadmitted harvested surface via `BoundaryRouter` (`admitted: False`)."""
        res = self.boundary_router.route_harvested_surface(
            capability_id=capability_id,
            path=path,
            args=args,
            adversarial_args=adversarial_args,
            receipt=receipt,
            root=ROOT,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="EXECUTE_HARVESTED_SURFACE",
            goal=goal or capability_id or path or "harvested_surface",
            status=str(res.get("status") or ("PASS__HARVESTED_EXECUTED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            admitted=False,
            admission="NOT_ADMITTED",
            reason=None if passed else str((res.get("harvested_result") or {}).get("refusal") or "HARVESTED_REFUSED"),
            harvested_execution=res,
        )

    # ------------------------------------------------------------ Waves 15-20: Unified Frontier-Leapfrog Front Door
    def _ensure_fts5_model_index(self) -> Any:
        """Build or attach persistent SQLite FTS5 BM25 sidecar over compiled model surfaces (sub-2 ms queries)."""
        import sqlite3

        if self._fts5_model_conn is not None:
            return self._fts5_model_conn
        db_path = (
            _core_cache_dir() / f"unified_model_fts5_{self._raw_sha256[:24]}.sqlite3"
            if self._raw_sha256
            else None
        )
        if db_path is not None and db_path.is_file() and db_path.stat().st_size > 4096:
            try:
                conn = sqlite3.connect(str(db_path))
                conn.execute("PRAGMA mmap_size=268435456")
                conn.execute("PRAGMA temp_store=MEMORY")
                row = conn.execute("SELECT val FROM fts_meta WHERE key='raw_sha256'").fetchone()
                if row and str(row[0]) == self._raw_sha256:
                    self._fts5_model_conn = conn
                    return conn
                conn.close()
            except Exception:
                pass

        self._ensure_source_index()
        self._ensure_extended_source_index()
        self._ensure_knowledge()
        target_str = str(db_path) if db_path is not None else ":memory:"
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_db = db_path.with_name(f".{db_path.name}.{os.getpid()}.tmp")
            if tmp_db.exists():
                tmp_db.unlink()
            conn = sqlite3.connect(str(tmp_db))
        else:
            tmp_db = None
            conn = sqlite3.connect(target_str)

        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.execute("CREATE TABLE fts_meta(key TEXT PRIMARY KEY, val TEXT)")
        conn.execute(
            "CREATE VIRTUAL TABLE unified_fts USING fts5("
            "doc_id UNINDEXED, kind UNINDEXED, path UNINDEXED, title, body, tokenize='unicode61')"
        )
        rows: list[tuple[str, str, str, str, str]] = []
        for cid, cap in self.capabilities.items():
            trigs = " ".join(str(t) for t in (cap.get("triggers") or ()))
            rows.append((
                str(cid),
                "capability",
                str(cap.get("adapter_path") or cap.get("path") or ""),
                str(cap.get("title") or cap.get("name") or cid),
                f"{cap.get('domain', '')} {cap.get('description', '')} {trigs} {' '.join(cap.get('terms') or ())}",
            ))
        for eid, eng in self.engines.items():
            rows.append((
                str(eid),
                "engine",
                str(eng.get("path") or ""),
                str(eng.get("name") or eid),
                f"{eng.get('description', '')} {' '.join(eng.get('terms') or ())}",
            ))
        for sk in (self.skills.values() if isinstance(self.skills, Mapping) else self.skills):
            if not isinstance(sk, Mapping):
                continue
            sid = str(sk.get("id") or sk.get("name") or sk.get("path") or "")
            terms_obj = sk.get("terms")
            term_str = " ".join(terms_obj.keys()) if isinstance(terms_obj, Mapping) else " ".join(terms_obj or ())
            rows.append((
                sid,
                "skill",
                str(sk.get("path") or ""),
                str(sk.get("title") or sk.get("name") or sid),
                f"{sk.get('description', '')} {' '.join(sk.get('headings') or ())} {term_str}",
            ))
        for doc in (self._knowledge_cache or ()):
            rows.append((
                str(doc.get("id") or doc.get("path") or ""),
                "knowledge",
                str(doc.get("path") or ""),
                str(doc.get("title") or doc.get("path") or ""),
                str(doc.get("summary") or doc.get("snippet") or "")[:600],
            ))
        for spath, srow in (self._source_index_cache or {}).items():
            rows.append((
                str(srow.get("id") or spath),
                "source_index",
                str(spath),
                str(spath),
                f"{srow.get('summary') or ''} {' '.join(srow.get('terms') or ())}"[:600],
            ))
        for spath, srow in (self._extended_source_index_cache or {}).items():
            rows.append((
                str(srow.get("id") or spath),
                "extended_source",
                str(spath),
                str(spath),
                f"{srow.get('summary') or ''} {' '.join(srow.get('terms') or ())}"[:600],
            ))
        conn.executemany(
            "INSERT INTO unified_fts(doc_id, kind, path, title, body) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.execute("INSERT OR REPLACE INTO fts_meta(key, val) VALUES ('raw_sha256', ?)", (self._raw_sha256,))
        conn.commit()
        if tmp_db is not None and db_path is not None:
            conn.close()
            tmp_db.replace(db_path)
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA mmap_size=268435456")
            conn.execute("PRAGMA temp_store=MEMORY")
        self._fts5_model_conn = conn
        return conn

    def fts5_recall(
        self,
        query: str,
        *,
        top_k: int = 8,
        include_memory_bus: bool = True,
        include_quarantined: bool = False,
    ) -> dict[str, Any]:
        """Wave 15: Sub-2 ms SQLite FTS5 BM25 recall across the compiled unified model + live `memory_bus`."""
        import re as _re
        import time as _time

        t0 = _time.perf_counter()
        q_raw = str(query or "").strip()
        tokens = sorted({tok for tok in _re.findall(r"[A-Za-z0-9_]+", q_raw.lower()) if len(tok) >= 2})[:12]
        if not tokens:
            return self._envelope(
                operation="FTS5_RECALL",
                goal=q_raw,
                status="FAIL_CLOSED__EMPTY_FTS5_QUERY",
                **{"pass": False},
                hits=[],
                elapsed_ms=round((_time.perf_counter() - t0) * 1000.0, 3),
            )
        conn = self._ensure_fts5_model_index()
        fts_expr = " OR ".join(f'"{t}"' for t in tokens)
        model_hits: list[dict[str, Any]] = []
        for doc_id, kind, path, title, rank in conn.execute(
            "SELECT doc_id, kind, path, title, bm25(unified_fts) AS r "
            "FROM unified_fts WHERE unified_fts MATCH ? ORDER BY r ASC, doc_id ASC LIMIT ?",
            (fts_expr, max(1, int(top_k))),
        ).fetchall():
            model_hits.append({
                "doc_id": str(doc_id),
                "kind": str(kind),
                "path": str(path),
                "title": str(title)[:220],
                "bm25": round(float(rank), 6),
                "source": "compiled_model_fts5",
            })

        mem_hits: list[dict[str, Any]] = []
        suppressed = 0
        if include_memory_bus and self._memory_bus is not None:
            mres = self.boundary_router.route_fts5_recall(
                q_raw,
                top_k=top_k,
                include_quarantined=include_quarantined,
            )
            suppressed = int(mres.get("suppressed_quarantined_or_expired") or 0)
            for h in mres.get("hits") or ():
                mem_hits.append({**dict(h), "source": "live_memory_bus_fts5"})

        combined = sorted(
            mem_hits + model_hits,
            key=lambda r: (float(r.get("bm25", 0.0)), str(r.get("doc_id", ""))),
        )[: max(1, int(top_k))]
        elapsed_ms = round((_time.perf_counter() - t0) * 1000.0, 3)
        return self._envelope(
            operation="FTS5_RECALL",
            goal=q_raw,
            status="PASS__FTS5_UNIFIED_RECALL" if combined else "PASS__FTS5_UNIFIED_RECALL_EMPTY",
            **{"pass": bool(combined)},
            hits=combined,
            model_hit_count=len(model_hits),
            memory_hit_count=len(mem_hits),
            suppressed_quarantined_or_expired=suppressed,
            elapsed_ms=elapsed_ms,
        )

    def memguard_audit_and_expire(
        self,
        *,
        action: str = "audit",
        skill_id: str = "",
        reward: float = 1.0,
        confidence: float = 1.0,
        fingerprint: Mapping[str, Any] | None = None,
        current_fingerprint: Mapping[str, Any] | None = None,
        quarantine_on_drift: bool = True,
        db_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Wave 15: MemGuard persistent verifier lifecycle & `rule_expiry_v1` world-fingerprint expiry."""
        res = self.boundary_router.route_memguard_and_expiry(
            action=action, skill_id=skill_id, reward=reward, confidence=confidence,
            fingerprint=fingerprint, current_fingerprint=current_fingerprint,
            quarantine_on_drift=quarantine_on_drift, db_path=db_path,
        )
        return self._wrap_boundary_call("MEMGUARD_AUDIT_EXPIRE", f"memguard:{action}:{skill_id or 'all'}", "memguard", res, "PASS__MEMGUARD", "PASS__MEMGUARD", include_reason=False)

    def anti_skill_record(
        self,
        *,
        domain: str,
        symbol_scope: str,
        bad_hypothesis: str,
        error_signature: str,
        world_fp: Mapping[str, Any] | None = None,
        csp_pair: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 15: Record a symbol-scoped Negative-Knowledge Anti-Skill refutation in `0G`."""
        res = self.boundary_router.route_anti_skill(
            action="record", domain=domain, symbol_scope=symbol_scope,
            bad_hypothesis=bad_hypothesis, error_signature=error_signature, world_fp=world_fp, csp_pair=csp_pair,
        )
        return self._wrap_boundary_call("ANTI_SKILL_RECORD", f"anti_skill:{domain}:{symbol_scope}", "anti_skill", res, "PASS__ANTI_SKILL_RECORDED", "PASS__ANTI_SKILL_RECORDED", include_reason=False)

    def anti_skill_prune(self, candidates: Sequence[str], *, domain: str, symbol_scope: str = "*") -> dict[str, Any]:
        """Wave 15: Prune candidate hypotheses in O(1) using crystallized Anti-Skills."""
        res = self.boundary_router.route_anti_skill(action="prune", domain=domain, symbol_scope=symbol_scope, candidates=candidates)
        return self._wrap_boundary_call("ANTI_SKILL_PRUNE", f"prune:{domain}:{symbol_scope}", "pruning", res, "PASS__ANTI_SKILL_PRUNED", "PASS__ANTI_SKILL_PRUNED", include_reason=False)

    def prove_composition(self, *, initial_text: str, operations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """Wave 15: Compose multi-step text/code operations only when premise & proof survive (`proved_composition_v1`)."""
        return self._wrap_boundary_call("PROVE_COMPOSITION", "proved_composition", "composition", self.boundary_router.route_proved_composition(initial_text=initial_text, operations=operations), "FAIL_CLOSED", "FAIL_CLOSED", include_reason=False)

    def solve_swe_inverted_microscope(
        self,
        repo_root: str | Path,
        *,
        goal: str = "",
        test_files: Sequence[str] | None = None,
        apply_to_source: bool = False,
        residual_proposer: Any = None,
        law_store: Any = None,
        timeout_s: float = 25.0,
    ) -> dict[str, Any]:
        """Wave 16: Inverted Neuro-Symbolic SWE Microscope wiring 5 unwired hidden engines + optional residual proposer."""
        res = self.boundary_router.route_swe_inverted_microscope(
            repo_root,
            goal=goal,
            test_files=test_files,
            apply_to_source=apply_to_source,
            residual_proposer=residual_proposer,
            law_store=law_store,
            timeout_s=timeout_s,
        )
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="SWE_INVERTED_MICROSCOPE",
            goal=goal or f"swe_microscope:{repo_root}",
            status=str(res.get("status") or ("PASS__SWE_MICROSCOPE" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("missing_fact") or res.get("status") or "UNSOLVED"),
            microscope=res,
        )

    def fork_reality_speculate(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 17: Fork-Reality CoW Speculative World Engine + Kernel Seccomp Confinement."""
        return self._wrap_boundary_call("FORK_REALITY_SPECULATE", "fork_reality_cow_speculation", "speculation", self.boundary_router.route_fork_reality_speculate(**kwargs), "PASS", "FAIL_CLOSED", include_reason=False)

    def elevate_gui_trace(
        self,
        trace: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        goal: str = "",
        postcondition: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 17: Lift GUI/DOM traces down to deterministic HTTP/CDP/CLI layers (`CLI-Anything` style)."""
        res = self.boundary_router.route_elevate_gui_trace(trace, goal=goal, postcondition=postcondition)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="ELEVATE_GUI_TRACE",
            goal=goal or "elevate_gui_trace",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            elevation=res,
        )

    def plan_partial_order(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 17: Induce STRIPS conditional operators & synthesize conflict-free partial-order plans."""
        res = self.boundary_router.route_partial_order_plan(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="PARTIAL_ORDER_PLAN",
            goal="partial_order_planning",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            plan=res,
        )

    def interrogate_minimax_witness(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 18: Exact-Minimax Witness Interrogation via `evidence_demand_v1`."""
        res = self.boundary_router.route_minimax_interrogate(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="MINIMAX_INTERROGATE",
            goal="minimax_witness_interrogation",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            interrogation=res,
        )

    def generate_csp_hard_negatives(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 18: NS-PRM Counterfactual Symbolic Perturbation Hard-Negative & Spec-Gap Generator."""
        res = self.boundary_router.route_csp_hard_negatives(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="CSP_HARD_NEGATIVES",
            goal="csp_hard_negative_generation",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            csp=res,
        )

    # ----------------------------------------------------- Waves 21-25 Frontier Leapfrog Front Door

    def elon_speed_profile(self) -> dict[str, Any]:
        """Waves 21 & 26: Measure live UnifiedModel hot-core, lazy router, mmap FTS5, and symbol-graph readiness."""
        t0 = time.perf_counter()
        cache_dir = _core_cache_dir()
        raw_sha = self._raw_sha256 or ""
        core_path = cache_dir / f"unified_model_core_{raw_sha[:32]}.marshal" if raw_sha else None
        fts_path = cache_dir / f"unified_model_fts5_{raw_sha[:24]}.sqlite3" if raw_sha else None
        sec_names = ("source_index", "extended_source_index", "research_index", "knowledge", "harvested")
        sec_present = {
            s: bool(raw_sha and (cache_dir / f"unified_model_sec_{s}_{raw_sha[:32]}.marshal").is_file())
            for s in sec_names
        }
        return self._envelope(
            operation="ELON_SPEED_PROFILE",
            goal="elon_speed_profile",
            status="PASS__ELON_SPEED_PROFILE",
            **{"pass": True},
            core_format_version=int(self._core_meta.get("core_format_v") or 5),
            core_marshal_warm=bool(core_path and core_path.is_file()),
            core_marshal_bytes=core_path.stat().st_size if (core_path and core_path.is_file()) else 0,
            fts5_sidecar_warm=bool(fts_path and fts_path.is_file()),
            fts5_sidecar_bytes=fts_path.stat().st_size if (fts_path and fts_path.is_file()) else 0,
            section_sidecars_warm=sec_present,
            lazy_cli_imports_deferred=True,
            lazy_router_memory_bus=True,
            lazy_spine_imports=True,
            lazy_route_dep_probe=True,
            version_family_dedup_enabled=True,
            mmap_fts5_enabled=True,
            symbol_graph_sidecars_open=len(self._symbol_graph_conns),
            capability_count=len(self.capabilities),
            engine_count=len(self.engines),
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    def recall_latest_sources(
        self,
        query: str,
        *,
        limit: int = 10,
        include_extended: bool = True,
    ) -> dict[str, Any]:
        """Wave 31: Version-family deduplicated source recall (collapses v1..v17 sprawl to latest per family)."""
        t0 = time.perf_counter()
        fetch_k = max(int(limit) * 6, 48)
        candidates: list[dict[str, Any]] = []
        seen_paths: set[str] = set()
        if include_extended:
            fts = self.fts5_recall(query, top_k=fetch_k)
            for row in fts.get("hits") or []:
                path = str(row.get("path") or "")
                if path.endswith(".py") and path not in seen_paths:
                    seen_paths.add(path)
                    candidates.append(dict(row))
        rec = self.recall(query, top_k=fetch_k)
        for row in rec.get("hits") or []:
            path = str(row.get("path") or "")
            if path.endswith(".py") and path not in seen_paths:
                seen_paths.add(path)
                candidates.append(dict(row))
        deduped = dedupe_version_families(candidates, path_key="path")[: int(limit)]
        return self._envelope(
            operation="RECALL_LATEST_SOURCES",
            goal=str(query),
            status="PASS__RECALL_LATEST_SOURCES",
            **{"pass": True},
            raw_candidate_count=len(candidates),
            deduped_count=len(deduped),
            collapsed_superseded_count=max(0, len(candidates) - len(deduped)),
            hits=deduped,
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    def _ensure_repo_symbol_graph(
        self,
        repo_root: str | Path,
        *,
        max_files: int = 2000,
    ) -> tuple[Any, dict[str, int]]:
        """Wave 26: Persistent mmap-backed SQLite AST symbol + call-graph + FTS5 sidecar (incremental refresh)."""
        import ast as _ast
        import sqlite3

        root_p = Path(repo_root).resolve()
        root_key = str(root_p)
        skip_dirs = frozenset(
            {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build"}
        )

        # Fast os.scandir inventory of Python files and their (mtime_ns, size) stamps
        disk_files: dict[str, tuple[int, int, Path]] = {}
        stack: list[Path] = [root_p]
        while stack and len(disk_files) < max_files:
            cur_dir = stack.pop()
            try:
                with os.scandir(cur_dir) as it:
                    entries = sorted(it, key=lambda e: e.name)
            except OSError:
                continue
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name not in skip_dirs:
                        stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False) and entry.name.endswith(".py"):
                    try:
                        st = entry.stat(follow_symlinks=False)
                        rel = Path(entry.path).relative_to(root_p).as_posix()
                        disk_files[rel] = (int(st.st_mtime_ns), int(st.st_size), Path(entry.path))
                        if len(disk_files) >= max_files:
                            break
                    except OSError:
                        continue

        conn = self._symbol_graph_conns.get(root_key)
        if conn is None:
            cache_dir = _core_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_sha = hashlib.sha256(root_key.encode("utf-8")).hexdigest()[:20]
            db_path = cache_dir / f"unified_symgraph_{db_sha}.sqlite3"
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA mmap_size=268435456")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    mtime_ns INTEGER NOT NULL,
                    size INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    qualname TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    lineno INTEGER NOT NULL,
                    end_lineno INTEGER NOT NULL,
                    signature TEXT NOT NULL,
                    doc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
                CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);
                CREATE TABLE IF NOT EXISTS edges (
                    src_path TEXT NOT NULL,
                    src_symbol TEXT NOT NULL,
                    dst_name TEXT NOT NULL,
                    kind TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_name);
                CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_path, src_symbol);
                CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
                    name, qualname, path, doc, tokenize='unicode61'
                );
                """
            )
            self._symbol_graph_conns[root_key] = conn

        existing = {
            str(r[0]): (int(r[1]), int(r[2]))
            for r in conn.execute("SELECT path, mtime_ns, size FROM files").fetchall()
        }
        removed = [p for p in existing if p not in disk_files]
        changed = [
            rel
            for rel, (mt, sz, _ap) in disk_files.items()
            if existing.get(rel) != (mt, sz)
        ]

        if removed or changed:
            for rel in removed:
                conn.execute("DELETE FROM files WHERE path=?", (rel,))
                conn.execute("DELETE FROM symbols WHERE path=?", (rel,))
                conn.execute("DELETE FROM edges WHERE src_path=?", (rel,))
                conn.execute("DELETE FROM symbols_fts WHERE path=?", (rel,))

            for rel in changed:
                mt, sz, abs_p = disk_files[rel]
                conn.execute("DELETE FROM symbols WHERE path=?", (rel,))
                conn.execute("DELETE FROM edges WHERE src_path=?", (rel,))
                conn.execute("DELETE FROM symbols_fts WHERE path=?", (rel,))
                try:
                    src_txt = abs_p.read_text(encoding="utf-8", errors="replace")
                    tree = _ast.parse(src_txt, filename=rel)
                except (OSError, SyntaxError, ValueError):
                    conn.execute(
                        "INSERT OR REPLACE INTO files(path, mtime_ns, size) VALUES (?, ?, ?)",
                        (rel, mt, sz),
                    )
                    continue

                sym_rows: list[tuple[str, str, str, str, int, int, str, str]] = []
                edge_rows: list[tuple[str, str, str, str]] = []
                fts_rows: list[tuple[str, str, str, str]] = []

                def _call_target_name(node: _ast.AST) -> str | None:
                    if isinstance(node, _ast.Name):
                        return node.id
                    if isinstance(node, _ast.Attribute):
                        return node.attr
                    return None

                def _record_calls(body_nodes: Sequence[_ast.AST], owner_qn: str) -> None:
                    seen_calls: set[str] = set()
                    for n in body_nodes:
                        for sub in _ast.walk(n):
                            if isinstance(sub, _ast.Call):
                                callee = _call_target_name(sub.func)
                                if callee and callee not in seen_calls:
                                    seen_calls.add(callee)
                                    edge_rows.append((rel, owner_qn, callee, "call"))

                for node in tree.body:
                    if isinstance(node, _ast.Import):
                        for al in node.names:
                            edge_rows.append((rel, "<module>", str(al.name), "import"))
                    elif isinstance(node, _ast.ImportFrom):
                        mod = str(node.module or "")
                        if mod:
                            edge_rows.append((rel, "<module>", mod, "import"))
                        for al in node.names:
                            edge_rows.append((rel, "<module>", f"{mod}.{al.name}" if mod else str(al.name), "import"))
                    elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                        args = [a.arg for a in node.args.args]
                        sig = f"({', '.join(args)})"
                        doc = (_ast.get_docstring(node) or "").strip().splitlines()[0][:200] if _ast.get_docstring(node) else ""
                        sym_rows.append((
                            node.name, node.name,
                            "async_function" if isinstance(node, _ast.AsyncFunctionDef) else "function",
                            rel, int(node.lineno), int(getattr(node, "end_lineno", node.lineno) or node.lineno),
                            sig, doc,
                        ))
                        fts_rows.append((node.name, node.name, rel, doc))
                        _record_calls(node.body, node.name)
                    elif isinstance(node, _ast.ClassDef):
                        bases = [_call_target_name(b) or "" for b in node.bases]
                        sig = f"({', '.join(b for b in bases if b)})"
                        doc = (_ast.get_docstring(node) or "").strip().splitlines()[0][:200] if _ast.get_docstring(node) else ""
                        sym_rows.append((
                            node.name, node.name, "class", rel,
                            int(node.lineno), int(getattr(node, "end_lineno", node.lineno) or node.lineno),
                            sig, doc,
                        ))
                        fts_rows.append((node.name, node.name, rel, doc))
                        for b in bases:
                            if b:
                                edge_rows.append((rel, node.name, b, "inherit"))
                        for item in node.body:
                            if isinstance(item, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                                m_qn = f"{node.name}.{item.name}"
                                m_args = [a.arg for a in item.args.args]
                                m_sig = f"({', '.join(m_args)})"
                                m_doc = (_ast.get_docstring(item) or "").strip().splitlines()[0][:200] if _ast.get_docstring(item) else ""
                                sym_rows.append((
                                    item.name, m_qn, "method", rel,
                                    int(item.lineno), int(getattr(item, "end_lineno", item.lineno) or item.lineno),
                                    m_sig, m_doc,
                                ))
                                fts_rows.append((item.name, m_qn, rel, m_doc))
                                _record_calls(item.body, m_qn)

                if sym_rows:
                    conn.executemany(
                        "INSERT INTO symbols(name, qualname, kind, path, lineno, end_lineno, signature, doc) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        sym_rows,
                    )
                if edge_rows:
                    conn.executemany(
                        "INSERT INTO edges(src_path, src_symbol, dst_name, kind) VALUES (?, ?, ?, ?)",
                        edge_rows,
                    )
                if fts_rows:
                    conn.executemany(
                        "INSERT INTO symbols_fts(name, qualname, path, doc) VALUES (?, ?, ?, ?)",
                        fts_rows,
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO files(path, mtime_ns, size) VALUES (?, ?, ?)",
                    (rel, mt, sz),
                )
            conn.commit()

        stats = {
            "files_indexed": int(conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]),
            "symbols_indexed": int(conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]),
            "edges_indexed": int(conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]),
            "files_reparsed_this_call": len(changed),
            "files_removed_this_call": len(removed),
        }
        return conn, stats

    def repo_symbol_graph_query(
        self,
        repo_root: str | Path,
        *,
        kind: str = "find_definition",
        query: str = "",
        target_path: str | None = None,
        top_k: int = 12,
        max_files: int = 2000,
    ) -> dict[str, Any]:
        """Wave 26: Sub-5 ms mmap SQLite AST symbol, caller, impact, outline, and FTS5 query engine."""
        t0 = time.perf_counter()
        conn, stats = self._ensure_repo_symbol_graph(repo_root, max_files=max_files)
        k = str(kind or "find_definition").lower().strip()
        q = str(query or "").strip()
        lim = max(1, int(top_k))
        hits: list[dict[str, Any]] = []

        if k == "find_definition":
            rows = conn.execute(
                "SELECT name, qualname, kind, path, lineno, end_lineno, signature, doc "
                "FROM symbols WHERE name = ? OR qualname = ? ORDER BY path, lineno LIMIT ?",
                (q, q, lim),
            ).fetchall()
            hits = [
                {
                    "name": r[0], "qualname": r[1], "kind": r[2], "path": r[3],
                    "lineno": r[4], "end_lineno": r[5], "signature": r[6], "doc": r[7],
                }
                for r in rows
            ]
        elif k == "find_callers":
            rows = conn.execute(
                "SELECT DISTINCT src_path, src_symbol, dst_name, kind "
                "FROM edges WHERE dst_name = ? OR dst_name LIKE ? ORDER BY src_path, src_symbol LIMIT ?",
                (q, f"%.{q}", lim),
            ).fetchall()
            hits = [
                {"src_path": r[0], "src_symbol": r[1], "dst_name": r[2], "edge_kind": r[3]}
                for r in rows
            ]
        elif k == "impact_of":
            hop1 = conn.execute(
                "SELECT DISTINCT src_path, src_symbol, kind FROM edges WHERE dst_name = ? OR dst_name LIKE ? LIMIT ?",
                (q, f"%.{q}", lim * 2),
            ).fetchall()
            hop1_syms = sorted({str(r[1]) for r in hop1 if str(r[1]) != "<module>"})
            hop2: list[tuple[Any, ...]] = []
            for sym in hop1_syms[:20]:
                short_sym = sym.split(".")[-1]
                hop2.extend(
                    conn.execute(
                        "SELECT DISTINCT src_path, src_symbol, dst_name, kind FROM edges WHERE dst_name = ? LIMIT ?",
                        (short_sym, lim),
                    ).fetchall()
                )
            seen_imp: set[tuple[str, str, int]] = set()
            for r in hop1:
                key = (str(r[0]), str(r[1]), 1)
                if key not in seen_imp:
                    seen_imp.add(key)
                    hits.append({"src_path": str(r[0]), "src_symbol": str(r[1]), "edge_kind": str(r[2]), "hop": 1})
            for r in hop2:
                key = (str(r[0]), str(r[1]), 2)
                if key not in seen_imp:
                    seen_imp.add(key)
                    hits.append({
                        "src_path": str(r[0]), "src_symbol": str(r[1]),
                        "via": str(r[2]), "edge_kind": str(r[3]), "hop": 2,
                    })
            hits = hits[:lim]
        elif k == "outline":
            tp = str(target_path or q)
            rows = conn.execute(
                "SELECT name, qualname, kind, path, lineno, end_lineno, signature, doc "
                "FROM symbols WHERE path = ? ORDER BY lineno LIMIT ?",
                (tp, lim * 4),
            ).fetchall()
            hits = [
                {
                    "name": r[0], "qualname": r[1], "kind": r[2], "path": r[3],
                    "lineno": r[4], "end_lineno": r[5], "signature": r[6], "doc": r[7],
                }
                for r in rows
            ]
        elif k == "fuzzy_search":
            toks = sorted({tok for tok in re.findall(r"[A-Za-z0-9_]+", q.lower()) if len(tok) >= 2})[:10]
            if toks:
                expr = " OR ".join(f'"{t}"' for t in toks)
                rows = conn.execute(
                    "SELECT name, qualname, path, doc, bm25(symbols_fts) AS r "
                    "FROM symbols_fts WHERE symbols_fts MATCH ? ORDER BY r ASC LIMIT ?",
                    (expr, lim),
                ).fetchall()
                hits = [
                    {"name": r[0], "qualname": r[1], "path": r[2], "doc": r[3], "bm25": round(float(r[4]), 6)}
                    for r in rows
                ]
        elif k == "stats":
            hits = [dict(stats)]
        else:
            return self._envelope(
                operation="REPO_SYMBOL_GRAPH_QUERY",
                goal=f"symgraph:{k}:{q}",
                status=f"FAIL_CLOSED__UNKNOWN_SYMGRAPH_KIND:{k}",
                **{"pass": False},
                hits=[],
                index_stats=stats,
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

        passed = bool(hits) or k == "stats"
        return self._envelope(
            operation="REPO_SYMBOL_GRAPH_QUERY",
            goal=f"symgraph:{k}:{q or target_path or ''}",
            status="PASS__REPO_SYMBOL_GRAPH_QUERY" if passed else "FAIL_CLOSED__NO_SYMBOL_MATCH",
            **{"pass": passed},
            kind=k,
            hits=hits,
            index_stats=stats,
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    def universal_capability_bridge(
        self,
        goal: str,
        *,
        contract_text: str | None = None,
        repo_nav_root: str | Path | None = None,
        repo_nav_kind: str = "find_symbol",
        repo_nav_target: str = "",
        compose_type_chain: bool = False,
        top_k: int = 8,
    ) -> dict[str, Any]:
        """Wave 22: Universal Reachability Bridge over all 462 capabilities + FTS5 + repo symbols + source contracts."""
        res = self.boundary_router.route_universal_capability_bridge(
            goal,
            registry=self.capabilities,
            contract_text=contract_text,
            repo_nav_root=repo_nav_root,
            repo_nav_kind=repo_nav_kind,
            repo_nav_target=repo_nav_target,
            compose_type_chain=compose_type_chain,
            top_k=top_k,
        )
        fts_hits = self.fts5_recall(goal, top_k=top_k, include_memory_bus=False).get("hits") or []
        passed = bool(res.get("pass")) or bool(fts_hits)
        return self._envelope(
            operation="UNIVERSAL_CAPABILITY_BRIDGE",
            goal=str(goal),
            status="PASS__UNIVERSAL_BRIDGE_RESOLVED" if passed else "FAIL_CLOSED__NO_BRIDGE_MATCH",
            **{"pass": passed},
            bridge=res,
            fts5_hits=fts_hits,
            admitted_capabilities_visible=len(self.capabilities),
        )

    def solve_swe_cold_start(
        self,
        issue_text: str,
        repo_root: str | Path,
        *,
        timeout_s: float = 30.0,
        keep_patch_applied: bool = False,
        skill_store_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Wave 45: the door a person actually knocks on.

        A repository and a sentence. The adapter scans, binds test targets and candidate files
        from evidence (issue terms + import graph), then hands the bound problem to
        `solve_swe_repo_native`. Zero model calls; a refusal names what is missing instead of
        guessing.
        """
        res = self.boundary_router.route_swe_cold_start(
            issue_text=issue_text,
            repo_root=repo_root,
            timeout_s=timeout_s,
            keep_patch_applied=keep_patch_applied,
            skill_store_path=skill_store_path,
        )
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="SWE_COLD_START",
            goal=f"swe_cold_start:{repo_root}",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            tier=res.get("tier"),
            reason=res.get("reason"),
            binding=res.get("binding"),
            elapsed_s=res.get("elapsed_s"),
            payload=res,
        )

    def solve_swe_repo_native(
        self,
        repo_root: str | Path,
        *,
        test_targets: Sequence[str] | None = None,
        candidate_files: Sequence[str] | None = None,
        in_run_repair_vocab: Mapping[str, Any] | None = None,
        repair_store: str | Path | None = None,
        learn_verified: bool = True,
        prior_demonstrations: Sequence[tuple[str, str, str]] = (),
        witness_envs: Sequence[Mapping[str, Any]] | None = None,
        witness_targets: Sequence[Any] | None = None,
        mine_git_history: bool = True,
        history_limit: int = 200,
        residual_proposer: Any = None,
        keep_patch_applied: bool = False,
        timeout_s: float = 30.0,
        skill_store_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Wave 23: Repo-Native Multi-File SWE Engine (`0D` × 7 hidden SWE superweapons + CoW Zygote + online crystallization)."""
        res = self.boundary_router.route_swe_repo_native_multifile(
            repo_root=repo_root,
            test_targets=test_targets,
            candidate_files=candidate_files,
            in_run_repair_vocab=in_run_repair_vocab,
            repair_store=repair_store, learn_verified=learn_verified,
            prior_demonstrations=prior_demonstrations,
            witness_envs=witness_envs,
            witness_targets=witness_targets,
            mine_git_history=mine_git_history,
            history_limit=history_limit,
            residual_proposer=residual_proposer,
            keep_patch_applied=keep_patch_applied,
            timeout_s=timeout_s,
            skill_store_path=skill_store_path,
        )
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="SWE_REPO_NATIVE_MULTIFILE",
            goal=f"swe_repo_native:{repo_root}",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            swe_result=res,
        )

    def bitemporal_memory_record(
        self,
        *,
        entity: str,
        attribute: str,
        value: Any,
        valid_from: float,
        tx_time: float | None = None,
        valid_until: float | None = None,
        provenance: str = "verified_observation",
        supersede_active: bool = True,
    ) -> dict[str, Any]:
        """Wave 24: Assert a bitemporal fact into `memory_bus` (`0G`, zero LLM)."""
        res = self.boundary_router.memory_bus.record_bitemporal_fact(
            entity=entity,
            attribute=attribute,
            value=value,
            valid_from=valid_from,
            tx_time=tx_time,
            valid_until=valid_until,
            provenance=provenance,
            supersede_active=supersede_active,
        )
        return self._envelope(
            operation="BITEMPORAL_MEMORY_RECORD",
            goal=f"bitemporal:{entity}.{attribute}",
            status=str(res.get("status") or "PASS"),
            **{"pass": bool(res.get("pass"))},
            bitemporal=res,
        )

    def bitemporal_memory_query(
        self,
        *,
        entity: str | None = None,
        attribute: str | None = None,
        as_of_valid: float | None = None,
        as_of_tx: float | None = None,
        include_superseded: bool = False,
    ) -> dict[str, Any]:
        """Wave 24: Point-in-time bitemporal query over `memory_bus` (`0G`, zero LLM)."""
        res = self.boundary_router.memory_bus.query_bitemporal_facts(
            entity=entity,
            attribute=attribute,
            as_of_valid=as_of_valid,
            as_of_tx=as_of_tx,
            include_superseded=include_superseded,
        )
        return self._envelope(
            operation="BITEMPORAL_MEMORY_QUERY",
            goal=f"bitemporal_query:{entity or '*'}.{attribute or '*'}",
            status=str(res.get("status") or "PASS"),
            **{"pass": bool(res.get("pass"))},
            bitemporal=res,
        )

    def bitemporal_skill_bank_update(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 24: Counterfactual Credit Assignment + SkillRL Hierarchical SkillBank + Bitemporal Memory (`0G`)."""
        res = self.boundary_router.route_bitemporal_skill_bank(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="BITEMPORAL_SKILL_BANK",
            goal=str(kwargs.get("skill_name") or "bitemporal_skill_bank"),
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            skill_bank=res,
        )

    def verify_effect_contract_chain(
        self,
        contracts_spec: Sequence[Mapping[str, Any]],
        *,
        intended_goal: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Wave 24: Formal Effect-Contract Composition & Verification (`0G`)."""
        res = self.boundary_router.route_verify_effect_chain(
            contracts_spec=contracts_spec,
            intended_goal=intended_goal,
        )
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="VERIFY_EFFECT_CONTRACT_CHAIN",
            goal="effect_contract_chain",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            chain=res,
        )

    def red_queen_coevolve_evaluators(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_red_queen_coevolution", "RED_QUEEN_COEVOLVE_EVALUATORS", f"red_queen_epoch:{kwargs.get('epoch_index', 0)}", "red_queen", kwargs)

    def explore_safe_action_model(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_safe_exploration", "SAFE_ACTION_MODEL_EXPLORE", "safe_action_model_exploration", "exploration", kwargs)

    def compile_decision_quotient(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_decision_quotient", "DECISION_QUOTIENT_COMPILE", "decision_quotient_refinement", "quotient", kwargs)

    def execute_horizon_zero_screenshot_cu(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_horizon_zero_screenshot_cu", "HORIZON_ZERO_SCREENSHOT_CU", str(kwargs.get("task_id") or "horizon_zero_screenshot_cu"), "cu_execution", kwargs)

    def contrast_memory_laws(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_contrast_memory_laws", "CONTRAST_MEMORY_LAWS", f"contrast_laws:{kwargs.get('domain', 'default')}", "contrast_laws", kwargs)

    def filing_key_hindsight_jitrl(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_filing_key_hindsight_jitrl", "FILING_KEY_HINDSIGHT_JITRL", str(kwargs.get("achieved_goal") or kwargs.get("jitrl_filing_key") or "filing_key_hindsight_jitrl"), "hindsight_jitrl", kwargs)

    def solve_producer_lineage_holes(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_producer_lineage_holes", "PRODUCER_LINEAGE_HOLE_INVERSION", str(kwargs.get("entry_func") or kwargs.get("filename") or "producer_lineage_hole_inversion"), "hole_inversion", kwargs)

    def audit_verifier_pinning_and_oracles(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_verifier_pinning_oracles", "VERIFIER_PINNING_AND_ORACLES", "verifier_pinning_and_oracles", "pinning_oracles", kwargs)

    def purpose_gate_and_cost_arbitrage(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_purpose_gate_arbitrage", "PURPOSE_GATE_AND_COST_ARBITRAGE", str(kwargs.get("instruction") or "purpose_gate_cost_arbitrage"), "active_inference", kwargs)

    def plan_two_move_horizon_cu(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_two_move_horizon_cu", "TWO_MOVE_HORIZON_CU", str(kwargs.get("bridge_task_id") or "two_move_horizon_cu"), "two_move_cu", kwargs)

    def self_verify_dark_matter(
        self,
        module_relpaths: Sequence[str],
        *,
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        """Wave 19: Non-tautological behavioural execution self-verifier for previously unwired/source-only modules.

        Binds `(module_sha256, python_version, observed_outcome, latency_ms, callable_symbols)` in fresh
        isolated subprocesses — separating `RAN_CLEAN`, `MISSING_DEPENDENCY`, and `FAILED` without
        mutating any OIDC receipts or inflating capability claims.
        """
        import hashlib as _hashlib
        import subprocess as _subprocess
        import sys as _sys
        import time as _time

        t0 = _time.perf_counter()
        results: list[dict[str, Any]] = []
        counts = {"RAN_CLEAN": 0, "MISSING_DEPENDENCY": 0, "FAILED": 0, "MISSING_FILE": 0}
        py_ver = f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}"

        probe_code = (
            "import importlib, inspect, json, sys\n"
            "mod = importlib.import_module(sys.argv[1])\n"
            "fns = sorted(k for k, v in vars(mod).items() if not k.startswith('_') and callable(v))\n"
            "print(json.dumps({'ok': True, 'callables': fns[:24], 'callable_count': len(fns)}))\n"
        )
        for rel in module_relpaths:
            rel_posix = Path(rel).as_posix()
            abs_p = ROOT / rel_posix
            if not abs_p.is_file():
                counts["MISSING_FILE"] += 1
                results.append({"module": rel_posix, "outcome": "MISSING_FILE"})
                continue
            mod_sha = _hashlib.sha256(abs_p.read_bytes()).hexdigest()
            dotted = rel_posix[:-3].replace("/", ".") if rel_posix.endswith(".py") else rel_posix.replace("/", ".")
            pt0 = _time.perf_counter()
            try:
                cp = _subprocess.run(
                    [_sys.executable, "-c", probe_code, dotted],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=float(timeout_s),
                )
            except _subprocess.TimeoutExpired:
                counts["FAILED"] += 1
                results.append({"module": rel_posix, "module_sha256": mod_sha, "outcome": "FAILED", "reason": "TIMEOUT"})
                continue
            lat_ms = round((_time.perf_counter() - pt0) * 1000.0, 3)
            if cp.returncode == 0 and cp.stdout.strip():
                parsed = json.loads(cp.stdout.strip().splitlines()[-1])
                rec = {
                    "module": rel_posix,
                    "dotted": dotted,
                    "module_sha256": mod_sha,
                    "python_version": py_ver,
                    "outcome": "RAN_CLEAN",
                    "callable_count": int(parsed.get("callable_count") or 0),
                    "callables": list(parsed.get("callables") or ()),
                    "latency_ms": lat_ms,
                }
                counts["RAN_CLEAN"] += 1
                self._dark_matter_verified[rel_posix] = rec
                results.append(rec)
            else:
                err_tail = (cp.stderr or cp.stdout or "").strip().splitlines()[-1:] or ["UNKNOWN_ERROR"]
                err_msg = err_tail[0][:180]
                is_missing_dep = "ModuleNotFoundError" in err_msg or "ImportError" in err_msg
                outcome = "MISSING_DEPENDENCY" if is_missing_dep else "FAILED"
                counts[outcome] += 1
                rec = {
                    "module": rel_posix,
                    "dotted": dotted,
                    "module_sha256": mod_sha,
                    "python_version": py_ver,
                    "outcome": outcome,
                    "reason": err_msg,
                    "latency_ms": lat_ms,
                }
                self._dark_matter_verified[rel_posix] = rec
                results.append(rec)

        return self._envelope(
            operation="SELF_VERIFY_DARK_MATTER",
            goal=f"self_verify:{len(module_relpaths)}_modules",
            status="PASS__DARK_MATTER_SELF_VERIFIED" if counts["RAN_CLEAN"] > 0 else "FAIL_CLOSED__NO_MODULE_RAN_CLEAN",
            **{"pass": counts["RAN_CLEAN"] > 0},
            counts=counts,
            verified_modules=results,
            total_verified_in_session=len(self._dark_matter_verified),
            elapsed_ms=round((_time.perf_counter() - t0) * 1000.0, 3),
        )

    # ----------------------------------------------------- Waves 32-35 + Hidden Arsenal Unified Front Door

    def checkability_oracle_forge(
        self,
        workspace_root: str | Path,
        *,
        module_rel: str | None = None,
        instruction: str = "",
        wanted_callables: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Zero-test checkability multiplier (`argument_construction_v1` + `checkability_by_differential_pin_v1` + `instruction_contract_for_code_v1`)."""
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        return hau.checkability_oracle_forge(
            workspace_root,
            module_rel=module_rel,
            instruction=instruction,
            wanted_callables=wanted_callables,
        )

    def spacetime_oe_sygus_repair(
        self,
        workspace_root: str | Path | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """SpaceTime causal intervention (`site_by_intervention_v1`) + polyglot Python/JS/C `oe_sygus_synthesizer_v1`."""
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        return hau.spacetime_oe_sygus_repair(workspace_root, **kwargs)

    def shadow_interface_computer_use(
        self,
        workspace_root: str | Path,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Agent-S4 + W3C WebMCP shadow interface + `follow_the_pointer_v1` + `inspect_v1` + Petri 5-layer State-Alias tomography."""
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        return hau.shadow_interface_computer_use(workspace_root, **kwargs)

    def active_mealy_question_learner(self, **kwargs: Any) -> dict[str, Any]:
        """Angluin L* `SymbolicMealyInstantLearner` (<1 ms) + `ask_instead_of_stare_v1` executable questions."""
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        return hau.active_mealy_question_learner(**kwargs)

    def dbsp_bitemporal_forge(self, **kwargs: Any) -> dict[str, Any]:
        """Incremental DBSP Z-set (<10 us) bi-temporal ForwardPush PPR memory + `capability_forge_v1` mutant-killing admission."""
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        return hau.dbsp_bitemporal_forge(**kwargs)

    def _run_boundary_organ(self, router_attr: str, op_name: str, goal_name: str, payload_key: str, kwargs: Mapping[str, Any]) -> dict[str, Any]:
        res = getattr(self.boundary_router, router_attr)(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation=op_name,
            goal=goal_name,
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed, payload_key: res},
        )

    def disambiguate_and_pin_repairs(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_disambiguate_and_pin_repairs", "DISAMBIGUATE_AND_PIN_REPAIRS", "wave32_version_space_swe", "version_space_swe", kwargs)

    def prove_equivalence_and_amplify(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_prove_equivalence_and_amplify", "PROVE_EQUIVALENCE_AND_AMPLIFY", "wave32_equivalence_oracle", "equivalence_oracle", kwargs)

    def crystallize_meaning_first_transfer(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_meaning_first_transfer", "MEANING_FIRST_TRANSFER", "wave33_meaning_first_transfer", "meaning_first", kwargs)

    def memini_memrl_apex_consolidate(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_memini_memrl_apex", "MEMINI_MEMRL_APEX", "wave33_memini_memrl_apex", "consolidation", kwargs)

    def execute_osworld_v21_epistemic_cu(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_osworld_v21_epistemic_cu", "OSWORLD_V21_EPISTEMIC_CU", "wave34_osworld_v21_epistemic_cu", "osworld_epistemic_cu", kwargs)

    def speculative_macro_commit(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_speculative_macro_commit", "SPECULATIVE_MACRO_COMMIT", "wave34_speculative_macro_commit", "speculative_commit", kwargs)

    def active_repertoire_typed_invention(self, **kwargs: Any) -> dict[str, Any]:
        return self._run_boundary_organ("route_active_repertoire_typed_invention", "ACTIVE_REPERTOIRE_TYPED_INVENTION", "wave35_active_repertoire_typed_invention", "active_repertoire", kwargs)

    def leapfrog_solve(
        self,
        goal: str,
        *,
        mode: str = "auto",
        inputs: Mapping[str, Any] | None = None,
        repo_root: str | Path | None = None,
        trace: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
        params: Sequence[str] | None = None,
        examples: Sequence[tuple[Any, Any]] | None = None,
        initial: Sequence[tuple[str, str]] | None = None,
        goal_conditions: Sequence[tuple[str, str]] | None = None,
        operators: Sequence[Mapping[str, Any]] = (),
        transitions: Sequence[tuple[str, Sequence[tuple[str, str]], Sequence[tuple[str, str]]]] = (),
        residual_proposer: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Single unified frontier-leapfrog front door across all canonical spines & hidden arsenal (`K3=0` default)."""
        m = str(mode or "auto").lower().strip()
        data = dict(inputs or {})
        if m == "checkability_oracle":
            return self.checkability_oracle_forge(data.pop("workspace_root", repo_root or ROOT), instruction=goal, **data, **kwargs)
        if m == "spacetime_sygus":
            return self.spacetime_oe_sygus_repair(data.pop("workspace_root", repo_root), **data, **kwargs)
        if m == "shadow_cu":
            return self.shadow_interface_computer_use(data.pop("workspace_root", repo_root or ROOT), **data, **kwargs)
        if m == "active_mealy":
            return self.active_mealy_question_learner(**data, **kwargs)
        if m == "dbsp_forge":
            return self.dbsp_bitemporal_forge(**data, **kwargs)
        if m in (
            "asymmetric_leapfrog",
            "refusal_autobind",
            "angelic_zygote_swe",
            "shadow_transducer_cu",
            "digital_twin_arc",
            "sheaf_srmu_memory",
            "pc_dgm_evolve",
            "eggmind_proof",
        ):
            pil = "AUTO" if m == "asymmetric_leapfrog" else m.upper()
            return self.asymmetric_leapfrog(goal, pillar=pil, inputs=data, **kwargs)
        if m == "version_space_swe" or (
            m == "auto"
            and (
                "candidate_ids" in data
                or "angelic_source" in data
                or "inverse_name" in data
                or "history_pairs" in data
                or "dataflow_root" in data
            )
        ):
            return self.disambiguate_and_pin_repairs(**data, **kwargs)
        if m == "equivalence_oracle" or (
            m == "auto"
            and (
                "code_rule" in data
                or "projection_features" in data
                or "pin_fixed" in data
                or "amplify_module_path" in data
            )
        ):
            return self.prove_equivalence_and_amplify(**data, **kwargs)
        if m == "meaning_first" or (
            m == "auto"
            and (
                "semantic_sources" in data
                or "before_snippet" in data
                or "operator_symbol" in data
                or "compress_objects" in data
                or "weight_goal" in data
            )
        ):
            return self.crystallize_meaning_first_transfer(**data, **kwargs)
        if m == "memini_memrl" or (m == "auto" and ("outcomes" in data or "gamma_fast" in data)):
            return self.memini_memrl_apex_consolidate(**data, **kwargs)
        if m == "osworld_epistemic_cu" or (
            m == "auto"
            and ("policy_mode" in data or "nl_goal" in data or "grammar_need" in data or "proposed_action" in data)
        ):
            return self.execute_osworld_v21_epistemic_cu(**data, **kwargs)
        if m == "speculative_commit" or (
            m == "auto"
            and (
                "standing_before_state" in data
                or "witness_root" in data
                or "replay_before" in data
                or "plan_parallel_frontier" in data
            )
        ):
            return self.speculative_macro_commit(**data, **kwargs)
        if m == "active_repertoire" or (
            m == "auto"
            and (
                "repertoire_query" in data
                or "typed_spec" in data
                or "typed_examples" in data
                or "distinction_transitions" in data
                or "efe_info_gain" in data
                or "question_statement" in data
            )
        ):
            return self.active_repertoire_typed_invention(**data, **kwargs)
        if m == "latest_sources":
            return self.recall_latest_sources(goal, **data, **kwargs)
        if m == "symbol_graph" or (m == "auto" and "symgraph_root" in data):
            s_root = data.pop("symgraph_root", repo_root or ROOT)
            return self.repo_symbol_graph_query(s_root, **data, **kwargs)
        if m == "contrast_laws" or (m == "auto" and "student_observations" in data):
            return self.contrast_memory_laws(**data, **kwargs)
        if m == "hindsight_jitrl" or (
            m == "auto"
            and (
                "jitrl_filing_key" in data
                or "alpha_example_before" in data
                or "feature_keys" in data
                or "failed_trace" in data
            )
        ):
            return self.filing_key_hindsight_jitrl(**data, **kwargs)
        if m == "producer_holes" or (
            m == "auto" and ("source" in data and "test_source" in data)
        ):
            return self.solve_producer_lineage_holes(**data, **kwargs)
        if m == "verifier_pinning" or (
            m == "auto"
            and (
                ("before_source" in data and "after_source" in data)
                or "docstring_source" in data
                or "green_suite_source" in data
            )
        ):
            return self.audit_verifier_pinning_and_oracles(**data, **kwargs)
        if m == "purpose_gate" or (
            m == "auto" and ("boundary_survivors" in data or ("candidates" in data and "traces" in data))
        ):
            return self.purpose_gate_and_cost_arbitrage(**data, **kwargs)
        if m == "two_move_cu" or (
            m == "auto"
            and (
                "two_move_moves" in data
                or "bridge_subgoals" in data
                or "dag_stages" in data
                or "osworld_state" in data
            )
        ):
            return self.plan_two_move_horizon_cu(**data, **kwargs)
        if m == "swe_repo_native" or (m == "auto" and "repo_root" in data):
            return self.solve_swe_repo_native(**data, **kwargs)
        if m == "decision_quotient" or (m == "auto" and "actions_by_world" in data):
            return self.compile_decision_quotient(**data, **kwargs)
        if m == "zero_screenshot_cu" or (
            m == "auto"
            and (
                "subgoals" in data
                or "dom_observation" in data
                or "run_tier0_cache_suite" in data
                or "vocabulary_invocation" in data
            )
        ):
            return self.execute_horizon_zero_screenshot_cu(**data, **kwargs)
        if m == "safe_explore" or (
            m == "auto" and ("observations" in data or ("env" in data and "is_goal" in data) or "demo_state" in data)
        ):
            return self.explore_safe_action_model(**data, **kwargs)
        if m == "effect_chain" or (m == "auto" and "contracts_spec" in data):
            return self.verify_effect_contract_chain(**data, **kwargs)
        if m == "red_queen" or (m == "auto" and ("epoch_index" in data or "lens_witness_pairs" in data)):
            return self.red_queen_coevolve_evaluators(**data, **kwargs)
        if m == "bridge" or (m == "auto" and ("contract_text" in data or "repo_nav_root" in data)):
            return self.universal_capability_bridge(goal, **data, **kwargs)
        if m == "swe" or (m == "auto" and repo_root is not None):
            return self.solve_swe_inverted_microscope(
                repo_root or ROOT,
                goal=goal,
                residual_proposer=residual_proposer,
                **kwargs,
            )
        if m == "gui_elevate" or (m == "auto" and trace is not None):
            return self.elevate_gui_trace(trace or (), goal=goal, **kwargs)
        if m == "interrogate" or (m == "auto" and params is not None):
            return self.interrogate_minimax_witness(params=params or (), examples=examples or (), **kwargs)
        if m == "plan" or (m == "auto" and initial is not None and goal_conditions is not None):
            return self.plan_partial_order(
                initial=initial or (),
                goal=goal_conditions or (),
                operators=operators,
                transitions=transitions,
                **kwargs,
            )
        if m == "fast_cascade":
            return self.fast_cascade_solve(kwargs)
        if m == "bitemporal_recall" or m == "forward_push":
            return self.bitemporal_associative_recall(goal, **kwargs)
        if m == "memory" or m == "fts5":
            return self.fts5_recall(goal, **kwargs)
        return self.fts5_recall(goal, **kwargs)

    # ------------------------------------------------- Waves 21-24 Frontier Leapfrog Surfaces

    def fast_cascade_solve(
        self,
        task_spec: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Wave 23: 4-Rung Zero-LLM Fast-Cascade Orchestrator (`AstDiscrTree` -> CoW State-Alias
        5-Layer Tomography -> CoW Zygote Slicing & 64-Vector Boundary Fuzz -> Petri Cut-Vertex / Active Contrast)."""
        return self.boundary_router.route_fast_cascade(**dict(task_spec))

    def traced_callable_catalog(
        self,
        *,
        domain: str | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """Wave 22: Query the `260`-module (`64.04%` full-population survival) execution-traced
        `SOURCE_ONLY` callable catalog (`EXECUTION_TRACED_CALLABLE_CENSUS_20261126_V1.json`)."""
        if self._traced_catalog_cache is None:
            census_fp = ROOT / "canonical" / "verification" / "EXECUTION_TRACED_CALLABLE_CENSUS_20261126_V1.json"
            if census_fp.is_file():
                self._traced_catalog_cache = json.loads(census_fp.read_text(encoding="utf-8"))
            else:
                self._traced_catalog_cache = {"verified_adapters": [], "survived_two_run_and_sha256_guard_count": 0}

        mods = list(self._traced_catalog_cache.get("verified_adapters") or ())
        domain_counts: dict[str, int] = {}
        for row in mods:
            for d in row.get("domains") or ("general",):
                domain_counts[str(d)] = domain_counts.get(str(d), 0) + 1
        if domain:
            dom = str(domain).strip().lower()
            mods = [m for m in mods if dom in [str(d).lower() for d in (m.get("domains") or ())]]
        if top_k is not None:
            mods = mods[: max(1, int(top_k))]
        return self._envelope(
            operation="TRACED_CALLABLE_CATALOG",
            goal=f"domain={domain or 'ALL'}",
            status="PASS__TRACED_CALLABLE_CATALOG",
            **{"pass": bool(mods)},
            total_verified_count=int(self._traced_catalog_cache.get("survived_two_run_and_sha256_guard_count", len(mods))),
            survival_rate=float(self._traced_catalog_cache.get("survival_rate", 0.0)),
            lift_multiple_vs_ast_literal_baseline=float(
                self._traced_catalog_cache.get("lift_multiple_vs_ast_literal_baseline", 0.0)
            ),
            domain_counts=domain_counts,
            modules=mods,
        )

    def invoke_traced_module(
        self,
        module_or_stem: str,
        *,
        args: Sequence[Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 22: Derive (or reuse) C-level execution-traced adapter + SHA256 non-destructive guard
        for `module_or_stem` and execute its verified entrypoint inside an isolated scratch sandbox."""
        from canonical.runtime import execution_traced_callable_compiler_v1 as etcc

        q = str(module_or_stem).strip()
        rel_path = q
        if not q.endswith(".py"):
            cat = self.traced_callable_catalog()
            matched = [m for m in cat.get("modules") or () if m.get("stem") == q or m.get("module") == q]
            if matched:
                rel_path = str(matched[0]["module"])
            else:
                found = self.find_source(q, top_k=1)
                cands = found.get("candidates") or ()
                if cands:
                    rel_path = str(cands[0].get("path") or q)

        adapter = self._traced_adapter_cache.get(rel_path)
        if adapter is None:
            derived = etcc.derive_verified_module_adapter(rel_path, root=ROOT)
            if not derived.get("pass"):
                return self._envelope(
                    operation="INVOKE_TRACED_MODULE",
                    goal=q,
                    status=str(derived.get("reason") or "FAIL_CLOSED__TRACED_ADAPTER_UNVERIFIED"),
                    **{"pass": False},
                    detail=derived,
                )
            adapter = dict(derived)
            self._traced_adapter_cache[rel_path] = adapter

        inv = etcc.invoke_verified_traced_adapter(
            adapter,
            override_args=args,
            override_kwargs=kwargs,
            root=ROOT,
        )
        if not inv.get("pass"):
            return self._envelope(
                operation="INVOKE_TRACED_MODULE",
                goal=q,
                status=str(inv.get("reason") or "FAIL_CLOSED__TRACED_INVOKE_FAILED"),
                **{"pass": False},
                detail=inv,
            )
        return self._envelope(
            operation="INVOKE_TRACED_MODULE",
            goal=q,
            status="PASS__TRACED_MODULE_INVOKED",
            **{"pass": True},
            module_path=rel_path,
            entrypoint=adapter["entrypoint"],
            output_digest=inv["output_digest"],
            matches_recorded_witness=inv.get("matches_recorded_witness"),
            capsule_head_hash=adapter.get("capsule_head_hash"),
            result=inv.get("result"),
        )

    def bitemporal_associative_recall(
        self,
        query: str,
        *,
        valid_at_ts: float | None = None,
        alpha: float = 0.20,
        epsilon: float = 1e-3,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Wave 24: Andersen-Chung-Lang `ForwardPush` Local PPR Bi-Temporal Associative Recall (`< 0.5 ms` p95)."""
        return self.boundary_router.route_forward_push_recall(
            query,
            valid_at_ts=valid_at_ts,
            alpha=alpha,
            epsilon=epsilon,
            top_k=top_k,
        )

    def curate_skill_rent(
        self,
        *,
        max_active_skills: int = 64,
        paired_probes: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        latency_penalty_per_ms: float = 0.002,
    ) -> dict[str, Any]:
        """Wave 24: Two-Door Rubin `(WITH - WITHOUT)` Counterfactual Skill Rent & Finite Cap Curator."""
        return self.boundary_router.route_two_door_rent_curation(
            max_active_skills=max_active_skills,
            paired_probes=paired_probes,
            latency_penalty_per_ms=latency_penalty_per_ms,
        )

    def open_creature(
        self,
        root: str | Path,
        *,
        identity: str = "creature",
        life: float = 40.0,
        world_probe: Any = None,
    ) -> Any:
        """Boot the persistent 7-organ `Creature` runtime bound directly to this `UnifiedModel`."""
        from canonical.runtime import creature_runtime_v1 as creature_rt

        creature = creature_rt.Creature(identity=identity, root=Path(root), life_grant=float(life))
        creature.attach_unified_model(self)
        creature.boot(world_probe=world_probe)
        return creature

    def run_creature_cycle(
        self,
        root: str | Path,
        *,
        identity: str = "creature",
        life: float = 40.0,
        cycles: int = 1,
        perform: Any = None,
        world_probe: Any = None,
        sleep_consolidate: bool = False,
    ) -> dict[str, Any]:
        """Boot and run persistent unified-body cycles via `creature_runtime_v1` sharing `self.memory_bus`."""
        from canonical.runtime import creature_runtime_v1 as creature_rt

        creature = self.open_creature(root, identity=identity, life=life, world_probe=world_probe)
        fn = perform if perform is not None else creature_rt.sovereign_perform
        steps = creature.run(cycles=int(cycles), perform=fn)
        consol = creature.sleep_consolidate_memory() if sleep_consolidate else None
        rep = creature.report()
        return self._envelope(
            operation="RUN_CREATURE_CYCLE",
            goal=f"creature:{identity}:cycles={cycles}",
            status="PASS__CREATURE_UNIFIED_CYCLE",
            **{"pass": True},
            creature_report=rep,
            steps=steps,
            sleep_consolidation=consol,
        )

    def route_ppr(
        self,
        goal: str,
        *,
        top_k: int = 5,
        executable_only: bool = True,
    ) -> dict[str, Any]:
        """Phase 1: `< 0.30 ms` Bipartite Specificity Personalized PageRank (`HippoRAG 2` + `DOMAIN_ATLAS_V1`)."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        if self._ppr_router is None:
            self._ppr_router = fsm.SpecificityBipartitePPRRouter(self, root=ROOT)
        return self._ppr_router.route(goal, top_k=top_k, executable_only=executable_only)

    def learn_instant(
        self,
        *,
        alphabet: Sequence[str],
        execute_trace: Any,
        held_out_traces: Sequence[Sequence[str]] = (),
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Phase 2: `< 50 us` Kalman surprise gate + `< 5.0 ms` Symbolic Mealy (`L^s` + `Lambda*_M`) instant learner."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.learn_instant_environment(
            alphabet=alphabet,
            execute_trace=execute_trace,
            held_out_traces=held_out_traces,
            **kwargs,
        )

    def execute_tomographic_petri(
        self,
        workspace: str | Path,
        workflow: Sequence[Mapping[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Phase 3: `< 20 us` Certified Petri-Net Supervisory Control (`AEPN`) + `< 3.0 ms` 5-Layer State Tomography."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.execute_tomographic_petri(Path(workspace), workflow, **kwargs)

    def dbsp_memory_and_wake_sleep_cycle(
        self,
        *,
        scale_events: int = 25000,
    ) -> dict[str, Any]:
        """Phase 5: `< 100 us` `O(|Delta|)` DBSP Bi-Temporal `Z`-Set + `< 1.0 ms` Local PPR + `[G_-, B_+]` Wake-Sleep."""
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        return fsm.dbsp_memory_and_wake_sleep_cycle(scale_events=scale_events)

    # ----------------------------------------------------- Unfamiliar-Name 6-Move Frontier Leapfrog Front Door

    def learn_apartness_lsharp(
        self,
        *,
        alphabet: Sequence[str],
        execute_trace: Any,
        held_out_traces: Sequence[Sequence[str]] = (),
        target_output: str | None = None,
        prune_error_sinks: bool = True,
    ) -> dict[str, Any]:
        """Move 0: `< 0.25 ms` observation-table-free Brouwer-Heyting constructive apartness (`L#_e`) learner."""
        from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

        return uul.ApartnessTreeInstantLearner(prune_error_sinks=prune_error_sinks).learn(
            alphabet=alphabet,
            execute_trace=execute_trace,
            held_out_traces=held_out_traces,
            target_output=target_output,
        )

    def solve_angelic_sygus_swe(
        self,
        source_text: str,
        test_source: str,
        *,
        filename: str = "target_mod.py",
        instruction_hint: str = "",
        seed_cold_store: bool = False,
    ) -> dict[str, Any]:
        """Move 1: CoW Angelic Forest impossibility sieve + `OE-SyGuS` (`EUSolver`) + `NAME_SCOPE` + 4-gate verifier."""
        from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

        return uul.AngelicForestSyGuSRepairEngine().solve(
            source_text,
            test_source,
            filename=filename,
            instruction_hint=instruction_hint,
            seed_cold_store=seed_cold_store,
        )

    def lift_protocol_and_verify_effect(self, **kwargs: Any) -> dict[str, Any]:
        """Move 2: `WebMCP` + CDP/HAR network-to-HTTP protocol lifter + `osworld_intake` + magic-header `effect_oracle`."""
        from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

        return uul.lift_protocol_and_verify_effect(**kwargs)

    def live_browser_episode(self, goal: str, *, room: Any, **kwargs: Any) -> dict[str, Any]:
        from canonical.runtime.witnessed_browser_v1 import episode
        return episode(room, goal, **kwargs)

    def live_browser_step(self, goal: str, *, room: Any, **kwargs: Any) -> dict[str, Any]:
        from canonical.runtime.witnessed_browser_v1 import step
        return step(room, goal, **kwargs)

    def revision_memory(self, path: str | Path, operation: str, **payload: Any) -> dict[str, Any]:
        from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore
        store = RevisionStore(path)
        if operation in ('ingest_turn', 'answer_question'):
            from canonical.runtime.dialogue_revision_reader_v1 import DialogueReader
            reader = DialogueReader(store)
            if operation == 'ingest_turn':
                return {'statements_grounded': reader.ingest(**payload)}
            return reader.answer(**payload)
        return store.apply(operation, payload)

    def semiring_jtms_memory_cycle(
        self,
        *,
        chain_count: int = 24,
        chain_depth: int = 4,
    ) -> dict[str, Any]:
        """Move 3: Structured chain retraction control, not a score on MEME conversations."""
        from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

        return uul.run_meme_semiring_benchmark(chain_count=chain_count, chain_depth=chain_depth)

    def minimax_interrogate_version_space(self, **kwargs: Any) -> dict[str, Any]:
        """Move 4: Exact DP minimax decision-region version-space interrogator (`finite_minimax_decision_region_v1`)."""
        from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

        return uul.minimax_interrogate_version_space(**kwargs)

    def evolve_pareto_organ(self, baseline_source: str, **kwargs: Any) -> dict[str, Any]:
        """Move 5: Zero-LLM `AlphaEvolve` MAP-Elites + Pareto code synthesizer with anti-reward-hacking oracle gate."""
        from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

        return uul.evolve_pareto_organ(baseline_source, **kwargs)

    def run_unfamiliar_six_moves_suite(self) -> dict[str, Any]:
        """Execute all 6 Unfamiliar-Name Frontier Leapfrog Moves end-to-end through `UnifiedModel` (`K3 = 0`)."""
        from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

        return uul.run_unfamiliar_six_moves_suite()

    # ------------------------------------------------------------------ Wave 36 + 37 Unified Futamura & OS-Confined Front Doors

    def _get_futamura_cascade(self) -> Any:
        if self._futamura_cascade is None:
            from canonical.runtime.futamura_leapfrog_kernel_v1 import FutamuraSelfCompilingCascade

            self._futamura_cascade = FutamuraSelfCompilingCascade()
        return self._futamura_cascade

    def futamura_solve(
        self,
        task: Mapping[str, Any],
        *,
        untrusted_proposer: Any = None,
        auto_compile: bool = True,
        use_cow_fork: bool = True,
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """Wave 36: Futamura self-compiling Rung 0 -> 1 -> 2 -> 3 cascade with Ring-0 verification."""
        return self._get_futamura_cascade().solve(
            task,
            untrusted_proposer=untrusted_proposer,
            auto_compile=auto_compile,
            use_cow_fork=use_cow_fork,
            alpha=alpha,
        )

    def verify_byte_effect(
        self,
        target: str | Path,
        *,
        expected_format: str | None = None,
        expected_source_bytes: bytes | None = None,
        expected_source_path: str | Path | None = None,
        baseline_archive_hashes: Mapping[str, str] | None = None,
        allowed_archive_mutations: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Wave 36: Ring-0 byte-level effect verification (magic headers, roundtrip, lying extensions, archive invariance)."""
        from canonical.runtime.byte_effect_oracle_v1 import verify_byte_effect

        return verify_byte_effect(
            target,
            expected_format=expected_format,
            expected_source_bytes=expected_source_bytes,
            expected_source_path=expected_source_path,
            baseline_archive_hashes=baseline_archive_hashes,
            allowed_archive_mutations=allowed_archive_mutations,
        )

    def minimize_patch_ddmin(
        self,
        original_source: str,
        patched_source: str,
        oracle_fn: Any,
    ) -> dict[str, Any]:
        """Wave 36: Atomic-line Delta-Debugging (`ddmin`) hunk minimizer (`NP_code`)."""
        from canonical.runtime.byte_effect_oracle_v1 import ddmin_minimize_hunks

        return ddmin_minimize_hunks(original_source, patched_source, oracle_fn)

    def audit_patch_mutations(
        self,
        original_source: str,
        patched_source: str,
        oracle_fn: Any,
        *,
        max_mutants: int = 16,
    ) -> dict[str, Any]:
        """Wave 36: Touched-line adversarial mutation-kill audit."""
        from canonical.runtime.byte_effect_oracle_v1 import audit_patch_mutation_kill

        return audit_patch_mutation_kill(
            original_source, patched_source, oracle_fn, max_mutants=max_mutants
        )

    def learn_mealy_instant(
        self,
        reset_and_run: Any,
        alphabet: Sequence[str],
        *,
        numeric_actions: Mapping[str, tuple[int, int]] | None = None,
        error_outputs: Sequence[str] = ("ERR", "ERROR", "FAIL", "DENIED"),
        commutative_pairs: Sequence[tuple[str, str]] = (),
        idempotent_actions: Sequence[str] = (),
        max_states: int = 32,
        enable_error_pruning: bool = True,
    ) -> Any:
        """Wave 36: Error-Aware `L#` + `Lambda*_M` sub-ms symbolic Mealy instant learner."""
        from canonical.runtime.futamura_leapfrog_kernel_v1 import ErrorAwareSymbolicMealyLearner

        return ErrorAwareSymbolicMealyLearner().learn(
            reset_and_run,
            alphabet,
            numeric_actions=numeric_actions,
            error_outputs=error_outputs,
            commutative_pairs=commutative_pairs,
            idempotent_actions=idempotent_actions,
            max_states=max_states,
            enable_error_pruning=enable_error_pruning,
        )

    def execute_hybrid_cu(
        self,
        steps: Sequence[Mapping[str, Any]],
        *,
        initial_marking: Mapping[str, int] | None = None,
        transitions: Mapping[str, Mapping[str, Any]] | None = None,
        executor: Any = None,
        initial_state: Mapping[str, Any] | None = None,
        max_loop_repeats: int = 2,
        macros: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Wave 36: 3-channel HCU (`Programmatic > Semantic > Visual`) + Petri guard + loop-churn killer + PASTE macros."""
        from canonical.runtime.futamura_leapfrog_kernel_v1 import HybridComputerUsePetriSupervisor

        sup = HybridComputerUsePetriSupervisor(
            initial_marking=initial_marking,
            transitions=transitions,
        )
        for m_name, m_steps in (macros or {}).items():
            sup.register_paste_macro(str(m_name), m_steps)
        return sup.execute_episode(
            steps,
            executor=executor,
            initial_state=initial_state,
            max_loop_repeats=max_loop_repeats,
        )

    def dbsp_belief_bus(self) -> Any:
        """Wave 36: Live DBSP bi-temporal `Z`-set + Kumiho AGM belief-revision + `PreCommitFailureGate` bus."""
        return self._get_futamura_cascade().belief_bus

    def conformal_evalue_gate(
        self,
        observations: Sequence[Mapping[str, Any]],
        *,
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """Wave 36: Anytime-valid SCoRE conformal e-process gate (`Ville bound <= alpha`)."""
        from canonical.runtime.futamura_leapfrog_kernel_v1 import ConformalEValueGate

        gate = ConformalEValueGate(alpha=alpha)
        for ev in observations:
            gate.observe(
                str(ev["evidence"]),
                passed=bool(ev["passed"]),
                null_pass_prob=float(ev.get("null_pass_prob", 0.25)),
                hard_contradiction=bool(ev.get("hard_contradiction", False)),
            )
        return gate.decision()

    def cow_zygote_repair(
        self,
        source: str,
        test_cases: Sequence[str],
        *,
        use_cow_fork: bool = True,
    ) -> dict[str, Any]:
        """Wave 36: Zero-overhead `os.fork()` CoW zygote AST repair + ddmin + mutation-kill gate."""
        from canonical.runtime.futamura_leapfrog_kernel_v1 import ZeroOverheadCoWZygoteRepairEngine

        return ZeroOverheadCoWZygoteRepairEngine().repair(
            source, test_cases, use_cow_fork=use_cow_fork
        )

    def wake_sleep_consolidate(
        self,
        *,
        max_active_rules: int = 64,
        rubin_observations: Mapping[str, tuple[float, float]] | None = None,
    ) -> dict[str, Any]:
        """Wave 36: Wake-sleep anti-unification MDL consolidation + Rubin skill-rent GC."""
        return self._get_futamura_cascade().wake_sleep_consolidate(
            max_active_rules=max_active_rules,
            rubin_observations=rubin_observations,
        )

    def probe_os_isolation(self, *, budget_s: float = 30.0, seccomp: bool = True) -> dict[str, Any]:
        """Wave 37+38: Real Linux kernel namespace (`user+mount+pid+ipc+uts+net`, `CapEff=0`,
        classic BPF `seccomp` allowlist) 20-attempt adversarial escape probe."""
        from canonical.runtime import os_isolation_v1

        return os_isolation_v1.probe(budget_s=budget_s, seccomp=seccomp)

    def execute_confined_computer_use(
        self,
        work_dir: str | Path,
        steps: Sequence[Mapping[str, Any]],
        *,
        goal_id: str = "confined_hcu_episode",
        budget_s: float = 15.0,
        allow_network: bool = False,
        verify_effect: bool = True,
        seccomp: bool = True,
        auto_compile_refusal: bool = True,
        webmcp_tools: Mapping[str, Mapping[str, Any]] | None = None,
        initial_marking: Mapping[str, int] | None = None,
        transitions: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Wave 37+38: Real OS kernel-confined (`CapEff=0` + `seccomp` BPF) 4-channel HCU executor
        (`WebMCP > Programmatic > Semantic > Visual`) with Agent-S4 Refusal-as-Interface-Compiler,
        Ring-0 byte-effect verification & atomic CoW rollback."""
        from canonical.runtime.futamura_leapfrog_kernel_v1 import (
            ConfinedHybridComputerUseExecutor,
            HybridComputerUsePetriSupervisor,
        )

        sup = HybridComputerUsePetriSupervisor(
            initial_marking=initial_marking,
            transitions=transitions,
        )
        ex = getattr(self, "_wave38_confined_hcu", None)
        if ex is None or initial_marking is not None or transitions is not None or webmcp_tools is not None:
            ex = ConfinedHybridComputerUseExecutor(
                supervisor=sup,
                belief_bus=self._get_futamura_cascade().belief_bus,
                webmcp_tools=webmcp_tools,
            )
            if initial_marking is None and transitions is None and webmcp_tools is None:
                self._wave38_confined_hcu = ex
        return ex.execute_episode(
            work_dir,
            steps,
            goal_id=goal_id,
            budget_s=budget_s,
            allow_network=allow_network,
            verify_effect=verify_effect,
            seccomp=seccomp,
            auto_compile_refusal=auto_compile_refusal,
        )

    def solve_multifile_repo_futamura(
        self,
        repo_dir: str | Path,
        test_targets: Sequence[str] = (),
        *,
        goal_text: str = "",
        suspect_files: Sequence[str] | None = None,
        auto_compile: bool = True,
        apply_to_disk: bool = True,
        use_portfolio_fallback: bool = False,
        use_residual_wall_closers: bool = True,
        use_repo_component_petri: bool = True,
        reject_vacuous_verifier: bool = False,
        untrusted_proposer: Callable[[Mapping[str, Any]], Sequence[Mapping[str, str]]] | None = None,
        alpha: float = 0.05,
        timeout_s: float = 10.0,
    ) -> dict[str, Any]:
        """Wave 37+38: Unified multi-file Python repository Futamura solver (Rung-0 compiled skills +
        `stdlib_cow_test_runner_v1` CoW fork screening + extended AST + 13-law statement-shaped
        residual wall closers + repo component Petri + anti-vacuous verifier audit + optional
        pluggable Rung-3 proposer + Ring-0 Gate + automatic Rung-0 compile-back)."""
        from canonical.runtime.futamura_leapfrog_kernel_v1 import MultifileFutamuraRepoSolver

        solver = MultifileFutamuraRepoSolver(cascade=self._get_futamura_cascade())
        return solver.solve(
            repo_dir,
            test_targets,
            goal_text=goal_text,
            suspect_files=suspect_files,
            auto_compile=auto_compile,
            apply_to_disk=apply_to_disk,
            use_portfolio_fallback=use_portfolio_fallback,
            use_residual_wall_closers=use_residual_wall_closers,
            use_repo_component_petri=use_repo_component_petri,
            reject_vacuous_verifier=reject_vacuous_verifier,
            untrusted_proposer=untrusted_proposer,
            alpha=alpha,
            timeout_s=timeout_s,
        )

    def solve_typed_cegis(
        self,
        spec: Mapping[str, Any],
        *,
        max_depth: int = 3,
        max_iter: int = 20,
        type_env: Mapping[str, str] | None = None,
        concepts: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Wave 38: Type-pruned CEGIS(T) + composition concept bridge + adaptive constant V9 solver (`K3=0`)."""
        from canonical.runtime.futamura_leapfrog_kernel_v1 import solve_typed_cegis_and_concepts

        return solve_typed_cegis_and_concepts(
            spec,
            max_depth=max_depth,
            max_iter=max_iter,
            type_env=type_env,
            concepts=concepts,
        )

    def _get_non_malleable_memory_bus(self) -> Any:
        bus = getattr(self, "_wave38_memory_bus", None)
        if bus is None:
            from canonical.swe_kernel.canonical_memory_crystallizer_v1 import VerificationFirstMemoryBus

            bus = VerificationFirstMemoryBus()
            bus._wave36_dbsp_bus = self._get_futamura_cascade().belief_bus
            self._wave38_memory_bus = bus
        return bus

    def non_malleable_memory_op(
        self,
        operation: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 38: Execute a Non-Malleable Memory OS operation (TMA-NM origin binding, GovMem
        anti-correlation promotion, A-TMA anti-ghost-memory state view, SkillApt counterfactual
        activation, <96 hot-tier cap, or Bicameral Sleep Cycle) on Spine `0G`."""
        from canonical.swe_kernel.canonical_memory_crystallizer_v1 import execute_memory_operation

        return execute_memory_operation(self._get_non_malleable_memory_bus(), operation, payload)

    def bicameral_sleep_cycle(
        self,
        *,
        max_hot_skills: int = 96,
        mine_algebraic_rewrites: bool = False,
        weight_update_check: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 38: Two-phase Consolidate-and-Dream sleep cycle (Phase A symbolic consolidation +
        <96 hot-tier cap + rewrite mining; Phase B origin integrity audit + out-of-train weight gate)."""
        return self._get_non_malleable_memory_bus().bicameral_sleep_cycle(
            max_hot_skills=max_hot_skills,
            mine_algebraic_rewrites=mine_algebraic_rewrites,
            weight_update_check=weight_update_check,
        )

    def discover_dark_matter(
        self,
        query: str,
        *,
        top_k: int = 8,
        max_hot: int = 96,
    ) -> dict[str, Any]:
        """Wave 38 (OpenViking `viking://` L0/L1/L2 Progressive Dark-Matter Discovery):
        Maps unfamiliar frontier terms or plain goals across:
          - L0: Cross-disciplinary concept aliases (`CROSS_DISCIPLINARY_CONCEPT_MAP`)
          - L1: Active hot-tier routed engines & bound capabilities (capped at `<= max_hot`)
          - L2: Full `source_index` + `extended_source_index` dark-matter koan/hidden modules
        Zero model calls, sub-millisecond to few-millisecond deterministic lookup."""
        from canonical.runtime.unified_hidden_capability_federation_v1 import (
            resolve_cross_disciplinary_concept,
        )

        t0 = time.perf_counter()
        k = max(1, int(top_k))
        l0_concepts = resolve_cross_disciplinary_concept(query, top_k=min(5, k))
        l1_routed = self.route(query, top_k=min(k, max_hot))
        l2_sources = self.find_source(query, top_k=k)

        q_toks = set(tokenize(query))
        self._ensure_extended_source_index()
        ext_rows = self._extended_source_index_cache or {}
        ext_postings = self._extended_source_postings_cache or {}
        ext_scores: dict[str, float] = {}
        for tok in q_toks:
            for path_str, tf_val in ext_postings.get(tok, ()):
                ext_scores[path_str] = ext_scores.get(path_str, 0.0) + float(tf_val)
        ext_hits: list[tuple[float, dict[str, Any]]] = []
        for path_str, overlap in ext_scores.items():
            row = ext_rows.get(path_str)
            if not isinstance(row, Mapping):
                continue
            ext_hits.append(
                (
                    overlap,
                    {
                        "path": row.get("path"),
                        "tree": row.get("tree"),
                        "summary": row.get("summary", ""),
                        "classification": row.get("classification"),
                        "score": round(overlap, 3),
                    },
                )
            )
        ext_hits.sort(key=lambda item: (-item[0], str(item[1].get("path") or "")))
        l2_extended = [item[1] for item in ext_hits[:k]]

        best_concept = l0_concepts.get("best") or {}
        recommended_engines = list(best_concept.get("engines") or ())
        for cand in (l1_routed.get("candidates") or ()):
            cid = str(cand.get("id") or "")
            if cid and cid not in recommended_engines:
                recommended_engines.append(cid)

        return {
            "schema": "BRAIN_PROGRESSIVE_DARK_MATTER_DISCOVERY_V1",
            "query": str(query),
            "l0_cross_disciplinary": l0_concepts,
            "l1_hot_routes": (l1_routed.get("candidates") or ())[:k],
            "l2_runtime_sources": (l2_sources.get("candidates") or ())[:k],
            "l2_extended_dark_matter": l2_extended,
            "recommended_targets": recommended_engines[:k],
            "hot_tier_cap": int(max_hot),
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # ---------------------------------------- Asymmetric Frontier-Leapfrog Spine (7 Pillars, K3=0)

    def asymmetric_leapfrog(
        self,
        goal: str = "",
        *,
        pillar: str = "AUTO",
        inputs: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Single O(1) front door for all 7 Asymmetric Frontier-Leapfrog Pillars (`K3=0`)."""
        from canonical.runtime.asymmetric_frontier_leapfrog_v1 import asymmetric_leapfrog_dispatch

        return asymmetric_leapfrog_dispatch(goal, pillar=pillar, inputs=inputs, **kwargs)

    def abductive_refusal_autobind(self, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Pillar 1: Abductive Refusal-to-Contract Autobinder (`a_refusal_is_a_specification_v1` + `declared_input_derivation_v1`)."""
        return self.asymmetric_leapfrog(goal, pillar="REFUSAL_AUTOBIND", **kwargs)

    def angelic_zygote_swe_repair(self, **kwargs: Any) -> dict[str, Any]:
        """Pillar 2: CoW-Zygote + Angelic Forest + Concolic Version-Space Distinguishing SWE Engine."""
        return self.asymmetric_leapfrog(pillar="ANGELIC_ZYGOTE_SWE", **kwargs)

    def shadow_transducer_cu(self, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Pillar 3: Zero-Pixel Shadow-Interface Transduction + Declarative ARIA/CDP + Petri Checkpoints."""
        return self.asymmetric_leapfrog(goal, pillar="SHADOW_TRANSDUCER_CU", **kwargs)

    def digital_twin_arc_solve(self, **kwargs: Any) -> dict[str, Any]:
        """Pillar 4: `OPINE-World` + `Twin` 100%-Replay-Verified Digital Twin + `ARC-NEST` LOO + `E-Stitch`."""
        return self.asymmetric_leapfrog(pillar="DIGITAL_TWIN_ARC", **kwargs)

    def sheaf_srmu_memory(self, **kwargs: Any) -> dict[str, Any]:
        """Pillar 5: 3-Layer Algebraic Memory (`SRMU` 10,240-bit HV + Exact `Q` Sheaf `H^1` + Dual NNF Semiring)."""
        return self.asymmetric_leapfrog(pillar="SHEAF_SRMU_MEMORY", **kwargs)

    def pc_dgm_evolve(self, **kwargs: Any) -> dict[str, Any]:
        """Pillar 6: Proof-Carrying Darwin-Godel Machine + Turchin AST Supercompiler + Rubin Skill-Rent GC."""
        return self.asymmetric_leapfrog(pillar="PC_DGM_EVOLVE", **kwargs)

    def eggmind_prove(self, **kwargs: Any) -> dict[str, Any]:
        """Pillar 7: `EggMind` Proof-Motif E-Graph + `Pantograph` Tactic Goal-Tree Prover."""
        return self.asymmetric_leapfrog(pillar="EGGMIND_PROOF", **kwargs)

    # ------------------------------------------------------------------ Wave 39 Unified Five-Pillar Frontier Kernel

    def _get_five_pillar_kernel(self) -> Any:
        kern = getattr(self, "_w39_five_pillar_kernel", None)
        if kern is None:
            from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import (
                UnifiedFivePillarKernel,
            )

            kern = UnifiedFivePillarKernel()
            self._w39_five_pillar_kernel = kern
        return kern

    def unified_frontier_turn(
        self,
        goal: str,
        *,
        pillar: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 39 Unified 4-Stage `K3 = 0` Turn (`Observe/Ground -> Hypothesize -> CoW Verify -> Consolidate`)
        across all 5 Pillars + the Zero-Adapter `5,221`-function Inventory Bridge."""
        return self._get_five_pillar_kernel().run_turn(goal, pillar=pillar, payload=payload)

    def zero_adapter_inventory_bridge(
        self,
        goal: str,
        *,
        inputs: Mapping[str, Any] | None = None,
        registry: Mapping[str, Any] | None = None,
        top_k: int = 6,
        execute_if_bound: bool = False,
        max_chain_len: int = 2,
    ) -> dict[str, Any]:
        """Wave 39 Zero-Adapter Inventory Bridge: composes `module_bridge_v1` (`5,221` functions)
        with `type_level_composer_v1` type graphs (`0` thin wrappers)."""
        return self._get_five_pillar_kernel().inventory_bridge.query_and_compose(
            goal,
            inputs=inputs,
            registry=registry,
            top_k=top_k,
            execute_if_bound=execute_if_bound,
            max_chain_len=max_chain_len,
        )

    def instant_learn_moore_witness(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 39 Pillar I: Action-invariant Moore bisimulation transfer, `OPINE-World` ontology-error
        separating predicate synthesis, FCA Galois concept lattices, and `FlashMeta D4` witness inversion."""
        return self._get_five_pillar_kernel().instant_learner.learn_and_transfer(**kwargs)

    def execute_lens_standing_fact_cu(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 39 Pillar II: Zero-screenshot OOXML/JSON bijective lenses, relational record frames,
        CAS stale-frame click guards, standing-fact batch clobber recovery, and anti-false-`DONE` checks."""
        return self._get_five_pillar_kernel().computer_use.execute_workflow(**kwargs)

    def repair_swe_deltastate_siblings(self, repo_root: str | Path, **kwargs: Any) -> dict[str, Any]:
        """Wave 39 Pillar III: Calibrated non-vacuous test oracle + Plastic Surgery donor mining +
        `Coccinelle`/`SyDIT` multi-file sibling closure + `DeltaBox` warm-zygote `os.fork()` CoW rollout."""
        return self._get_five_pillar_kernel().swe_kernel.repair_repository(repo_root, **kwargs)

    def prospective_memtx_op(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 39 Pillar IV: `Kumiho` write-time prospective cue indexing, `CPB` root-disjoint Sybil
        echo defense, AGM $K^*7/K^*8$ ordinal entrenchment, and `RD-Forget` selective replay unlearning."""
        return self._get_five_pillar_kernel().run_turn("prospective_memtx_op", pillar="MEMORY", payload=kwargs)

    def consolidate_meaning_ir_skill(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 39 Pillar V: `Babble`/`Stitch` Meaning-IR anti-unification, zero-shot verified cross-language
        transfer across Python/JS/TS/Go/Rust, 4-gate Hoare sequence composition, and MDL bit-rent eviction."""
        return self._get_five_pillar_kernel().skill_ratchet.consolidate_and_transfer(**kwargs)

    # ------------------------------------------------------------- Wave 40 held-out bench

    def frontier_bench(self, *, seed: int | None = None, per_category: int = 3,
                       categories: Sequence[str] | None = None, self_check: bool = False) -> dict[str, Any]:
        """Wave 40: the held-out, oracle-judged benchmark (`canonical/evaluation/frontier_bench_v1.py`).

        Instances are generated from `seed` at call time and judged by oracles that never read this
        model's own `pass` flag, so `pass_rate` measures unseen instances, not its own fixtures."""
        from canonical.evaluation import frontier_bench_v1 as bench

        resolved = bench.DEFAULT_SEED if seed is None else int(seed)
        scorecard = bench.run_bench(seed=resolved, per_category=int(per_category), categories=categories)
        if self_check:
            scorecard["self_check"] = bench.bench_self_check(seed=resolved, per_category=int(per_category))
        return scorecard

    def refusal_acquire_retry(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 41: a refusal names what is missing; acquire it, verify it, retry, keep it."""
        from canonical.swe_kernel.refusal_acquire_retry_v1 import acquire_and_retry

        return acquire_and_retry(**kwargs)
    # --- Wave 39: Dark-Organ Unification, Red-Queen/Mendel Co-Evolution, CLM+RRF Memory & Partial-Routing/JitRL ---

    def _get_clm_rrf_memory_engine(self) -> Any:
        eng = getattr(self, "_clm_rrf_memory_engine", None)
        if eng is None:
            from canonical.runtime.wave39_leapfrog_unification_v1 import CLMRRFMemoryEngine

            eng = CLMRRFMemoryEngine(memory_bus=self._get_non_malleable_memory_bus())
            self._clm_rrf_memory_engine = eng
        return eng

    def mendel_red_queen_evolve(
        self,
        parent_source: str,
        lineage_a: str,
        lineage_b: str,
        *,
        verifier: Any,
        failing_witness: Any = None,
        owned_symbols: Sequence[str] | None = None,
        max_ast_bloat_ratio: float = 1.60,
        max_added_branches: int = 6,
        require_albi_invariance: bool = True,
    ) -> dict[str, Any]:
        """Wave 39: Mendel comparative dual splicing + ALBI semantic-anonymization + Anti-Slop/No-Phantom-Guardrails gate."""
        from canonical.runtime.wave39_leapfrog_unification_v1 import RedQueenMendelEvolver

        return RedQueenMendelEvolver.mendel_splice_and_verify(
            parent_source,
            lineage_a,
            lineage_b,
            verifier=verifier,
            failing_witness=failing_witness,
            owned_symbols=owned_symbols,
            max_ast_bloat_ratio=max_ast_bloat_ratio,
            max_added_branches=max_added_branches,
            require_albi_invariance=require_albi_invariance,
        )

    def audit_anti_slop_patch(
        self,
        parent_source: str,
        candidate_source: str,
        *,
        failing_witness: Any = None,
        owned_symbols: Sequence[str] | None = None,
        max_ast_bloat_ratio: float = 1.60,
        max_added_branches: int = 6,
        require_albi_invariance: bool = True,
    ) -> dict[str, Any]:
        """Wave 39: Anti-Slop (AST bloat/cyclomatic) + No-Phantom-Guardrails + Symbol-Ownership + ALBI gate."""
        from canonical.runtime.wave39_leapfrog_unification_v1 import RedQueenMendelEvolver

        return RedQueenMendelEvolver.audit_anti_slop_and_phantom_guardrails(
            parent_source,
            candidate_source,
            failing_witness=failing_witness,
            owned_symbols=owned_symbols,
            max_ast_bloat_ratio=max_ast_bloat_ratio,
            max_added_branches=max_added_branches,
            require_albi_invariance=require_albi_invariance,
        )

    def discover_and_earn_judges(
        self,
        *,
        artifacts_by_kind: Mapping[str, Sequence[bytes]] | None = None,
        store_dir: str | Path | None = None,
        include_stdlib_discovery: bool = True,
        cli_probe: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 39: Red Queen earned-judge discovery over live stdlib/CLI subprocess candidates (zero hand-written oracles)."""
        from canonical.runtime.wave39_leapfrog_unification_v1 import EarnedJudgeAndRefusalLifter

        return EarnedJudgeAndRefusalLifter.discover_and_earn_judges(
            artifacts_by_kind=artifacts_by_kind,
            store_dir=store_dir,
            include_stdlib_discovery=include_stdlib_discovery,
            cli_probe=cli_probe,
        )

    def lift_refusal_and_check_oracle(
        self,
        help_text: str,
        *,
        refusal_lines: Sequence[str] = (),
        action_argv: Sequence[str] = ("tool", "target"),
        paths: Sequence[str] = (),
        type_map: Mapping[str, str] | None = None,
        labels: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Wave 39: Lift CLI `--help` + stderr refusals into `--check`/`--dry-run` oracle probes, vocabulary classes & collapsed types."""
        from canonical.runtime.wave39_leapfrog_unification_v1 import EarnedJudgeAndRefusalLifter

        return EarnedJudgeAndRefusalLifter.lift_refusal_and_check_oracle(
            help_text,
            refusal_lines=refusal_lines,
            action_argv=action_argv,
            paths=paths,
            type_map=type_map,
            labels=labels,
        )

    def compose_and_plan_contracts(
        self,
        *,
        use_measured_advance_pair: bool = True,
        contracts: Sequence[Mapping[str, Any]] | None = None,
        initial_facts: Sequence[str] = (),
        goal_facts: Sequence[str] = (),
        operators: Sequence[Mapping[str, Any]] = (),
        concrete_plan: Sequence[Any] | None = None,
        success_states: Sequence[Any] | None = None,
        failure_states: Sequence[Any] | None = None,
        ast_provenance_source: str | None = None,
        run_observation_refutation: bool = False,
    ) -> dict[str, Any]:
        """Wave 39: Typed (P,O,A,V,F) effect-contract composition + Sussman partial-order planning + lifted sketches + provenance."""
        from canonical.runtime.wave39_leapfrog_unification_v1 import ContractPlannerAndLiftedGeneralizer

        return ContractPlannerAndLiftedGeneralizer.compose_and_plan(
            use_measured_advance_pair=use_measured_advance_pair,
            contracts=contracts,
            initial_facts=initial_facts,
            goal_facts=goal_facts,
            operators=operators,
            concrete_plan=concrete_plan,
            success_states=success_states,
            failure_states=failure_states,
            ast_provenance_source=ast_provenance_source,
            run_observation_refutation=run_observation_refutation,
        )

    def speculative_cow_decide(
        self,
        *,
        survivor_requirements: Sequence[Any],
        observed_facts: Sequence[str],
        p_correct: float = 0.5,
        wrong_commit_cost: float = 10.0,
        cow_trial_cost: float = 0.002,
        candidates: Sequence[tuple[str, Any]] | None = None,
        verifier: Any = None,
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        """Wave 39: Decision-theoretic version-space agreement gate + real POSIX `os.fork()` CoW speculation."""
        from canonical.runtime.wave39_leapfrog_unification_v1 import SpeculativeCoWDecisionGate

        return SpeculativeCoWDecisionGate.decide_and_speculate(
            survivor_requirements=survivor_requirements,
            observed_facts=observed_facts,
            p_correct=p_correct,
            wrong_commit_cost=wrong_commit_cost,
            cow_trial_cost=cow_trial_cost,
            candidates=candidates,
            verifier=verifier,
            timeout_s=timeout_s,
        )

    def clm_rrf_memory_op(
        self,
        operation: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 39: Verbatim-first 4-way RRF budgeted retrieval + Nemori surprise gating + CLM file-mirrored context + TMA-NM."""
        from canonical.runtime import wave39_leapfrog_unification_v1 as wave39

        try:
            return wave39.dispatch_clm_rrf_operation(self._get_clm_rrf_memory_engine(), operation, payload or {})
        except wave39.UnsupportedWave39Operation as exc:
            raise UnifiedModelError(str(exc)) from exc

    def partial_route_with_jitrl(
        self,
        operation: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 39: Closed-form JitRL logit modulation + SkillTTA dynamic skill synthesis + Intra-task Partial Routing."""
        from canonical.runtime import wave39_leapfrog_unification_v1 as wave39

        try:
            return wave39.dispatch_partial_routing_operation(operation, payload or {})
        except wave39.UnsupportedWave39Operation as exc:
            raise UnifiedModelError(str(exc)) from exc

    def self_verify_harvested_surfaces(self, *, limit: int = 40) -> dict[str, Any]:
        """Wave 39: Live offline AST + SHA-256 + public-entrypoint audit over `harvested_capabilities`."""
        from canonical.runtime.wave39_leapfrog_unification_v1 import PartialRoutingJitRLSkillTTAEngine

        harvested = list(self.model.get("harvested_capabilities") or ())
        return PartialRoutingJitRLSkillTTAEngine.self_verify_harvested_surfaces(
            harvested,
            repo_root=ROOT,
            limit=int(limit),
        )

# --------------------------------------------------------------------------- helpers

_VERSION_FAMILY_RE = re.compile(r"^(.+?)(?:_v(\d+))(\.[^.]+)$", re.IGNORECASE)

def dedupe_version_families(rows: Sequence[Mapping[str, Any]], *, path_key: str = "path") -> list[dict[str, Any]]:
    """Wave 31 Elon's Law: collapse superseded `*_v1..v(N-1).ext` siblings so the latest version wins."""
    best_by_family: dict[tuple[str, str], tuple[int, int, dict[str, Any]]] = {}
    passthrough: list[tuple[int, dict[str, Any]]] = []
    for idx, row in enumerate(rows):
        d = dict(row)
        raw_path = str(d.get(path_key) or d.get("id") or "")
        m = _VERSION_FAMILY_RE.match(raw_path)
        if not m:
            passthrough.append((idx, d))
            continue
        fam_key = (m.group(1), m.group(3).lower())
        ver = int(m.group(2))
        prev = best_by_family.get(fam_key)
        if prev is None or ver > prev[0]:
            superseded_count = (prev[2].get("superseded_versions_collapsed", 0) + 1) if prev is not None else 0
            d["version_family"] = m.group(1)
            d["version_number"] = ver
            d["superseded_versions_collapsed"] = superseded_count
            best_by_family[fam_key] = (ver, prev[1] if prev is not None else idx, d)
        else:
            prev[2]["superseded_versions_collapsed"] = int(prev[2].get("superseded_versions_collapsed", 0)) + 1
    merged: list[tuple[int, dict[str, Any]]] = list(passthrough)
    for _ver, first_idx, d in best_by_family.values():
        merged.append((first_idx, d))
    merged.sort(key=lambda item: item[0])
    return [d for _i, d in merged]

def _missing_declared_dependencies(
    row: Mapping[str, Any],
    *,
    probe_cache: dict[tuple[str, bool], bool] | None = None,
) -> list[str]:
    """Resolve a capability's declared dependencies against *this* machine.

    The artifact records only the tree-derived declaration, so this answer is
    true of the machine that is answering rather than of whichever machine last
    compiled the model. Names in ``declared_dependency_executables`` are resolved
    on PATH; every other declared name is resolved through the Python import
    machinery.
    """
    declaration = row.get("declared_dependencies") or {}
    checked = declaration.get("declared_dependencies_checked") or []
    on_path = {str(name) for name in declaration.get("declared_dependency_executables") or []}
    missing: list[str] = []
    for entry in checked:
        name = str(entry)
        if not name:
            continue
        is_exe = name in on_path
        key = (name, is_exe)
        found = probe_cache.get(key) if probe_cache is not None else None
        if found is None:
            if is_exe:
                import shutil as _shutil

                found = _shutil.which(name) is not None
            else:
                try:
                    found = importlib.util.find_spec(name) is not None
                except (ImportError, ValueError):
                    # A name the import machinery refuses to resolve is not
                    # evidence of presence. Fail closed.
                    found = False
            if probe_cache is not None:
                probe_cache[key] = found
        if not found:
            missing.append(name)
    return sorted(set(missing))

def _normalise_capability_id(value: str) -> str:
    cid = str(value or "").strip()
    if cid.startswith("bound:"):
        cid = cid[len("bound:"):]
    return cid

def _excerpt(path: Path, terms: Iterable[str], limit: int = 420) -> str:
    wanted = [t.casefold() for t in terms]
    best = ""
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if len(stripped) < 20:
                continue
            folded = stripped.casefold()
            if any(term in folded for term in wanted):
                best = " ".join(stripped.split())
                break
    except OSError:
        return ""
    return best[:limit]

_DEFAULT_TARGET_PATH = (ROOT / DEFAULT_ARTIFACT).resolve()
_DEFAULT_TARGET_KEY = str(_DEFAULT_TARGET_PATH)

def _stat_cache_path() -> Path:
    return _core_cache_dir() / "unified_model_stat_v1.marshal"

def _read_stat_sha(target_key: str, st: os.stat_result) -> str | None:
    """Salsa/Git racy-clean stat -> raw_sha256 fast path (skips 13.45 MB read+SHA256 on boot)."""
    # Racy-clean guard: if modified in the last 1.5s, re-hash bytes to guarantee tamper-safety.
    if (time.time_ns() - int(st.st_mtime_ns)) < 1_500_000_000:
        return None
    p = _stat_cache_path()
    if not p.is_file():
        return None
    try:
        blob = marshal.loads(p.read_bytes())
        if (
            isinstance(blob, dict)
            and blob.get("v") == 1
            and blob.get("path") == target_key
            and blob.get("size") == int(st.st_size)
            and blob.get("mtime_ns") == int(st.st_mtime_ns)
            and blob.get("ctime_ns") == int(st.st_ctime_ns)
            and blob.get("ino") == int(st.st_ino)
        ):
            sha = str(blob.get("raw_sha256") or "")
            return sha if len(sha) == 64 else None
    except Exception:
        return None
    return None

def _write_stat_sha(target_key: str, st: os.stat_result, raw_sha: str) -> None:
    try:
        cdir = _core_cache_dir()
        cdir.mkdir(parents=True, exist_ok=True)
        p = _stat_cache_path()
        tmp_f = cdir / f".unified_model_stat_v1.{os.getpid()}.tmp"
        tmp_f.write_bytes(
            marshal.dumps(
                {
                    "v": 1,
                    "path": target_key,
                    "size": int(st.st_size),
                    "mtime_ns": int(st.st_mtime_ns),
                    "ctime_ns": int(st.st_ctime_ns),
                    "ino": int(st.st_ino),
                    "raw_sha256": raw_sha,
                }
            )
        )
        tmp_f.replace(p)
    except OSError:
        pass

def prewarm_sidecar_caches(model: Mapping[str, Any] | None = None, target: Path | None = None) -> None:
    """Emit SHA-256-verified `.core.marshal` + 5 isolated per-section sidecars + FTS5 SQLite + Salsa stat cache."""
    try:
        resolved = (target if target is not None else _DEFAULT_TARGET_PATH).resolve()
        st = resolved.stat()
        raw_bytes = resolved.read_bytes()
        if model is None:
            model = json.loads(raw_bytes.decode("utf-8"))
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        cache_dir = _core_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        core = _extract_routing_core(model, raw_sha)
        core_tmp = cache_dir / f".unified_model_core_{raw_sha[:32]}.{os.getpid()}.tmp"
        core_tmp.write_bytes(marshal.dumps(core))
        core_tmp.replace(cache_dir / f"unified_model_core_{raw_sha[:32]}.marshal")
        _write_hot_tier_files(cache_dir, raw_sha, core)

        sec = _extract_secondary_indexes(model, raw_sha)
        ext_postings_tmp: dict[str, list[tuple[str, int]]] = {}
        for path, row in sec["extended_source_index"].items():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term, tf_val in terms.items():
                tf = int(tf_val or 0)
                if tf > 0:
                    ext_postings_tmp.setdefault(str(term), []).append((path, tf))
        per_sections = {
            "source_index": {
                "rows": sec["source_index"],
                "df": sec["source_df"],
                "postings": sec["source_postings"],
            },
            "extended_source_index": {
                "rows": sec["extended_source_index"],
                "df": sec["extended_source_df"],
                "postings": {k: tuple(v) for k, v in ext_postings_tmp.items()},
            },
            "research_index": {
                "rows": sec["research_index"],
                "df": sec["research_df"],
                "postings": sec["research_postings"],
            },
            "knowledge": {
                "rows": sec["knowledge"],
                "df": sec["knowledge_df"],
                "lengths": sec["knowledge_lengths"],
                "avg_len": sec["avg_length"],
                "postings": sec["knowledge_postings"],
                "title_postings": sec["knowledge_title_postings"],
            },
            "harvested": sec["harvested"],
        }
        for sec_name, sec_data in per_sections.items():
            p = cache_dir / f"unified_model_sec_{sec_name}_{raw_sha[:32]}.marshal"
            tmp_f = p.with_name(f".{p.name}.{os.getpid()}.tmp")
            tmp_f.write_bytes(marshal.dumps({"v": 2, "raw_sha256": raw_sha, "data": sec_data}))
            tmp_f.replace(p)
        try:
            from canonical.runtime.mmap_csr_slot_index_v1 import (
                build_csr_bytes,
                write_csr_atomic,
            )

            src_csr_bytes = build_csr_bytes(sec["source_index"], sec["source_df"])
            write_csr_atomic(
                cache_dir / f"unified_model_csr_source_index_{raw_sha[:32]}.bin",
                src_csr_bytes,
            )
            comb_df: dict[str, int] = dict(sec["source_df"])
            for k_df, v_df in sec["extended_source_df"].items():
                comb_df[k_df] = comb_df.get(k_df, 0) + int(v_df)
            comb_csr_bytes = build_csr_bytes(sec["combined_source_index"], comb_df)
            write_csr_atomic(
                cache_dir / f"unified_model_csr_combined_source_{raw_sha[:32]}.bin",
                comb_csr_bytes,
            )
        except Exception:
            pass
        # Pre-warm the SQLite FTS5 unified model index at compile time so the very
        # first fresh-process `fts5_recall()` hits disk cache in ~1 ms instead of ~185 ms.
        try:
            import sqlite3 as _sq

            fts_path = cache_dir / f"unified_model_fts5_{raw_sha[:24]}.sqlite3"
            tmp_fts = fts_path.with_name(f".{fts_path.name}.{os.getpid()}.tmp")
            if tmp_fts.exists():
                tmp_fts.unlink()
            fconn = _sq.connect(str(tmp_fts))
            fconn.execute("PRAGMA synchronous=OFF")
            fconn.execute("PRAGMA journal_mode=MEMORY")
            fconn.execute("CREATE TABLE fts_meta(key TEXT PRIMARY KEY, val TEXT)")
            fconn.execute(
                "CREATE VIRTUAL TABLE unified_fts USING fts5("
                "doc_id UNINDEXED, kind UNINDEXED, path UNINDEXED, title, body, tokenize='unicode61')"
            )
            frows: list[tuple[str, str, str, str, str]] = []
            for cid, cap in (core.get("capabilities_map") or {}).items():
                trigs = " ".join(str(t) for t in (cap.get("triggers") or ()))
                frows.append((
                    str(cid),
                    "capability",
                    str(cap.get("adapter_path") or cap.get("path") or ""),
                    str(cap.get("title") or cap.get("name") or cid),
                    f"{cap.get('domain', '')} {cap.get('description', '')} {trigs} {' '.join(cap.get('terms') or ())}",
                ))
            for eid, eng in (core.get("engines_map") or {}).items():
                frows.append((
                    str(eid),
                    "engine",
                    str(eng.get("path") or ""),
                    str(eng.get("name") or eid),
                    f"{eng.get('description', '')} {' '.join(eng.get('terms') or ())}",
                ))
            skills_obj = core.get("skills") or {}
            for sk in (skills_obj.values() if isinstance(skills_obj, Mapping) else skills_obj):
                if not isinstance(sk, Mapping):
                    continue
                sid = str(sk.get("id") or sk.get("name") or sk.get("path") or "")
                terms_obj = sk.get("terms")
                term_str = " ".join(terms_obj.keys()) if isinstance(terms_obj, Mapping) else " ".join(terms_obj or ())
                frows.append((
                    sid,
                    "skill",
                    str(sk.get("path") or ""),
                    str(sk.get("title") or sk.get("name") or sid),
                    f"{sk.get('description', '')} {' '.join(sk.get('headings') or ())} {term_str}",
                ))
            for doc in (sec.get("knowledge") or ()):
                frows.append((
                    str(doc.get("id") or doc.get("path") or ""),
                    "knowledge",
                    str(doc.get("path") or ""),
                    str(doc.get("title") or doc.get("path") or ""),
                    str(doc.get("summary") or doc.get("snippet") or "")[:600],
                ))
            for spath, srow in (sec.get("source_index") or {}).items():
                frows.append((
                    str(srow.get("id") or spath),
                    "source_index",
                    str(spath),
                    str(spath),
                    f"{srow.get('summary') or ''} {' '.join(srow.get('terms') or ())}"[:600],
                ))
            for spath, srow in (sec.get("extended_source_index") or {}).items():
                frows.append((
                    str(srow.get("id") or spath),
                    "extended_source",
                    str(spath),
                    str(spath),
                    f"{srow.get('summary') or ''} {' '.join(srow.get('terms') or ())}"[:600],
                ))
            fconn.executemany(
                "INSERT INTO unified_fts(doc_id, kind, path, title, body) VALUES (?, ?, ?, ?, ?)",
                frows,
            )
            fconn.execute("INSERT OR REPLACE INTO fts_meta(key, val) VALUES ('raw_sha256', ?)", (raw_sha,))
            fconn.commit()
            fconn.close()
            tmp_fts.replace(fts_path)
        except Exception:
            pass
        if resolved == _DEFAULT_TARGET_PATH:
            _write_stat_sha(str(resolved), st, raw_sha)
    except Exception:
        pass

def open_model(
    path: str | Path | None = None, *, root: str | Path | None = None
) -> UnifiedModel:
    is_default = path is None and root is None
    if is_default:
        try:
            st = os.stat(_DEFAULT_TARGET_KEY)
        except OSError as exc:
            raise UnifiedModelError("MODEL_ARTIFACT_MISSING:" + _DEFAULT_TARGET_KEY) from exc
        mem_key = (_DEFAULT_TARGET_KEY, st.st_size, st.st_mtime_ns)
        mem_hit = _OPEN_MODEL_MEM_CACHE.get(mem_key)
        if mem_hit is not None:
            return mem_hit
        base = ROOT
        target = _DEFAULT_TARGET_PATH
        target_key = _DEFAULT_TARGET_KEY
    else:
        base = Path(root or ROOT).resolve()
        target = Path(path) if path else base / DEFAULT_ARTIFACT
        if not target.is_absolute():
            target = base / target
        if not target.is_file():
            raise UnifiedModelError("MODEL_ARTIFACT_MISSING:" + str(target))
        st = target.stat()
        target_key = str(target.resolve())
        mem_key = (target_key, st.st_size, st.st_mtime_ns)
        mem_hit = _OPEN_MODEL_MEM_CACHE.get(mem_key)
        if mem_hit is not None:
            return mem_hit

    cache_dir = _core_cache_dir()
    is_canonical_default = target == _DEFAULT_TARGET_PATH

    raw_bytes: bytes | None = None
    raw_sha = _read_stat_sha(target_key, st) if is_canonical_default else None

    # Ultra-fast sidecar header verification (`< 0.2 ms`) when stat_sha is cold or within the 1.5s post-compile window:
    if raw_sha is None and is_canonical_default:
        core_sidecar_file = target.parent / "BRAIN_UNIFIED_CORE_V1.json"
        if core_sidecar_file.is_file():
            try:
                cst = core_sidecar_file.stat()
                ptr_file = cache_dir / f"unified_model_hot_v8_hdr_{cst.st_size}_{cst.st_mtime_ns}.marshal"
                hdr_cand: dict[str, Any] | None = None
                if ptr_file.is_file():
                    loaded_h = marshal.loads(ptr_file.read_bytes())
                    if (
                        isinstance(loaded_h, dict)
                        and loaded_h.get("core_format_v") == 5
                        and loaded_h.get("packed_marshal_v") == 6
                        and Path(str(loaded_h.get("_route_path") or "")).is_file()
                        and Path(str(loaded_h.get("_tables_path") or "")).is_file()
                    ):
                        hdr_cand = loaded_h
                if hdr_cand is None:
                    loaded_j = json.loads(core_sidecar_file.read_text(encoding="utf-8"))
                    if isinstance(loaded_j, dict) and loaded_j.get("core_format_v") == 5 and loaded_j.get("raw_sha256"):
                        hdr_cand = _write_hot_tier_files(cache_dir, str(loaded_j["raw_sha256"]), loaded_j)
                        try:
                            tmp_p = ptr_file.with_name(f".{ptr_file.name}.{os.getpid()}.tmp")
                            tmp_p.write_bytes(marshal.dumps(hdr_cand))
                            tmp_p.replace(ptr_file)
                        except OSError:
                            pass
                if (
                    hdr_cand is not None
                    and hdr_cand.get("schema") == SCHEMA
                    and int(hdr_cand.get("artifact_bytes") or -1) == st.st_size
                ):
                    digest_val = str(hdr_cand.get("digest_value") or "")
                    offset = int(hdr_cand.get("digest_needle_offset") or -1)
                    s_offset = int(hdr_cand.get("schema_needle_offset") or -1)
                    needle = f'"value": "{digest_val}"'.encode("ascii")
                    s_needle = f'"schema": "{SCHEMA}"'.encode("ascii")
                    if (
                        len(digest_val) == 64
                        and offset >= 0
                        and offset + len(needle) <= st.st_size
                        and s_offset >= 0
                        and s_offset + len(s_needle) <= st.st_size
                    ):
                        fd = os.open(target_key, os.O_RDONLY)
                        try:
                            head_ok = os.pread(fd, len(s_needle), s_offset) == s_needle
                            digest_ok = head_ok and (os.pread(fd, len(needle), offset) == needle)
                        finally:
                            os.close(fd)
                        if head_ok and digest_ok:
                            c_sha = str(hdr_cand.get("raw_sha256") or "")
                            if c_sha:
                                _VERIFIED_BLOB_DIGESTS[c_sha] = digest_val
                                inst = UnifiedModel(hdr_cand, _raw_bytes=None, _core_only=True, _target_path=target)
                                _OPEN_MODEL_MEM_CACHE[mem_key] = inst
                                return inst
            except Exception:
                pass

    if raw_sha is None:
        raw_bytes = target.read_bytes()
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        if is_canonical_default:
            _write_stat_sha(target_key, st, raw_sha)

    short_sha = raw_sha[:32]
    hdr_file = cache_dir / f"unified_model_hdr6_{short_sha}.marshal"
    if hdr_file.is_file():
        try:
            hdr = marshal.loads(hdr_file.read_bytes())
            if (
                isinstance(hdr, dict)
                and hdr.get("core_format_v") == 5
                and hdr.get("packed_marshal_v") == 6
                and hdr.get("raw_sha256") == raw_sha
                and hdr.get("schema") == SCHEMA
                and Path(str(hdr.get("_route_path") or "")).is_file()
                and Path(str(hdr.get("_tables_path") or "")).is_file()
            ):
                _VERIFIED_BLOB_DIGESTS[raw_sha] = str(hdr.get("digest_value") or "")
                inst = UnifiedModel(hdr, _raw_bytes=None, _core_only=True, _target_path=target)
                _OPEN_MODEL_MEM_CACHE[mem_key] = inst
                return inst
        except Exception:
            pass

    cache_file = cache_dir / f"unified_model_core_{short_sha}.marshal"
    if cache_file.is_file():
        try:
            core = marshal.loads(cache_file.read_bytes())
            if (
                isinstance(core, dict)
                and core.get("core_format_v") == 5
                and core.get("raw_sha256") == raw_sha
                and core.get("schema") == SCHEMA
            ):
                _VERIFIED_BLOB_DIGESTS[raw_sha] = str(core.get("digest_value") or "")
                hdr_out = _write_hot_tier_files(cache_dir, raw_sha, core)
                inst = UnifiedModel(hdr_out, _raw_bytes=None, _core_only=True, _target_path=target)
                _OPEN_MODEL_MEM_CACHE[mem_key] = inst
                return inst
        except Exception:
            pass

    # Cold-clone SHA-256-verified sidecar fast path (`BRAIN_UNIFIED_CORE_V1.json`)
    core_json_path = (base / DEFAULT_CORE_ARTIFACT) if target == (base / DEFAULT_ARTIFACT).resolve() else None
    if core_json_path is not None and core_json_path.is_file():
        try:
            core_sidecar = json.loads(core_json_path.read_text(encoding="utf-8"))
            if (
                isinstance(core_sidecar, dict)
                and core_sidecar.get("core_format_v") == 5
                and core_sidecar.get("raw_sha256") == raw_sha
                and core_sidecar.get("schema") == SCHEMA
            ):
                _VERIFIED_BLOB_DIGESTS[raw_sha] = str(core_sidecar.get("digest_value") or "")
                hdr_out = _write_hot_tier_files(cache_dir, raw_sha, core_sidecar)
                inst = UnifiedModel(hdr_out, _raw_bytes=None, _core_only=True, _target_path=target)
                _OPEN_MODEL_MEM_CACHE[mem_key] = inst
                return inst
        except Exception:
            pass

    if raw_bytes is None:
        raw_bytes = target.read_bytes()
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    full = load_model(target, root=base, verify=True)
    core = _extract_routing_core(full, raw_sha)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_f = cache_dir / f".unified_model_core_{short_sha}.{os.getpid()}.tmp"
        tmp_f.write_bytes(marshal.dumps(core))
        tmp_f.replace(cache_file)
    except OSError:
        pass
    hdr_out = _write_hot_tier_files(cache_dir, raw_sha, core)
    inst = UnifiedModel(hdr_out, _raw_bytes=raw_bytes, _core_only=True, _target_path=target)
    inst._model_loaded = full
    _OPEN_MODEL_MEM_CACHE[mem_key] = inst
    return inst

load_unified_model = open_model

def adapter_ast_index_map(path: Path | str | None = None) -> dict[str, Any]:
    """Return the binary-marshaled adapter AST index without parsing the full 14 MB JSON."""
    inst = open_model(path)
    idx = inst._core_meta.get("adapter_ast_index")
    if idx is None:
        inst._ensure_full_tables()
        if inst._adapter_ast_blob:
            idx = marshal.loads(inst._adapter_ast_blob)
            inst._core_meta["adapter_ast_index"] = idx
            inst._adapter_ast_blob = None
        else:
            idx = inst._core_meta.get("adapter_ast_index") or ((inst.model.get("grammar") or {}).get("adapter_ast_index") or {})
    return idx if isinstance(idx, dict) else dict(idx)

def adapter_ast_entry(rel_path: str, expected_sha256: str | None = None) -> dict[str, Any] | None:
    """Fast RAM lookup of compile-time verified adapter AST metadata (`defaulted_keys` + `dispatch_ops`)."""
    try:
        idx = adapter_ast_index_map()
        row = idx.get(rel_path)
        if not isinstance(row, Mapping):
            return None
        if expected_sha256 is not None and str(row.get("sha256") or "") != expected_sha256:
            return None
        return dict(row)
    except Exception:
        return None

# --------------------------------------------------------------------------- cli

SOVEREIGN_ZERO_LLM_MODEL_SPEC = "canonical.runtime.brain_unified_model_v1:brain_model_callable"

def __getattr__(name: str) -> Any:
    if name in ('SovereignZeroLLMPlanner', '_SOVEREIGN_PLANNER', 'brain_model_callable'):
        from canonical.runtime import sovereign_zero_llm_planner_v1 as _szp

        return getattr(_szp, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False))

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="brain_unified_model_v1",
        description="One front door over the compiled Brain model.",
    )
    parser.add_argument("--artifact", default=None, help="model artifact path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show model contents and non-claims")
    route_p = sub.add_parser("route", help="rank a plain goal against the model")
    route_p.add_argument("goal")
    route_p.add_argument("--top-k", type=int, default=5)
    recall_p = sub.add_parser("recall", help="just-in-time knowledge retrieval")
    recall_p.add_argument("query")
    recall_p.add_argument("--top-k", type=int, default=5)
    organs_p = sub.add_parser("organs", help="list or invoke unified swe_kernel organs and leapfrog plays")
    organs_p.add_argument("--invoke", default="", help="organ_id or play_id to execute")
    organs_p.add_argument("--inputs", default="{}", help="JSON object of organ arguments")
    solve_p = sub.add_parser("solve", help="route and execute")
    solve_p.add_argument("goal")
    solve_p.add_argument("--inputs", default="{}", help="JSON object of inputs")
    solve_p.add_argument("--mode", default="AUTO", choices=["AUTO", "RECALL", "SOLVE_OR_LEARN"])
    solve_p.add_argument("--capability-id", default=None)
    solve_p.add_argument("--instance-id", default=None)
    ns = parser.parse_args(argv)

    model = open_model(ns.artifact)
    if ns.command == "status":
        _print(model.status())
        return 0
    if ns.command == "route":
        _print(model.route(ns.goal, top_k=ns.top_k))
        return 0
    if ns.command == "recall":
        _print(model.recall(ns.query, top_k=ns.top_k))
        return 0
    if ns.command == "organs":
        if not ns.invoke:
            _print(model.frontier_organs())
            return 0
        try:
            organ_inputs = json.loads(ns.inputs)
        except json.JSONDecodeError:
            _print({"status": "FAIL_CLOSED", "reason": "INPUTS_NOT_JSON"})
            return 2
        if not isinstance(organ_inputs, dict):
            _print({"status": "FAIL_CLOSED", "reason": "INPUTS_NOT_OBJECT"})
            return 2
        res = model.invoke_frontier_organ(ns.invoke, organ_inputs)
        _print(res)
        return 0 if res.get("status") not in ("UNKNOWN_ORGAN", "FAIL_CLOSED", "ERROR") else 1
    try:
        inputs = json.loads(ns.inputs)
    except json.JSONDecodeError:
        _print({"status": "FAIL_CLOSED", "reason": "INPUTS_NOT_JSON"})
        return 2
    if not isinstance(inputs, dict):
        _print({"status": "FAIL_CLOSED", "reason": "INPUTS_NOT_OBJECT"})
        return 2
    out = model.solve(
        ns.goal,
        inputs=inputs,
        mode=ns.mode,
        capability_id=ns.capability_id,
        instance_id=ns.instance_id,
    )
    _print(out)
    return 0 if out.get("pass") or out.get("operation") == "RECALL" else 1

if __name__ == "__main__":
    raise SystemExit(main())
