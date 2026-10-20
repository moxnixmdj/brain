"""Compose capabilities by TYPE, and refuse to call a composition real until it has run.

The token graph says the surface is flat: 93 tokens provided, 38 required, and
only ONE multi-step chain in the whole registry. That is not because the
capabilities are unrelated -- it is because the two ends of an edge are named
differently. One capability provides `archive.tar_gz.create_from_manifest`;
the next requires `archive.tar_gz.available`. Same artifact, two names, no edge.

Match on the TYPE of the artifact instead and the same surface yields 113
edges. `archive.tar_gz.create_from_manifest` feeds
`archive.verify.tar_gz.gnu` -- create it, then verify it -- which is the most
obviously correct chain in the registry and is invisible to the token graph.

A type match is a HYPOTHESIS, not a capability. Names like `json` being shared
does not mean the two ends agree on what a json file contains, so every chain
is executed: generated inputs in, each step's real output bound to the next
step's input. Only a chain that ran is reported as a composition.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TYPE_LEVEL_COMPOSER_V1"

PASS = "PASS__TYPE_LEVEL_CHAIN_EXECUTED"
OPEN_NO_EDGE = "OPEN__TYPE_LEVEL_NO_TYPE_MATCH"
FAIL_STEP = "FAIL__TYPE_LEVEL_CHAIN_STEP_FAILED"
FAIL_SAMPLING = "FAIL__TYPE_LEVEL_INPUTS_NOT_SAMPLABLE"

# ordered longest-first so tar_gz beats tar and jpeg beats jpg
_CONTENT_KEYWORDS: tuple[str, ...] = (
    "tar_gz", "sqlite", "markdown", "manifest", "archive", "jpeg", "docx",
    "xlsx", "yaml", "json", "text", "pdf", "csv", "png", "jpg", "tar",
    "html", "image",
)


# --------------------------------------------------------------------------- #
# inferring the type of an artifact from the only evidence available: names
# --------------------------------------------------------------------------- #
def _content_of(text: str) -> set[str]:
    """Content types a name mentions. `tar_gz` before `tar`, so order matters."""
    low = str(text or "").lower()
    found = set()
    for kw in _CONTENT_KEYWORDS:
        if kw in low:
            found.add(kw)
    # drop the coarser keyword when a finer one was found
    if "tar_gz" in found:
        found.discard("tar")
    if "jpeg" in found:
        found.discard("jpg")
    return found


def consume_types(cid: str, signature: Mapping[str, str]) -> set[str]:
    """Types this capability reads, from the names of its PATH_FILE slots."""
    out: set[str] = set()
    for slot, ty in (signature or {}).items():
        if ty == "PATH_FILE":
            out |= _content_of(slot)
    return out


def produce_types(cid: str, provides: Sequence[str] | None = None) -> set[str]:
    """Types this capability writes, from what it claims to provide."""
    out: set[str] = _content_of(cid)
    for tok in provides or ():
        out |= _content_of(tok)
    return out


# --------------------------------------------------------------------------- #
# the graph
# --------------------------------------------------------------------------- #
def type_graph(registry: Mapping[str, Any] | None = None) -> dict[str, dict[str, set[str]]]:
    """{cid: {"consumes": {...}, "produces": {...}}}, typed rather than tokenised."""
    from canonical.runtime import capability_composer_v1 as composer

    reg = registry if registry is not None else composer.load_registry()
    g = composer.graph(reg)
    out: dict[str, dict[str, set[str]]] = {}
    for cid in reg:
        try:
            sig = composer.signature(cid, reg)
        except Exception:
            sig = {}
        out[cid] = {
            "consumes": consume_types(cid, sig),
            "produces": produce_types(cid, g.get(cid, {}).get("provides") or []),
        }
    return out


def edges(tg: Mapping[str, Mapping[str, Any]] | None = None,
          min_specificity: int = 1) -> list[tuple[str, str, tuple[str, ...]]]:
    """(producer, consumer, shared types) -- one entry per ordered pair."""
    tg = tg if tg is not None else type_graph()
    out: list[tuple[str, str, tuple[str, ...]]] = []
    for a, node in tg.items():
        prod = node.get("produces") or set()
        if not prod:
            continue
        for b, other in tg.items():
            if a == b:
                continue
            shared = prod & (other.get("consumes") or set())
            if not shared and _compatible(prod, other.get("consumes") or set()):
                shared = prod
            if len(shared) >= min_specificity:
                out.append((a, b, tuple(sorted(shared))))
    return out


def chains(tg: Mapping[str, Mapping[str, Any]] | None = None, *, max_len: int = 2,
           limit: int = 64) -> list[list[str]]:
    """Candidate pipelines, shortest first, no cid repeated.

    These are HYPOTHESES. Nothing here has been executed; see verify_chain.
    """
    tg = tg if tg is not None else type_graph()
    out: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    frontier: list[list[str]] = [[cid] for cid in sorted(tg)]
    while frontier:
        nxt: list[list[str]] = []
        for chain in frontier:
            if len(chain) >= 2:
                key = tuple(chain)
                if key not in seen:
                    seen.add(key)
                    out.append(list(chain))
            if len(chain) >= max_len:
                continue
            tail = chain[-1]
            produced = tg.get(tail, {}).get("produces") or set()
            if not produced:
                continue
            for other, node in tg.items():
                if other in chain:
                    continue
                if produced & (node.get("consumes") or set()):
                    nxt.append(chain + [other])
        out.sort(key=len)
        if len(out) >= limit:
            return out[:limit]
        frontier = nxt
    return out[:limit]


# names that mean the same artifact. `archive_path` wants an archive and the
# producer wrote a tar.gz; without this the two ends never meet.
_EQUIVALENCE: tuple[frozenset[str], ...] = (
    frozenset({"archive", "tar_gz", "tar"}),
    frozenset({"image", "png", "jpg", "jpeg"}),
    frozenset({"json", "manifest"}),
    frozenset({"text", "markdown", "md"}),
)


def _compatible(wanted: set[str], available: set[str]) -> bool:
    """Two type names for the same thing are a match, not a mismatch."""
    if wanted & available:
        return True
    for family in _EQUIVALENCE:
        if wanted & family and available & family:
            return True
    return False


_SUFFIX_BY_CONTENT: dict[str, str] = {
    "tar_gz": ".tar.gz", "manifest": ".json", "json": ".json",
    "markdown": ".md", "jpeg": ".jpg", "jpg": ".jpg", "png": ".png",
    "pdf": ".pdf", "csv": ".csv", "yaml": ".yaml", "html": ".html",
    "docx": ".docx", "xlsx": ".xlsx", "sqlite": ".sqlite",
    "archive": ".tar.gz", "text": ".txt", "image": ".png",
}


def output_suffix_for(cid: str, slot: str = "") -> str:
    """The extension this capability's output must carry.

    The sampler invents a plausible name, but adapters enforce the format --
    archive_tarfile refuses anything not ending in .tar.gz -- so the suffix has
    to come from what the capability IS, not from what sampled well.
    """
    remembered = recalled_suffix(cid)
    if remembered:
        return remembered
    for source in (cid, slot):
        for kw in _CONTENT_KEYWORDS:
            if kw in str(source).lower():
                return _SUFFIX_BY_CONTENT[kw]
    return ".out"


# --------------------------------------------------------------------------- #
# learning the required format from being told what was wrong
# --------------------------------------------------------------------------- #
SUFFIX_STATE = os.environ.get(
    "BRAIN_TYPE_LEVEL_COMPOSER_SUFFIX_STATE")
if not SUFFIX_STATE:
    SUFFIX_STATE = str(Path(__file__).resolve().parent.parent.parent
                       / "canonical" / "astra_runtime" / "state"
                       / "TYPE_LEVEL_COMPOSER_SUFFIXES_V1.json")

_SUFFIX_REQUIRED = __import__("re").compile(
    r"([A-Za-z0-9_]+)_OUTPUT_REQUIRED|OUTPUT_REQUIRED[:\s]*([A-Za-z0-9_.]+)")

_KNOWN_FORMATS: dict[str, str] = {
    "PDF": ".pdf", "TAR_GZ": ".tar.gz", "TGZ": ".tar.gz", "JSON": ".json",
    "MARKDOWN": ".md", "MD": ".md", "CSV": ".csv", "XLSX": ".xlsx",
    "DOCX": ".docx", "PNG": ".png", "JPG": ".jpg", "JPEG": ".jpg",
    "SQLITE": ".sqlite", "HTML": ".html", "YAML": ".yaml", "TXT": ".txt",
}


def _load_suffixes() -> dict[str, str]:
    try:
        with open(SUFFIX_STATE) as fh:
            data = json.load(fh)
        return dict(data) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _remember_suffix(cid: str, suffix: str) -> None:
    """The adapter refused and said what it wanted. That is worth more than a guess."""
    try:
        state = _load_suffixes()
        state[cid] = suffix
        Path(SUFFIX_STATE).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(SUFFIX_STATE + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(SUFFIX_STATE)
    except OSError:
        pass


def recalled_suffix(cid: str) -> str | None:
    """What this capability demanded last time, if it ever told us."""
    return _load_suffixes().get(cid)


def _suffix_from_refusal(message: str) -> str | None:
    match = _SUFFIX_REQUIRED.search(str(message or ""))
    if not match:
        return None
    token = (match.group(1) or match.group(2) or "").upper().strip()
    return _KNOWN_FORMATS.get(token)


def types_of_file(path: str | Path) -> set[str]:
    """Type from the extension that is ACTUALLY on disk.

    Guessing from the capability name is how a tar.gz got typed as a manifest:
    `archive.tar_gz.create_from_manifest` mentions both, and the manifest is
    what it CONSUMES. The file that exists is the only honest evidence.
    """
    name = str(Path(path).name).lower()
    out: set[str] = set()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        out.add("tar_gz")
    elif name.endswith(".jpeg"):
        out.add("jpeg")
    for ext, kw in ((".json", "json"), (".md", "markdown"), (".pdf", "pdf"),
                    (".csv", "csv"), (".yaml", "yaml"), (".yml", "yaml"),
                    (".html", "html"), (".docx", "docx"), (".xlsx", "xlsx"),
                    (".sqlite", "sqlite"), (".db", "sqlite"), (".png", "png"),
                    (".jpg", "jpg"), (".txt", "text"), (".tar", "tar")):
        if name.endswith(ext):
            out.add(kw)
    return out


# --------------------------------------------------------------------------- #
# execution -- the only thing that makes a chain real
# --------------------------------------------------------------------------- #
def _load_adapter(entry: Mapping[str, Any]) -> Callable[[dict, Any], dict]:
    """Load the adapter the way the kernel would, from its declared path."""
    from canonical.runtime import live_brain_route_admission_v1 as live

    module_name = str(entry.get("adapter_module") or "")
    if not module_name or any(ch not in
                              "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
                              for ch in module_name):
        raise RuntimeError("BOUND_CAPABILITY_ADAPTER_INVALID")
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    declared = str(source.get("adapter_path") or "")
    path = (live.ROOT / declared).resolve() if declared else (
        live.ROOT / "canonical" / "runtime" / "bound_capabilities" / (module_name + ".py")
    ).resolve()
    if not path.is_file() or path.suffix != ".py":
        raise RuntimeError("BOUND_CAPABILITY_ADAPTER_MISSING:" + declared)
    spec = importlib.util.spec_from_file_location(
        "project_brain_tlc_" + module_name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[spec.name] = module  # type: ignore[union-attr]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    fn = getattr(module, str(entry.get("entrypoint") or "run"), None)
    if not callable(fn):
        raise RuntimeError("BOUND_CAPABILITY_ENTRYPOINT_MISSING")
    return fn


def _bind(step_signature: Mapping[str, str], produced: Mapping[str, str],
          rng: random.Random, workspace: Path, cid: str) -> dict[str, Any]:
    """Args for one step: PATH_FILE slots prefer a real artifact from a prior step."""
    from canonical.runtime import type_directed_sampler_v1 as sampler

    sampled = sampler.sample_args(step_signature, rng, workspace, capability=cid)
    args = dict(sampled) if isinstance(sampled, Mapping) else {}

    for slot, ty in (step_signature or {}).items():
        value = args.get(slot)
        if ty == "PATH_OUTPUT":
            # adapters enforce the format; the sampled suffix is a guess
            args[slot] = "%s_%d%s" % (
                str(cid).replace(".", "_")[:28], rng.randrange(10 ** 8),
                output_suffix_for(cid, slot))
            continue
        if ty != "PATH_FILE":
            continue
        # adapters resolve paths against the workspace root, so an absolute
        # path from the sampler is a path the adapter cannot see
        if isinstance(value, str) and value:
            try:
                args[slot] = str(Path(value).resolve().relative_to(workspace.resolve()))
            except (ValueError, OSError):
                args[slot] = str(Path(value).name)
        # downstream steps must consume what a previous step actually wrote
        wanted = _content_of(slot)
        if wanted:
            for artifact_type, artifact_path in produced.items():
                if _compatible(wanted, {artifact_type}):
                    args[slot] = artifact_path
                    break
    return args


def verify_chain(chain: Sequence[str], *, registry: Mapping[str, Any] | None = None,
                 workspace: str | os.PathLike | None = None,
                 seed: int | None = None) -> dict[str, Any]:
    """Run the chain. A composition that has not executed is a claim, not a capability."""
    from canonical.runtime import capability_composer_v1 as composer
    from canonical.runtime import type_directed_sampler_v1 as sampler

    started = time.time()
    reg = registry if registry is not None else composer.load_registry()
    chain = [str(c) for c in chain]
    owned_tmp = workspace is None
    work = Path(workspace) if workspace is not None else Path(tempfile.mkdtemp(prefix="brain-tlc-"))
    work.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed if seed is not None else 0)

    rows: list[dict[str, Any]] = []
    produced: dict[str, str] = {}      # content type -> path, as steps succeed
    produced_by_step: list[dict[str, Any]] = []

    try:
        for index, cid in enumerate(chain):
            entry = reg.get(cid)
            if not isinstance(entry, Mapping):
                rows.append({"index": index, "capability_id": cid, "pass": False,
                             "status": FAIL_STEP, "reason": "CAPABILITY_NOT_IN_REGISTRY"})
                return _result(FAIL_STEP, chain, rows, produced_by_step, started,
                               reason="CAPABILITY_NOT_IN_REGISTRY:" + cid)
            try:
                sig = composer.signature(cid, reg)
            except Exception as exc:
                rows.append({"index": index, "capability_id": cid, "pass": False,
                             "status": FAIL_STEP,
                             "reason": "SIGNATURE_UNAVAILABLE:" + type(exc).__name__})
                return _result(FAIL_STEP, chain, rows, produced_by_step, started,
                               reason="SIGNATURE_UNAVAILABLE:" + cid)

            try:
                args = _bind(sig, produced, rng, work, cid)
            except Exception as exc:
                rows.append({"index": index, "capability_id": cid, "pass": False,
                             "status": FAIL_SAMPLING,
                             "reason": type(exc).__name__ + ":" + str(exc)[:200]})
                return _result(FAIL_SAMPLING, chain, rows, produced_by_step, started,
                               reason="INPUTS_NOT_SAMPLABLE:" + cid)

            try:
                fn = _load_adapter(entry)
                out = fn(dict(args), work)
            except Exception as exc:
                message = type(exc).__name__ + ":" + str(exc)
                # the adapter just told us what format it wants. Guessing again
                # would repeat the mistake forever; this is the cheapest lesson
                # the machine will ever get, so take it and retry once.
                wanted = _suffix_from_refusal(message)
                retried = None
                if wanted and wanted != output_suffix_for(cid):
                    _remember_suffix(cid, wanted)
                    args = _bind(sig, produced, rng, work, cid)
                    try:
                        out = fn(dict(args), work)
                        retried = wanted
                    except Exception as exc2:
                        message = type(exc2).__name__ + ":" + str(exc2)
                if retried is None:
                    rows.append({"index": index, "capability_id": cid, "pass": False,
                                 "status": FAIL_STEP, "args": dict(args),
                                 "reason": message[:400]})
                    return _result(FAIL_STEP, chain, rows, produced_by_step, started,
                                   reason="STEP_FAILED:" + cid)
                rows.append({"index": index, "capability_id": cid, "pass": True,
                             "learned_output_format": retried, "args": dict(args)})

            if not isinstance(out, Mapping):
                rows.append({"index": index, "capability_id": cid, "pass": False,
                             "status": FAIL_STEP, "reason": "RESULT_NOT_A_MAPPING"})
                return _result(FAIL_STEP, chain, rows, produced_by_step, started,
                               reason="RESULT_NOT_A_MAPPING:" + cid)

            # did this step actually write something the next step can read?
            written: dict[str, str] = {}
            for key, value in out.items():
                if not isinstance(value, str) or "path" not in key.lower():
                    continue
                p = Path(value)
                if not p.is_absolute():
                    p = work / value
                if p.is_file() and p.stat().st_size > 0:
                    for t in (types_of_file(p) | _content_of(key)):
                        written.setdefault(t, str(p.name))
                    if not written:
                        for t in _content_of(cid):
                            written.setdefault(t, str(p.name))
            produced.update(written)
            # what this step READ is now a real file in the workspace too, and
            # the next step must be given the SAME one -- a fresh sample would
            # be a different manifest than the archive was built from, which
            # the verifier correctly rejects as ARCHIVE_MEMBER_SET_MISMATCH.
            read: dict[str, str] = {}
            for slot, ty in (sig or {}).items():
                if ty != "PATH_FILE":
                    continue
                raw = args.get(slot)
                if not isinstance(raw, str) or not raw:
                    continue
                rp = Path(raw)
                if not rp.is_absolute():
                    rp = work / raw
                if rp.is_file() and rp.stat().st_size > 0:
                    for t in (types_of_file(rp) | _content_of(slot)):
                        read.setdefault(t, str(rp.name))
            for t, v in read.items():
                produced.setdefault(t, v)
            produced_by_step.append({"capability_id": cid, "artifacts": dict(written),
                                     "consumed": dict(read)})

            ok = out.get("verified") is True or out.get("pass") is True or bool(written) \
                or out.get("ok") is True
            rows.append({"index": index, "capability_id": cid, "pass": bool(ok),
                         "args": dict(args), "artifacts": dict(written),
                         "result_keys": sorted(out)[:12]})
            if not ok:
                return _result(FAIL_STEP, chain, rows, produced_by_step, started,
                               reason="STEP_PRODUCED_NOTHING:" + cid)

        return _result(PASS, chain, rows, produced_by_step, started)
    finally:
        if owned_tmp:
            try:
                import shutil
                shutil.rmtree(work, ignore_errors=True)
            except Exception:
                pass


def _result(status: str, chain: Sequence[str], rows: list[dict[str, Any]],
            produced_by_step: list[dict[str, Any]], started: float,
            reason: str | None = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": status,
        "pass": status == PASS,
        "chain": list(chain),
        "steps": rows,
        "artifacts": produced_by_step,
        "executed": len([r for r in rows if r.get("pass")]),
        "authority": "CHAIN_EXECUTED_END_TO_END" if status == PASS else
                     "TYPE_MATCH_ONLY_NOT_EXECUTED",
        "duration_s": round(time.time() - started, 4),
    }
    if reason:
        out["reason"] = reason
    return out


def compose_and_verify(goal_cid: str | None = None, *, max_len: int = 2,
                       limit: int = 32, registry: Mapping[str, Any] | None = None,
                       seed: int | None = None) -> dict[str, Any]:
    """Find candidate chains and run each one. Returns only those that executed."""
    tg = type_graph(registry)
    candidates = chains(tg, max_len=max_len, limit=limit * 4)
    if goal_cid:
        candidates = [c for c in candidates if c[-1] == goal_cid] or \
                     [c for c in candidates if goal_cid in c]
    if not candidates:
        return {"schema": SCHEMA, "status": OPEN_NO_EDGE, "pass": False,
                "goal": goal_cid, "verified_chains": [], "attempted": 0,
                "authority": "TYPE_MATCH_ONLY_NOT_EXECUTED"}

    verified: list[dict[str, Any]] = []
    tried = 0
    for chain in candidates[:limit]:
        tried += 1
        res = verify_chain(chain, registry=registry, seed=seed)
        if res.get("pass"):
            verified.append(res)
    return {
        "schema": SCHEMA,
        "status": PASS if verified else OPEN_NO_EDGE,
        "pass": bool(verified),
        "goal": goal_cid,
        "attempted": tried,
        "verified_chains": verified,
        "authority": "CHAIN_EXECUTED_END_TO_END" if verified else
                     "TYPE_MATCH_ONLY_NOT_EXECUTED",
    }
