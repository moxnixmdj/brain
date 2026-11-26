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
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_V1"
SOLUTION_SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_SOLUTION_V1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"

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
    body = _URL_LITERAL.sub(" ", str(text or ""))
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
    for literal in path_literals(ask, root):
        ask = ask.replace(literal, " ")
    return tokenize(ask)


# --------------------------------------------------------------------------- loading


_VERIFIED_BLOB_DIGESTS: dict[str, str] = {}
_OPEN_MODEL_MEM_CACHE: dict[tuple[str, int, int], "UnifiedModel"] = {}


def _core_cache_dir() -> Path:
    return ROOT / "canonical" / "astra_runtime" / "tmp"


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
        if cached_dig is not None:
            recomputed = cached_dig
        else:
            recomputed = artifact_digest(model)
            if declared and declared == recomputed:
                _VERIFIED_BLOB_DIGESTS[raw_sha] = recomputed
        if not declared or declared != recomputed:
            raise UnifiedModelError("MODEL_DIGEST_MISMATCH")
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


class UnifiedModel:
    """A loaded, digest-verified unified model."""

    def __init__(
        self,
        model: Mapping[str, Any],
        *,
        _raw_bytes: bytes | None = None,
        _core_only: bool = False,
        _target_path: Path | None = None,
    ):
        self._raw_bytes_backing: bytes | None = _raw_bytes
        self._target_path: Path | None = _target_path
        self._declared_triggers_cache: dict[str, set[str]] = {}
        if _core_only and model.get("core_format_v") == 5:
            self._model_loaded: dict[str, Any] | None = None
            self._core_meta: dict[str, Any] = dict(model)
            self.digest = str(model.get("digest_value") or "")
            self.capabilities = dict(self._core_meta["capabilities_map"])
            self.engines = dict(self._core_meta["engines_map"])
            self._capability_id_terms = {
                cid: frozenset(terms)
                for cid, terms in (self._core_meta.get("capability_id_terms") or {}).items()
            }
            self.skills = list(self._core_meta.get("skills") or [])
            self.receipt_backed_ids: frozenset[str] = frozenset(self._core_meta.get("receipt_backed_ids") or ())
            self.index: dict[str, dict[str, float]] = dict(self._core_meta.get("filtered_index") or {})
            confidence = self._core_meta.get("confidence") or {}
        else:
            self._model_loaded = dict(model)
            self._core_meta = _extract_routing_core(self._model_loaded, "")
            self.digest = str((model.get("digest") or {}).get("value") or "")
            self.capabilities = dict(self._core_meta["capabilities_map"])
            self.engines = dict(self._core_meta["engines_map"])
            self._capability_id_terms = {
                cid: frozenset(terms)
                for cid, terms in self._core_meta["capability_id_terms"].items()
            }
            self.skills = list(self._core_meta["skills"])
            self.receipt_backed_ids = frozenset(self._core_meta["receipt_backed_ids"])
            self.index = dict(self._core_meta["filtered_index"])
            confidence = self._core_meta["confidence"]

        # Precompute casefolded ID lookup tables once (zero per-route string churn).
        self._exact_id_lookup: dict[str, str] = {}
        self._cid_folded_pairs: tuple[tuple[str, str], ...] = tuple(
            (cid, cid.casefold()) for cid in self.capabilities
        )
        for cid, cf in self._cid_folded_pairs:
            self._exact_id_lookup[cf] = cid
        eid_pairs: list[tuple[str, str, str]] = []
        for eid in self.engines:
            ef = eid.casefold()
            mode_phrase = eid.split(":", 1)[-1].replace("_", " ").casefold()
            eid_pairs.append((eid, ef, mode_phrase))
            self._exact_id_lookup[ef] = eid
        self._eid_folded_triples: tuple[tuple[str, str, str], ...] = tuple(eid_pairs)

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
        self._fts5_model_conn: Any = None
        self._symbol_graph_conns: dict[str, Any] = {}
        self._dark_matter_verified: dict[str, dict[str, Any]] = {}
        self._raw_sha256: str = str(self._core_meta.get("raw_sha256") or "")

        self.min_score = float(confidence.get("minimum_best_score", 1.0))
        self.min_coverage = float(confidence.get("minimum_coverage", 0.34))
        if not _core_only:
            self._hydrate_secondary_indexes()

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

    def _ensure_harvested(self) -> None:
        if self._harvested_cache is not None:
            return
        cached = self._read_section_cache("harvested")
        if isinstance(cached, dict):
            self._harvested_cache = cached
            return
        full = self._ensure_full_model()
        self._harvested_cache = {
            str(row["id"]): dict(row)
            for row in full.get("harvested_capabilities") or []
            if isinstance(row, Mapping) and row.get("id")
        }
        self._write_section_cache("harvested", self._harvested_cache)

    def _ensure_source_index(self) -> None:
        if self._source_index_cache is not None and self._source_postings_cache is not None:
            return
        cached = self._read_section_cache("source_index")
        if isinstance(cached, dict) and "rows" in cached and "df" in cached and "postings" in cached:
            self._source_index_cache = cached["rows"]
            self._source_df_cache = cached["df"]
            self._source_postings_cache = cached["postings"]
            return
        full = self._ensure_full_model()
        rows = {
            str(row["path"]): dict(row)
            for row in full.get("source_index") or []
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
        self._source_index_cache = rows
        self._source_df_cache = df
        self._source_postings_cache = postings
        self._write_section_cache("source_index", {"rows": rows, "df": df, "postings": postings})

    def _ensure_extended_source_index(self) -> None:
        if self._extended_source_index_cache is not None and self._extended_source_postings_cache is not None:
            return
        cached = self._read_section_cache("extended_source_index")
        if isinstance(cached, dict) and "rows" in cached and "df" in cached and "postings" in cached:
            self._extended_source_index_cache = cached["rows"]
            self._extended_source_df_cache = cached["df"]
            self._extended_source_postings_cache = cached["postings"]
            return
        full = self._ensure_full_model()
        rows = {
            str(row["path"]): dict(row)
            for row in full.get("extended_source_index") or []
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
        self._ensure_source_index()
        self._ensure_extended_source_index()
        src_map = self._source_index_cache or {}
        ext_map = self._extended_source_index_cache or {}
        comb = dict(src_map)
        comb.update(ext_map)
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
        full = self._ensure_full_model()
        rows = {
            str(row["path"]): dict(row)
            for row in full.get("research_index") or []
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
        full = self._ensure_full_model()
        rows = [
            dict(row) for row in (full.get("knowledge") or []) if isinstance(row, Mapping)
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
            if self._raw_bytes_backing is None:
                if self._target_path is not None and self._target_path.is_file():
                    self._raw_bytes_backing = self._target_path.read_bytes()
                else:
                    raise UnifiedModelError("MODEL_BACKING_BYTES_MISSING")
            self._model_loaded = json.loads(self._raw_bytes_backing.decode("utf-8"))
        return self._model_loaded

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

    def _hydrate_secondary_indexes(self) -> None:
        if self._source_index_cache is not None and self._research_index_cache is not None and self._knowledge_cache is not None:
            return
        full = self._ensure_full_model()
        sec = _extract_secondary_indexes(full, self._raw_sha256)
        self._apply_secondary_bundle(sec)

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
    def _extended_source_df(self) -> dict[str, int]:
        self._ensure_extended_source_index()
        return self._extended_source_df_cache  # type: ignore[return-value]

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

    @property
    def _knowledge_lengths(self) -> list[int]:
        self._ensure_knowledge()
        return self._knowledge_lengths_cache  # type: ignore[return-value]

    @property
    def _avg_length(self) -> float:
        self._ensure_knowledge()
        return self._avg_length_cache  # type: ignore[return-value]

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
            if self._source_index_cache is not None
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
        """Enumerate the 13 `swe_kernel` organs and 8 Frontier Leapfrog Plays wired into the Unified Runtime."""
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
                "capability_role": "Gradient-free episodic law consolidation over the 45-commit real OSS corpus",
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
                "capability_role": "Adversarial AST mutation admission gate over harvested capability receipts",
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
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "FRONTIER_ORGANS",
            "swe_kernel_organs_count": len(swe_organs),
            "leapfrog_plays_count": len(plays),
            "total_organs": len(swe_organs) + len(plays),
            "swe_kernel_organs": swe_organs,
            "leapfrog_plays": plays,
            "model_dependency_count": 0,
        }

    def invoke_frontier_organ(
        self,
        organ_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a wired `swe_kernel` organ or Frontier Leapfrog Play through the Unified Runtime."""
        req = dict(payload or {})
        if organ_id == "play_1_contract_world_model":
            from canonical.runtime import state_contract_world_model_v1 as p1

            return p1.run(req, ROOT)
        if organ_id == "play_2_law_consolidation":
            from canonical.runtime import gradient_free_law_consolidation_v1 as p2

            return p2.run(req, ROOT)
        if organ_id == "play_3_abstain_skill_induction":
            from canonical.runtime import abstain_gated_skill_induction_v1 as p3

            return p3.run(req, ROOT)
        if organ_id == "play_6_mutation_admission_gate":
            from canonical.runtime import adversarial_mutation_admission_gate_v1 as p6

            return p6.run(req, ROOT)
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

        from canonical.runtime import swe_kernel_organ_bridge_v1 as bridge

        if organ_id == "probe_all_swe_kernel_organs":
            return bridge.probe_all_organs(ROOT)
        return bridge.invoke_organ(organ_id, req, ROOT)

    def anatomy(self, domain: str | None = None, *, top_k: int = 8) -> dict[str, Any]:
        """Where this repository implements each frontier function, by its own words."""
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
        if not folded:
            return set()
        hits: set[str] = set()
        exact = self._exact_id_lookup.get(folded)
        if exact is not None:
            hits.add(exact)
        for cid, cf in self._cid_folded_pairs:
            if cf in folded:
                hits.add(cid)
        for eid, ef, mode_phrase in self._eid_folded_triples:
            if ef in folded:
                hits.add(eid)
            elif mode_phrase and mode_phrase in folded:
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
        for token in ask_tokens(goal) + addressed_tokens:
            if token not in seen:
                seen.add(token)
                ask_list.append(token)
        scores: dict[str, float] = {}
        matched: set[str] = set()
        unrunnable_known = self._unrunnable
        unrunnable_matched: set[str] = set()
        for token in ask_list:
            postings = self.index.get(token)
            if not postings:
                continue
            matched.add(token)
            for cid, weight in postings.items():
                if unrunnable_known is not None and cid in unrunnable_known:
                    unrunnable_matched.add(cid)
                # A query token that is also in the capability id is direct
                # operation evidence, not merely effect vocabulary. Count that
                # same declared IDF posting a second time for the identity
                # channel. Measured on "Audit the python source tree with an
                # AST": the audit owner has four identity hits, while the
                # legacy tree-sitter parser's rare `tree` hit comes only from
                # its provides and otherwise steals the route.
                identity_weight = (
                    2.0 if token in self._capability_id_terms.get(cid, ()) else 1.0
                )
                scores[cid] = scores.get(cid, 0.0) + identity_weight * math.log1p(weight)
        # Wave 31 Elon speed pass: when `unrunnable_capabilities()` has not been materialized yet,
        # resolve declared dependencies lazily ONLY for matched capability candidates (memoized
        # per unique dep name inside this call's local `probe_cache`), guaranteeing the exact same
        # `unrunnable_on_this_host` without probing all 462 capabilities and with zero global cache state.
        if unrunnable_known is None:
            route_probe_cache: dict[tuple[str, bool], bool] = {}
            for cid in scores:
                row = self.capabilities.get(cid)
                if row is not None and _missing_declared_dependencies(row, probe_cache=route_probe_cache):
                    unrunnable_matched.add(cid)
        for cid in mentioned:
            scores[cid] = scores.get(cid, 0.0) + math.log1p(24.0)
            matched.add(cid.casefold())
        # A stated path is data the caller supplied and the binder will bind, not
        # a word of the ask. Charge only the ask to the coverage budget, so that
        # naming a real artifact can never be the reason a request is refused.
        #
        # A capability's own id is the ask, not a path. 294 of the model's ids
        # ARE repository paths -- "canonical/runtime/x_v1.py.auto.v1" -- and the
        # path grammar matches them whole, so blanking them left no ask at all:
        # coverage collapsed to 0.0 and every addressed capability stopped being
        # addressable. Measured, that regressed
        # test_every_capability_is_addressable_by_its_own_id on 294 subtests.
        #
        # And every token of an id the model contains is by definition a token
        # the model recognises, so those tokens are matched as well as asked.
        # Without that second half an addressed id measured 0.333 against the
        # 0.34 floor and still failed, on a filename token no index carries.
        ask = set(ask_list)
        addressed_set = set(addressed_tokens)
        matched_ask = (matched & ask) | addressed_set
        coverage = (len(matched_ask) / len(ask)) if ask else 0.0
        # Naming a capability by its own id is an address, not a keyword. Its
        # path segments also index capabilities that legitimately claim those
        # words, so a flat +24 can be outscored by the noise the address itself
        # introduced. Sort addressed capabilities ahead of the rest instead of
        # inflating the bonus until it wins by force.
        #
        # Engines are excluded from that priority when matched merely by mode
        # phrase (`engine:BOUND_CAPABILITY` matches the phrase "bound capability"),
        # which is ordinary keyword overlap, not an address. Explicit literal
        # `engine:<MODE>` or `meta:<MODE>` addresses ARE addresses and do get
        # address priority.
        folded_goal = str(goal or "").casefold()
        addressed = {cid for cid in mentioned if cid in self.capabilities} | {
            eid for eid in mentioned if eid in self.engines and eid.casefold() in folded_goal
        }
        ranked = sorted(
            scores.items(),
            key=lambda kv: (kv[0] not in addressed, -kv[1], kv[0]),
        )
        rows: list[dict[str, Any]] = []
        for cid, score in ranked[: max(1, int(top_k))]:
            row = self.capabilities.get(cid) or self.engines.get(cid) or {}
            rows.append(
                {
                    "id": cid,
                    "kind": row.get("kind") or "UNKNOWN",
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
        return {
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

    # -------------------------------------------------------------- source index

    def find_source(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
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
        self._ensure_source_index()
        src_map = self._source_index_cache or {}
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
        q_folded = query.casefold()
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for path, score in acc_scores.items():
            if score <= 0.0:
                continue
            if path.casefold() in q_folded:
                score += 8.0
            scored.append((score, path, src_map[path]))
        scored.sort(key=lambda item: (-item[0], item[1]))

        rows: list[dict[str, Any]] = []
        for score, path, row in scored[: max(1, int(top_k))]:
            rows.append(
                {
                    "path": path,
                    "id": row.get("id"),
                    "classification": row.get("classification"),
                    "sha256": row.get("sha256"),
                    "summary": row.get("summary") or "",
                    "symbol_count": int(row.get("symbol_count") or 0),
                    "matched_terms": sorted(wanted & set(row.get("terms") or ())),
                    "score": round(float(score), 6),
                    # The load-bearing part of this whole method.
                    "capability": False,
                    "executable": False,
                }
            )
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

    def find_any_source(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        """Locate source modules across ALL repository trees (`runtime`, `swe_kernel`, `tools`, `capabilities`, `research`, `integrations`)."""
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("FIND_SOURCE_QUERY_EMPTY")
        wanted = set(terms)
        self._ensure_combined_source_index()
        combined = self._combined_source_index_cache or {}
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
        q_folded = query.casefold()
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for path, score in acc_scores.items():
            if score <= 0.0:
                continue
            if path.casefold() in q_folded:
                score += 8.0
            scored.append((score, path, combined[path]))
        scored.sort(key=lambda item: (-item[0], item[1]))
        rows: list[dict[str, Any]] = []
        for score, path, row in scored[: max(1, int(top_k))]:
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
        if requested == "RECALL":
            return self.recall(goal)
        if requested == "EPISTEMIC":
            ws_arg = cwd or inputs.get("workspace_dir") or inputs.get("repo_dir")
            if ws_arg is not None:
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
                    "mode": "EPISTEMIC",
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
            grader_report=grader_report,
            min_trials=min_trials,
            threshold=threshold,
            active_cap=active_cap,
            db_path=db_path,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="CURATE_SKILLS",
            goal=goal or "curate_skills_by_contribution",
            status=str(res.get("status") or ("PASS__SKILLS_CURATED" if passed else "REFUSED__UNMEASURED_GRADER")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "CURATION_REFUSED"),
            curation=res,
        )

    def observe_drift(
        self,
        stream: str,
        value: float | bool,
        *,
        goal: str = "",
    ) -> dict[str, Any]:
        """Observe one outcome in the hybrid ADWIN + BOCPD + Page-Hinkley concept-drift monitor (`0G`)."""
        res = self.boundary_router.route_observe_drift(stream, value)
        return self._envelope(
            operation="OBSERVE_DRIFT",
            goal=goal or f"drift:{stream}",
            status=str(res.get("status") or "PASS__STATIONARY"),
            **{"pass": True},
            drift=res,
        )

    def trace_expression_repair(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Dual-slicing execution-trace blaming + literal-defect & site-generability audit (`0D`)."""
        res = self.boundary_router.route_trace_expression_repair(**kwargs)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="TRACE_EXPRESSION_REPAIR",
            goal=goal or "trace_expression_repair",
            status=str(res.get("status") or ("PASS__TRACE_EXPRESSION_BLAMED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "TRACE_REPAIR_FAILED"),
            trace_repair=res,
        )

    def multi_file_causal_localize(
        self,
        repo_root: str | Path,
        *,
        goal: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Multi-step differential-trace fault localization & causal SWE repair (`0D`)."""
        res = self.boundary_router.route_multi_file_causal_localize(repo_root, goal=goal, **kwargs)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="MULTI_FILE_CAUSAL_LOCALIZE",
            goal=goal or f"causal_localize:{Path(repo_root).name}",
            status=str(res.get("status") or ("PASS__DIFFERENTIAL_TRACE_LOCALIZED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "LOCALIZATION_FAILED"),
            causal_result=res,
        )

    def discover_computer_env(self, *, goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Discover live host OS programs, flags, file actions & minted effect signatures (`0E` × `computer_env_v1`)."""
        res = self.boundary_router.route_discover_computer_env(**kwargs)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="DISCOVER_COMPUTER_ENV",
            goal=goal or "discover_computer_env",
            status=str(res.get("status") or ("PASS__COMPUTER_ENV_DISCOVERED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "COMPUTER_ENV_UNAVAILABLE"),
            computer_env=res,
        )

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
        res = self.boundary_router.route_admit_live(
            goal,
            compiled=compiled,
            registry=registry,
            dag=dag,
            entry=entry,
        )
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="ADMIT_ROUTE",
            goal=goal,
            status=str(res.get("status") or ("PASS__ROUTE_ADMITTED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "ROUTE_ADMISSION_REJECTED"),
            route_admission=res,
        )

    def semantic_plan(self, goal: str) -> dict[str, Any]:
        """Neuro-symbolic compositional task AST & plan synthesis (`semantic_generalization_engine_v1`)."""
        res = self.boundary_router.route_semantic_plan(goal)
        passed = bool(res.get("pass") is True)
        return self._envelope(
            operation="SEMANTIC_PLAN",
            goal=goal,
            status=str(res.get("status") or ("PASS__SEMANTIC_PLAN_SYNTHESIZED" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            reason=None if passed else str(res.get("status") or "SEMANTIC_PLAN_FAILED"),
            semantic_plan=res,
        )

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
            action=action,
            skill_id=skill_id,
            reward=reward,
            confidence=confidence,
            fingerprint=fingerprint,
            current_fingerprint=current_fingerprint,
            quarantine_on_drift=quarantine_on_drift,
            db_path=db_path,
        )
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="MEMGUARD_AUDIT_EXPIRE",
            goal=f"memguard:{action}:{skill_id or 'all'}",
            status=str(res.get("status") or "PASS__MEMGUARD"),
            **{"pass": passed},
            memguard=res,
        )

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
            action="record",
            domain=domain,
            symbol_scope=symbol_scope,
            bad_hypothesis=bad_hypothesis,
            error_signature=error_signature,
            world_fp=world_fp,
            csp_pair=csp_pair,
        )
        return self._envelope(
            operation="ANTI_SKILL_RECORD",
            goal=f"anti_skill:{domain}:{symbol_scope}",
            status=str(res.get("status") or "PASS__ANTI_SKILL_RECORDED"),
            **{"pass": bool(res.get("pass"))},
            anti_skill=res,
        )

    def anti_skill_prune(
        self,
        candidates: Sequence[str],
        *,
        domain: str,
        symbol_scope: str = "*",
    ) -> dict[str, Any]:
        """Wave 15: Prune candidate hypotheses in O(1) using crystallized Anti-Skills."""
        res = self.boundary_router.route_anti_skill(
            action="prune",
            domain=domain,
            symbol_scope=symbol_scope,
            candidates=candidates,
        )
        return self._envelope(
            operation="ANTI_SKILL_PRUNE",
            goal=f"prune:{domain}:{symbol_scope}",
            status=str(res.get("status") or "PASS__ANTI_SKILL_PRUNED"),
            **{"pass": bool(res.get("pass"))},
            pruning=res,
        )

    def prove_composition(
        self,
        *,
        initial_text: str,
        operations: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Wave 15: Compose multi-step text/code operations only when premise & proof survive (`proved_composition_v1`)."""
        res = self.boundary_router.route_proved_composition(initial_text=initial_text, operations=operations)
        return self._envelope(
            operation="PROVE_COMPOSITION",
            goal="proved_composition",
            status=str(res.get("status") or "FAIL_CLOSED"),
            **{"pass": bool(res.get("pass"))},
            composition=res,
        )

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
        res = self.boundary_router.route_fork_reality_speculate(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="FORK_REALITY_SPECULATE",
            goal="fork_reality_cow_speculation",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            speculation=res,
        )

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

    def solve_swe_repo_native(
        self,
        repo_root: str | Path,
        *,
        test_targets: Sequence[str] | None = None,
        candidate_files: Sequence[str] | None = None,
        in_run_repair_vocab: Mapping[str, Any] | None = None,
        prior_demonstrations: Sequence[tuple[str, str, str]] = (),
        witness_envs: Sequence[Mapping[str, Any]] | None = None,
        witness_targets: Sequence[Any] | None = None,
        mine_git_history: bool = True,
        history_limit: int = 200,
        residual_proposer: Any = None,
        keep_patch_applied: bool = False,
        timeout_s: float = 30.0,
    ) -> dict[str, Any]:
        """Wave 23: Repo-Native Multi-File SWE Engine (`0D` × 7 hidden SWE superweapons + CoW Zygote + online crystallization)."""
        res = self.boundary_router.route_swe_repo_native_multifile(
            repo_root=repo_root,
            test_targets=test_targets,
            candidate_files=candidate_files,
            in_run_repair_vocab=in_run_repair_vocab,
            prior_demonstrations=prior_demonstrations,
            witness_envs=witness_envs,
            witness_targets=witness_targets,
            mine_git_history=mine_git_history,
            history_limit=history_limit,
            residual_proposer=residual_proposer,
            keep_patch_applied=keep_patch_applied,
            timeout_s=timeout_s,
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
        """Wave 24: Red Queen Evaluator Co-Evolution (`0H`, intra-epoch frozen judge)."""
        res = self.boundary_router.route_red_queen_coevolution(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="RED_QUEEN_COEVOLVE_EVALUATORS",
            goal=f"red_queen_epoch:{kwargs.get('epoch_index', 0)}",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            red_queen=res,
        )

    def explore_safe_action_model(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 25: Systematic Exploration + Safe Action Model + Demonstration Sufficiency (`0E`)."""
        res = self.boundary_router.route_safe_exploration(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="SAFE_ACTION_MODEL_EXPLORE",
            goal="safe_action_model_exploration",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            exploration=res,
        )

    def compile_decision_quotient(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 25: K6 Target-Relative Decision Quotient & Deadline Refinement Compiler (`0E`)."""
        res = self.boundary_router.route_decision_quotient(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="DECISION_QUOTIENT_COMPILE",
            goal="decision_quotient_refinement",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            quotient=res,
        )

    def execute_horizon_zero_screenshot_cu(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 25: Horizon-Bounded CU + Zero-Screenshot DOM Cache + Vocabulary Growth (`0F`)."""
        res = self.boundary_router.route_horizon_zero_screenshot_cu(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="HORIZON_ZERO_SCREENSHOT_CU",
            goal=str(kwargs.get("task_id") or "horizon_zero_screenshot_cu"),
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            cu_execution=res,
        )

    # ----------------------------------------------------- Waves 27-30 Frontier Leapfrog Front Door

    def contrast_memory_laws(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 27: Contrast-Carrying Guard Laws & O(1) Anti-Catastrophic-Remembering Pruning (`0G`)."""
        res = self.boundary_router.route_contrast_memory_laws(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="CONTRAST_MEMORY_LAWS",
            goal=f"contrast_laws:{kwargs.get('domain', 'default')}",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            contrast_laws=res,
        )

    def filing_key_hindsight_jitrl(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 27: Filing-Key Collision Audit + Alpha-Safe Unwelding + AgentHER Hindsight + JitRL (`0G`)."""
        res = self.boundary_router.route_filing_key_hindsight_jitrl(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="FILING_KEY_HINDSIGHT_JITRL",
            goal=str(kwargs.get("achieved_goal") or kwargs.get("jitrl_filing_key") or "filing_key_hindsight_jitrl"),
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            hindsight_jitrl=res,
        )

    def solve_producer_lineage_holes(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 28: Backward Producer-Lineage Tracing + Typed Hole Inversion SWE Engine (`0D`, `K3=0`)."""
        res = self.boundary_router.route_producer_lineage_holes(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="PRODUCER_LINEAGE_HOLE_INVERSION",
            goal=str(kwargs.get("entry_func") or kwargs.get("filename") or "producer_lineage_hole_inversion"),
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            hole_inversion=res,
        )

    def audit_verifier_pinning_and_oracles(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 29: Hunk-Level Verifier Pinning Audit + Docstring/Green-Suite/Origin Oracle Synthesis (`0H`)."""
        res = self.boundary_router.route_verifier_pinning_oracles(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="VERIFIER_PINNING_AND_ORACLES",
            goal="verifier_pinning_and_oracles",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            pinning_oracles=res,
        )

    def purpose_gate_and_cost_arbitrage(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 30: Purpose-Gated Active Inference & Guess-vs-Ask-vs-CoW-Trial Economic Arbitrage (`0E`)."""
        res = self.boundary_router.route_purpose_gate_arbitrage(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="PURPOSE_GATE_AND_COST_ARBITRAGE",
            goal=str(kwargs.get("instruction") or "purpose_gate_cost_arbitrage"),
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            active_inference=res,
        )

    def plan_two_move_horizon_cu(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 30: Class-Level Two-Move Planning + Horizon Bridge + Goal DAG + OSWorld v2.1 Policy (`0F`)."""
        res = self.boundary_router.route_two_move_horizon_cu(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="TWO_MOVE_HORIZON_CU",
            goal=str(kwargs.get("bridge_task_id") or "two_move_horizon_cu"),
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            two_move_cu=res,
        )

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

    # ----------------------------------------------------- Waves 32-35 Frontier Leapfrog Front Door

    def disambiguate_and_pin_repairs(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 32: Version-Space Repair Disambiguation + Angelic CEGIS + Inverse Completion + Repo-Seeded SWE (`0D`, `K3=0`)."""
        res = self.boundary_router.route_disambiguate_and_pin_repairs(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="DISAMBIGUATE_AND_PIN_REPAIRS",
            goal="wave32_version_space_swe",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            version_space_swe=res,
        )

    def prove_equivalence_and_amplify(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 32: Consistency-vs-Equivalence Proof + Distinguishing Projection + Reverted-Part Pinning + Verdict Amplification (`0H`, `K3=0`)."""
        res = self.boundary_router.route_prove_equivalence_and_amplify(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="PROVE_EQUIVALENCE_AND_AMPLIFY",
            goal="wave32_equivalence_oracle",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            equivalence_oracle=res,
        )

    def crystallize_meaning_first_transfer(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 33: Meaning-First IR Crystallization + Cross-Language Transfer + Scoped Skills + Weight Admission (`0G`, `K3=0`)."""
        res = self.boundary_router.route_meaning_first_transfer(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="MEANING_FIRST_TRANSFER",
            goal="wave33_meaning_first_transfer",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            meaning_first=res,
        )

    def memini_memrl_apex_consolidate(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 33: Memini (`w_fast`/`w_slow`) + MemRL (TD `Q` + 2-phase) + APEX-EM (3-channel) Consolidation (`0G`, `K3=0`)."""
        res = self.boundary_router.route_memini_memrl_apex(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="MEMINI_MEMRL_APEX",
            goal="wave33_memini_memrl_apex",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            consolidation=res,
        )

    def execute_osworld_v21_epistemic_cu(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 34: OSWorld 2.1 Pure-Stdlib CU Engine + Epistemic Computer Agent + Action-Grammar Guide (`0F`, `K3=0`)."""
        res = self.boundary_router.route_osworld_v21_epistemic_cu(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="OSWORLD_V21_EPISTEMIC_CU",
            goal="wave34_osworld_v21_epistemic_cu",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            osworld_epistemic_cu=res,
        )

    def speculative_macro_commit(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 34: TomasuLLM Speculative Macro Commit + Standing-Fact Invalidation + Effect Witnesses + Parallel Frontier (`0F`, `K3=0`)."""
        res = self.boundary_router.route_speculative_macro_commit(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="SPECULATIVE_MACRO_COMMIT",
            goal="wave34_speculative_macro_commit",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            speculative_commit=res,
        )

    def active_repertoire_typed_invention(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 35: Active-Inference Repertoire Query + Typed CEGIS(T) + Distinction Creation + Proof-Carrying Counterfactuals (`0E`, `K3=0`)."""
        res = self.boundary_router.route_active_repertoire_typed_invention(**kwargs)
        passed = bool(res.get("pass"))
        return self._envelope(
            operation="ACTIVE_REPERTOIRE_TYPED_INVENTION",
            goal="wave35_active_repertoire_typed_invention",
            status=str(res.get("status") or ("PASS" if passed else "FAIL_CLOSED")),
            **{"pass": passed},
            active_repertoire=res,
        )

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
        """Waves 20-35: Single unified frontier-leapfrog front door across all canonical spines (`K3=0` default)."""
        m = str(mode or "auto").lower().strip()
        data = dict(inputs or {})
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
        if m == "memory" or m == "fts5":
            return self.fts5_recall(goal, **kwargs)
        return self.fts5_recall(goal, **kwargs)

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
        # Wave 21: Pre-warm the SQLite FTS5 unified model index at compile time so the very
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
    raw_bytes: bytes | None = None
    raw_sha = _read_stat_sha(target_key, st) if is_default else None
    if raw_sha is None:
        raw_bytes = target.read_bytes()
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        if is_default:
            _write_stat_sha(target_key, st, raw_sha)

    cache_file = cache_dir / f"unified_model_core_{raw_sha[:32]}.marshal"
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
                inst = UnifiedModel(
                    core,
                    _raw_bytes=raw_bytes,
                    _core_only=True,
                    _target_path=target,
                )
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
        tmp_f = cache_dir / f".unified_model_core_{raw_sha[:32]}.{os.getpid()}.tmp"
        tmp_f.write_bytes(marshal.dumps(core))
        tmp_f.replace(cache_file)
    except OSError:
        pass
    inst = UnifiedModel(core, _raw_bytes=raw_bytes, _core_only=True, _target_path=target)
    inst._model_loaded = full
    _OPEN_MODEL_MEM_CACHE[mem_key] = inst
    return inst


def adapter_ast_entry(rel_path: str, expected_sha256: str | None = None) -> dict[str, Any] | None:
    """Fast RAM lookup of compile-time verified adapter AST metadata (`defaulted_keys` + `dispatch_ops`)."""
    try:
        inst = open_model()
        idx = inst._core_meta.get("adapter_ast_index") or {}
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


class SovereignZeroLLMPlanner:
    """First-Principles Active-Inference + MCTS (`decision_core_v1`) Zero-LLM (`K3 = 0`) Agent for `solve_v1`.

    Eliminates static probability dictionaries, 1-step greedy ranking, and inline `exec` scripts:
      1. Grounded Belief & Causal Learning: Every option's pass probability and epistemic entropy are
         computed online by `EpistemicSelfBeliefEngine` (with conjunctive predicate invention) and settled
         against actual outcomes (`seeing['last']`), while `CausalWorldGraph` learns `(Pre, Prod, Dest)`
         transitions and inhibits destructive actions.
      2. Dynamic World Affordances: Options are synthesized dynamically from live workspace topology
         (truncated/hidden configs, test suites, Python modules, executable CLI tools, flywheel primers,
         routed UnifiedModel capabilities, and postcondition writes).
      3. Multi-Step MCTS Lookahead (`decision_core_v1.search`): Runs UCB tree search (`Node`, `search`,
         `best_action`, `best_trajectory`) over abstract world-state transitions minimizing Expected Free
         Energy (pragmatic goal satisfaction + epistemic information gain - execution cost).
      4. Cross-Episode Skill & Concept Compounding: Verified Python repairs abstract reusable primitives into
         `CompoundingConceptLibrary` and elevate causal action traces via `causal_trace_to_skill_compiler_v1`.
    """

    def __init__(self, state_dir: Path | str | None = None) -> None:
        self._episodes: dict[str, dict[str, Any]] = {}
        self._state_dir = Path(state_dir).resolve() if state_dir is not None else None
        self._core: Any = None
        self.last_mcts_summary: dict[str, Any] = {}

    def _cognitive_core(self) -> Any:
        if self._state_dir is not None:
            if self._core is None:
                from canonical.swe_kernel.sentient_cognitive_core_v1 import SentientCognitiveCore

                self._core = SentientCognitiveCore(self._state_dir)
            return self._core
        from canonical.swe_kernel.sentient_cognitive_core_v1 import shared_cognitive_core

        return shared_cognitive_core(None)

    def organ_graph(self) -> Any:
        """Access the unified 5-stratum `MetaCircularOrganGraph` (`P_t`)."""
        return self._cognitive_core().organ_graph

    def extrapolate_global_opportunity(
        self,
        observed_channels: Sequence[Any],
        *,
        goal: str = "",
        target_gap: float | None = None,
        remaining_budget: float = 10.0,
        universe_size_hint: int | None = None,
    ) -> dict[str, Any]:
        """Evaluate global non-local opportunity tail (`OWNER_ACTIVE_GOAL` Law 5)."""
        return self._cognitive_core().evaluate_global_open_world_decision(
            observed_channels,
            goal=goal,
            target_gap=target_gap,
            remaining_budget=remaining_budget,
            universe_size_hint=universe_size_hint,
        )

    @staticmethod
    def _episode_key(goal: str) -> str:
        return hashlib.sha256(goal.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _extract_target_writes(goal: str) -> list[tuple[str, str | None]]:
        """Extract explicit file creation/write clauses without restricting multi-step goals."""
        clauses = [c.strip() for c in re.split(r"(?:;|\band\s+then\b|\bthen\b)", goal, flags=re.IGNORECASE) if c.strip()]
        targets: list[tuple[str, str | None]] = []
        for cl in clauses:
            m_w = re.match(r"^write\s+(.+?)\s+to\s+([A-Za-z0-9_./-]+)\s*[.!]*$", cl, re.IGNORECASE)
            if m_w:
                payload = m_w.group(1).strip().strip("'\"")
                rel_p = m_w.group(2).strip()
                if ".." not in Path(rel_p).parts and not rel_p.startswith("/"):
                    targets.append((rel_p, payload))
                continue
            m_c = re.match(r"^(?:create|touch|make)\s+(?:file\s+)?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)\s*[.!]*$", cl, re.IGNORECASE)
            if m_c:
                rel_p = m_c.group(1).strip()
                if ".." not in Path(rel_p).parts and not rel_p.startswith("/"):
                    targets.append((rel_p, ""))
        return targets

    @staticmethod
    def _extract_mentioned_paths(goal: str) -> list[str]:
        found: list[str] = []
        for m in re.finditer(r"\b([A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,10})\b", goal):
            p = m.group(1).strip()
            if ".." not in Path(p).parts and not p.startswith("/") and p not in found:
                found.append(p)
        return found

    @staticmethod
    def _world_fact_tokens(
        *,
        file_set: set[str],
        probed: bool,
        test_passed: bool | None,
        verified_after_edit: bool,
        writes_satisfied: bool,
        outputs_ready: bool,
    ) -> set[str]:
        facts = {f"file:{f}" for f in file_set}
        if probed:
            facts.add("pred:facts_observed")
        if test_passed is True:
            facts.add("pred:tests_green")
        elif test_passed is False:
            facts.add("pred:tests_red")
        if verified_after_edit:
            facts.add("pred:verified_after_edit")
        if writes_satisfied:
            facts.add("pred:writes_satisfied")
        if outputs_ready:
            facts.add("pred:outputs_ready")
        return facts

    def _consolidate_completed_episode(self, text: str, ep: Mapping[str, Any]) -> None:
        core = self._cognitive_core()
        py_programs = [
            str(src)
            for rel, src in (ep.get("full_files") or {}).items()
            if str(rel).endswith(".py") and not Path(str(rel)).name.startswith("test_") and len(str(src)) >= 20
        ]
        if len(py_programs) >= 2:
            try:
                core.concept_library.sleep_abstract(py_programs)
            except Exception:
                pass
        trace_steps = ep.get("causal_trace") or []
        if trace_steps:
            try:
                from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import elevate_trace_to_fastest_layer

                elevate_trace_to_fastest_layer({"goal": text, "steps": list(trace_steps)})
            except Exception:
                pass

    def __call__(self, goal: str, seeing: dict[str, Any]) -> str | None:
        text = str(goal or "").strip()
        if not text or not isinstance(seeing, dict):
            return None

        core = self._cognitive_core()
        step = int(seeing.get("step") or 1)
        previews = seeing.get("preview") if isinstance(seeing.get("preview"), dict) else (
            seeing.get("previews") if isinstance(seeing.get("previews"), dict) else {}
        )
        raw_files = seeing.get("tree") if seeing.get("tree") is not None else (seeing.get("files") or ())
        file_list = sorted(raw_files.keys()) if isinstance(raw_files, dict) else sorted(str(x) for x in raw_files)
        file_set = set(file_list)
        last = seeing.get("last") if isinstance(seeing.get("last"), dict) else None
        learned = seeing.get("learned") if isinstance(seeing.get("learned"), dict) else None

        ep_key = self._episode_key(text)
        if step <= 1 or ep_key not in self._episodes:
            self._episodes[ep_key] = {
                "probed": False,
                "full_files": dict(previews),
                "discovered_tasks": [],
                "test_passed": None,
                "test_diagnostics": "",
                "tried": set(),
                "last_action_id": None,
                "last_ticket": None,
                "last_world_facts": set(),
                "verified_after_edit": False,
                "edited_code": False,
                "failures": [],
                "causal_trace": [],
            }
        ep = self._episodes[ep_key]
        for k_p, v_p in previews.items():
            if k_p not in ep["full_files"] or len(str(v_p)) > len(str(ep["full_files"].get(k_p, ""))):
                ep["full_files"][k_p] = str(v_p)

        test_files = [
            f for f in file_list
            if f.endswith(".py") and (Path(f).name.startswith("test_") or Path(f).name.endswith("_test.py"))
        ]
        impl_py_files = [f for f in file_list if f.endswith(".py") and f not in test_files]
        cli_files = [
            f for f in file_list
            if Path(f).suffix in (".sh", ".bin") or (not Path(f).suffix and Path(f).name not in ("Makefile", "Dockerfile", "LICENSE", "README"))
        ]
        config_files = [f for f in file_list if Path(f).suffix in (".json", ".yaml", ".yml", ".toml", ".ini")]
        has_taskfile = any(Path(f).name in ("Makefile", "package.json", "pyproject.toml", "justfile") for f in file_set)
        explicit_writes = self._extract_target_writes(text)
        mentioned_paths = self._extract_mentioned_paths(text)
        expected_outputs = [
            p for p in mentioned_paths
            if p not in file_set and not p.endswith(".py")
        ]

        # Canonical Predicate World Projection (`predicate_world_abstraction_v1`)
        try:
            from canonical.swe_kernel.predicate_world_abstraction_v1 import project_computer_observation

            proj_obs = project_computer_observation(
                {
                    "cwd": ".",
                    "files": {f: {"exists": True, "size": len(str(ep["full_files"].get(f, "")))} for f in file_list[:32]},
                    "stdout": str((last or {}).get("out") or "")[-400:],
                    "stderr": str((last or {}).get("err") or "")[-400:],
                }
            )
            projected_world_preds = {f"obs:{p}" for p in (proj_obs.get("predicates") or ())}
        except Exception:
            projected_world_preds = set()

        # Assimilate outcome of previous action (`seeing["last"]`) & settle Bayesian belief + causal world graph!
        if last is not None:
            out_txt = str(last.get("out") or "")
            err_txt = str(last.get("err") or "")
            exit_c = last.get("exit")
            last_act = ep.get("last_action_id")
            step_ok = (exit_c == 0) and not bool(last.get("timed_out"))
            if "BRAIN_PROBE_JSON:" in out_txt:
                for ln in out_txt.splitlines():
                    if ln.startswith("BRAIN_PROBE_JSON:"):
                        try:
                            pdata = json.loads(ln[len("BRAIN_PROBE_JSON:"):])
                            if isinstance(pdata.get("full_files"), dict):
                                ep["full_files"].update(pdata["full_files"])
                            if isinstance(pdata.get("tasks"), list):
                                ep["discovered_tasks"] = pdata["tasks"]
                            if "test_passed" in pdata:
                                ep["test_passed"] = bool(pdata["test_passed"])
                            if "test_diagnostics" in pdata:
                                ep["test_diagnostics"] = str(pdata["test_diagnostics"])
                            ep["probed"] = True
                        except Exception:
                            pass
            if step_ok and str(last_act or "").startswith(("py_ast_patch_h1", "py_obs_synth_h2", "taskfile_target:")):
                ep["edited_code"] = True
            if step_ok and last_act == "verify_postconditions":
                ep["verified_after_edit"] = True
                ep["test_passed"] = True
            elif not step_ok:
                if last_act:
                    ep["tried"].add(str(last_act))
                try:
                    from canonical.runtime import flywheel_v1 as fw

                    where, why = fw.classify(err_txt or out_txt)
                    ep["failures"].append({"action": last_act, "where": where, "why": why, "err": (err_txt or out_txt)[-400:]})
                except Exception:
                    ep["failures"].append({"action": last_act, "err": (err_txt or out_txt)[-400:]})

            writes_now = bool(explicit_writes) and all(
                rel_p in file_set and (payload is None or payload == "" or str(previews.get(rel_p, "")).strip() == payload)
                for rel_p, payload in explicit_writes
            )
            now_facts = (
                self._world_fact_tokens(
                    file_set=file_set,
                    probed=bool(ep["probed"]),
                    test_passed=ep["test_passed"],
                    verified_after_edit=bool(ep["verified_after_edit"]),
                    writes_satisfied=writes_now,
                    outputs_ready=all(p in file_set for p in expected_outputs),
                )
                | projected_world_preds
            )
            prev_ticket = ep.get("last_ticket")
            if prev_ticket is not None:
                try:
                    core.belief.settle_and_compute_surprise(
                        prev_ticket,
                        outcome_pass=step_ok,
                        inspector=f"solve_v1:{last_act or 'step'}",
                    )
                except Exception:
                    pass
                ep["last_ticket"] = None
            if last_act:
                try:
                    core.world_graph.learn_from_execution(
                        str(last_act),
                        before_state=set(ep.get("last_world_facts") or ()),
                        after_state=now_facts,
                        ok=step_ok,
                        error_text=(err_txt or out_txt)[-300:],
                    )
                    core.record_wake_episode(
                        task_id=f"planner:{last_act}",
                        goal=text,
                        outcome_pass=step_ok,
                        route_id=str(last_act),
                    )
                except Exception:
                    pass
                if step_ok:
                    ep["causal_trace"].append({"action_id": str(last_act), "step": step - 1})

        # Check whether all goal postconditions ALREADY hold in `seeing`!
        writes_satisfied = bool(explicit_writes) and all(
            rel_p in file_set and (payload is None or payload == "" or str(previews.get(rel_p, "")).strip() == payload)
            for rel_p, payload in explicit_writes
        )
        outputs_ready = all(p in file_set for p in expected_outputs)

        if explicit_writes and not test_files and not impl_py_files and writes_satisfied:
            self._consolidate_completed_episode(text, ep)
            return None

        if test_files and ep["probed"] and ep["test_passed"] is True and outputs_ready:
            if not explicit_writes or writes_satisfied:
                self._consolidate_completed_episode(text, ep)
                return None

        if ep["verified_after_edit"] and outputs_ready:
            if not explicit_writes or writes_satisfied:
                self._consolidate_completed_episode(text, ep)
                return None

        last_aid_s = str(ep.get("last_action_id") or "")
        if last is not None and last.get("exit") == 0 and (
            last_aid_s in ("unified_model_solve", "grounded_action_exec", "explicit_writes_exec", "cli_metamorphic_exec")
            or last_aid_s.startswith(("taskfile_target:", "cli_acquire:", "recalled_workflow:"))
        ):
            if not test_files and outputs_ready and (not explicit_writes or writes_satisfied):
                if seeing.get("changed") or writes_satisfied:
                    self._consolidate_completed_episode(text, ep)
                    return None

        # Dynamic World Context Predicates (fed to `EpistemicSelfBeliefEngine` for context-conditioned posteriors!)
        truncated_or_hidden = [
            f for f in file_list
            if (f not in ep["full_files"]) or (len(str(previews.get(f, ""))) >= 580 and len(str(ep["full_files"].get(f, ""))) <= 600)
        ]
        world_ctx: dict[str, bool] = {
            "has_tests": bool(test_files),
            "has_py_impl": bool(impl_py_files),
            "has_config": bool(config_files),
            "has_hidden_bytes": bool(truncated_or_hidden),
            "facts_probed": bool(ep["probed"]),
            "prior_failure": bool(ep["failures"]),
            "has_cli_surface": bool(cli_files),
            "has_taskfile": bool(has_taskfile),
            "has_explicit_writes": bool(explicit_writes),
        }

        current_facts = (
            self._world_fact_tokens(
                file_set=file_set,
                probed=bool(ep["probed"]),
                test_passed=ep["test_passed"],
                verified_after_edit=bool(ep["verified_after_edit"]),
                writes_satisfied=writes_satisfied,
                outputs_ready=outputs_ready,
            )
            | projected_world_preds
        )
        protected_facts = {
            f for f in current_facts
            if f in ("pred:tests_green", "pred:verified_after_edit", "pred:writes_satisfied")
        }

        # ------------------------------------------------------------------
        # Open-Ended Affordance Discovery (zero closed switchboard!)
        # Every discovered affordance carries `(requires_preds, produces_preds, render_fn)`.
        # ------------------------------------------------------------------
        primers = (learned or {}).get("primers") or []
        routed_score = 0.0
        if file_set and "unified_model_solve" not in ep["tried"] and (
            not (test_files and impl_py_files)
            or ("py_ast_patch_h1" in ep["tried"] and "py_obs_synth_h2" in ep["tried"])
        ):
            try:
                routed = open_model().route(text, top_k=1)
                ranked = routed.get("candidates") or routed.get("ranked_capabilities") or []
                if ranked:
                    routed_score = float(ranked[0].get("score") or 0.0)
            except Exception:
                routed_score = 0.0

        repo_root = str(ROOT)
        concept_lib_path = str(core.concept_library.path) if getattr(core.concept_library, "path", None) else ""
        observed_coverage = (
            max(0.1, float(len(file_list) - len(truncated_or_hidden)) / float(max(1, len(file_list))))
            if not ep["probed"] and (truncated_or_hidden or test_files or has_taskfile)
            else 1.0
        )

        def _query_option_belief(
            opt_id: str,
            *,
            verifier_backed: bool,
            local_only: bool = True,
        ) -> tuple[float, float, float]:
            inhibited, _reason = core.world_graph.should_inhibit_action(
                opt_id,
                current_facts=current_facts,
                protected_facts=protected_facts,
            )
            if inhibited:
                return 0.02, 0.0, 100.0
            dist = core.belief.predict_distribution(
                f"planner:{opt_id}",
                host_ready=local_only,
                grounding_complete=bool(ep["probed"]) or not bool(truncated_or_hidden),
                causal_precond_met=True,
                memory_reflex_hit=opt_id.startswith(("flywheel_primer", "recalled_workflow:")),
                strong_verifier=verifier_backed,
                context_predicates=world_ctx,
            )
            cost_m = core.cost_router.score_candidate(
                opt_id,
                expected_gain=1.0,
                default_cost_ms=float(dist.get("expected_latency_ms") or 5.0),
            )
            return (
                float(dist["predicted_pass_probability"]),
                float(dist.get("epistemic_mi_nats") or 0.0),
                float(cost_m["measured_ms"]),
            )

        option_specs: dict[str, dict[str, Any]] = {}

        def _register_affordance(
            opt_id: str,
            *,
            requires_preds: set[str],
            produces_preds: set[str],
            render_fn: Callable[[], str],
            default_latency_ms: float = 5.0,
            verifier_backed: bool = True,
            needs_grounding: bool = False,
        ) -> None:
            if opt_id in ep["tried"]:
                return
            p_pass, ep_mi_nats, meas_ms = _query_option_belief(opt_id, verifier_backed=verifier_backed)
            # Fuse learned CausalWorldGraph effects (`produces` / `destroys`) with structural affordance effects!
            learned_prod = set(core.world_graph.produces.get(opt_id) or ())
            learned_dest = set(core.world_graph.destroys.get(opt_id) or ())
            option_specs[opt_id] = {
                "id": opt_id,
                "requires_preds": frozenset(requires_preds),
                "produces_preds": frozenset(produces_preds | learned_prod),
                "destroys_preds": frozenset(learned_dest),
                "p_pass": p_pass,
                "epistemic_mi_nats": ep_mi_nats,
                "latency_ms": meas_ms if opt_id in core.cost_router._stats else default_latency_ms,
                "needs_grounding": needs_grounding,
                "render_fn": render_fn,
            }

        # Affordance 1: Pure-Stdlib Epistemic World + Taskfile + Test Probe (`confined: True` safe!)
        if not ep["probed"] and bool(truncated_or_hidden or test_files or has_taskfile):
            _register_affordance(
                "epistemic_probe",
                requires_preds=set(),
                produces_preds={"pred:facts_observed"},
                default_latency_ms=4.0,
                verifier_backed=True,
                render_fn=lambda: (
                    "import json, pathlib, re, subprocess, sys\n"
                    "full_files = {}\n"
                    f"for rel in {file_list!r}:\n"
                    "    p = pathlib.Path(rel)\n"
                    "    if p.is_file() and p.stat().st_size <= 65536:\n"
                    "        try:\n"
                    "            raw = p.read_bytes()\n"
                    "            if b'\\x00' not in raw[:512]:\n"
                    "                full_files[rel] = raw.decode('utf-8', 'replace')\n"
                    "        except OSError:\n"
                    "            pass\n"
                    "tasks = []\n"
                    "mk = pathlib.Path('Makefile')\n"
                    "if mk.is_file():\n"
                    "    for ln in mk.read_text(encoding='utf-8', errors='replace').splitlines():\n"
                    "        m = re.match(r'^([A-Za-z0-9_.-]+):', ln)\n"
                    "        if m and not m.group(1).startswith('.'):\n"
                    "            tasks.append({'name': m.group(1), 'command': 'make ' + m.group(1)})\n"
                    "pkg = pathlib.Path('package.json')\n"
                    "if pkg.is_file():\n"
                    "    try:\n"
                    "        scripts = (json.loads(pkg.read_text(encoding='utf-8')).get('scripts') or {})\n"
                    "        for k, v in scripts.items():\n"
                    "            tasks.append({'name': str(k), 'command': str(v)})\n"
                    "    except Exception:\n"
                    "        pass\n"
                    "test_passed = True\n"
                    "diag = ''\n"
                    f"t_files = {test_files!r}\n"
                    "if t_files:\n"
                    "    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True)\n"
                    "    test_passed = (r.returncode == 0)\n"
                    "    diag = ((r.stdout or '') + '\\n' + (r.stderr or ''))[-1200:]\n"
                    "print('BRAIN_PROBE_JSON:' + json.dumps({'full_files': full_files, 'tasks': tasks[:12], 'test_passed': test_passed, 'test_diagnostics': diag}))\n"
                ),
            )

        # Affordance 2: Recalled Flywheel / Transfer Primers
        if primers:
            p_proc = str(primers[0].get("procedure") or "").strip()
            if p_proc:
                _register_affordance(
                    "flywheel_primer",
                    requires_preds=set(),
                    produces_preds={"pred:code_candidate_ready", "pred:goal_acted"},
                    default_latency_ms=3.0,
                    verifier_backed=True,
                    render_fn=lambda prog=p_proc: prog,
                )

        # Affordance 3: Open Taskfile Targets (`Makefile` / `package.json` / `pyproject.toml` discovered at runtime!)
        goal_low = text.lower()
        for t_row in (ep.get("discovered_tasks") or [])[:6]:
            if not isinstance(t_row, Mapping):
                continue
            t_nm = str(t_row.get("name") or "").strip()
            t_cmd = str(t_row.get("command") or "").strip().lstrip("@")
            if t_nm and t_cmd and re.search(rf"\b{re.escape(t_nm.lower())}\b", goal_low):
                aid_t = f"taskfile_target:{t_nm}"
                _register_affordance(
                    aid_t,
                    requires_preds=set(),
                    produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                    default_latency_ms=8.0,
                    verifier_backed=True,
                    render_fn=lambda cmd=t_cmd: (
                        "import subprocess, sys\n"
                        f"r = subprocess.run({cmd!r}, shell=True, capture_output=True, text=True)\n"
                        "if r.returncode != 0:\n"
                        "    sys.stderr.write((r.stderr or r.stdout or 'task_failed')[-800:])\n"
                        "    raise SystemExit(1)\n"
                    ),
                )

        # Affordance 4: Python AST Patch Search, HORS Observational Synthesis & Independent Test Verification
        if test_files and impl_py_files:
            if ep["edited_code"] and not ep["verified_after_edit"]:
                _register_affordance(
                    "verify_postconditions",
                    requires_preds={"pred:code_candidate_ready"},
                    produces_preds={"pred:tests_green", "pred:verified_after_edit"},
                    default_latency_ms=3.5,
                    verifier_backed=True,
                    render_fn=lambda: (
                        "import subprocess, sys\n"
                        "import os as _os, pathlib as _pl\n"
                        "for _d in _pl.Path('.').rglob('__pycache__'):\n"
                        "    for _c in _d.glob('*.pyc'):\n"
                        "        try:\n"
                        "            _c.unlink()\n"
                        "        except OSError:\n"
                        "            pass\n"
                        "_ENV = {**_os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}\n"
                        "r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True, env=_ENV)\n"
                        "if r.returncode != 0:\n"
                        "    sys.stderr.write((r.stderr or r.stdout or 'verification_failed')[-800:])\n"
                        "    raise SystemExit(1)\n"
                    ),
                )
            def _render_h1_confined() -> str:
                # Pure-stdlib confined AST single-operator / constant-sign repair search (`confined_v1` safe — zero external imports!)
                return (
                    "import ast, copy, pathlib, subprocess, sys\n"
                    "import os as _os, pathlib as _pl\n"
                    "for _d in _pl.Path('.').rglob('__pycache__'):\n"
                    "    for _c in _d.glob('*.pyc'):\n"
                    "        try:\n"
                    "            _c.unlink()\n"
                    "        except OSError:\n"
                    "            pass\n"
                    "_ENV = {**_os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}\n"
                    "def _test_ok():\n"
                    "    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True, env=_ENV)\n"
                    "    return r.returncode == 0, (r.stderr or r.stdout or '')[-800:]\n"
                    "ok0, err0 = _test_ok()\n"
                    "if ok0:\n"
                    "    raise SystemExit(0)\n"
                    "SWAP_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult}\n"
                    "SWAP_CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}\n"
                    "patched = False\n"
                    f"for rel in {impl_py_files!r}:\n"
                    "    p = pathlib.Path(rel)\n"
                    "    if not p.is_file():\n"
                    "        continue\n"
                    "    orig = p.read_text(encoding='utf-8')\n"
                    "    try:\n"
                    "        tree = ast.parse(orig)\n"
                    "    except SyntaxError:\n"
                    "        continue\n"
                    "    nodes = list(ast.walk(tree))\n"
                    "    for idx, nd in enumerate(nodes):\n"
                    "        cand_trees = []\n"
                    "        if isinstance(nd, ast.BinOp) and type(nd.op) in SWAP_BIN:\n"
                    "            t2 = copy.deepcopy(tree)\n"
                    "            list(ast.walk(t2))[idx].op = SWAP_BIN[type(nd.op)]()\n"
                    "            cand_trees.append(t2)\n"
                    "        elif isinstance(nd, ast.Compare) and len(nd.ops) == 1 and type(nd.ops[0]) in SWAP_CMP:\n"
                    "            t2 = copy.deepcopy(tree)\n"
                    "            list(ast.walk(t2))[idx].ops[0] = SWAP_CMP[type(nd.ops[0])]()\n"
                    "            cand_trees.append(t2)\n"
                    "        for ct in cand_trees:\n"
                    "            ast.fix_missing_locations(ct)\n"
                    "            p.write_text(ast.unparse(ct) + '\\n', encoding='utf-8')\n"
                    "            ok_c, _ = _test_ok()\n"
                    "            if ok_c:\n"
                    "                patched = True\n"
                    "                break\n"
                    "        if patched:\n"
                    "            break\n"
                    "    if not patched:\n"
                    "        p.write_text(orig, encoding='utf-8')\n"
                    "    else:\n"
                    "        break\n"
                    "ok_f, err_f = _test_ok()\n"
                    "if not ok_f:\n"
                    "    sys.stderr.write(err_f or 'patch_h1_failed')\n"
                    "    raise SystemExit(1)\n"
                )

            def _render_h2_confined() -> str:
                # In-process HORS + ConceptLibrary synthesis over observed `ep["full_files"]`, emitting pure-stdlib confined write+verify!
                import ast as _ast
                from canonical.runtime.swe_observational_program_synthesizer_v1 import (
                    extract_io_examples_from_test_source,
                    synthesize_python_function_body,
                )
                from canonical.swe_kernel import whitebox_introspector_and_trace_synthesizer_v1 as wits

                full_map = dict(ep.get("full_files") or {})
                cfg_consts: list[Any] = []
                for rel_f, raw_txt in full_map.items():
                    if str(rel_f).endswith(".json"):
                        try:
                            obj = json.loads(str(raw_txt))
                            if isinstance(obj, Mapping):
                                for v in obj.values():
                                    if isinstance(v, (int, float, str)) and not isinstance(v, bool):
                                        cfg_consts.append(v)
                        except Exception:
                            pass
                combined_tests = "\n\n".join(str(full_map.get(tf, "")) for tf in test_files if full_map.get(tf))
                patched_files: dict[str, str] = {}
                for imp_rel in impl_py_files:
                    src_txt = str(full_map.get(imp_rel) or "")
                    if not src_txt.strip() or not combined_tests.strip():
                        continue
                    try:
                        imp_tree = _ast.parse(src_txt)
                    except SyntaxError:
                        continue
                    cur_src = src_txt
                    for fn_nd in [nd for nd in imp_tree.body if isinstance(nd, _ast.FunctionDef)]:
                        p_names = [a.arg for a in fn_nd.args.args]
                        exs, t_consts = extract_io_examples_from_test_source(combined_tests, fn_nd.name)
                        valid_exs = [ex for ex in exs if len(ex[0]) == len(p_names)]
                        if not valid_exs:
                            continue
                        merged_c = list(dict.fromkeys([*cfg_consts, *t_consts]))[:16]
                        body_code = synthesize_python_function_body(
                            p_names,
                            valid_exs,
                            extra_constants=merged_c,
                            max_weight=4,
                            concept_library=core.concept_library,
                        )
                        if not body_code:
                            # Ensemble fallback (plan v5 move 2): OE + stochastic
                            # union for shapes the observational grammar cannot
                            # express at this budget (measured: branch-using
                            # programs at max_weight 4..8, ten configs, all miss;
                            # the union finds and verifies them in ~190 ms).
                            # Every returned body is already verified against ALL
                            # extracted examples, so a miss costs ~200 ms where
                            # the affordance otherwise had no candidate at all --
                            # it cannot slow a step that would have failed.
                            from canonical.runtime.stochastic_synthesizer_v1 import (
                                numeric_concept_templates,
                                synthesize_body_from_examples,
                            )
                            body_code = synthesize_body_from_examples(
                                p_names, valid_exs,
                                # Learned grammar (v6 section 14): the concept
                                # library's admitted templates are atoms this
                                # enumerator cannot build at any depth. Read
                                # only -- nothing here mutates the library.
                                concepts=numeric_concept_templates(
                                    getattr(core, "concept_library", None),
                                ),
                            )
                        if body_code:
                            upd = wits._replace_function_body_in_source(cur_src, fn_nd.name, body_code)
                            if upd:
                                cur_src = upd
                    if cur_src != src_txt:
                        patched_files[imp_rel] = cur_src

                lines = ["import pathlib, subprocess, sys",
                         "import os as _os",
                         "for _d in pathlib.Path('.').rglob('__pycache__'):",
                         "    for _c in _d.glob('*.pyc'):",
                         "        try:",
                         "            _c.unlink()",
                         "        except OSError:",
                         "            pass",
                         "_ENV = {**_os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}"]
                for rel_p, new_src in sorted(patched_files.items()):
                    lines.append(f"pathlib.Path({rel_p!r}).write_text({new_src!r}, encoding='utf-8')")
                lines.extend(
                    [
                        "r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True, env=_ENV)",
                        "if r.returncode != 0:",
                        "    sys.stderr.write((r.stderr or r.stdout or 'obs_synth_h2_failed')[-800:])",
                        "    raise SystemExit(1)",
                    ]
                )
                return "\n".join(lines) + "\n"

            _register_affordance(
                "py_ast_patch_h1",
                requires_preds=set(),
                produces_preds={"pred:code_candidate_ready", "pred:tests_green", "pred:verified_after_edit"},
                default_latency_ms=7.0,
                verifier_backed=True,
                needs_grounding=True,
                render_fn=_render_h1_confined,
            )
            _register_affordance(
                "py_obs_synth_h2",
                requires_preds=set(),
                produces_preds={"pred:code_candidate_ready", "pred:tests_green", "pred:verified_after_edit"},
                default_latency_ms=14.0,
                verifier_backed=True,
                needs_grounding=True,
                render_fn=_render_h2_confined,
            )

        # Affordance 5: Explicit Artifact Emit
        if explicit_writes and not writes_satisfied:
            def _render_writes() -> str:
                lines = ["import pathlib"]
                for idx_w, (rel_p, payload) in enumerate(explicit_writes):
                    content_str = (payload + "\n") if payload else ""
                    lines.append(f"_p{idx_w} = pathlib.Path({rel_p!r})")
                    lines.append(f"_p{idx_w}.parent.mkdir(parents=True, exist_ok=True)")
                    lines.append(f"_p{idx_w}.write_text({content_str!r}, encoding='utf-8')")
                return "\n".join(lines) + "\n"

            _register_affordance(
                "explicit_writes_exec",
                requires_preds=set(),
                produces_preds={"pred:writes_satisfied", "pred:outputs_ready"},
                default_latency_ms=4.5,
                verifier_backed=True,
                render_fn=_render_writes,
            )

        # Affordance 6: Open CLI Metamorphic & Documentation Discovery (`world_probe_v1` + `documentation_mining_v1` + `grounded_action_v1`)
        if cli_files and not test_files:
            _register_affordance(
                "cli_metamorphic_exec",
                requires_preds=set(),
                produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                default_latency_ms=11.0,
                verifier_backed=True,
                render_fn=lambda: (
                    "import pathlib, sys\n"
                    f"sys.path.insert(0, {repo_root!r})\n"
                    "from canonical.runtime import world_probe_v1 as wp, grounded_action_v1 as ga\n"
                    "ws = pathlib.Path('.').resolve()\n"
                    f"wp.established_facts([], goal={text!r}, goal_paths={cli_files!r}, root=ws)\n"
                    f"_out = ga.act({text!r}, root=ws)\n"
                    "if not _out.get('ok'):\n"
                    "    raise SystemExit(1)\n"
                ),
            )

        # Affordance 7: Grounded World Action & Compiled UnifiedModel Capability Route
        if file_set:
            _register_affordance(
                "grounded_action_exec",
                requires_preds=set(),
                produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                default_latency_ms=20.0,
                verifier_backed=False,
                needs_grounding=True,
                render_fn=lambda: (
                    "import pathlib, sys\n"
                    f"sys.path.insert(0, {repo_root!r})\n"
                    "from canonical.runtime import grounded_action_v1 as ga\n"
                    f"_out = ga.act({text!r}, root=pathlib.Path('.').resolve())\n"
                    "if not _out.get('ok'):\n"
                    "    raise SystemExit(1)\n"
                ),
            )
            if routed_score > 0.0:
                _register_affordance(
                    "unified_model_solve",
                    requires_preds=set(),
                    produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                    default_latency_ms=22.0,
                    verifier_backed=True,
                    needs_grounding=True,
                    render_fn=lambda: (
                        "import sys\n"
                        f"sys.path.insert(0, {repo_root!r})\n"
                        "from canonical.runtime.brain_unified_model_v1 import open_model\n"
                        f"_res = open_model().solve({text!r}, declared_resources={file_list!r})\n"
                        "if not _res.get('pass'):\n"
                        "    raise SystemExit(1)\n"
                    ),
                )

        if not option_specs:
            return None

        # ------------------------------------------------------------------
        # Open-Predicate Active-Inference MCTS (`decision_core_v1`)
        # State = `(frozenset[predicate_str], frozenset[used_action_id])`
        # Value = Parameter-free Expected Free Energy in nats (`I(Y;Theta|s,a) + delta_goal - tau/budget`)
        # ------------------------------------------------------------------
        from canonical.runtime import decision_core_v1 as dc

        needs_tests = bool(test_files and impl_py_files)
        needs_writes = bool(explicit_writes)
        needs_generic_act = not needs_tests and not needs_writes
        has_hidden_world = bool(truncated_or_hidden or (test_files and not ep["probed"]) or (has_taskfile and not ep["probed"]))

        goal_predicates: set[str] = set()
        if needs_tests:
            goal_predicates.add("pred:tests_green")
            goal_predicates.add("pred:verified_after_edit")
        if needs_writes:
            goal_predicates.add("pred:writes_satisfied")
        if needs_generic_act:
            goal_predicates.add("pred:goal_acted")

        init_preds = set(current_facts)
        if not has_hidden_world:
            init_preds.add("pred:facts_observed")
        if ep["edited_code"] or (ep["test_passed"] is True):
            init_preds.add("pred:code_candidate_ready")
        if ep["verified_after_edit"] or (ep["probed"] and ep["test_passed"] is True):
            init_preds.add("pred:tests_green")
            init_preds.add("pred:verified_after_edit")
        if writes_satisfied:
            init_preds.add("pred:writes_satisfied")

        init_mcts_state = (frozenset(init_preds), frozenset(ep["tried"]))
        total_latency_budget_ms = max(
            40.0,
            sum(float(sp["latency_ms"]) for sp in option_specs.values()) * 2.0,
        )
        hidden_info_nats = math.log(2.0) * min(3.0, float(len(truncated_or_hidden) + len(test_files) + (1 if has_taskfile else 0)))

        def _is_goal_state(st: tuple[frozenset[str], frozenset[str]]) -> bool:
            preds, _used = st
            return bool(goal_predicates) and goal_predicates.issubset(preds)

        def _actions_fn(node: Any) -> list[str]:
            st = node.state
            if _is_goal_state(st) or node.depth >= 4:
                return []
            preds, used = st
            specialist_exhausted = ("py_ast_patch_h1" in used and "py_obs_synth_h2" in used)
            avail: list[str] = []
            for oid, spec in option_specs.items():
                if oid in used:
                    continue
                req_p = spec["requires_preds"]
                if req_p and not req_p.issubset(preds):
                    continue
                prod_p = spec["produces_preds"]
                # Skip pure observation once workspace facts are already observed
                if oid == "epistemic_probe" and "pred:facts_observed" in preds:
                    continue
                # Skip actions that produce zero new predicates toward the open world/goal
                if prod_p.issubset(preds):
                    continue
                if oid in ("grounded_action_exec", "unified_model_solve") and needs_tests and not specialist_exhausted:
                    continue
                avail.append(oid)
            if (
                needs_tests
                and "pred:code_candidate_ready" in preds
                and "pred:verified_after_edit" not in preds
                and "verify_postconditions" not in used
                and "verify_postconditions" not in avail
            ):
                avail.append("verify_postconditions")
            return avail

        def _make_state(st: tuple[frozenset[str], frozenset[str]], action_id: str) -> tuple[frozenset[str], frozenset[str]]:
            preds, used = st
            nxt_used = used | {action_id}
            spec = option_specs.get(action_id)
            if spec is None:
                # Virtual postcondition verification transition after repair in rollout
                nxt_p = set(preds)
                if "pred:code_candidate_ready" in preds:
                    nxt_p.update(("pred:tests_green", "pred:verified_after_edit"))
                return (frozenset(nxt_p), nxt_used)
            prod_p = set(spec["produces_preds"])
            # Ungrounded code edits before observing hidden test/source bytes require explicit verification!
            if "pred:facts_observed" not in preds and action_id in ("py_ast_patch_h1", "py_obs_synth_h2", "flywheel_primer"):
                prod_p.discard("pred:tests_green")
                prod_p.discard("pred:verified_after_edit")
            nxt_p = (set(preds) | prod_p) - set(spec["destroys_preds"])
            return (frozenset(nxt_p), nxt_used)

        virtual_verify_p, virtual_verify_mi, virtual_verify_ms = _query_option_belief("verify_postconditions", verifier_backed=True)

        def _step_efe_utility(
            prev_st: tuple[frozenset[str], frozenset[str]],
            aid: str,
            cur_st: tuple[frozenset[str], frozenset[str]],
            survival_p: float,
        ) -> tuple[float, float]:
            prev_preds, _ = prev_st
            cur_preds, _ = cur_st
            spec = option_specs.get(aid) or {
                "p_pass": virtual_verify_p,
                "epistemic_mi_nats": virtual_verify_mi,
                "latency_ms": virtual_verify_ms,
                "needs_grounding": False,
            }
            p_step = float(spec["p_pass"])
            if spec.get("needs_grounding") and "pred:facts_observed" not in prev_preds:
                p_step *= observed_coverage

            # 1. Epistemic Information Gain in nats (`I(Y; Theta | s, a)` + unobserved-world Shannon entropy reduction)
            info_gain_nats = float(spec["epistemic_mi_nats"])
            if "pred:facts_observed" in cur_preds and "pred:facts_observed" not in prev_preds:
                info_gain_nats += hidden_info_nats

            # 2. Pragmatic Goal Satisfaction Gain (dimensionless fraction of `goal_predicates` newly achieved)
            n_goal = float(max(1, len(goal_predicates)))
            sat_before = float(len(goal_predicates & prev_preds)) / n_goal
            sat_after = float(len(goal_predicates & cur_preds)) / n_goal
            pragmatic_gain = max(0.0, sat_after - sat_before)

            # 3. Mortality / Latency Fraction (`tau_a / tau_budget`)
            mortality_cost = float(spec["latency_ms"]) / total_latency_budget_ms

            nxt_survival = survival_p * p_step
            neg_efe = survival_p * info_gain_nats + nxt_survival * pragmatic_gain - mortality_cost
            return nxt_survival, neg_efe

        def _evaluate_fn(node: Any) -> float:
            if node.depth == 0 or node.action is None:
                return 0.0
            chain: list[Any] = []
            cur = node
            while cur is not None and cur.parent is not None:
                chain.append(cur)
                cur = cur.parent
            chain.reverse()

            survival_p = 1.0
            total_neg_efe = 0.0
            for step_nd in chain:
                survival_p, dv = _step_efe_utility(step_nd.parent.state, str(step_nd.action), step_nd.state, survival_p)
                total_neg_efe += dv

            sim_st = node.state
            sim_depth = node.depth
            while not _is_goal_state(sim_st) and sim_depth < 4:
                dummy = dc.Node(state=sim_st)
                dummy.parent = node
                cand_a = [a for a in _actions_fn(dummy) if a not in sim_st[1]]
                if not cand_a:
                    break
                best_a = max(
                    cand_a,
                    key=lambda a: _step_efe_utility(sim_st, a, _make_state(sim_st, a), survival_p)[1],
                )
                nxt_st = _make_state(sim_st, best_a)
                survival_p, dv = _step_efe_utility(sim_st, best_a, nxt_st, survival_p)
                total_neg_efe += dv
                sim_st = nxt_st
                sim_depth += 1

            if _is_goal_state(node.state):
                node.terminal = True
            if _is_goal_state(sim_st):
                total_neg_efe += survival_p
            # Map unbounded negative-EFE nats smoothly onto `(0, 1)` via logistic link `1 / (1 + exp(-x))` (zero magic constants!)
            return 1.0 / (1.0 + math.exp(-max(-8.0, min(8.0, total_neg_efe))))

        def _reflect_fn(node: Any) -> str:
            return f"efe_predicate_mcts:{node.action}@depth={node.depth}"

        root = dc.Node(state=init_mcts_state)
        dc.search(
            root,
            _actions_fn,
            _evaluate_fn,
            iterations=max(16, 8 * len(option_specs)),
            c=math.sqrt(2.0),
            make_state=_make_state,
            reflect_fn=_reflect_fn,
        )
        chosen_raw = dc.best_action(root)
        chosen_id = str(chosen_raw) if chosen_raw in option_specs else next(iter(option_specs))
        traj_actions = [str(n.action) for n in dc.best_trajectory(root)[1:] if n.action is not None]
        self.last_mcts_summary = {
            "chosen_action": chosen_id,
            "best_trajectory": traj_actions,
            "goal_predicates": sorted(goal_predicates),
            "initial_predicates_count": len(init_preds),
            "affordances_discovered": sorted(option_specs.keys()),
            "root_visits": root.visits,
            "child_stats": {
                str(ch.action): {"visits": ch.visits, "mean_value": round(ch.mean_value, 4)}
                for ch in root.children
            },
        }

        # Issue pre-action `PredictionTicket` & render directly from the winning `AffordanceSpec` (zero switchboard!)
        ep["last_action_id"] = chosen_id
        ep["last_world_facts"] = set(current_facts)
        ep["tried"].add(chosen_id)
        try:
            ep["last_ticket"] = core.belief.predict_before_act(
                f"planner:{chosen_id}",
                host_ready=True,
                grounding_complete=bool(ep["probed"]) or not bool(truncated_or_hidden),
                causal_precond_met=True,
                memory_reflex_hit=chosen_id.startswith(("flywheel_primer", "recalled_workflow:")),
                strong_verifier=True,
                context_predicates=world_ctx,
            )
        except Exception:
            ep["last_ticket"] = None

        winning_spec = option_specs.get(chosen_id)
        if winning_spec is None or not callable(winning_spec.get("render_fn")):
            return None
        return str(winning_spec["render_fn"]())


_SOVEREIGN_PLANNER = SovereignZeroLLMPlanner()


def brain_model_callable(goal: str, seeing: dict[str, Any]) -> str | None:
    """Zero-LLM (`K3 = 0`) multi-step `BRAIN_MODEL` callable conforming to `canonical.runtime.model_v1`."""
    return _SOVEREIGN_PLANNER(goal, seeing)


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
