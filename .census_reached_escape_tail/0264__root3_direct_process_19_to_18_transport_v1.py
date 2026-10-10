from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OLD_COMMIT = "fd60e692d08176c8f5cb40cbc915fa46eaea2fa5"
OLD_CERT = "canonical/governance/ROOT3_DIRECT_PROCESS_MEDIATION_DOMINATOR_CERT_20261005_V1.json"
OLD_VERIFICATION = "canonical/verification/ROOT3_DIRECT_PROCESS_MEDIATION_DOMINATOR_SPRITE_VERIFICATION_20261005_V1.json"
DELETED_KEY = (
    "canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",
    40,
    "subprocess.run",
)
PATHS = {
    "dominator": "canonical/runtime/shared_channel_dominator_v1.py",
    "mediator": "canonical/runtime/root3_subprocess_mediator_v2.py",
    "authorizer": "canonical/runtime/root3_subprocess_final_authorizer_adapter_v2.py",
    "classifier": "canonical/runtime/root3_subprocess_callsite_classifier_v1.py",
    "registry": "canonical/runtime/root3_subprocess_effect_class_registry_v1.py",
    "mediator_verification": "canonical/verification/ROOT3_CLASS_BOUND_SUBPROCESS_MEDIATOR_V2_SPRITE_VERIFICATION_20261005_V1.json",
}
EXPECTED_CURRENT_BLOBS = {
    PATHS["dominator"]: "bd7d63b190e9e3cbbcd29c5392439de49fe0778f",
    PATHS["mediator"]: "80560cdfa91c11a4b47b9ee2161af726b2f9bccf",
    PATHS["authorizer"]: "14182a4a5112c7d585cdcac68f2eca1dfcf6c17d",
    PATHS["classifier"]: "e654b264096dba724d82f04e5adef0dc6d6c90f7",
    PATHS["registry"]: "24e00a3e6b70d0879cab664a8512f243973c6196",
    PATHS["mediator_verification"]: "6a96adf77e2d63fb006198f457345a8a995a7997",
}
EXPECTED_OLD_BLOBS = {
    OLD_CERT: "9357a15cfd4313092baba45d206c20239be4aadc",
    OLD_VERIFICATION: "f0637b3a6a2be733cee947083bbde2e97e618548",
    PATHS["dominator"]: "bd7d63b190e9e3cbbcd29c5392439de49fe0778f",
    PATHS["mediator"]: "9ca4dfee3d986327850bd3de9ff6f10101769ac7",
    PATHS["authorizer"]: "3dd17e22153771483d7746280ce18bb92a1ff009",
    PATHS["classifier"]: "ca6bf4da45dd7b59ba7d73ebcbe05525c654743d",
    PATHS["registry"]: "c5d97db30a737fe9608a18e422910a48f6ec74f1",
    PATHS["mediator_verification"]: "6a96adf77e2d63fb006198f457345a8a995a7997",
}


class TransportError(RuntimeError):
    pass


def _git_show(commit: str, path: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "show", f"{commit}:{path}"],
            cwd=ROOT,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        raise TransportError(
            "GIT_SHOW_FAILED:" + commit + ":" + path + ":" + exc.output.decode("utf-8", "replace")
        ) from exc


def _current(path: str) -> bytes:
    p = ROOT / path
    if not p.is_file():
        raise TransportError("CURRENT_PATH_MISSING:" + path)
    return p.read_bytes()


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _assert_blob(data: bytes, expected: str, label: str) -> None:
    got = _blob_sha(data)
    if got != expected:
        raise TransportError(f"BLOB_MISMATCH:{label}:{got}!={expected}")


def _assignment_literal(source: str, name: str) -> Any:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return ast.literal_eval(node.value)
    raise TransportError("ASSIGNMENT_NOT_FOUND:" + name)


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            if node.end_lineno is None:
                raise TransportError("FUNCTION_END_MISSING:" + name)
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise TransportError("FUNCTION_NOT_FOUND:" + name)


def _normalize_mediator(old: str, new: str) -> tuple[str, str]:
    old = old.replace("exact 29-site subprocess universe", "exact N-site subprocess universe")
    new = new.replace("exact 18-site subprocess universe", "exact N-site subprocess universe")
    return old, new


def _normalize_authorizer(old: str, new: str) -> tuple[str, str]:
    old = old.replace('registry_site_count", -1)) != 19:', 'registry_site_count", -1)) != N:')
    new = new.replace('registry_site_count", -1)) != 18:', 'registry_site_count", -1)) != N:')
    return old, new


def _normalize_classifier(old: str, new: str) -> tuple[str, str]:
    replacements = (
        ("frozen as 19 exact Python process-creation", "frozen as N exact Python process-creation"),
        ("modifying the 19 callers", "modifying the N callers"),
        ("len(EXPECTED) != 19", "len(EXPECTED) != N"),
    )
    for a, b in replacements:
        old = old.replace(a, b)
    replacements_new = (
        ("frozen as 18 exact Python process-creation", "frozen as N exact Python process-creation"),
        ("modifying the 18 callers", "modifying the N callers"),
        ("len(EXPECTED) != 18", "len(EXPECTED) != N"),
    )
    for a, b in replacements_new:
        new = new.replace(a, b)
    return old, new


def verify(root: Path = ROOT) -> dict[str, Any]:
    global ROOT
    prior_root = ROOT
    ROOT = root
    try:
        old_bytes = {path: _git_show(OLD_COMMIT, path) for path in EXPECTED_OLD_BLOBS}
        current_bytes = {path: _current(path) for path in EXPECTED_CURRENT_BLOBS}
        for path, expected in EXPECTED_OLD_BLOBS.items():
            _assert_blob(old_bytes[path], expected, "OLD:" + path)
        for path, expected in EXPECTED_CURRENT_BLOBS.items():
            _assert_blob(current_bytes[path], expected, "CURRENT:" + path)

        old_cert = json.loads(old_bytes[OLD_CERT])
        old_ver = json.loads(old_bytes[OLD_VERIFICATION])
        if old_ver.get("exact_result", {}).get("shared_no_bypass_proved_for_declared_graph") is not True:
            raise TransportError("OLD_INDEPENDENT_NO_BYPASS_NOT_PROVED")
        if old_ver.get("exact_result", {}).get("reachable_load_bearing_edge_count") != 19:
            raise TransportError("OLD_VERIFIED_EDGE_COUNT_NOT_19")
        old_sites = {
            (row["module_path"], int(row["lineno"]), row["process_api"])
            for row in old_cert.get("site_bindings", [])
        }
        if len(old_sites) != 19:
            raise TransportError("OLD_CERT_SITE_COUNT_NOT_19")
        if DELETED_KEY not in old_sites:
            raise TransportError("DECLARED_DELETED_SITE_NOT_IN_OLD_CERT")

        old_registry = old_bytes[PATHS["registry"]].decode()
        new_registry = current_bytes[PATHS["registry"]].decode()
        old_expected = _assignment_literal(old_registry, "EXPECTED")
        new_expected = _assignment_literal(new_registry, "EXPECTED")
        if len(old_expected) != 19 or len(new_expected) != 18:
            raise TransportError("REGISTRY_CARDINALITY_MISMATCH")
        if set(old_expected) != old_sites:
            raise TransportError("OLD_CERT_AND_OLD_REGISTRY_SITE_SET_MISMATCH")
        if set(new_expected) != old_sites - {DELETED_KEY}:
            raise TransportError("CURRENT_REGISTRY_NOT_EXACT_OLD_MINUS_ONE")
        if DELETED_KEY in new_expected:
            raise TransportError("DELETED_SITE_STILL_CURRENT")
        for key, value in new_expected.items():
            if old_expected.get(key) != value:
                raise TransportError("SURVIVING_EFFECT_CLASS_DRIFT:" + repr(key))

        if current_bytes[PATHS["dominator"]] != old_bytes[PATHS["dominator"]]:
            raise TransportError("SHARED_DOMINATOR_BYTES_CHANGED")
        if current_bytes[PATHS["mediator_verification"]] != old_bytes[PATHS["mediator_verification"]]:
            raise TransportError("MEDIATOR_VERIFICATION_BYTES_CHANGED")

        old_m = old_bytes[PATHS["mediator"]].decode()
        new_m = current_bytes[PATHS["mediator"]].decode()
        if _normalize_mediator(old_m, new_m)[0] != _normalize_mediator(old_m, new_m)[1]:
            raise TransportError("MEDIATOR_DRIFT_BEYOND_DECLARED_COUNT_TEXT")

        old_a = old_bytes[PATHS["authorizer"]].decode()
        new_a = current_bytes[PATHS["authorizer"]].decode()
        if _normalize_authorizer(old_a, new_a)[0] != _normalize_authorizer(old_a, new_a)[1]:
            raise TransportError("FINAL_AUTHORIZER_DRIFT_BEYOND_SITE_COUNT")

        old_c = old_bytes[PATHS["classifier"]].decode()
        new_c = current_bytes[PATHS["classifier"]].decode()
        if _normalize_classifier(old_c, new_c)[0] != _normalize_classifier(old_c, new_c)[1]:
            raise TransportError("CLASSIFIER_DRIFT_BEYOND_SITE_COUNT")

        # Registry semantics outside exact site membership/count must remain equal.
        if _assignment_literal(old_registry, "CLASSES") != _assignment_literal(new_registry, "CLASSES"):
            raise TransportError("EFFECT_CLASS_SET_DRIFT")
        if _assignment_literal(old_registry, "CLASS_PROOF_RESIDUALS") != _assignment_literal(new_registry, "CLASS_PROOF_RESIDUALS"):
            raise TransportError("CLASS_PROOF_RESIDUAL_DRIFT")

        old_fn = _function_source(old_registry, "classify_rows")
        new_fn = _function_source(new_registry, "classify_rows")
        old_fn = old_fn.replace("!= 19", "!= N").replace("== 19", "== N").replace("19 - len(CLASSES)", "N - len(CLASSES)")
        old_fn = old_fn.replace("19_PROCESS", "N_PROCESS").replace("19,", "N,")
        old_fn = old_fn.replace("CLASSIFICATION_COUNT_NOT_19", "CLASSIFICATION_COUNT_NOT_N").replace("/ 19 * 100.0", "/ N * 100.0")
        new_fn = new_fn.replace("!= 18", "!= N").replace("== 18", "== N").replace("18 - len(CLASSES)", "N - len(CLASSES)")
        new_fn = new_fn.replace("18_PROCESS", "N_PROCESS").replace("18,", "N,")
        new_fn = new_fn.replace("CLASSIFICATION_COUNT_NOT_18", "CLASSIFICATION_COUNT_NOT_N").replace("/ 18 * 100.0", "/ N * 100.0")
        if old_fn != new_fn:
            raise TransportError("REGISTRY_CLASSIFIER_LOGIC_DRIFT_BEYOND_COUNT")

        return {
            "schema": "PROJECT_BRAIN_ROOT3_DIRECT_PROCESS_19_TO_18_TRANSPORT_RESULT_V1",
            "status": "PASS__MONOTONE_SUBSET_TRANSPORT",
            "old_verified_site_count": 19,
            "current_site_count": 18,
            "deleted_sites": [list(DELETED_KEY)],
            "new_sites": [],
            "surviving_site_count": 18,
            "shared_dominator_identical": True,
            "mediator_semantics_transport": True,
            "final_authorizer_semantics_transport": True,
            "classifier_semantics_transport": True,
            "effect_class_registry_semantics_transport": True,
            "conclusion": "CURRENT_18_SITE_DIRECT_PROCESS_CLASSIFICATION_FINAL_AUTHORIZATION_AND_EXACT_CLASS_EXECUTOR_GATE_NO_BYPASS_FOLLOWS_BY_RESTRICTION_OF_THE_INDEPENDENTLY_VERIFIED_19_SITE_GRAPH",
            "remaining_open": [
                "PRODUCTION_BOOTSTRAP_ENTRY_DOMINANCE",
                "CHILD_PROCESS_INTERNAL_EFFECT_TOTALITY",
                "NATIVE_EXTENSION_INTERNAL_EFFECT_TOTALITY",
                "NONREPO_DEPENDENCY_EFFECT_TOTALITY",
                "EXTERNAL_TOOL_BRIDGE_OTHER_PROCESS_EFFECT_TOTALITY",
                "CLASS_EXECUTOR_SEMANTIC_SOUNDNESS",
            ],
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    finally:
        ROOT = prior_root


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
