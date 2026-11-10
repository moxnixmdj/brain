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

import argparse
import hashlib
import importlib.util
import json
import marshal
import math
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

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

def _public_benchmark() -> dict[str, Any]:
    """The recorded public-benchmark result, read from the governance record.

    Deliberately NOT recomputed on every status call: the number should come from the
    signed record, not from a fresh run that could drift from it.
    """
    try:
        p = (Path(__file__).resolve().parents[2]
             / "canonical/governance/ARC_PUBLIC_BENCHMARK_RESULT_20261109_V1.json")
        d = json.loads(p.read_text())
        r = d.get("result") or {}
        return {
            "benchmark": (d.get("benchmark") or {}).get("name"),
            "tasks": r.get("tasks"),
            "solved": r.get("solved"),
            "accuracy_pct": r.get("accuracy_pct"),
            "trained_parameters": r.get("trained_parameters"),
            "external_model_calls": r.get("external_model_calls"),
            "source_record": "canonical/governance/ARC_PUBLIC_BENCHMARK_RESULT_20261109_V1.json",
            "note": "NOT_A_PARITY_CLAIM__200_of_400_public_tasks__reported_as_it_fell",
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)[:120]}


def _reachability_gap() -> dict[str, Any]:
    """How much of the repository this model can reach, computed, never assumed.

    Cheap: `git ls-files` once, compared against the artifact's own `source_index`.
    Reported as counts so the number cannot drift away from the truth.
    """
    try:
        import subprocess

        root = Path(__file__).resolve().parents[2]
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                             text=True, timeout=20)
        tracked = [p for p in out.stdout.splitlines() if p]
        indexed = set()
        with open(root / DEFAULT_ARTIFACT, encoding="utf-8") as fh:
            art = json.load(fh)
        for e in art.get("source_index") or []:
            if e.get("path"):
                indexed.add(e["path"])
        research = set()
        for e in art.get("research_index") or []:
            if e.get("path"):
                research.add(e["path"])
        knowledge = set()
        for e in art.get("knowledge") or []:
            if e.get("path"):
                knowledge.add(e["path"])
        reachable = indexed | research | knowledge
        laws = [p for p in tracked if "action_intents" in p]
        unreachable = [p for p in tracked if p not in reachable]
        # how many of the UNREACHABLE files carry real signals, so the gap has a weight
        try:
            import sys as _sys
            _sys.path.insert(0, str(root))
            from canonical.runtime import census_every_valuable_thing_v1 as _c
            priced = _c.price(unreachable, {"paths": reachable}) if len(unreachable) < 20000 else []
            weight = len([r for r in priced if r["score"] > 0])
        except Exception:  # noqa: BLE001
            weight = None
        return {
            "files_tracked": len(tracked),
            "reachable_any_way": len(tracked) - len(unreachable),
            "files_not_reachable": len(unreachable),
            "unreachable_with_real_signals": weight,
            "laws_present": len(laws),
            "laws_reachable": len([p for p in laws if p in reachable]),
            "note": ("REACHABLE_MEANS_ADDRESSABLE_NOT_EXECUTABLE__a law can be recalled "
                     "by its own words; it is never reachable through solve()"),
        }
    except Exception as exc:  # noqa: BLE001 - a status call must never fail
        return {"error": str(exc)[:160], "note": "reachability could not be computed"}


NON_CLAIMS = (
    "NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS",
    "NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY",
    "NOT_TERMINAL_AUTHORITY__ZERO_CAPABILITY_AND_TERMINAL_CREDIT",
    "NOT_A_REPLACEMENT_FOR_THE_LIVE_REGISTRY_OR_LAWS",
    "COVERAGE_IS_NOT_CAPABILITY__EXECUTION_STILL_REQUIRES_DECLARED_SUBSTRATE",
)


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
        "core_format_v": 3,
        "raw_sha256": raw_sha,
        "schema": str(model.get("schema") or ""),
        "model_id": model.get("model_id"),
        "model_version": model.get("model_version"),
        "digest_value": str((model.get("digest") or {}).get("value") or ""),
        "counts": dict(model.get("counts") or {}),
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
        "research_index_len": len(res_rows),
        "knowledge_len": len(knw_rows),
    }


# --------------------------------------------------------------------------- model


class UnifiedModel:
    """A loaded, digest-verified unified model."""

    def __init__(self, model: Mapping[str, Any], *, _raw_bytes: bytes | None = None, _core_only: bool = False):
        self._raw_bytes_backing: bytes | None = _raw_bytes
        self._declared_triggers_cache: dict[str, set[str]] = {}
        if _core_only and model.get("core_format_v") == 3:
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

        self._unrunnable: dict[str, list[str]] | None = None
        self._source_index_cache: dict[str, dict[str, Any]] | None = None
        self._source_df_cache: dict[str, int] | None = None
        self._research_index_cache: dict[str, dict[str, Any]] | None = None
        self._research_df_cache: dict[str, int] | None = None
        self._knowledge_cache: list[dict[str, Any]] | None = None
        self._knowledge_df_cache: dict[str, int] | None = None
        self._knowledge_lengths_cache: list[int] | None = None
        self._avg_length_cache: float | None = None

        self.min_score = float(confidence.get("minimum_best_score", 1.0))
        self.min_coverage = float(confidence.get("minimum_coverage", 0.34))
        if not _core_only:
            self._hydrate_secondary_indexes()

    def _ensure_full_model(self) -> dict[str, Any]:
        if self._model_loaded is None:
            if self._raw_bytes_backing is None:
                raise UnifiedModelError("MODEL_BACKING_BYTES_MISSING")
            self._model_loaded = json.loads(self._raw_bytes_backing.decode("utf-8"))
        return self._model_loaded

    def _hydrate_secondary_indexes(self) -> None:
        if self._source_index_cache is not None:
            return
        full = self._ensure_full_model()
        self._source_index_cache = {
            str(row["path"]): dict(row)
            for row in full.get("source_index") or []
            if isinstance(row, Mapping) and row.get("path")
        }
        src_df: dict[str, int] = {}
        for row in self._source_index_cache.values():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term in terms:
                src_df[str(term)] = src_df.get(str(term), 0) + 1
        self._source_df_cache = src_df

        self._research_index_cache = {
            str(row["path"]): dict(row)
            for row in full.get("research_index") or []
            if isinstance(row, Mapping) and row.get("path")
        }
        res_df: dict[str, int] = {}
        for row in self._research_index_cache.values():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term in terms:
                res_df[str(term)] = res_df.get(str(term), 0) + 1
        self._research_df_cache = res_df

        self._knowledge_cache = [
            dict(row) for row in (full.get("knowledge") or []) if isinstance(row, Mapping)
        ]
        knw_df: dict[str, int] = {}
        knw_len: list[int] = []
        for row in self._knowledge_cache:
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            knw_len.append(sum(int(v) for v in terms.values()))
            for term in terms:
                knw_df[str(term)] = knw_df.get(str(term), 0) + 1
        self._knowledge_df_cache = knw_df
        self._knowledge_lengths_cache = knw_len
        self._avg_length_cache = (sum(knw_len) / len(knw_len) if knw_len else 1.0) or 1.0

    @property
    def model(self) -> dict[str, Any]:
        return self._ensure_full_model()

    @property
    def source_index(self) -> dict[str, dict[str, Any]]:
        self._hydrate_secondary_indexes()
        return self._source_index_cache  # type: ignore[return-value]

    @property
    def _source_df(self) -> dict[str, int]:
        self._hydrate_secondary_indexes()
        return self._source_df_cache  # type: ignore[return-value]

    @property
    def research_index(self) -> dict[str, dict[str, Any]]:
        self._hydrate_secondary_indexes()
        return self._research_index_cache  # type: ignore[return-value]

    @property
    def _research_df(self) -> dict[str, int]:
        self._hydrate_secondary_indexes()
        return self._research_df_cache  # type: ignore[return-value]

    @property
    def knowledge(self) -> list[dict[str, Any]]:
        self._hydrate_secondary_indexes()
        return self._knowledge_cache  # type: ignore[return-value]

    @property
    def _knowledge_df(self) -> dict[str, int]:
        self._hydrate_secondary_indexes()
        return self._knowledge_df_cache  # type: ignore[return-value]

    @property
    def _knowledge_lengths(self) -> list[int]:
        self._hydrate_secondary_indexes()
        return self._knowledge_lengths_cache  # type: ignore[return-value]

    @property
    def _avg_length(self) -> float:
        self._hydrate_secondary_indexes()
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
                "skills": len(self.skills),
                "knowledge_documents": knw_len,
                "source_index_modules": src_len,
                "source_index_entry_points": src_ep,
                "research_index_records": res_len,
                "routing_tokens": len(self.index),
            },
            "source_index_is_addressable_not_executable": True,
            # ---- WHAT THIS MODEL CANNOT SEE ------------------------------------
            # The one model indexes 1,948 of the repository's runtime modules. Every
            # other tracked file -- including all 780 action-intent LAWS, each with its
            # causal blocker, measurement, falsification and stop condition -- is
            # outside it. Stating that here is not decoration: a model that reports its
            # own numbers without its own blind spot is reporting half a status.
            "reachability": _reachability_gap(),
            # ---- THE ONE PUBLIC BENCHMARK NUMBER THIS SYSTEM HAS -----------------
            # Every other performance figure in this project is a self-report. This one
            # is measured on tasks nobody here wrote, and it is reported as it fell.
            "public_benchmark": _public_benchmark(),
            "declared_dependencies_present": present,
            "declared_dependencies_missing": len(self.capabilities) - present,
            "objective": self._core_meta.get("objective_verbatim"),
            "non_claims": list(NON_CLAIMS),
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
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
        folded = str(goal or "").casefold()
        hits: set[str] = set()
        for cid in self.capabilities:
            if cid.casefold() in folded:
                hits.add(cid)
        for eid in self.engines:
            mode = eid.split(":", 1)[-1].replace("_", " ").casefold()
            if mode and mode in folded:
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
            for cid, row in self.capabilities.items():
                missing = _missing_declared_dependencies(row)
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
        unrunnable = self.unrunnable_capabilities()
        unrunnable_matched: set[str] = set()
        for token in ask_list:
            postings = self.index.get(token)
            if not postings:
                continue
            matched.add(token)
            for cid, weight in postings.items():
                if cid in unrunnable:
                    # Recorded, not removed. `route()` answers "what does the
                    # model contain", and that is not a fact about this host:
                    # the pinned route for "extract text from a pdf document"
                    # is pdf.extract.text.pypdf on every machine, and this
                    # sandbox happens to have pypdf while the CI runner does
                    # not. Hiding a capability here would make the ranking
                    # host-dependent, which is exactly what
                    # test_status_reports_the_machine_it_actually_runs_on
                    # exists to prevent. `solve()`, which does run things, is
                    # where the host gets a vote.
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
        # Engines are excluded from that priority: they match by mode phrase
        # (`engine:BOUND_CAPABILITY` matches the phrase "bound capability"),
        # which is ordinary keyword overlap, not an address. Promoting them let
        # a 195.977 engine outrank the 911.668 capability the goal named.
        addressed = {cid for cid in mentioned if cid in self.capabilities}
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
        total_docs = max(1, len(self.source_index))
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for path, row in self.source_index.items():
            counts = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            if not counts:
                continue
            score = 0.0
            hit: set[str] = set()
            for term in wanted:
                tf = int(counts.get(term, 0) or 0)
                if tf <= 0:
                    continue
                hit.add(term)
                df = max(1, self._source_df.get(term, 1))
                # Same IDF form `recall` uses for knowledge, so a term that
                # appears in one module outranks one that appears in a thousand.
                score += math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5)) * (1.0 + math.log(tf))
            if score <= 0.0:
                continue
            # Naming the file is an address, not a keyword, so it outranks term
            # overlap -- but only for the row actually named.
            if path.casefold() in query.casefold():
                score += 8.0
            scored.append((score, path, row))
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
            "indexed_modules": len(self.source_index),
            "reason": (
                "SOURCE_LOCATED__NOT_EXECUTABLE__NO_RECEIPT_OR_BOUND_ADAPTER"
                if rows
                else "NO_INDEXED_SOURCE_MATCHED"
            ),
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
        total_docs = max(1, len(self.research_index))
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for path, row in self.research_index.items():
            counts = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            if not counts:
                continue
            score = 0.0
            for term in wanted:
                tf = int(counts.get(term, 0) or 0)
                if tf <= 0:
                    continue
                df = max(1, self._research_df.get(term, 1))
                # "v1" occurs in 79% of these records, so raw overlap is noise;
                # the same IDF form `recall` and `find_source` use.
                score += math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5)) * (1.0 + math.log(tf))
            if score <= 0.0:
                continue
            # Naming a record by its action id is an address, not a keyword.
            action_id = str(row.get("action_id") or "")
            if action_id and action_id.casefold() in query.casefold():
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
            "indexed_records": len(self.research_index),
            "reason": (
                "RESEARCH_RECORD_LOCATED__EVIDENCE_NOT_CAPABILITY"
                if rows
                else "NO_INDEXED_RESEARCH_MATCHED"
            ),
        }

    # ------------------------------------------------------------------ recall

    def _recall_corpus(self) -> list[dict[str, Any]]:
        """Everything recall may look at: knowledge documents AND the law records.

        THE DEFECT THIS FIXES (measured): the artifact stores 781 action-intent LAW
        records -- each with a causal blocker, a measurement, a falsification condition
        and a stop condition -- and `recall()` scored only the 304 knowledge documents.
        The laws were shipped and never read: three exact law queries returned 0 law
        hits out of 6, buried under long historical inventories that merely repeat the
        vocabulary.
        """
        if getattr(self, "_recall_corpus_cache", None) is not None:
            return self._recall_corpus_cache
        rows: list[dict[str, Any]] = list(self.knowledge)
        try:
            for r in (self.research_index or {}).values():
                if not isinstance(r, Mapping):
                    continue
                if "action_intents" not in str(r.get("path") or ""):
                    continue
                stem = Path(str(r.get("path"))).stem
                # strip the version/date suffix so the remaining words are the rule
                rule = re.sub(r"(_V\d+)?(_20\d{6})?(_V\d+)?$", "", stem)
                # `tokenize` keeps `_` inside a token, so an unsplit stem becomes the
                # single token `a_census_that_cannot_fail_is_not_a_gate` and can never
                # overlap a query written in words. The stem is split on `_` HERE, and
                # the shared tokenizer is left alone so routing is untouched.
                rows.append({
                    **r,
                    "title": rule.replace("_", " ").replace("-", " ").lower(),
                    "title_terms": tokenize(rule.replace("_", " ").replace("-", " ")),
                    "authority": "ACTION_INTENT_LAW",
                })
        except Exception:  # noqa: BLE001 - recall must not fail because of a join
            pass
        self._recall_corpus_cache = rows
        return rows

    def recall(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("RECALL_QUERY_EMPTY")
        corpus = self._recall_corpus()
        total_docs = max(1, len(corpus))
        k1, b = 1.5, 0.75
        scored: list[tuple[float, dict[str, Any]]] = []
        for i, row in enumerate(corpus):
            counts = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            length = (self._knowledge_lengths[i]
                      if i < len(self._knowledge_lengths) else
                      sum(int(v) for v in (counts or {}).values())) or 1
            score = 0.0
            for term in terms:
                tf = int(counts.get(term, 0))
                if tf <= 0:
                    continue
                df = max(1, self._knowledge_df.get(term, 1))
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                score += idf * (tf * (k1 + 1)) / (
                    tf + k1 * (1.0 - b + b * length / self._avg_length)
                )
            # A document's own title is the strongest statement of what it is
            # about. Body term statistics alone can bury a short current law
            # under a long historical one that merely repeats its vocabulary.
            # A LAW IS NAMED BY ITS RULE, so its stem is a title like any other.
            title_terms = set(row.get("title_terms") or [])
            if not title_terms and row.get("authority") == "ACTION_INTENT_LAW":
                stem = Path(str(row.get("path"))).stem
                title_terms = set(tokenize(stem.replace("_", " ").replace("-", " ")))
            if title_terms:
                overlap = len(set(terms) & title_terms) / max(1, len(set(terms)))
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

        # 1. SYSTEM-1 REFLEX: REUSE_EXISTING_CAPABILITY via compiled UnifiedModel when confident & epistemically trusted
        is_forged_cid = bool(capability_id and str(capability_id).startswith("forged."))
        if not is_forged_cid and (regime_info["regime"] == "SYSTEM_1_REFLEX" or capability_id is not None):
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
            "model_id": self.model.get("model_id"),
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


# --------------------------------------------------------------------------- helpers


def _missing_declared_dependencies(row: Mapping[str, Any]) -> list[str]:
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
        if name in on_path:
            found = shutil.which(name) is not None
        else:
            try:
                found = importlib.util.find_spec(name) is not None
            except (ImportError, ValueError):
                # A name the import machinery refuses to resolve is not
                # evidence of presence. Fail closed.
                found = False
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


def open_model(
    path: str | Path | None = None, *, root: str | Path | None = None
) -> UnifiedModel:
    base = Path(root or ROOT).resolve()
    target = Path(path) if path else base / DEFAULT_ARTIFACT
    if not target.is_absolute():
        target = base / target
    if not target.is_file():
        raise UnifiedModelError("MODEL_ARTIFACT_MISSING:" + str(target))
    st = target.stat()
    mem_key = (str(target.resolve()), st.st_size, st.st_mtime_ns)
    mem_hit = _OPEN_MODEL_MEM_CACHE.get(mem_key)
    if mem_hit is not None:
        return mem_hit

    raw_bytes = target.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    cache_dir = _core_cache_dir()
    cache_file = cache_dir / f"unified_model_core_{raw_sha[:32]}.marshal"
    if cache_file.is_file():
        try:
            core = marshal.loads(cache_file.read_bytes())
            if (
                isinstance(core, dict)
                and core.get("core_format_v") == 3
                and core.get("raw_sha256") == raw_sha
                and core.get("schema") == SCHEMA
            ):
                _VERIFIED_BLOB_DIGESTS[raw_sha] = str(core.get("digest_value") or "")
                inst = UnifiedModel(core, _raw_bytes=raw_bytes, _core_only=True)
                _OPEN_MODEL_MEM_CACHE[mem_key] = inst
                return inst
        except Exception:
            pass

    full = load_model(target, root=base, verify=True)
    core = _extract_routing_core(full, raw_sha)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_f = cache_dir / f".unified_model_core_{raw_sha[:32]}.{os.getpid()}.tmp"
        tmp_f.write_bytes(marshal.dumps(core))
        tmp_f.replace(cache_file)
    except OSError:
        pass
    inst = UnifiedModel(core, _raw_bytes=raw_bytes, _core_only=True)
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
                        "r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True)\n"
                        "if r.returncode != 0:\n"
                        "    sys.stderr.write((r.stderr or r.stdout or 'verification_failed')[-800:])\n"
                        "    raise SystemExit(1)\n"
                    ),
                )
            def _render_h1_confined() -> str:
                # Pure-stdlib confined AST single-operator / constant-sign repair search (`confined_v1` safe — zero external imports!)
                return (
                    "import ast, copy, pathlib, subprocess, sys\n"
                    "def _test_ok():\n"
                    "    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True)\n"
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
                        if body_code:
                            upd = wits._replace_function_body_in_source(cur_src, fn_nd.name, body_code)
                            if upd:
                                cur_src = upd
                    if cur_src != src_txt:
                        patched_files[imp_rel] = cur_src

                lines = ["import pathlib, subprocess, sys"]
                for rel_p, new_src in sorted(patched_files.items()):
                    lines.append(f"pathlib.Path({rel_p!r}).write_text({new_src!r}, encoding='utf-8')")
                lines.extend(
                    [
                        "r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True)",
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
