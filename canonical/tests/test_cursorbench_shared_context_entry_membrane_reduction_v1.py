from __future__ import annotations

import copy
import json
import os
import pathlib
import pwd
import tempfile

from canonical.runtime import honesty_closed_world_input_manifest_v1 as manifest
from canonical.runtime import zero_ambient_namespace_launcher_v1 as namespace

ROOT = pathlib.Path(__file__).resolve().parents[2]
REDUCTION = ROOT / "canonical/governance/CURSORBENCH_SHARED_CONTEXT_ENTRY_MEMBRANE_REDUCTION_20261009_V1.json"
SOURCE_CUT = ROOT / "canonical/governance/CURSORBENCH_SOURCE_COVERAGE_MINCUT_20261009_V1.json"
BOUNDARY_CUT = ROOT / "canonical/governance/CURSORBENCH_PREVERIFIER_INFORMATION_BOUNDARY_MINCUT_20261009_V1.json"


def _identity():
    if os.geteuid() != 0:
        return os.geteuid(), os.getegid()
    for name in ("oai", "ubuntu", "nobody"):
        try:
            ent = pwd.getpwnam(name)
        except KeyError:
            continue
        if ent.pw_uid > 0 and ent.pw_gid > 0:
            return ent.pw_uid, ent.pw_gid
    for ent in pwd.getpwall():
        if ent.pw_uid >= 1000 and ent.pw_gid > 0:
            return ent.pw_uid, ent.pw_gid
    raise RuntimeError("NO_NONROOT_TEST_IDENTITY")


def test_shared_context_entry_membrane_reuses_existing_closed_world_mechanics_without_truth_credit():
    reduction = json.loads(REDUCTION.read_text(encoding="utf-8"))
    source_cut = json.loads(SOURCE_CUT.read_text(encoding="utf-8"))
    boundary_cut = json.loads(BOUNDARY_CUT.read_text(encoding="utf-8"))

    assert reduction["source_mincut"]["git_blob_sha"] == "ebec2bb7267947360d386e7fda7eabd45eb8e2d6"
    assert reduction["information_boundary_mincut"]["git_blob_sha"] == "a5c283e8e09f82ff10c9daaeea0951a304bd6e6d"
    assert source_cut["verifier_premise_decomposition"]["context_boundary"][0]["id"] == "SC_SOURCE_AUTHORITY_COMPLETENESS"
    assert boundary_cut["minimal_sufficient_proof"]["brain_controlled_per_model_internal_audit"] is not None

    uid, gid = _identity()
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        if os.geteuid() == 0:
            os.chown(root, uid, gid)
        (root / "task.txt").write_text("visible task bytes", encoding="utf-8")
        (root / "builder.py").write_text("print('builder placeholder')\n", encoding="utf-8")
        if os.geteuid() == 0:
            os.chown(root / "task.txt", uid, gid)
            os.chown(root / "builder.py", uid, gid)

        scanned = manifest.scan_input_dir(root)
        declared = {
            "schema": manifest.SCHEMA,
            "entries": copy.deepcopy(scanned["entries"]),
            "manifest_sha256": scanned["manifest_sha256"],
        }
        verified = manifest.verify_declared_manifest(
            input_dir=root,
            declared_manifest=declared,
        )
        assert verified["status"] == "PASS__EXACT_CLOSED_WORLD_INPUT_TREE_BOUND"
        assert verified["entry_count"] == 2
        assert verified["extra_unmanifested_file_count"] == 0
        assert len(verified["ledger_declared_inputs"]) == 2

        policy = namespace.canonical_policy({
            "argv": ["/usr/bin/python3", "-I", "/input/builder.py"],
            "input_dir": str(root),
            "host_uid": uid,
            "host_gid": gid,
            "limits": {
                "pids": 16,
                "memory_mb": 128,
                "cpu_seconds": 3,
                "wallclock_s": 5,
                "scratch_mb": 16,
                "max_file_mb": 2,
                "nofile": 32,
                "broker_max_bytes": 65536,
            },
        })
        assert policy["input_dir"] == str(root.resolve())
        assert policy["authority"]["network"] == "PRIVATE_NAMESPACE_LOOPBACK_ONLY"
        assert policy["authority"]["host_filesystem"] == "READ_ONLY_SYSTEM_AND_SINGLE_INPUT_BIND_ONLY"
        assert policy["authority"]["linux_capabilities"] == "DROPPED_BEFORE_WORKLOAD"
        assert policy["authority"]["privilege_escalation"] == "DENY_NO_NEW_PRIVILEGES"
        assert policy["authority"]["material_effect_channel"] == "ONE_INHERITED_BROKER_FD_ONLY"

        (root / "undeclared-secret.txt").write_text("not in frozen manifest", encoding="utf-8")
        if os.geteuid() == 0:
            os.chown(root / "undeclared-secret.txt", uid, gid)
        try:
            manifest.verify_declared_manifest(
                input_dir=root,
                declared_manifest=declared,
            )
        except manifest.ClosedWorldInputError as exc:
            assert "DOES_NOT_EQUAL_ACTUAL_TREE" in str(exc)
        else:
            raise AssertionError("unmanifested input was accepted")

    theorem = reduction["theorem"]
    assert theorem["internal_per_context_pipeline_count_before"] == 2
    assert theorem["internal_per_context_pipeline_count_after"] == 1
    assert theorem["semantic_truth_delta"] == 0
    assert theorem["current_4_0_protocol_continuity_delta"] == 0
    assert theorem["atom_truth_delta"] == 0

    assert source_cut["deduction"]["typed_semantics_atom_truth_proved"] is False
    assert source_cut["deduction"]["failure_mode_completeness_atom_truth_proved"] is False
    assert boundary_cut["deduction"]["no_hidden_verifier_access_atom_truth_proved"] is False
