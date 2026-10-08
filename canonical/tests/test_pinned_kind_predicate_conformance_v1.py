"""Actual pinned production-predicate conformance and tamper tests."""
from pathlib import Path
import tempfile

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.pinned_kind_predicate_conformance_v1 import validate

KIND = "SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_V1"
REAL_PATH = "canonical/runtime/symbolic_router_deployment_canary_predicate_v1.py"
KNOWN_SOURCE_BLOB = "b8a9ba97dc4a2e11cfbcf03fb36dcaa5ca0e45e6"


def original_source():
    root = Path(__file__).resolve().parents[2]
    return (root / REAL_PATH).read_text(encoding="utf-8")


def check(text=None, expected_kind=KIND, stale_digest=False):
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        file = root / REAL_PATH
        file.parent.mkdir(parents=True)
        data = (original_source() if text is None else text).encode("utf-8")
        file.write_bytes(data)
        sha = git_blob_id(data, object_format="sha1")
        if stale_digest:
            sha = "0"*40
        return validate({"path":REAL_PATH, "git_blob_sha":sha},
                        repo_root=root, expected_kind=expected_kind)


def test_real_exact_pinned_source_matches():
    root = Path(__file__).resolve().parents[2]
    data = (root / REAL_PATH).read_bytes()
    assert git_blob_id(data, object_format="sha1") == KNOWN_SOURCE_BLOB
    result = validate({"path":REAL_PATH,"git_blob_sha":KNOWN_SOURCE_BLOB},
                      repo_root=root, expected_kind=KIND)
    assert result["pass"] is True
    assert result["source_to_contract_conformance"] is True
    assert result["production_route_adequacy"] is False
    assert result["target_scope_complete"] is False
    assert result["creditable"] is False
    assert result["u_empty_authorized"] is False
    assert result["terminal_authority"] is False


def test_wrong_expected_kind_is_rejected():
    assert check(expected_kind="DIFFERENT_KIND")["pass"] is False


def test_stale_content_hash_is_rejected():
    assert check(stale_digest=True)["reason"] == "SOURCE_BLOB_MISMATCH"


def test_changed_key_is_rejected():
    modified = original_source().replace('get("kind")', 'get("other")')
    assert check(text=modified)["reason"] == "FUNCTION_SEMANTICS_DO_NOT_MATCH_RESTRICTED_FORM"


def test_changed_comparison_is_rejected():
    modified = original_source().replace(" == \"SYMBOLIC_ROUTER", " != \"SYMBOLIC_ROUTER")
    assert check(text=modified)["pass"] is False


def test_guard_inversion_is_rejected():
    modified = original_source().replace("if not isinstance", "if isinstance")
    assert check(text=modified)["pass"] is False


def test_added_print_side_effect_is_rejected():
    modified = original_source().replace(
        '    return context.get("kind")',
        '    print("side effect")\n    return context.get("kind")')
    assert check(text=modified)["pass"] is False


def test_global_mutation_is_rejected():
    assert check(text=original_source() + "\nMapping = dict\n")["pass"] is False


def test_extra_function_is_rejected():
    assert check(text=original_source() + "\ndef secondary():\n    return True\n")["pass"] is False


def test_extra_function_call_is_rejected():
    modified = original_source().replace('context.get("kind")', 'context.get("kind").upper()')
    assert check(text=modified)["pass"] is False


def test_real_source_pins_not_regenerated_claims():
    assert check()["source_git_blob_sha"] == KNOWN_SOURCE_BLOB
