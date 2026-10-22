"""Live integrated Brain V1.

Runs a compiled real task through the existing verified bound-capability registry,
minimum-cost capability planner, promoted executor, and independent execution
trace verifier. This is a construction runtime, not a benchmark scorer.

V1 intentionally accepts an already-compiled task contract. Raw natural-language
task compilation remains outside this file and is surfaced as a precise failure
instead of guessed.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from time import perf_counter_ns
from typing import Any
# isinstance(x, typing.Mapping) routes every check through typing's python-level
# __instancecheck__ (measured: 6,468 calls, 21 ms of a 39 ms registry load).
# collections.abc.Mapping is the C-implemented ABC the same objects register with, so
# the checks stay identical and stop being the dominant cost.
from collections.abc import Mapping

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime import astra_runtime, goal_compiler, goal_front_compiler_v1
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_archive_acceptance_v1 import verify as verify_raw_archive_acceptance
from canonical.runtime.raw_goal_archive_compound_acceptance_v1 import (
    GRAMMAR as RAW_ARCHIVE_COMPOUND_GRAMMAR,
)
from canonical.runtime.raw_goal_archive_compound_acceptance_v1 import (
    verify as verify_raw_archive_compound_acceptance,
)
from canonical.runtime.raw_goal_trace_acceptance_v1 import (
    verify as verify_raw_goal_trace_acceptance,
)
from canonical.runtime.runtime_cognition_credit_guard_v1 import assert_credit_path_cognition_governance

SCHEMA = "PROJECT_BRAIN_LIVE_INTEGRATED_BRAIN_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class LiveBrainError(ValueError):
    pass


def _tokens(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise LiveBrainError(label + "_MUST_BE_LIST")
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LiveBrainError(label + "_ITEM_INVALID")
        token = item.strip()
        if token in out:
            raise LiveBrainError(label + "_DUPLICATE:" + token)
        out.append(token)
    if not allow_empty and not out:
        raise LiveBrainError(label + "_EMPTY")
    return out


RECEIPT_SCHEMA = "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1"
VERIFICATION_SCHEMA = "PROJECT_BRAIN_CAPABILITY_INDEPENDENT_VERIFICATION_V1"
PROJECTION = ROOT / "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json"


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _receipt_admits(entry: Mapping[str, Any], root: Path) -> bool:
    """Admit a capability on independently reproduced execution evidence — never on a string.

    A `status` field is writable by any program, which is why the extended registry could be
    mass-flipped to `VERIFIED_BOUND_CAPABILITY` unnoticed.  A receipt alone is not enough
    either: a receipt this project issues to itself is the SESSION_E0A256F8 failure mode
    ("produced 464 self-verified receipts").  So admission needs BOTH:

      1. a producer receipt for *this* module at *this* content hash, and
      2. an independent verification record — a DIFFERENT identity re-ran it, the observed
         result hash matched, and the run reference carries a platform-attested
         `github_run_id`.

    (2) is why only a real runner can mint admission, and why nothing admitted here is a
    status flip. Deliberately ADDITIVE: it never demotes anything.
    """
    verification = entry.get("verification")
    if not isinstance(verification, Mapping):
        return False
    receipt_path = verification.get("receipt_path")
    source = entry.get("source")
    module_path = (source or {}).get("path") if isinstance(source, Mapping) else None
    if not isinstance(receipt_path, str) or not isinstance(module_path, str):
        return False
    # Imported only now: most of the 2,309 extended entries carry no evidence at all and
    # return above, so they should not pay an import statement each (2,612 imports/load).
    from canonical.runtime import capability_receipt_lane_v1 as lane

    receipt_file, module_file = root / receipt_path, root / module_path

    # Cheap gate FIRST.  Independent verification is the rare case; hashing every module on
    # every load cost 20.5 ms/call (measured) versus 8.4 ms when this check short-circuits.
    verification_file = root / lane.verification_path_for(receipt_path)
    if not verification_file.is_file():
        return False
    if not receipt_file.is_file() or not module_file.is_file():
        return False
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(receipt, Mapping) or receipt.get("schema") != RECEIPT_SCHEMA:
        return False
    if receipt.get("module_path") != module_path:
        return False
    if int(receipt.get("model_dependency_count", 1) or 0) != 0:
        return False
    if _sha256_of(module_file) != receipt.get("module_sha256"):
        return False

    try:
        record = json.loads(verification_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(record, Mapping) or record.get("schema") != VERIFICATION_SCHEMA:
        return False
    if record.get("reproduced") is not True:
        return False
    if record.get("module_sha256") != receipt.get("module_sha256"):
        return False
    if record.get("verifier_result_sha256") != receipt.get("result_sha256"):
        return False
    verifier = str(record.get("independent_verifier") or "")
    if not verifier or verifier == str(receipt.get("ran_by") or ""):
        return False
    run_reference = record.get("independent_run_reference")
    if not isinstance(run_reference, Mapping) or not run_reference.get("github_run_id"):
        return False
    # And the reference must carry a GitHub-SIGNED OIDC attestation, not a number a local
    # process typed. `brain-trusted-oidc-receipt.yml` is this repo's own idiom for it:
    # `id-token: write` yields a token whose `iss` is GitHub's issuer and whose claims name
    # the repository, workflow and run that produced it.
    claims = run_reference.get("oidc_claims")
    if not isinstance(claims, Mapping):
        return False
    if claims.get("iss") != "https://token.actions.githubusercontent.com":
        return False
    return bool(claims.get("repository"))


_REGISTRY_CACHE: dict[tuple[int, int, int], dict[str, Mapping[str, Any]]] = {}


def load_verified_registry(include_extended: bool = True) -> dict[str, Mapping[str, Any]]:
    # Parsing 1.06 MB of JSON on every solve() was the dominant cost (864 KB of it inventory
    # that is ~98% filtered away).  Memoise on the mtimes that can change the answer.
    # The evidence directory's mtime is in the token because verification records appear
    # there long after the projection is written: without it the cache returned a stale
    # 67 after a record was stamped in-process. One stat, not a directory scan.
    evidence_dir = ROOT / "canonical/astra_runtime/evidence"
    token = (REGISTRY.stat().st_mtime_ns,
             (ROOT / "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json").stat().st_mtime_ns
             if (ROOT / "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json").is_file() else 0,
             PROJECTION.stat().st_mtime_ns if PROJECTION.is_file() else 0,
             evidence_dir.stat().st_mtime_ns if evidence_dir.is_dir() else 0)
    if include_extended and token in _REGISTRY_CACHE:
        return dict(_REGISTRY_CACHE[token])

    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise LiveBrainError("BOUND_CAPABILITY_REGISTRY_SCHEMA_INVALID")
    raw = doc.get("capabilities")
    if not isinstance(raw, Mapping):
        raise LiveBrainError("BOUND_CAPABILITY_REGISTRY_INVALID")
    out: dict[str, Mapping[str, Any]] = {}
    for cid, entry in raw.items():
        if not isinstance(cid, str) or not isinstance(entry, Mapping):
            continue
        if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            continue
        if float(entry.get("incremental_spend_usd", 0)) != 0:
            continue
        out[cid] = entry
    # Canonical entries win collisions. Inventory alone is never executable.
    ext_path = REGISTRY.parent / "AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
    if include_extended and ext_path.is_file():
        try:
            ext_doc = json.loads(ext_path.read_text(encoding="utf-8"))
            if not isinstance(ext_doc, dict) or ext_doc.get("schema") != "PROJECT_BRAIN_AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1":
                raise ValueError("extended registry schema")
            extended = ext_doc.get("capabilities")
            if not isinstance(extended, dict):
                raise ValueError("extended capabilities must be an object")
            for cid, entry in extended.items():
                if not isinstance(cid, str) or not cid or not isinstance(entry, dict):
                    raise ValueError("invalid extended entry")
                if cid in out:
                    continue
                # Admission from inventory is by RECEIPT EVIDENCE ONLY — the status field is
                # not consulted, because a status is a string any program can write.
                #
                # This path used to admit `status == VERIFIED_BOUND_CAPABILITY` with
                # `verification.verified is True` and zero spend directly, which is exactly
                # the SESSION_E0A256F8 failure mode ("produced 464 self-verified receipts"):
                # flipping 500 inventory entries moved this loader from 67 to 567 admitted
                # with no execution evidence at all.
                #
                # Measured before removing it: 0 of the 2,309 inventory entries carried that
                # status, and 0 of the 361 admitted capabilities came from this path, so the
                # removal is live-count neutral (361 before and after) and only takes away
                # the ability to flip one in.  The curated bound registry above keeps its own
                # gate: that file is where the project's original verified capabilities live,
                # not user-writable inventory.
                if _receipt_admits(entry, ROOT):
                    out[cid] = {**entry, "capability_id": cid, "receipt_backed": True}
        except (OSError, ValueError, TypeError) as exc:
            raise LiveBrainError("EXTENDED_CAPABILITY_REGISTRY_INVALID") from exc

        # Third source: receipt-backed capabilities.  The projection is DERIVED evidence
        # (execution + independent reproduction), not a declaration, so admitting from it
        # adds no registry entry and therefore declares no new capability.  An entry here
        # keeps status RECEIPT_BACKED_FROM_PROJECTION and is admitted only if the
        # independent-verification gate passes.
        if PROJECTION.is_file():
            try:
                projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                projection = {}
            for cid, entry in (projection.get("entries") or {}).items():
                if cid in out or not isinstance(entry, dict):
                    continue
                if _receipt_admits(entry, ROOT):
                    composed = _with_declared_contract(entry, (extended or {}).get(cid))
                    out[cid] = {**composed, "capability_id": cid,
                                "capability_source": "receipt_projection"}
    if not out:
        raise LiveBrainError("NO_VERIFIED_ZERO_SPEND_CAPABILITIES")
    if include_extended:
        _REGISTRY_CACHE[token] = dict(out)
    return out


def _with_declared_contract(entry: Mapping[str, Any], declared: Any) -> dict[str, Any]:
    """Give a derived entry the argument contract its declaration states.

    A receipt-projection entry carries the EXECUTION contract (entrypoint, adapter, expectation) and
    the evidence paths; the human-written argument contract - the names a sentence must state - lives
    in the extended declaration.  Measured consequence of leaving the two apart, on one sentence:
    `run_raw_goal` executed it while `solve()` answered FAIL_CLOSED__ROUTE_ADMISSION_REJECTED with rule
    `R2_OUTPUT_ARTIFACT_UNSERVED`, because the entry that door read had no `${input.*}` placeholders
    and was therefore "a tool that takes no input" that cannot serve the output file the sentence
    names.  Composing here - in the single loader both doors read - is what makes them agree.

    This grants no authority: admission is still the producer receipt plus an independent
    reproduction, and the composition only makes the DECLARED argument names visible to the executors
    that have to render them (`_render_template` raises rather than emitting a placeholder, and the
    adapter drops an unbound one instead of forwarding it).
    """
    if not isinstance(declared, Mapping):
        return dict(entry)
    template = declared.get("action_template")
    if not isinstance(template, Mapping):
        return dict(entry)
    args = template.get("args")
    placeholders = [v for v in (args or {}).values()
                    if isinstance(v, str) and v.startswith("${input.")]
    if not placeholders:
        return dict(entry)
    # ADDITIVE, and that is the whole design: the executable `action_template` the lane derived stays
    # exactly as it is, because it IS a contract - the zero-input form, which is what the capability's
    # own receipt was minted from and what `run <cid>` must keep reaching.  The declared argument
    # contract is exposed beside it for the readers that need argument NAMES (a door judging whether
    # the sentence serves the output file it names, the binder, and the renderer that has to put the
    # stated values into the action).  Replacing the template instead was measured to break a real
    # invariant: `run <cid>` on a capability whose declaration has four inputs stopped being reachable
    # by name at all.
    return {**dict(entry), "declared_action_template": dict(template),
            "declared_contract_sha256": hashlib.sha256(
                json.dumps(template, sort_keys=True, default=str).encode("utf-8")).hexdigest()}


def compile_against_live_registry(goal: str, root: Any = None) -> tuple[
        dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[str, Any]]:
    """The front-door policy in ONE place: THE verified registry, its platform-admissible
    projection, and the front compile of the goal.

    Both live doors call this - `run_raw_goal` here and `live_brain_route_admission_v1.solve` - and
    the reason is a measured one, not tidiness.  Policy in two places has already drifted in this
    project once in exactly this class: a path that read a *declaration* where the *evidence* was the
    authority decided whether a capability existed at all.  The two preambles were identical except
    that one passed `include_extended=True` explicitly and the other relied on a default, so a change
    to that default would silently have given the two doors different views of which capabilities
    exist.  It is explicit here, and `GoalCompilationFailure` is raised for each door to map into its
    own failure shape rather than being swallowed.
    """
    base = Path(root) if root is not None else ROOT
    registry = load_verified_registry(include_extended=True)
    admissible = goal_compiler._platform_admissible_registry(dict(registry))
    return registry, admissible, goal_front_compiler_v1.compile_goal(goal, admissible, base)


def compile_capability_graph(
    *,
    initial_facts: list[str],
    target_effects: list[str],
    registry: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    capabilities = []
    for cid, entry in registry.items():
        requires = list(entry.get("requires") or [])
        provides = list(entry.get("provides") or [])
        if not provides:
            continue
        capabilities.append(
            {
                "id": cid,
                "requires": requires,
                "provides": provides,
                "cost": float(entry.get("cost", 1)),
                "action": {"type": "verified_bound_capability"},
                "result_fields": list(entry.get("result_fields") or []),
            }
        )
    return {
        "initial_facts": list(initial_facts),
        "target_effects": list(target_effects),
        "capabilities": capabilities,
        "max_expansions": 100000,
    }


_BOUND_IDS_CACHE: frozenset[str] | None = None


def _bound_capability_ids() -> frozenset[str]:
    """Capability ids the BOUND registry knows how to execute. Cached."""
    global _BOUND_IDS_CACHE
    if _BOUND_IDS_CACHE is None:
        try:
            from canonical.runtime import availability_v1

            _BOUND_IDS_CACHE = frozenset(availability_v1.load_registry())
        except Exception:
            _BOUND_IDS_CACHE = frozenset()
    return _BOUND_IDS_CACHE


def _plan_lineage(out: Any) -> tuple[list[str], list[str]]:
    """What the executed plan needed before it started and produced by the end.

    Taken from the capabilities that actually ran -- the first one's
    requirements and the last one's provisions -- rather than from the compiled
    plan, so the lineage describes the execution rather than the intention. The
    controller's finish row carries no capability and is not part of it.
    """
    trace = ((out or {}).get("controller_execution") or {}).get("trace")
    if not isinstance(trace, list):
        return [], []
    results = []
    for row in trace:
        result = row.get("result") if isinstance(row, Mapping) else None
        if isinstance(result, Mapping) and result.get("capability_id"):
            results.append(result)
    if not results:
        return [], []
    facts = [str(x) for x in (results[0].get("requires") or [])]
    effects = [str(x) for x in (results[-1].get("provides") or [])]
    return facts, effects


_INPUT_REF = re.compile(r"^\$\{input\.([A-Za-z0-9_]+)\}$")


def _independently_verified(entry: Mapping[str, Any]) -> bool:
    """The verified bound adapter's own gate, read the same way it reads it.

    Duplicated rather than imported because it lives inline in that module's
    ``execute``. The consequence of drifting is bounded in both directions: too
    strict and a plan simply is not upgraded, too permissive and the adapter
    refuses at execution and fails closed, which the corpus census reports
    immediately as a goal that stopped being accepted.
    """
    verification = entry.get("verification")
    if not isinstance(verification, Mapping):
        return False
    return (
        verification.get("independent_verified") is True
        or verification.get("independently_verified") is True
        or isinstance(verification.get("independently_verified_by"), str)
        or verification.get("producer_independent") is True
    )


def _inputs_from_rendered_args(
    entry: Mapping[str, Any], rendered_args: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Recover the raw input names a rendered action was built from.

    A registry template renames inputs onto argument names -- ``"path":
    "${input.docx_path}"`` -- and the verified bound adapter renders that
    template itself from the inputs it is handed. Handing it the already-renamed
    arguments would ask it to resolve ``${input.docx_path}`` from a mapping that
    only has ``path``. The template is the exact record of that renaming, so it
    is read backwards. Returns None when nothing is recoverable, so the caller
    leaves the action alone instead of guessing.
    """
    template = entry.get("action_template")
    template_args = template.get("args") if isinstance(template, Mapping) else None
    if not isinstance(template_args, Mapping):
        return None
    inputs: dict[str, Any] = {}
    for name, spec in template_args.items():
        match = _INPUT_REF.match(spec) if isinstance(spec, str) else None
        if match is None:
            continue
        if name in rendered_args:
            inputs[match.group(1)] = rendered_args[name]
    return inputs or None


def _upgrade_compound_actions(actions: Any, admissible: Mapping[str, Any]) -> Any:
    """Send a compiled plan through the proof-bearing action, all of it or none.

    A multi-clause goal's actions are built by the compiler, and that shape's
    trace carries no proof digests -- so no compound goal could become verified
    experience however real its work was. Upgrading here, at the one place the
    front door takes the compiled plan in hand, covers every compiler path
    instead of chasing each of them.

    All or none is the point. The learning adapter binds an episode only when
    every recorded step came through the verified bound adapter, so a partially
    upgraded plan is worth nothing -- and the verified bound adapter refuses any
    capability that has not been independently verified, which would turn a
    working run into a failed one. So a plan is upgraded only when every
    capability step in it is one the BOUND registry can execute, has had its
    independence established, and has inputs recoverable exactly from its
    template. Any plan that is not, is passed through untouched and executes
    exactly as it did before.
    """
    if not isinstance(actions, list):
        return actions
    bound = _bound_capability_ids()
    planned = []
    for action in actions:
        if not isinstance(action, Mapping) or action.get("type") != "invoke_capability":
            planned.append((None, action))
            continue
        args = action.get("args")
        cid = (
            str((args or {}).get("capability_id") or "")
            if isinstance(args, Mapping) else ""
        )
        entry = admissible.get(cid) if isinstance(admissible, Mapping) else None
        if (
            not cid
            or not isinstance(args, Mapping)
            or not isinstance(entry, Mapping)
            or cid not in bound
            or not _independently_verified(entry)
        ):
            return actions
        inputs = _inputs_from_rendered_args(entry, args)
        if inputs is None:
            return actions
        planned.append((bound_capability_controller_action(cid, entry, inputs), action))
    if not any(built is not None for built, _ in planned):
        return actions
    return [built if built is not None else original for built, original in planned]


def bound_capability_controller_action(cid: str, entry: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    """The one controller action shape that executes a verified capability.

    Both entry points build it here: ``run()`` for a planned task and ``run_raw_goal()`` for a
    raw goal.  A registry ``action_template`` of type ``invoke_capability`` cannot be used for a
    receipt-backed capability: the controller resolves that type through the BOUND registry,
    which by design holds only promoted entries, so every receipt-backed capability answered
    ``Blocker:BOUND_CAPABILITY_UNKNOWN`` (measured: 294 of 294, all before any work was done).
    """
    return {
        "type": "invoke_verified_bound_capability_adapter",
        "args": {
            "capability_id": cid,
            "inputs": dict(inputs),
            "instance_id": cid,
            "requires": list(entry.get("requires") or []),
            "provides": list(entry.get("provides") or []),
            "result_fields": list(entry.get("result_fields") or []),
        },
        "expect": {"type": "field_equals", "field": "pass", "value": True},
    }


def run(request: Mapping[str, Any]) -> dict[str, Any]:
    assert_credit_path_cognition_governance(ROOT)
    started = perf_counter_ns()
    try:
        if not isinstance(request, Mapping):
            raise LiveBrainError("REQUEST_NOT_OBJECT")
        task_id = str(request.get("task_id") or "").strip()
        if not task_id:
            raise LiveBrainError("TASK_ID_REQUIRED")
        initial = _tokens(request.get("initial_facts", []), "INITIAL_FACTS")
        targets = _tokens(request.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
        capability_inputs = request.get("capability_inputs", {})
        if not isinstance(capability_inputs, Mapping):
            raise LiveBrainError("CAPABILITY_INPUTS_NOT_OBJECT")

        registry = load_verified_registry()
        allowed = request.get("allowed_capability_ids")
        if allowed is not None:
            allowed_ids = _tokens(allowed, "ALLOWED_CAPABILITY_IDS", allow_empty=False)
            unknown = sorted(set(allowed_ids) - set(registry))
            if unknown:
                raise LiveBrainError("ALLOWED_CAPABILITY_UNKNOWN:" + ",".join(unknown))
            registry = {cid: registry[cid] for cid in allowed_ids}
        problem = compile_capability_graph(
            initial_facts=initial,
            target_effects=targets,
            registry=registry,
        )
        try:
            planned = plan_capabilities(problem)
        except PlanningFailure as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
                "pass": False,
                "task_id": task_id,
                "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
                "planner_code": exc.code,
                "planner_detail": exc.detail,
                "verified_registry_capability_count": len(registry),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        controller_actions = []
        for cid in planned["plan"]:
            entry = registry[cid]
            inputs = capability_inputs.get(cid)
            if not isinstance(inputs, Mapping):
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__MISSING_CAPABILITY_INPUTS",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "TASK_CONTRACT_COMPILATION_GAP",
                    "capability_id": cid,
                    "selected_plan": list(planned["plan"]),
                    "verified_registry_capability_count": len(registry),
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            controller_actions.append(bound_capability_controller_action(cid, entry, inputs))
        controller_actions.append({
            "type": "finish",
            "args": {"summary": "COMPILED_TASK_COMPLETE"},
        })

        try:
            controller = astra_runtime.run_goal(
                {
                    "id": "live-compiled-task-controller",
                    "controller_actions": controller_actions,
                    "max_controller_actions": 64,
                },
                {
                    "mission_id": task_id,
                    "goal": "execute compiled verified capability task",
                },
            )
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__VERIFIED_CAPABILITY_EXECUTION",
                "pass": False,
                "task_id": task_id,
                "failure_class": "EXECUTION_OR_BOUND_CONTRACT_FAILURE",
                "selected_plan": list(planned["plan"]),
                "reason": type(exc).__name__ + ":" + str(exc),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        trace = controller.get("trace") if isinstance(controller, Mapping) else None
        if (
            not isinstance(trace, list)
            or len(trace) != len(planned["plan"]) + 1
            or controller.get("returncode") != 0
            or controller.get("controller_mode") != "MODEL_INDEPENDENT_ACTION_PLAN"
            or controller.get("cognition_dependency_class") != "MODEL_INDEPENDENT"
            or controller.get("model_dependency_count") != 0
        ):
            return {
                "schema": SCHEMA,
                "status": "FAIL__VERIFIED_CAPABILITY_EXECUTION",
                "pass": False,
                "task_id": task_id,
                "failure_class": "EXECUTION_OR_BOUND_CONTRACT_FAILURE",
                "selected_plan": list(planned["plan"]),
                "controller_execution": controller,
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        current = set(initial)
        execution = []
        for index, cid in enumerate(planned["plan"]):
            row = trace[index]
            out = row.get("result") if isinstance(row, Mapping) else None
            if not isinstance(out, Mapping):
                raise LiveBrainError("CONTROLLER_PROMOTED_CAPABILITY_RESULT_MISSING:" + cid)
            execution.append({
                "capability_id": cid,
                "pass": out.get("pass") is True,
                "status": out.get("status"),
                "composition_capsule_head_hash": out.get("composition_capsule_head_hash"),
                "result": out.get("result"),
                "errors": out.get("errors"),
            })
            if out.get("pass") is not True:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__VERIFIED_CAPABILITY_EXECUTION",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "EXECUTION_OR_BOUND_CONTRACT_FAILURE",
                    "capability_id": cid,
                    "selected_plan": list(planned["plan"]),
                    "execution": execution,
                    "controller_execution": dict(controller),
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            current.update(registry[cid].get("provides") or [])

        missing = sorted(set(targets) - current)
        if missing:
            raise LiveBrainError("POST_EXECUTION_TARGETS_MISSING:" + ",".join(missing))

        return {
            "schema": SCHEMA,
            "status": "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
            "pass": True,
            "task_id": task_id,
            "selected_plan": list(planned["plan"]),
            "planner_total_cost": planned["total_cost"],
            "planner_expanded_states": planned["expanded_states"],
            "verified_registry_capability_count": len(registry),
            "execution": execution,
            "controller_execution": dict(controller),
            "controller_checkpoint": controller.get("controller_checkpoint"),
            "cognition_dependency_class": controller.get("cognition_dependency_class"),
            "model_dependency_count": controller.get("model_dependency_count"),
            "verified_target_effects": sorted(targets),
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
            "benchmark_specific": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "failure_class": "INTEGRATION_RUNTIME_ERROR",
            "reason": type(exc).__name__ + ":" + str(exc),
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
        }



MAX_CONTROLLER_ACTIONS = 64


def controller_actions_permitted(controller_actions: Any) -> bool:
    """The control-plan contract, in ONE place, because two doors execute it.

    Measured: this predicate existed twice - once here and once in the other live door's executor -
    with the same rule (a non-empty list of at most 64 action mappings) and two copies of the same
    `astra_runtime.run_goal` call beneath it.  Duplication of a policy is how two doors come to
    disagree; the policy is one line long, so there is no reason to own it twice.
    """
    return (isinstance(controller_actions, list) and bool(controller_actions)
            and len(controller_actions) <= MAX_CONTROLLER_ACTIONS
            and all(isinstance(action, Mapping) for action in controller_actions))


def drive_controller(task_id: str, goal: str, controller_actions: Any,
                     controller_id: str = "live-raw-goal-controller") -> tuple[Any, str | None]:
    """Drive the pinned kernel with these actions: ONE call site for both live doors.

    Returns ``(controller, None)`` on success and ``(None, detail)`` when the plan is invalid or the
    kernel raised.  Only the call is shared - each door keeps its own result envelope, because their
    status vocabularies legitimately differ; what must not differ is HOW the kernel is run.
    """
    if not controller_actions_permitted(controller_actions):
        return None, "CONTROL_PLAN_INVALID"
    try:
        controller = astra_runtime.run_goal(
            {"id": controller_id, "controller_actions": [dict(action) for action in controller_actions],
             "max_controller_actions": MAX_CONTROLLER_ACTIONS},
            {"mission_id": task_id, "goal": goal},
        )
    except Exception as exc:  # noqa: BLE001 - the caller owns the envelope, this owns the call
        return None, type(exc).__name__ + ":" + str(exc)
    return controller, None


def _run_raw_goal_impl(request: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one raw plain-language goal into the live verified runtime.

    Raw text is preserved losslessly as acceptance obligations. The deterministic
    goal compiler may choose routing/execution, but routing never becomes success
    authority. V1 supports the existing single-capability compiled shape; richer
    controller/composition shapes fail closed instead of being guessed.
    """
    assert_credit_path_cognition_governance(ROOT)
    started = perf_counter_ns()
    try:
        if not isinstance(request, Mapping):
            raise LiveBrainError("REQUEST_NOT_OBJECT")
        task_id = str(request.get("task_id") or "").strip()
        goal = str(request.get("goal") or "").strip()
        if not task_id:
            raise LiveBrainError("TASK_ID_REQUIRED")
        if not goal:
            raise LiveBrainError("RAW_GOAL_REQUIRED")

        try:
            registry, admissible, compiled = compile_against_live_registry(goal)
        except goal_compiler.GoalCompilationFailure as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__RAW_GOAL_COMPILATION_GAP",
                "pass": False,
                "task_id": task_id,
                "failure_class": "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
                "compiler_code": exc.code,
                "compiler_detail": exc.detail,
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        controller_actions = _upgrade_compound_actions(
            compiled.get("controller_actions"), admissible
        )
        routing_targets = list(compiled.get("target_effects") or [])
        if not routing_targets:
            for part in compiled.get("compiled_parts") or []:
                if isinstance(part, Mapping):
                    for effect in part.get("target_effects") or []:
                        if isinstance(effect, str) and effect and effect not in routing_targets:
                            routing_targets.append(effect)

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=routing_targets,
        )
        if raw_contract.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "FAIL__LOSSLESS_RAW_TASK_CONTRACT",
                "pass": False,
                "task_id": task_id,
                "failure_class": "RAW_TASK_OBLIGATION_ENVELOPE_FAILURE",
                "errors": raw_contract.get("errors"),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        if controller_actions is not None:
            if not controller_actions_permitted(controller_actions):
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__COMPILED_CONTROL_PLAN_INVALID",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "LIVE_RUNTIME_COMPOSITION_CONTRACT_INVALID",
                    "compiler_mode": compiled.get("compiler_mode"),
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            controller, controller_error = drive_controller(task_id, goal, controller_actions)
            if controller_error is not None:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__LIVE_CONTROLLER_EXECUTION",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE",
                    "compiler_mode": compiled.get("compiler_mode"),
                    "reason": controller_error,
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            passed = (
                isinstance(controller, Mapping)
                and controller.get("returncode") == 0
                and controller.get("controller_mode") == "MODEL_INDEPENDENT_ACTION_PLAN"
                and controller.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
                and controller.get("model_dependency_count") == 0
                and isinstance(controller.get("final_summary"), str)
                and bool(controller.get("final_summary").strip())
            )
            compound_result = {
                "schema": SCHEMA,
                "status": (
                    "PASS__RAW_GOAL_COMPILED_CONTROLLER_EXECUTED_VERIFIED_AND_CHECKPOINTED__"
                    "RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
                    if passed else "FAIL__LIVE_CONTROLLER_RESULT_INVALID"
                ),
                "pass": passed,
                "task_id": task_id,
                "raw_goal": goal,
                "raw_goal_sha256": raw_contract["task_sha256"],
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "raw_acceptance_obligation_count": len(
                    raw_contract["acceptance_contract"]["obligations"]
                ),
                "raw_source_coverage_complete": raw_contract[
                    "nonwhitespace_source_coverage_complete"
                ],
                "compiler_mode": compiled.get("compiler_mode"),
                "compiled_part_count": len(compiled.get("compiled_parts") or []),
                "controller_action_count": len(controller_actions),
                "controller_execution": dict(controller) if isinstance(controller, Mapping) else controller,
                "controller_checkpoint": (
                    controller.get("controller_checkpoint")
                    if isinstance(controller, Mapping) else None
                ),
                "cognition_dependency_class": (
                    controller.get("cognition_dependency_class")
                    if isinstance(controller, Mapping) else None
                ),
                "model_dependency_count": (
                    controller.get("model_dependency_count")
                    if isinstance(controller, Mapping) else None
                ),
                "routing_success_authority": False,
                "semantic_acceptance_complete": False,
                "accepted_raw_obligation_ids": [],
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
                "benchmark_specific": False,
                "terminal_credit_delta": 0,
            }
            # A compound plan used to hardcode acceptance to False here, which
            # is why ``semantic_acceptance_complete`` was unreachable for every
            # multi-clause goal no matter what the machine actually produced.
            # Execution success is still not acceptance: the sentence's exact
            # grammar has to match, the trace has to be the capabilities the
            # sentence asked for in the order it asked for them, and the
            # artifact is re-opened from disk rather than believed.
            if passed:
                trace = (controller or {}).get("trace")
                # The single-plan return path reports ``selected_plan`` and the
                # compound one did not, so a passing multi-clause goal was
                # retained with no proof capsule at all:
                # ``_make_success_proof_capsule`` requires that key, and without
                # it the observation carries no material for any adapter to
                # re-inspect. Derived from the executed trace rather than from
                # the compiled plan, so it records what actually ran, including
                # the order it ran in. Summary rows carry no capability and are
                # not part of the work.
                if isinstance(trace, list):
                    executed = []
                    for row in trace:
                        result = row.get("result") if isinstance(row, Mapping) else None
                        cid = (
                            str(result.get("capability_id") or "").strip()
                            if isinstance(result, Mapping) else ""
                        )
                        if cid:
                            executed.append(cid)
                    if executed:
                        compound_result["selected_plan"] = executed
                if isinstance(trace, list) and trace:
                    acceptance = None
                    if RAW_ARCHIVE_COMPOUND_GRAMMAR.fullmatch(goal) is not None:
                        acceptance = verify_raw_archive_compound_acceptance(
                            goal=goal,
                            execution=trace,
                            raw_contract=raw_contract,
                            root=ROOT,
                        )
                    # A sentence-specific verifier stays authoritative when it
                    # accepts. Otherwise the generic trace verifier measures the
                    # work itself: it re-opens every artifact from disk and
                    # refuses any capability it has no re-inspector for, so
                    # acceptance can only grow when a real inspector is written.
                    if not (
                        isinstance(acceptance, Mapping)
                        and acceptance.get("semantic_acceptance_complete") is True
                    ):
                        generic = verify_raw_goal_trace_acceptance(
                            goal=goal,
                            compiled_plan=compiled,
                            execution=trace,
                            raw_contract=raw_contract,
                            root=ROOT,
                        )
                        if acceptance is None or (
                            isinstance(generic, Mapping)
                            and generic.get("semantic_acceptance_complete") is True
                        ):
                            acceptance = generic
                    compound_result["raw_goal_acceptance"] = acceptance
                    accepted = list(
                        acceptance.get("accepted_obligation_ids") or []
                    ) if isinstance(acceptance, Mapping) else []
                    compound_result["accepted_raw_obligation_ids"] = accepted
                    compound_result["semantic_acceptance_complete"] = (
                        isinstance(acceptance, Mapping)
                        and acceptance.get("semantic_acceptance_complete") is True
                        and len(accepted) == compound_result[
                            "raw_acceptance_obligation_count"
                        ]
                    )
                    if compound_result["semantic_acceptance_complete"]:
                        compound_result["status"] = (
                            "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_"
                            "ACCEPTANCE_VERIFIED"
                        )
            return compound_result

        selected = str(compiled.get("selected_capability") or "").strip()
        inputs = compiled.get("inputs")
        targets = compiled.get("target_effects")
        initial = compiled.get("initial_facts")
        if (
            not selected
            or selected not in admissible
            or not isinstance(inputs, Mapping)
            or not isinstance(targets, list)
            or not targets
            or not isinstance(initial, list)
        ):
            return {
                "schema": SCHEMA,
                "status": "FAIL__COMPILED_SHAPE_NOT_EXECUTABLE",
                "pass": False,
                "task_id": task_id,
                "failure_class": "RAW_GOAL_COMPILED_SHAPE_GAP",
                "compiler_mode": compiled.get("compiler_mode"),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        entry = admissible[selected]
        # Receipt-backed capabilities have always needed the verified bound
        # adapter action, because the registry's own template resolves through
        # the BOUND registry and refuses them before any work is done. Every
        # other capability that registry also knows how to execute is sent the
        # same way, because that action shape is the only one whose trace
        # carries proof digests -- and without them the learning adapters have
        # nothing to bind an episode to, so the run is executed, accepted and
        # then forgotten. Capabilities it does not know keep their template,
        # which is what makes this bounded rather than blanket: an unknown id
        # would answer BOUND_CAPABILITY_UNKNOWN.
        # Archive capabilities are deliberately left out of the widening below.
        # They are served by dedicated sentence-specific acceptance verifiers
        # that were written against the flat trace shape and report fields the
        # generic verifier does not, such as ``verified_output_sha256``. Sending
        # them through the bound adapter moved them onto the generic verifier
        # instead, which still accepted and still re-inspected the bytes but
        # answered a different question. None of the goals this change makes
        # learnable is an archive goal, so excluding them costs nothing here and
        # keeps a verifier boundary I have not re-proven exactly as it was.
        if entry.get("capability_source") == "receipt_projection" or (
            selected in _bound_capability_ids()
        ):
            action = bound_capability_controller_action(selected, entry, dict(inputs))
            # Carry the registry's own argument names alongside the raw inputs.
            # A template declares how inputs map onto arguments -- the document
            # verifier's reads "path": "${input.docx_path}" -- and everything
            # downstream reads arguments by those declared names. The bound
            # adapter takes the inputs unmapped, so without this the trace
            # would carry ``docx_path`` where a re-inspector asks for ``path``.
            # The adapter ignores keys it does not use, and ``setdefault``
            # leaves its own identity and proof keys untouched.
            rendered = goal_compiler._render_template(
                entry["action_template"], dict(inputs)
            )
            rendered_args = (
                rendered.get("args") if isinstance(rendered, Mapping) else None
            )
            if isinstance(rendered_args, Mapping):
                for name, value in rendered_args.items():
                    action["args"].setdefault(name, value)
        else:
            action = goal_compiler._render_template(entry["action_template"], dict(inputs))
        controller_actions = [
            action,
            {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}},
        ]
        try:
            controller = astra_runtime.run_goal(
                {
                    "id": "live-raw-goal-controller",
                    "controller_actions": controller_actions,
                    "max_controller_actions": 64,
                },
                {
                    "mission_id": task_id,
                    "goal": goal,
                },
            )
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__LIVE_CONTROLLER_EXECUTION",
                "pass": False,
                "task_id": task_id,
                "failure_class": "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE",
                "compiled_capability_id": selected,
                "compiler_mode": compiled.get("compiler_mode"),
                "reason": type(exc).__name__ + ":" + str(exc),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        trace = controller.get("trace") if isinstance(controller, Mapping) else None
        first_trace = trace[0] if isinstance(trace, list) and trace else None
        first_result = (
            first_trace.get("result")
            if isinstance(first_trace, Mapping)
            and isinstance(first_trace.get("result"), Mapping)
            else None
        )
        checkpoint = (
            controller.get("controller_checkpoint")
            if isinstance(controller, Mapping)
            and isinstance(controller.get("controller_checkpoint"), Mapping)
            else {}
        )
        passed = (
            isinstance(controller, Mapping)
            and controller.get("returncode") == 0
            and controller.get("controller_mode") == "MODEL_INDEPENDENT_ACTION_PLAN"
            and controller.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
            and controller.get("model_dependency_count") == 0
            and isinstance(controller.get("final_summary"), str)
            and bool(controller.get("final_summary").strip())
            and isinstance(first_result, Mapping)
        )
        execution_row = {
            "capability_id": selected,
            "pass": passed,
            "status": (
                "PASS__MODEL_INDEPENDENT_CONTROLLER_ACTION"
                if passed else "FAIL__MODEL_INDEPENDENT_CONTROLLER_ACTION"
            ),
            "result": dict(first_result) if isinstance(first_result, Mapping) else None,
            "execution_proof_type": "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1",
            "controller_plan_sha256": checkpoint.get("plan_sha256"),
            "controller_trace": list(trace) if isinstance(trace, list) else [],
        }
        result = {
            "schema": SCHEMA,
            "status": (
                "PASS__RAW_GOAL_COMPILED_CONTROLLER_EXECUTED_VERIFIED_AND_CHECKPOINTED__"
                "RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
                if passed else "FAIL__LIVE_CONTROLLER_RESULT_INVALID"
            ),
            "pass": passed,
            "task_id": task_id,
            "selected_plan": [selected],
            "verified_registry_capability_count": len(admissible),
            "execution": [execution_row],
            "controller_execution": dict(controller) if isinstance(controller, Mapping) else controller,
            "controller_checkpoint": dict(checkpoint),
            "cognition_dependency_class": (
                controller.get("cognition_dependency_class")
                if isinstance(controller, Mapping) else None
            ),
            "model_dependency_count": (
                controller.get("model_dependency_count")
                if isinstance(controller, Mapping) else None
            ),
            "raw_goal": goal,
            "raw_goal_sha256": raw_contract["task_sha256"],
            "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
            "raw_acceptance_obligation_count": len(
                raw_contract["acceptance_contract"]["obligations"]
            ),
            "raw_source_coverage_complete": raw_contract[
                "nonwhitespace_source_coverage_complete"
            ],
            "compiled_capability_id": selected,
            "compiler_mode": compiled.get("compiler_mode"),
            "routing_success_authority": False,
            "semantic_acceptance_complete": False,
            "accepted_raw_obligation_ids": [],
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
            "benchmark_specific": False,
            "terminal_credit_delta": 0,
        }
        # Execution success alone is not raw-goal acceptance. For the one
        # explicit archive semantics currently understood, independently inspect
        # the artifact and bind all exact source obligations to the receipt.
        acceptance = None
        rows = result.get("execution")
        if (
            result.get("pass") is True
            and selected == "archive.tar_gz.create_from_manifest"
            and isinstance(rows, list)
            and len(rows) == 1
        ):
            acceptance = verify_raw_archive_acceptance(
                goal=goal,
                capability_id=selected,
                inputs=inputs,
                execution=rows[0],
                raw_contract=raw_contract,
                root=ROOT,
            )
        # A compound plan reports its work in the controller trace, not in
        # ``execution``, so the single-row gate above can never see it -- which
        # is why acceptance has stayed unreachable for every compound goal. The
        # create-and-verify archive sentence asks for two capabilities and the
        # compiler really does plan two, so its acceptance is checked against
        # the trace instead, and the archive is re-opened from disk rather than
        # believed.
        #
        # Gated on the exact grammar so no other goal's behaviour changes: a
        # goal that does not match still gets ``acceptance is None``, exactly as
        # before.
        if (
            acceptance is None
            and result.get("pass") is True
            and RAW_ARCHIVE_COMPOUND_GRAMMAR.fullmatch(goal) is not None
        ):
            trace = (result.get("controller_execution") or {}).get("trace")
            if isinstance(trace, list) and trace:
                acceptance = verify_raw_archive_compound_acceptance(
                    goal=goal,
                    execution=trace,
                    raw_contract=raw_contract,
                    root=ROOT,
                )
        # Same asymmetry on the single-plan path: a sentence-specific verifier
        # wins when it accepts, otherwise the generic trace verifier re-opens
        # the artifacts from disk and refuses whatever it cannot re-inspect.
        if (
            result.get("pass") is True
            and not (
                isinstance(acceptance, Mapping)
                and acceptance.get("semantic_acceptance_complete") is True
            )
        ):
            trace = (result.get("controller_execution") or {}).get("trace")
            if isinstance(trace, list) and trace:
                generic = verify_raw_goal_trace_acceptance(
                    goal=goal,
                    compiled_plan=compiled,
                    execution=trace,
                    raw_contract=raw_contract,
                    root=ROOT,
                )
                if acceptance is None or (
                    isinstance(generic, Mapping)
                    and generic.get("semantic_acceptance_complete") is True
                ):
                    acceptance = generic
        result["raw_goal_acceptance"] = acceptance
        result["accepted_raw_obligation_ids"] = (
            list(acceptance.get("accepted_obligation_ids") or [])
            if isinstance(acceptance, Mapping) else []
        )
        result["routing_success_authority"] = False
        result["semantic_acceptance_complete"] = (
            isinstance(acceptance, Mapping)
            and acceptance.get("semantic_acceptance_complete") is True
            and len(result["accepted_raw_obligation_ids"])
                == result["raw_acceptance_obligation_count"]
        )
        result["elapsed_ns"] = perf_counter_ns() - started
        if result.get("pass") is True:
            result["status"] = (
                "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"
                if result["semantic_acceptance_complete"] else
                "PASS__RAW_GOAL_COMPILED_PLANNED_EXECUTED_REVERIFIED__"
                "RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
            )
        return result
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "failure_class": "RAW_GOAL_INTEGRATION_RUNTIME_ERROR",
            "reason": type(exc).__name__ + ":" + str(exc),
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
        }


def _raw_goal_replay_context(request: Any, out: Any = None) -> dict[str, Any] | None:
    """The exact shape the Brain's own raw success adapter accepts.

    `r3_raw_success_adapter_v1.adapt` is one of four success adapters the
    improvement driver owns, and it is the one that turns a retained raw-goal
    success into a verifiable episode. It requires `mode == "raw_bound"` and a
    `request` mapping carrying both the goal and the task_id, and returns None
    for anything else. When every adapter returns None the driver parks the work
    as IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE, so a
    wrongly shaped context does not fail loudly -- it silently strands the
    experience, which is what a `{"surface", "goal"}` context did.

    The adapter does not re-execute the goal. It reconstructs the episode from
    the retained proof capsule and the controller checkpoint the run already
    wrote, so the task_id names evidence that already exists rather than
    requesting a second run. Every field it checks -- raw_goal_sha256, the
    acceptance contract, selected_plan, accepted_raw_obligation_ids -- is
    already present in the proof capsule this recording stores.
    """
    if not isinstance(request, Mapping):
        return None
    goal = str(request.get("goal") or "").strip()
    task_id = str(request.get("task_id") or "").strip()
    if not goal or not task_id:
        return None
    base = {"goal": goal, "task_id": task_id}
    facts, effects = _plan_lineage(out)
    if effects:
        # The general adapter's mode: the one that works for any bound
        # capability rather than a single sentence shape, and which needs the
        # lineage to bind an episode's preconditions and postconditions.
        return {
            "mode": "compiled_bound",
            "request": {**base, "initial_facts": facts, "target_effects": effects},
        }
    return {"mode": "raw_bound", "request": base}


def _record_raw_goal_experience(out: Any, request: Any = None) -> None:
    """Retain what the front door actually achieved, without judging it.

    106 modules in this tree implement learning, episode retention, skill
    induction and Pareto admission, and the front door called none of them:
    `grep -c` for the self-improvement, learning and feedback symbols in this
    file returned 0. So every goal the machine carried out was forgotten the
    instant it returned, and the learning loop had no experience to learn from.

    The retained record carries a replay context, so the improvement driver can
    act on it rather than stranding it; see `_raw_goal_replay_context`.

    This records and nothing else. `record_success_observation` refuses an
    output that did not pass, and it deliberately does not promote anything --
    promotion still requires that module's own independent verification, which
    is an authority boundary this function has no part in. Nothing here can
    make a run succeed, and nothing here is consulted to decide one.

    The call is contained because forgetting must never become failing: a
    learning layer that can break execution is worse than no learning layer.
    Any error is swallowed deliberately, and the caller's result is returned
    byte for byte whatever happens here.
    """
    try:
        if not isinstance(out, Mapping) or out.get("pass") is not True:
            return
        from canonical.runtime import (
            autonomous_verified_self_improvement_v1 as _self_improvement,
        )

        _self_improvement.record_success_observation(
            out,
            surface="RAW_GOAL_FRONT_DOOR_V1",
            replay_context=_raw_goal_replay_context(request, out),
        )
    except Exception:
        # Deliberate: see the docstring. Experience is best-effort by design.
        pass


def _advance_learning_queue() -> None:
    """Turn what the machine just did into verified experience, in the same run.

    Recording alone left the loop open. The front door retained each success,
    and the improvement queue driver -- with its own independent verifier -- was
    sitting right there able to turn one into a verified episode, but nothing on
    the live path ever called it. Measured: after a run the state held a pending
    improvement and `verified_episode_count` stayed 0 until `advance_once` was
    invoked by hand. Learning that only happens when someone remembers to ask
    for it is not instant learning.

    `drain` executes the highest-priority actionable improvements and stops when
    none are actionable. It grants nothing by itself: promotion still requires
    the independent verifier, and a queue with no actionable work is a no-op
    rather than an error. It is contained for the same reason recording is --
    learning must never be able to fail a run -- and nothing it writes is read
    back to decide this run's outcome.
    """
    try:
        from canonical.runtime import (
            r3_improvement_queue_driver_v1 as _improvement_driver,
        )

        _improvement_driver.drain(max_actions=4)
    except Exception:
        # Deliberate: see the docstring. Learning is best-effort by design.
        pass


def _pathology_reason_code(reason: Any) -> str:
    """The reason code, unwrapped from the front door's blocker envelope.

    The front door reports a blocker as ``Blocker:CODE:detail:RESULT={...}``,
    and an action expectation wraps a second one inside it
    (``...REASON=Blocker:CODE2:...``). ``experience_v1`` keys a memory cell on
    the leading code of whatever string it is handed, so passing the raw
    envelope files every failure on this path under the single useless cell
    ``<capability>|blocker``. Taking the innermost ``REASON=`` payload keeps the
    unit of memory the pathology, which is what that module is built around --
    ``BOUND_APT_METADATA_NOT_FOUND`` and
    ``BOUND_CAPABILITY_SOURCE_UNSUPPORTED`` are different facts about this
    machine and must not share an address.

    Nothing is interpreted here. The code is copied out of the string the run
    already produced; when there is no envelope the string is used as-is.
    """
    text = str(reason or "")
    while True:
        idx = text.rfind("REASON=")
        if idx < 0:
            break
        text = text[idx + len("REASON="):]
    if text.startswith("Blocker:"):
        text = text[len("Blocker:"):]
    return text.split(":", 1)[0][:60] or "FAILED"


def _record_raw_goal_pathology(out: Any, request: Any = None, path: Any = None) -> None:
    """Fold what the front door just did into the machine's pathology memory.

    WHAT WAS MISSING. ``_record_raw_goal_experience`` returns unless
    ``out["pass"] is True``, so the shipping path remembered successes into the
    episode store and dropped every failure on the floor. Meanwhile
    ``experience_v1`` -- whose entire purpose is that ``image.extract.ocr.
    tesseract`` x ``BOUND_CAPABILITY_SOURCE_UNSUPPORTED`` "will be true on this
    machine forever" and is therefore worth remembering -- was written by
    ``grounded_action_v1`` alone. Measured before this change: the store held 37
    cells, not one of them from a front-door run, while the front door
    rediscovered the same four dead routes on every single run. That is exactly
    the failure the module's own docstring says it exists to prevent.

    So the two stores now hold different things, as designed: the episode store
    keeps what the machine ACHIEVED, and this one keeps how this box BEHAVES.
    Failures belong in the second and nowhere else, which is why
    `_record_raw_goal_experience` was left alone rather than widened.

    This writes memory and consults nothing. ``experience_v1.is_suppressed`` is
    deliberately NOT called on this path: suppression would drop
    ``image.extract.ocr.tesseract`` from the candidate pool, and that capability
    is the benchmark's own expected selection for ``EXT_OCR_SCANNED_IMAGE``, so
    consulting here would trade a correct selection for a faster refusal. The
    memory is still worth having -- ``grounded_action_v1`` consults the same
    file and now benefits from what the front door learns.

    Contained for the same reason recording is: a memory that can fail a run is
    worse than no memory, and the caller's result is returned byte for byte.

    ``path`` is a passthrough to ``experience_v1``'s own state-location
    argument, unused by the live path. It exists so a test can aim this at a
    scratch store instead of the tracked one; production behaviour is unchanged
    because the default is that module's own default.
    """
    try:
        if not isinstance(out, Mapping):
            return
        from canonical.runtime import experience_v1 as _experience

        goal = ""
        if isinstance(request, Mapping):
            goal = str(request.get("goal") or "")
        receipt = {
            "capability_id": str(out.get("compiled_capability_id") or ""),
            "error": _pathology_reason_code(out.get("reason")),
            "verified": out.get("pass") is True,
        }
        if not receipt["capability_id"]:
            return
        _experience.observe(goal, receipt, path=path)
    except Exception:
        # Deliberate: see the docstring. Memory is best-effort by design.
        pass


def _record_raw_goal_failure_diagnosis(
    out: Any, request: Any = None, state_path: Any = None
) -> None:
    """Diagnose and count what the front door could not do.

    WHAT WAS MISSING. Both existing hooks on this path bail out on a failure:
    `_record_raw_goal_experience` returns unless ``out["pass"] is True``, and
    `_record_raw_goal_pathology` writes a cell about how this box behaves but
    keeps no account of the failure itself. So the episode store's ``failures``
    table stayed permanently empty -- measured at ``failure_class_count: 0``
    after running all 23 benchmark goals, of which 11 fail -- even though
    `integrate_solver_output` already contains the whole failure half of the
    learning loop: it diagnoses, fingerprints, counts repeats, and records a
    repair class. Nothing on the shipping path ever called it.

    The consequence is not a missing statistic. ``count`` is the difference
    between "this failed once" and "this fails every single time", and that
    distinction is the only thing that separates a transient problem from a
    permanent one. Measured: three runs of one failing goal now give one
    failure class with ``count == 3``, where before they gave nothing at all.
    Two modules already read this table -- `live_brain_runtime_v1` for retry
    context and `r3_historical_failure_irreducibility_v1` for the irreducibility
    proof -- and neither could ever run against an empty one.

    Only failures are passed here. `record_success_observation` handles
    successes and itself refuses an output that did not pass, so sending both
    would record a success twice; the split is deliberate, not incidental.

    WHAT THIS DOES NOT DO. It grants no repair and authorizes no replay. With
    no retry context there is no capsule, so the disposition is honestly
    ``FAILURE_DIAGNOSED__ORPHANED_TELEMETRY__NO_REPAIR_OBLIGATION_CREATED``,
    and the improvement queue gains no actionable work -- measured, and said
    plainly rather than left to be inferred. Retrying a failed goal would
    re-execute an action whose effects may already have occurred, which is
    exactly what `_effect_may_have_occurred` exists to gate; that belongs to a
    door that owns the retry, not to a recorder.

    `state_path` is a passthrough to that module's own argument, unused by the
    live path, so a test can aim this at a scratch state instead of the real
    one. Contained for the same reason the other two hooks are: a learning
    layer that can fail a run is worse than no learning layer, and the caller's
    result is returned byte for byte whatever happens here.
    """
    try:
        if not isinstance(out, Mapping) or out.get("pass") is True:
            return
        from canonical.runtime import (
            autonomous_verified_self_improvement_v1 as _self_improvement,
        )

        kwargs: dict[str, Any] = {}
        if state_path is not None:
            kwargs["state_path"] = state_path
        _self_improvement.integrate_solver_output(out, **kwargs)
    except Exception:
        # Deliberate: see the docstring. Diagnosis is best-effort by design.
        pass


def run_raw_goal(request: Mapping[str, Any]) -> dict[str, Any]:
    """Compile and run one raw plain-language goal, then remember the outcome.

    A thin wrapper: the compile/plan/execute/verify path is
    `_run_raw_goal_impl`, unchanged. Wrapping rather than editing its many
    return sites means experience is recorded on exactly one code path, so no
    return can be missed and none can be recorded twice.

    The three hooks are disjoint by outcome, not redundant: a success becomes
    an episode, either outcome becomes a pathology cell about this machine, and
    a failure becomes a diagnosed, counted failure class.
    """
    out = _run_raw_goal_impl(request)
    _record_raw_goal_experience(out, request)
    _record_raw_goal_pathology(out, request)
    _record_raw_goal_failure_diagnosis(out, request)
    _advance_learning_queue()
    return out
