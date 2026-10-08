"""R2 transactional direct adequacy for exact machine-readable visual-code goals.

Bounded family only:
- QR PNG generated from one exact quoted ASCII payload.
- Code 128 PNG generated from one exact quoted ASCII payload.

Adequacy is granted only when an exact side-effect-free grammar selects the
expected verified Brain-owned producer, execution creates the one declared
repository-local PNG, and the independently verified zbarimg capability decodes
that PNG to exactly the quoted payload. Failure restores prior output bytes or
removes a newly created artifact. No external or irreversible-effect authority
is granted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as bound_exec
from canonical.runtime.bound_capabilities import cli_command
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA = "PROJECT_BRAIN_R2_VISUAL_CODE_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
_PAYLOAD = r"[A-Za-z0-9 _.,:/@+\-]{1,128}"
GRAMMAR = re.compile(
    r'^Generate a (?P<kind>QR code|Code 128 barcode) image encoding exactly "'
    + r'(?P<payload>' + _PAYLOAD + r')" and save it to '
    + r'(?P<output>' + _PATH + r'\.png)\.?$',
    re.IGNORECASE,
)

PRODUCERS = {
    "QR": "image.qr.generate.qrencode",
    "CODE128": "auto.apt.zint",
}
VERIFIER = "image.code.decode.zbarimg"


def _base(status: str, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _inside(root: Path, rel: str) -> Path:
    rr = root.resolve()
    p = (rr / str(rel)).resolve()
    if p == rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _format(kind: str) -> str:
    return "QR" if kind.lower().startswith("qr") else "CODE128"


def _packages(entry: Mapping[str, Any]) -> set[str]:
    source = entry.get("source")
    if not isinstance(source, Mapping):
        return set()
    rows = source.get("packages")
    if not isinstance(rows, list):
        return set()
    return {
        str(row.get("name") or "").strip()
        for row in rows
        if isinstance(row, Mapping) and str(row.get("name") or "").strip()
    }


def _verified_pair(
    registry: Mapping[str, Any],
    fmt: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    producer_id = PRODUCERS[fmt]
    producer = registry.get(producer_id)
    verifier = registry.get(VERIFIER)
    if not isinstance(producer, Mapping) or producer.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("VISUAL_CODE_PRODUCER_NOT_VERIFIED:" + producer_id)
    if not isinstance(verifier, Mapping) or verifier.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("VISUAL_CODE_VERIFIER_NOT_VERIFIED")
    if str(producer.get("adapter_module") or "") != "cli_command":
        raise ValueError("VISUAL_CODE_PRODUCER_ADAPTER_UNSUPPORTED")
    if str(verifier.get("adapter_module") or "") != "cli_command":
        raise ValueError("VISUAL_CODE_VERIFIER_ADAPTER_UNSUPPORTED")
    vv = verifier.get("verification")
    if not isinstance(vv, Mapping) or vv.get("independent_verified") is not True:
        raise ValueError("VISUAL_CODE_INDEPENDENT_VERIFIER_REQUIRED")
    formats = {str(x).upper() for x in (vv.get("formats") or [])}
    if fmt not in formats:
        raise ValueError("VISUAL_CODE_FORMAT_NOT_IN_VERIFIER_AUTHORITY:" + fmt)
    producer_packages = _packages(producer)
    verifier_packages = _packages(verifier)
    if not producer_packages or not verifier_packages or producer_packages & verifier_packages:
        raise ValueError("VISUAL_CODE_PRODUCER_VERIFIER_SUPPLIER_INDEPENDENCE_UNPROVED")
    return producer, verifier


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}

    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    root = Path(repo_root).resolve()
    fmt = _format(match.group("kind"))
    payload = match.group("payload")
    output_path = match.group("output")
    producer_id = PRODUCERS[fmt]

    try:
        destination = _inside(root, output_path)
        registry = live_bound.load_verified_registry()
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        producer, verifier = _verified_pair(admissible, fmt)

        if fmt == "QR":
            compiled = goal_compiler.compile_goal(goal, admissible, root)
            if compiled.get("controller_actions") is not None:
                raise ValueError("COMPOUND_CONTROLLER_NOT_ALLOWED")
            if compiled.get("selected_capability") != producer_id:
                raise ValueError(
                    "VISUAL_CODE_PRODUCER_SELECTION_MISMATCH:"
                    + str(compiled.get("selected_capability"))
                )
            inputs = compiled.get("inputs")
            if not isinstance(inputs, Mapping):
                raise ValueError("COMPILED_INPUTS_INVALID")
            if inputs.get("text") != payload or inputs.get("output_path") != output_path:
                raise ValueError("COMPILED_PAYLOAD_OR_OUTPUT_BINDING_MISMATCH")
            targets = compiled.get("target_effects")
            if not isinstance(targets, list) or not targets:
                raise ValueError("COMPILED_TARGETS_INVALID")
            execution_binding = {
                "execution_mode": "LIVE_RAW_GOAL",
                "execution_instance_id": None,
                "registry_file_sha256": None,
                "registry_entry_sha256": None,
                "rendered_action_sha256": None,
            }
        else:
            instance_id = (
                "r2-visual-code-"
                + sha256((producer_id + "\n" + goal).encode("utf-8")).hexdigest()[:16]
            )
            prepared = bound_exec.prepare(
                producer_id,
                inputs={"text": payload, "output_path": output_path},
                instance_id=instance_id,
            )
            targets = prepared.get("provides")
            if not isinstance(targets, list) or not targets:
                raise ValueError("BOUND_EXECUTION_TARGETS_INVALID")
            execution_binding = {
                "execution_mode": "VERIFIED_BOUND_EXECUTION_ADAPTER",
                "execution_instance_id": instance_id,
                "registry_file_sha256": prepared["registry_file_sha256"],
                "registry_entry_sha256": prepared["registry_entry_sha256"],
                "rendered_action_sha256": prepared["rendered_action_sha256"],
            }
        contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=targets,
        )
        if contract.get("pass") is not True:
            raise ValueError("LOSSLESS_RAW_CONTRACT_FAILED")

        return {
            **_base("DIRECT_VISUAL_CODE_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id": goal_scoped_policy_id(producer_id, goal),
            "format": fmt,
            "payload": payload,
            "payload_sha256": sha256(payload.encode("utf-8")).hexdigest(),
            "capability_id": producer_id,
            "verifier_capability_id": VERIFIER,
            "producer_packages": sorted(_packages(producer)),
            "verifier_packages": sorted(_packages(verifier)),
            "output_path": output_path,
            **execution_binding,
            "raw_contract": contract,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "acceptance_obligation_count": len(
                contract["acceptance_contract"]["obligations"]
            ),
            "transaction_scope": "ONE_REPOSITORY_LOCAL_PNG_OUTPUT",
            "preflight_execution_authority": False,
            "destination_existed_before": destination.exists(),
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _independent_decode(
    pf: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> Mapping[str, Any]:
    result = cli_command.run(
        {
            "argv": ["zbarimg", "--quiet", "--raw", str(pf["output_path"])],
            "capability_id": VERIFIER,
            "timeout_s": 60,
        },
        repo_root,
    )
    decoded = str(result.get("stdout") or "").rstrip("\r\n")
    return {
        "verified": decoded == pf["payload"],
        "producer_independent": True,
        "decoded_payload": decoded,
        "decoded_payload_sha256": sha256(decoded.encode("utf-8")).hexdigest(),
        "expected_payload_sha256": pf["payload_sha256"],
        "verifier_capability_id": VERIFIER,
        "producer_packages": list(pf["producer_packages"]),
        "verifier_packages": list(pf["verifier_packages"]),
        "supplier_packages_disjoint": not (
            set(pf["producer_packages"]) & set(pf["verifier_packages"])
        ),
        "raw_decoder_result": deepcopy(dict(result)),
    }


def _restore(path: Path, existed: bool, prior: bytes | None) -> None:
    if existed:
        assert prior is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    verifier_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    pf = preflight(request, repo_root=repo_root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    root = Path(repo_root).resolve()
    destination = _inside(root, str(pf["output_path"]))
    existed = destination.exists()
    prior = destination.read_bytes() if existed else None

    try:
        if pf["execution_mode"] == "LIVE_RAW_GOAL":
            raw = live_bound.run_raw_goal(request)
            execution_ok = (
                isinstance(raw, Mapping)
                and raw.get("pass") is True
                and raw.get("compiled_capability_id") == pf["capability_id"]
                and raw.get("raw_goal_sha256") == pf["goal_sha256"]
                and raw.get("raw_source_coverage_complete") is True
            )
        elif pf["execution_mode"] == "VERIFIED_BOUND_EXECUTION_ADAPTER":
            raw = bound_exec.execute(
                pf["capability_id"],
                inputs={
                    "text": pf["payload"],
                    "output_path": pf["output_path"],
                },
                instance_id=pf["execution_instance_id"],
                expected_registry_file_sha256=pf["registry_file_sha256"],
                expected_registry_entry_sha256=pf["registry_entry_sha256"],
                expected_rendered_action_sha256=pf["rendered_action_sha256"],
            )
            execution_ok = (
                isinstance(raw, Mapping)
                and raw.get("pass") is True
                and raw.get("capability_id") == pf["capability_id"]
                and raw.get("registry_file_sha256") == pf["registry_file_sha256"]
                and raw.get("registry_entry_sha256") == pf["registry_entry_sha256"]
                and raw.get("rendered_action_sha256") == pf["rendered_action_sha256"]
                and isinstance(raw.get("result"), Mapping)
                and raw["result"].get("output_path") == pf["output_path"]
                and raw["result"].get("output_verified") is True
            )
        else:
            raw = None
            execution_ok = False

        if not execution_ok:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__TRANSACTIONAL_VISUAL_CODE_EXECUTION_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "transaction_rolled_back": True,
                "raw_result": deepcopy(dict(raw)) if isinstance(raw, Mapping) else raw,
            }

        if (
            not destination.is_file()
            or not destination.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        ):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "PNG_OUTPUT_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }

        evidence = (
            verifier_provider(pf)
            if verifier_provider is not None
            else _independent_decode(pf, repo_root=root)
        )
        full_decode = (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent") is True
            and evidence.get("supplier_packages_disjoint") is not False
            and evidence.get("decoded_payload") == pf["payload"]
        )
        if not full_decode:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__INDEPENDENT_VISUAL_CODE_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "transaction_rolled_back": True,
                "independent_verification": deepcopy(dict(evidence))
                if isinstance(evidence, Mapping) else None,
            }

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_VISUAL_CODE_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "policy_id": pf["policy_id"],
            "capability_id": pf["capability_id"],
            "verifier_capability_id": pf["verifier_capability_id"],
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "format": pf["format"],
            "execution_mode": pf["execution_mode"],
            "payload_sha256": pf["payload_sha256"],
            "output_path": pf["output_path"],
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "policy_adequacy_authority": True,
            "transaction_committed": True,
            "transaction_rolled_back": False,
            "independent_verification": deepcopy(dict(evidence)),
            "raw_result": deepcopy(dict(raw)),
            "authority_boundary": (
                "ONLY_EXACT_SINGLE_ACTION_QUOTED_ASCII_PAYLOAD_TO_QR_OR_CODE128_PNG_GRAMMARS;"
                "ONE_REPOSITORY_LOCAL_PNG_OUTPUT;VERIFIED_BOUND_PRODUCER;"
                "PRODUCER_INDEPENDENT_ZBARIMG_SEMANTIC_DECODE_EQUALS_EXACT_PAYLOAD;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(destination, existed, prior)
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "policy_id": pf.get("policy_id"),
            "capability_id": pf.get("capability_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
            "transaction_rolled_back": True,
        }
