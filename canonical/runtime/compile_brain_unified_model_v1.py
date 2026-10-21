#!/usr/bin/env python3
"""Compile the whole live Brain into one content-addressed model artifact.

What this is
------------
The repository already owns a large, heterogeneous capability surface:

* the live verified capability registry (promoted bound capabilities plus
  receipt-backed executions) served by ``live_integrated_brain_v1``;
* the unified cognitive fabric's engine modes;
* internalized skill procedures (``SKILL.md``) that were harvested from
  white-box donors and kept as Brain-owned text;
* the laws, research notes, governance records and orientation documents that
  define what the machine is allowed to mean by "capable".

What it did not own was *one thing*: a single artifact that can be loaded,
hashed, shipped, and executed as a model of all of that. This compiler produces
that artifact.

What the artifact is and is not
-------------------------------
It is a **compiled projection**, not a new authority:

* capabilities are *descriptors plus routes*.  Execution still goes through the
  existing verified adapter, which re-reads the live registry and re-checks the
  independent-verification evidence at call time.  Deleting a capability from
  the live registry therefore disables it in the model; the model cannot
  promote, widen, or launder anything.
* knowledge is an *index*, not an embedded copy.  The repo's theory keeps
  knowledge external and just-in-time, so the model stores content hashes,
  headings, and retrieval terms, and the runtime opens the file only when a
  query asks for it.  No text is counted as capability.
* there are no trained weights in this artifact and it does not claim any.  It
  is the deterministic executable model of what Brain currently owns.  Learned
  mechanisms (the H100 parametric packs) keep their own verification records
  and are referenced, not silently absorbed.

Determinism
-----------
No timestamps, no environment-derived values, and no unsorted iteration enter
the artifact.  Compiling twice from the same tree produces byte-identical
output, and the ``digest`` block hashes the canonical JSON of the artifact with
that block removed.  ``compile_model()`` is the only writer.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import warnings
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_V1"
MODEL_ID = "BRAIN-UNIFIED-MODEL-V1"
MODEL_VERSION = 1
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
FABRIC_PATH = "canonical/runtime/unified_cognitive_fabric_v1.py"
REGISTRY_PATH = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

# Retrieval is intentionally simple and deterministic. A token that appears in
# every capability carries no routing information; ``_idf_weight`` below makes
# that mechanical rather than a hand-tuned keyword list.
STOPWORDS = frozenset(
    """
    a an and are as at be by can could do does for from has have how i if in into
    is it its of on or our that the their them then there these this to using was
    we what when where which who why will with without you your
    """.split()
)

# Knowledge sources: markdown that carries law, research, orientation or
# procedure.  Superseded files stay in the index (history is useful context) but
# are labelled by the version rule, never presented as current authority.
KNOWLEDGE_GLOBS = (
    "*.md",
    "canonical/README.md",
    "canonical/laws/*.md",
    "canonical/research/**/*.md",
    "canonical/governance/*.md",
    "canonical/reasoning/*.md",
    "canonical/evidence/*.md",
    "canonical/handoffs/*.md",
    "canonical/verification/*.md",
    "canonical/capabilities/**/*.md",
    "canonical/research_sources/**/*.md",
)
KNOWLEDGE_EXCLUDE_PREFIXES = (
    "canonical/astra_runtime/tmp/",
    "canonical/capabilities/internalized/software_engineering/mini_swe_agent_02",
)
STRUCTURED_KNOWLEDGE_PATHS = (
    "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
    "canonical/verification/HONEST_SUITE_BASELINE_20261014_V1.json",
)
STRUCTURED_KNOWLEDGE_GLOBS = ("canonical/capabilities/frontier/*.json",)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+.-]*")
PLACEHOLDER_RE = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")


class UnifiedModelCompileError(ValueError):
    """A compile input was missing or contradicted the canon."""


# --------------------------------------------------------------------------- bytes


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def artifact_digest(model: Mapping[str, Any]) -> str:
    """Digest of the model with its own digest block removed."""
    body = {k: v for k, v in model.items() if k != "digest"}
    return digest_value(body)


# --------------------------------------------------------------------------- text


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for token in TOKEN_RE.findall(str(text or "").casefold()):
        token = token.strip("._-")
        if len(token) < 2 or token in STOPWORDS:
            continue
        out.append(token)
    return out


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        item = str(raw or "").strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _first_paragraph(text: str) -> str:
    paragraph: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("```"):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    return " ".join(paragraph)[:400]


def _headings(text: str, limit: int = 40) -> list[str]:
    out: list[str] = []
    for _, title in HEADING_RE.findall(text):
        clean = " ".join(title.split())
        if clean and clean not in out:
            out.append(clean[:160])
        if len(out) >= limit:
            break
    return out


def _term_counts(text: str, limit: int = 48) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokenize(text):
        counts[token] = counts.get(token, 0) + 1
    return dict(
        sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    )


def _bullets(text: str, limit: int = 40) -> list[str]:
    """Extract procedure lines from a SKILL.md.

    Skill files are the Brain-owned residue of a white-box donor: the useful
    procedure, not the donor's runtime.  Keeping the operational lines in the
    model is what makes a skill executable advice rather than a filename.
    """
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("- ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ")):
            continue
        clean = " ".join(stripped.lstrip("-*").strip().split())
        if len(clean) < 12:
            continue
        if clean not in out:
            out.append(clean[:280])
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- law authority


def _law_family_and_version(path: Path) -> tuple[str, int] | None:
    match = re.fullmatch(r"(.+?)_V(\d+)\.md", path.name)
    if not match:
        return None
    return match.group(1), int(match.group(2))


def law_authority_map(law_paths: Iterable[Path]) -> dict[str, str]:
    """Highest version in a family is current; every lower version is history.

    This is the repository's own rule (``README.md`` section 6).  It is applied
    mechanically here so the model can never hand an agent a superseded law as
    if it were current authority.
    """
    highest: dict[str, tuple[int, str]] = {}
    known: list[tuple[str, str, int]] = []
    for path in law_paths:
        parsed = _law_family_and_version(path)
        if parsed is None:
            continue
        rel = path.relative_to(ROOT).as_posix()
        family, version = parsed
        known.append((rel, family, version))
        if family not in highest or version > highest[family][0]:
            highest[family] = (version, rel)
    current = {rel for version, rel in highest.values()}
    out: dict[str, str] = {}
    by_pass: dict[str, bool] = {}
    for path in law_paths:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")[:4000]
        if re.search(r"status\s*:\s*SUPERSEDED", text, flags=re.IGNORECASE):
            by_pass[rel] = True
    for rel, _, _ in known:
        if rel in current and not by_pass.get(rel):
            out[rel] = "CURRENT_LAW"
        elif by_pass.get(rel):
            out[rel] = "SUPERSEDED_LAW"
        else:
            out[rel] = "HISTORICAL_LAW_VERSION"
    return out


# --------------------------------------------------------------------------- sources


def _live_registry(root: Path) -> dict[str, Mapping[str, Any]]:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from canonical.runtime import live_integrated_brain_v1 as live_brain

    registry = live_brain.load_verified_registry()
    if not isinstance(registry, Mapping) or not registry:
        raise UnifiedModelCompileError("LIVE_VERIFIED_REGISTRY_EMPTY")
    return {str(k): v for k, v in registry.items() if isinstance(v, Mapping)}


def _fabric_surfaces(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Read the fabric's mode tables without importing ~30 engine modules."""
    path = root / FABRIC_PATH
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id in {"ENGINE_DESCRIPTORS", "META_ORCHESTRATORS"}:
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, SyntaxError) as exc:
                raise UnifiedModelCompileError(
                    "FABRIC_MODE_TABLE_NOT_LITERAL:" + target.id
                ) from exc
            if not isinstance(value, dict):
                raise UnifiedModelCompileError("FABRIC_MODE_TABLE_NOT_DICT:" + target.id)
            found[target.id] = {str(k): str(v) for k, v in value.items()}
    if "ENGINE_DESCRIPTORS" not in found:
        raise UnifiedModelCompileError("FABRIC_ENGINE_DESCRIPTORS_MISSING")
    return found["ENGINE_DESCRIPTORS"], found.get("META_ORCHESTRATORS", {})


def _placeholders(value: Any) -> list[str]:
    out: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, str):
            for name in PLACEHOLDER_RE.findall(item):
                if name not in out:
                    out.append(name)
        elif isinstance(item, Mapping):
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return sorted(out)


def _adapter_imports(root: Path, rel: str | None) -> list[str]:
    if not rel:
        return []
    path = root / rel
    if not path.is_file():
        return []
    try:
        # Repository sources include regex-heavy modules written before raw
        # strings were the norm. Their escape warnings are not this compiler's
        # finding, and printing them would make a deterministic build noisy.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in modules:
                    modules.append(top)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            top = node.module.split(".")[0]
            if top not in modules:
                modules.append(top)
    return sorted(modules)


def _dependency_declaration(
    entry: Mapping[str, Any], root: Path
) -> dict[str, Any]:
    """Record the capability's *declared* dependencies without probing for them.

    This used to be called ``_dependency_probe`` and it answered "are they
    present here?" by calling ``shutil.which`` and ``importlib.util.find_spec``
    at compile time.  That made the artifact depend on the machine that compiled
    it, which contradicts this module's own contract -- "no environment-derived
    values ... compiling twice from the same tree produces byte-identical
    output".  Measured, it was not a theoretical worry: installing Pillow and
    nothing else changed the model digest from ``4d7e627e...`` to ``8c158876...``
    across 6 capabilities, and the verifier's own
    ``recompilation_is_byte_identical`` case failed on that machine.

    Presence is a property of the machine, not of the tree, so it is no longer
    recorded here.  What is recorded is the tree-derived *declaration*: which
    names would have to resolve, and by which mechanism.  ``UnifiedModel``
    probes them at run time, where the answer is actually true of the machine
    answering.  Nothing here touches the file system or the import state.

    This is deliberately not called "available": BOUND_APT_METADATA_NOT_FOUND
    and a dozen other fail-closed adapter preconditions cannot be decided by
    looking at a file system.  The verifier measures actual execution; this
    field only says what an operator would have to install or import.
    """
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    source_type = str(source.get("type") or "unknown")
    adapter_path = source.get("adapter_path") or source.get("path")
    executable = source.get("executable")
    module = source.get("module")

    checked: list[str] = []
    executables: list[str] = []
    kind = "DECLARED_SOURCE_UNKNOWN"

    if executable:
        kind = "EXECUTABLE"
        checked.append(str(executable))
        executables.append(str(executable))
    elif source_type in {"pypi", "npm", "apt", "system_tool", "brain_bound_system_tool"}:
        kind = "PACKAGE_OR_SYSTEM_TOOL"
        if source_type == "npm":
            checked.append("node")
            executables.append("node")
        if module:
            checked.append(str(module))
            # An npm module is resolved by node, not by the Python import
            # machinery, so it is declared but not probed here -- matching the
            # original behaviour, which only probed the npm case via "node".
    else:
        kind = "PYTHON_SOURCE"
        modules = _adapter_imports(root, str(adapter_path) if adapter_path else None)
        if module and str(module) not in modules:
            modules = sorted(set(modules) | {str(module)})
        for name in modules:
            if name in {"__future__"} or name.startswith("canonical"):
                continue
            checked.append(name)
            # Standard-library membership is a property of the interpreter, not
            # of this tree, so it is not filtered here. Resolving a stdlib name
            # succeeds at run time and costs nothing.

    return {
        "kind": kind,
        "declared_dependencies_checked": sorted(checked),
        # Names resolved on PATH. Every other declared name is resolved through
        # the Python import machinery. Stating the exception rather than one
        # method per name keeps the artifact free of restated data.
        "declared_dependency_executables": sorted(executables),
    }


def _capability_row(
    capability_id: str,
    entry: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    template = entry.get("action_template")
    declared = entry.get("declared_action_template")
    contract = declared if isinstance(declared, Mapping) and declared else template
    if not isinstance(contract, Mapping):
        contract = {}

    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    verification = (
        entry.get("verification") if isinstance(entry.get("verification"), Mapping) else {}
    )
    evidence_path = verification.get("receipt_path") or verification.get("evidence_path")

    keywords = [str(x) for x in (entry.get("keywords") or []) if str(x).strip()]
    id_tokens = tokenize(capability_id.replace("/", " ").replace(".", " "))
    provides = [str(x) for x in (entry.get("provides") or []) if str(x).strip()]
    provide_tokens: list[str] = []
    for item in provides:
        provide_tokens.extend(tokenize(item.replace(".", " ").replace("_", " ")))

    triggers = _unique(
        [k.casefold() for k in keywords]
        + id_tokens
        + provide_tokens
    )

    expect = contract.get("expect") if isinstance(contract.get("expect"), Mapping) else {}
    expected_field = str(expect.get("field") or "").strip() or None

    independent = (
        verification.get("independent_verified") is True
        or verification.get("independently_verified") is True
        or isinstance(verification.get("independently_verified_by"), str)
        or verification.get("producer_independent") is True
    )

    source_path = source.get("adapter_path") or source.get("path")
    source_sha = None
    if isinstance(source_path, str) and (root / source_path).is_file():
        source_sha = digest_file(root / source_path)

    evidence_sha = None
    if isinstance(evidence_path, str) and (root / evidence_path).is_file():
        evidence_sha = digest_file(root / evidence_path)

    return {
        "id": capability_id,
        "kind": (
            "RECEIPT_BACKED_CAPABILITY"
            if entry.get("capability_source") == "receipt_projection"
            else "BOUND_CAPABILITY"
        ),
        "registry_status": str(entry.get("status") or "UNSPECIFIED"),
        "incremental_spend_usd": entry.get("incremental_spend_usd", 0),
        "cost": entry.get("cost", 1),
        "triggers": triggers,
        "input_names": _placeholders(contract),
        "input_contract_source": "declared_action_template" if contract is declared else "action_template",
        "output_fields": [expected_field] if expected_field else [],
        "requires": sorted(str(x) for x in (entry.get("requires") or [])),
        "provides": sorted(provides),
        "adapter_module": entry.get("adapter_module"),
        "entrypoint": entry.get("entrypoint"),
        "route": {
            "carrier": "verified_bound_capability_execution_adapter_v1.execute",
            "carrier_path": "canonical/runtime/verified_bound_capability_execution_adapter_v1.py",
            "call": "execute(capability_id, inputs=..., instance_id=...)",
            "authority": "LIVE_VERIFIED_REGISTRY_RECHECKED_AT_CALL_TIME",
        },
        "verification": {
            "independent_verification_evident": independent,
            "mission_id": verification.get("mission_id"),
            "producer_independent": verification.get("producer_independent"),
            "module_sha256": verification.get("module_sha256"),
            "evidence_path": evidence_path,
            "evidence_sha256": evidence_sha,
            "evidence_present_note": (
                "embedding this record does not grant credit; the adapter re-reads "
                "the live registry and its evidence on every call"
            ),
        },
        "provenance": {
            "source_path": source_path,
            "source_sha256": source_sha,
            "source_type": source.get("type"),
            "source_module": source.get("module"),
            "source_executable": source.get("executable"),
        },
        "declared_dependencies": _dependency_declaration(entry, root),
        "platforms": sorted(str(x) for x in (entry.get("platforms") or [])),
    }


# --------------------------------------------------------------------------- grammar


def _build_grammar(capabilities: list[Mapping[str, Any]], engines: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[tuple[str, str, int]] = []
    for cap in capabilities:
        cid = str(cap["id"])
        seen: set[str] = set()
        # A multiword keyword such as "direct label" contributes both of its
        # words; keeping the phrase as a single key would make it unreachable
        # because the runtime tokenizer never produces spaces.
        for trigger in cap.get("triggers") or []:
            for token in tokenize(str(trigger)):
                if token in seen:
                    continue
                seen.add(token)
                rows.append((token, cid, 3 if " " in str(trigger) else 2))
        for token in tokenize(cid):
            if token not in seen:
                rows.append((token, cid, 3))
                seen.add(token)
        # The capability id itself gets the strongest signal when a caller names
        # it, but the runtime also checks the literal id separately.
        rows.append((cid.casefold(), cid, 12))
    for engine in engines:
        eid = str(engine["id"])
        for trigger in engine.get("triggers") or []:
            for token in tokenize(str(trigger)):
                rows.append((token, eid, 2))
        rows.append((eid.casefold().replace("engine:", ""), eid, 8))

    postings: dict[str, dict[str, int]] = {}
    doc_freq: dict[str, int] = {}
    for token, cid, weight in rows:
        posting = postings.setdefault(token, {})
        posting[cid] = max(posting.get(cid, 0), weight)
        if token not in doc_freq:
            doc_freq[token] = 0
    for token, posting in postings.items():
        doc_freq[token] = len(posting)

    total = max(1, len(capabilities) + len(engines))
    index: dict[str, dict[str, float]] = {}
    for token in sorted(postings):
        idf = 1.0 + (total / (1.0 + doc_freq[token]))
        index[token] = {
            cid: round(weight * idf, 6)
            for cid, weight in sorted(postings[token].items())
        }

    return {
        "tokenizer": "lowercase-ascii-words-then-stopword-removal",
        "stopwords": sorted(STOPWORDS),
        "index": index,
        "confidence": {
            "minimum_best_score": 1.0,
            "minimum_coverage": 0.34,
            "coverage_definition": "matched_query_tokens / query_tokens",
            "tie_break": "lexicographic capability id",
        },
        "note": (
            "Routing is a deterministic lexical projection of declared triggers. "
            "It fails closed rather than guessing; unknown goals are exposed, not "
            "answered by a model."
        ),
    }


# --------------------------------------------------------------------------- knowledge


def _knowledge_rows(root: Path) -> list[dict[str, Any]]:
    paths: list[Path] = []
    for pattern in KNOWLEDGE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                paths.append(path)
    for pattern in STRUCTURED_KNOWLEDGE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                paths.append(path)
    for rel in STRUCTURED_KNOWLEDGE_PATHS:
        path = root / rel
        if path.is_file():
            paths.append(path)

    seen: set[str] = set()
    unique: list[Path] = []
    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in KNOWLEDGE_EXCLUDE_PREFIXES):
            continue
        if rel in seen:
            continue
        seen.add(rel)
        unique.append(path)

    laws = [p for p in unique if p.relative_to(root).as_posix().startswith("canonical/laws/")]
    authority = law_authority_map(laws)

    rows: list[dict[str, Any]] = []
    for path in unique:
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        if rel.endswith(".json"):
            try:
                doc = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                doc = None
            text = json.dumps(doc, sort_keys=True, ensure_ascii=False) if doc is not None else raw.decode("utf-8", errors="replace")
            title = ""
            if isinstance(doc, Mapping):
                for key in ("capability_id", "action_id", "schema", "objective", "title"):
                    value = doc.get(key)
                    if isinstance(value, str) and value.strip():
                        title = value.strip()
                        break
            headings = []
            summary = text[:400]
            kind = "STRUCTURED_RECORD"
        else:
            text = raw.decode("utf-8", errors="replace")
            headings = _headings(text)
            title = headings[0] if headings else path.stem.replace("_", " ")
            summary = _first_paragraph(text)
            kind = "LAW" if rel.startswith("canonical/laws/") else "DOCUMENT"
        rows.append(
            {
                "path": rel,
                "kind": kind,
                "title": title[:240],
                "title_terms": sorted(set(tokenize(title))),
                "headings": headings,
                "summary": summary,
                "bytes": len(raw),
                "sha256": digest_bytes(raw),
                "terms": _term_counts(text),
                "authority": authority.get(rel, "NOT_A_LAW"),
            }
        )
    return rows


def _skill_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    paths = sorted(
        {
            path
            for path in root.glob("canonical/capabilities/**/SKILL.md")
            if path.is_file()
        }
    )
    for path in paths:
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        headings = _headings(text)
        rows.append(
            {
                "id": "skill:" + rel,
                "kind": "SKILL_PROCEDURE",
                "path": rel,
                "title": (headings[0] if headings else path.parent.name)[:240],
                "title_terms": sorted(
                    set(tokenize(headings[0] if headings else path.parent.name))
                ),
                "headings": headings,
                "procedure": _bullets(text),
                "terms": _term_counts(text),
                "bytes": len(raw),
                "sha256": digest_bytes(raw),
            }
        )
    return rows


# --------------------------------------------------------------------------- model


def _engine_rows(root: Path) -> list[dict[str, Any]]:
    engines, meta = _fabric_surfaces(root)
    fabric_sha = digest_file(root / FABRIC_PATH)
    rows: list[dict[str, Any]] = []
    for mode, descriptor in sorted(engines.items()):
        rows.append(
            {
                "id": "engine:" + mode,
                "kind": "FABRIC_ENGINE",
                "mode": mode,
                "descriptor": descriptor,
                "triggers": tokenize(mode.replace("_", " ")),
                "route": {
                    "carrier": "unified_cognitive_fabric_v1.run",
                    "carrier_path": FABRIC_PATH,
                    "carrier_sha256": fabric_sha,
                    "call": "run({**request, 'mode': mode})",
                    "authority": "FABRIC_CONTRACTS_UNCHANGED",
                },
                "host_providers_may_be_required": True,
            }
        )
    for mode, descriptor in sorted(meta.items()):
        rows.append(
            {
                "id": "meta:" + mode,
                "kind": "FABRIC_META_ORCHESTRATOR",
                "mode": mode,
                "descriptor": descriptor,
                "triggers": tokenize(mode.replace("_", " ")),
                "route": {
                    "carrier": descriptor,
                    "carrier_path": FABRIC_PATH,
                    "carrier_sha256": fabric_sha,
                    "call": descriptor,
                    "authority": "FABRIC_CONTRACTS_UNCHANGED",
                },
                "host_providers_may_be_required": True,
            }
        )
    return rows


def _objective_block(root: Path) -> dict[str, Any]:
    rel = "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
    path = root / rel
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    return {
        "verbatim": str(doc.get("real_objective") or ""),
        "terminality": doc.get("mission_terminality"),
        "opus_5_5_role": doc.get("opus_5_5_role"),
        "spend_rule": doc.get("spend_rule"),
        "source": rel,
        "source_sha256": digest_bytes(raw),
    }


def _theory_block() -> dict[str, Any]:
    return {
        "effective_intelligence": (
            "BRAIN_OWNED_CAPABILITY_MECHANISMS + EXTERNAL_JIT_KNOWLEDGE + "
            "GENERAL_COMPUTATION_SUBSTRATE"
        ),
        "knowledge_policy": "EXTERNAL_JUST_IN_TIME__NEVER_COUNTED_AS_CAPABILITY",
        "capability_policy": "MUST_RUN_WITH_EVERY_OUTSIDE_MODEL_DELETED",
        "producer_cognition_model_dependency_count": 0,
    }


def compile_model(root: str | Path | None = None) -> dict[str, Any]:
    """Compile the model in memory. The caller decides whether to persist it."""
    base = Path(root or ROOT).resolve()
    registry = _live_registry(base)
    capabilities = [
        _capability_row(cid, registry[cid], base) for cid in sorted(registry)
    ]
    engines = _engine_rows(base)
    skills = _skill_rows(base)
    knowledge = _knowledge_rows(base)

    for row in capabilities:
        if not row["triggers"]:
            raise UnifiedModelCompileError("CAPABILITY_WITHOUT_TRIGGERS:" + row["id"])

    grammar = _build_grammar(capabilities, engines)

    included_sources: list[tuple[str, str]] = []
    for row in capabilities:
        source_path = row["provenance"].get("source_path")
        source_sha = row["provenance"].get("source_sha256")
        if isinstance(source_path, str) and isinstance(source_sha, str):
            included_sources.append((source_path, source_sha))
        evidence_path = row["verification"].get("evidence_path")
        evidence_sha = row["verification"].get("evidence_sha256")
        if isinstance(evidence_path, str) and isinstance(evidence_sha, str):
            included_sources.append((evidence_path, evidence_sha))
    for row in knowledge + skills:
        included_sources.append((str(row["path"]), str(row["sha256"])))
    for rel in (FABRIC_PATH, REGISTRY_PATH):
        path = base / rel
        if path.is_file():
            included_sources.append((rel, digest_file(path)))

    model: dict[str, Any] = {
        "schema": SCHEMA,
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "objective": _objective_block(base),
        "theory": _theory_block(),
        "capabilities": capabilities,
        "engines": engines,
        "skills": skills,
        "knowledge": knowledge,
        "grammar": grammar,
        "counts": {
            "capabilities": len(capabilities),
            "bound_capabilities": sum(
                1 for row in capabilities if row["kind"] == "BOUND_CAPABILITY"
            ),
            "receipt_backed_capabilities": sum(
                1 for row in capabilities if row["kind"] == "RECEIPT_BACKED_CAPABILITY"
            ),
            "engines": len(engines),
            "skills": len(skills),
            "knowledge_documents": len(knowledge),
            "routing_tokens": len(grammar["index"]),
        },
        "provenance": {
            "compiler": "canonical/runtime/compile_brain_unified_model_v1.py",
            "compiler_sha256": digest_file(
                base / "canonical/runtime/compile_brain_unified_model_v1.py"
            ),
            "source_tree_digest": digest_value(
                sorted(included_sources)
            ),
            "included_source_count": len(included_sources),
            "external_model_calls": 0,
            "network_calls": 0,
            "incremental_spend_usd": 0,
            "deterministic": True,
            "generated_from": "REPOSITORY_TREE_AT_COMPILE_TIME",
        },
        "non_claims": [
            "NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS",
            "NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY",
            "NOT_TERMINAL_AUTHORITY__ZERO_CAPABILITY_AND_TERMINAL_CREDIT",
            "NOT_A_REPLACEMENT_FOR_THE_LIVE_REGISTRY_OR_LAWS",
            "KNOWLEDGE_IS_INDEXED_NOT_EMBEDDED__RETRIEVED_JUST_IN_TIME",
            "COVERAGE_IS_NOT_CAPABILITY__EXECUTION_STILL_REQUIRES_DECLARED_SUBSTRATE",
        ],
    }
    model["digest"] = {
        "algorithm": "sha256",
        "scope": "CANONICAL_JSON_OF_THIS_OBJECT_WITHOUT_THE_DIGEST_BLOCK",
        "value": artifact_digest(model),
    }
    return model


def write_model(
    model: Mapping[str, Any],
    path: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> Path:
    base = Path(root or ROOT).resolve()
    target = Path(path) if path else base / DEFAULT_OUTPUT
    if not target.is_absolute():
        target = base / target
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(model, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    target.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    output = DEFAULT_OUTPUT
    if args:
        if len(args) != 2 or args[0] != "--output":
            print("usage: compile_brain_unified_model_v1.py [--output PATH]", file=sys.stderr)
            return 2
        output = args[1]
    model = compile_model()
    target = write_model(model, output)
    reloaded = json.loads(target.read_text(encoding="utf-8"))
    recomputed = artifact_digest(reloaded)
    if recomputed != model["digest"]["value"]:
        raise SystemExit("MODEL_DIGEST_DOES_NOT_RELOAD")
    print("WROTE", target.relative_to(ROOT).as_posix())
    print("DIGEST", recomputed)
    for key, value in model["counts"].items():
        print(f"{key.upper()} {value}")
    print("BYTES", target.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
