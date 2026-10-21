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


def run_raw_goal(request: Mapping[str, Any]) -> dict[str, Any]:
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

        controller_actions = compiled.get("controller_actions")
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
        if entry.get("capability_source") == "receipt_projection":
            # the registry's own template resolves through the BOUND registry (promoted entries
            # only) and refuses every receipt-backed capability before any work is done
            action = bound_capability_controller_action(selected, entry, dict(inputs))
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
