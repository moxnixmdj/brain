"""Acceptance must inspect the manifest and the actual archived bytes.

The traces below include real adapter outputs for positive controls. Negative
controls deliberately forge successful trace metadata; they exercise the direct
acceptance boundary, not a claim of a live-front-door exploit.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities import archive_tarfile, archive_verify_gnu_tar
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_archive_compound_acceptance_v1 import verify as verify_compound
from canonical.runtime.raw_goal_trace_acceptance_v1 import (
    _inspect_archive_verify,
    _inspect_tar_gz_create_from_manifest,
    verify as verify_trace,
)

COMPOUND = "Create a tar.gz archive from a manifest and verify the archive against that manifest."
SINGLE = "Verify a tar.gz archive against its manifest."
SINGLE_CREATE = "Create a tar.gz archive from a manifest."
CREATE = "archive.tar_gz.create_from_manifest"
VERIFY = "archive.verify.tar_gz.gnu"
MANIFEST = "canonical/manifest.json"
SOURCE = "canonical/source.txt"
ARCHIVE = "bundle.tar.gz"


@pytest.fixture
def bundle(tmp_path: Path):
    (tmp_path / "canonical").mkdir()
    (tmp_path / SOURCE).write_bytes(b"original bytes\n")
    (tmp_path / "canonical/extra.txt").write_bytes(b"extra bytes\n")
    (tmp_path / MANIFEST).write_text(
        json.dumps({"records": [{"verification_paths": [SOURCE]}]}), encoding="utf-8"
    )
    create_args = {"capability_id": CREATE, "manifest_path": MANIFEST, "output_path": ARCHIVE}
    verify_args = {"capability_id": VERIFY, "manifest_path": MANIFEST, "archive_path": ARCHIVE}
    created = archive_tarfile.run(create_args, tmp_path)
    verified = archive_verify_gnu_tar.run(verify_args, tmp_path)
    return tmp_path, create_args, verify_args, created, verified


def _contract(goal):
    return compile_contract(goal, source_id="user", routing_target_effects=["archive.verified"])


def _compound(root, create_args, verify_args, created, verified):
    trace = [{"plan": {"args": create_args}, "result": created},
             {"plan": {"args": verify_args}, "result": verified},
             {"result": {"type": "finish"}}]
    return verify_compound(goal=COMPOUND, execution=trace, raw_contract=_contract(COMPOUND), root=root)


def _single(root, verify_args, verified, goal=SINGLE):
    return verify_trace(
        goal=goal,
        compiled_plan={"selected_capability": VERIFY},
        execution=[{"plan": {"args": verify_args}, "result": verified},
                   {"result": {"type": "finish"}}],
        raw_contract=_contract(goal), root=root,
    )


def _add_bytes(tf, name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    tf.addfile(info, io.BytesIO(data))


def _rewrite_invalid(root, kind):
    with tarfile.open(root / ARCHIVE, "w:gz") as tf:
        manifest_bytes = (root / MANIFEST).read_bytes()
        if kind == "changed_manifest_bytes":
            manifest_bytes += b" "
        _add_bytes(tf, MANIFEST, manifest_bytes)
        if kind == "missing_member":
            return
        if kind == "symlink_member":
            info = tarfile.TarInfo(SOURCE)
            info.type = tarfile.SYMTYPE
            info.linkname = "source.txt"
            tf.addfile(info)
        else:
            data = b"corrupted\n" if kind == "changed_member_bytes" else (root / SOURCE).read_bytes()
            _add_bytes(tf, SOURCE, data)
        if kind == "duplicate_member":
            _add_bytes(tf, SOURCE, (root / SOURCE).read_bytes())
        if kind == "extra_existing_member":
            _add_bytes(tf, "canonical/extra.txt", (root / "canonical/extra.txt").read_bytes())


def test_real_create_and_verify_satisfy_the_exact_compound_goal(bundle):
    assert _compound(*bundle)["semantic_acceptance_complete"] is True


@pytest.mark.parametrize("goal", [SINGLE, "Verify bundle.tar.gz against canonical/manifest.json"])
def test_real_verification_satisfies_only_the_exact_bounded_sentence(bundle, goal):
    root, _, verify_args, _, verified = bundle
    result = _single(root, verify_args, verified, goal)
    assert result["semantic_acceptance_complete"] is True, result
    assert result["independent_reinspection"] is True


@pytest.mark.parametrize("kind", [
    "changed_member_bytes", "changed_manifest_bytes", "missing_member",
    "extra_existing_member", "duplicate_member", "symlink_member",
])
def test_both_reinspectors_reject_forged_success_for_invalid_archive(bundle, kind):
    root, create_args, verify_args, created, verified = bundle
    _rewrite_invalid(root, kind)
    # Forge the claimed member list as well; neither inspector may use it as
    # authority for the member set or the contents.
    with tarfile.open(root / ARCHIVE, "r:gz") as tf:
        members = sorted(tf.getnames())
    forged = {**verified, "members": members, "member_count": len(members), "verified": True}
    compound = _compound(root, create_args, verify_args, created, forged)
    ok, _, _ = _inspect_archive_verify(verify_args, forged, root)
    assert compound["semantic_acceptance_complete"] is False, (kind, compound)
    assert ok is False, kind


def test_real_creation_satisfies_the_exact_bounded_sentence(bundle):
    root, create_args, _, created, _ = bundle
    result = verify_trace(
        goal=SINGLE_CREATE, compiled_plan={"selected_capability": CREATE},
        execution=[{"plan": {"args": create_args}, "result": created},
                   {"result": {"type": "finish"}}],
        raw_contract=_contract(SINGLE_CREATE), root=root,
    )
    assert result["semantic_acceptance_complete"] is True, result
    assert result["independent_reinspection"] is True


@pytest.mark.parametrize("kind", [
    "changed_member_bytes", "changed_manifest_bytes", "missing_member",
    "extra_existing_member", "duplicate_member", "symlink_member",
])
def test_create_reinspection_rejects_forged_metadata_for_invalid_archive(bundle, kind):
    root, create_args, _, created, _ = bundle
    _rewrite_invalid(root, kind)
    with tarfile.open(root / ARCHIVE, "r:gz") as tf:
        members = sorted(tf.getnames())
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in members if (root / name).is_file()}
    forged = {**created, "output_sha256": hashlib.sha256((root / ARCHIVE).read_bytes()).hexdigest(),
              "output_bytes": (root / ARCHIVE).stat().st_size,
              "members": members, "member_count": len(members), "source_sha256": hashes}
    ok, _, _ = _inspect_tar_gz_create_from_manifest(create_args, forged, root)
    assert ok is False, kind


@pytest.mark.parametrize("kind", [
    "truncate_one", "truncate_footer", "truncate_more", "bad_crc", "trailing_garbage", "second_gzip_member",
])
def test_reinspectors_require_a_complete_intact_gzip_stream(bundle, kind):
    root, create_args, verify_args, created, verified = bundle
    path = root / ARCHIVE
    raw = path.read_bytes()
    corrupted = {
        "truncate_one": raw[:-1],
        "truncate_footer": raw[:-8],
        "truncate_more": raw[:-16],
        "bad_crc": raw[:-8] + bytes(8),
        "trailing_garbage": raw + b"garbage",
        "second_gzip_member": raw + gzip.compress(b"unexpected data"),
    }[kind]
    path.write_bytes(corrupted)
    digest = hashlib.sha256(corrupted).hexdigest()
    forged_create = {**created, "output_sha256": digest, "output_bytes": len(corrupted)}
    forged_verify = {**verified, "archive_sha256": digest}
    assert _compound(root, create_args, verify_args, forged_create, forged_verify)[
        "semantic_acceptance_complete"] is False, kind
    assert _inspect_tar_gz_create_from_manifest(create_args, forged_create, root)[0] is False, kind
    assert _inspect_archive_verify(verify_args, forged_verify, root)[0] is False, kind


def test_matching_paths_and_exact_sentence_do_not_license_an_unperformed_followup(bundle):
    root, _, verify_args, _, verified = bundle
    goal = SINGLE + " Delete canonical/source.txt."
    result = _single(root, verify_args, verified, goal)
    assert result["semantic_acceptance_complete"] is False
    assert (root / SOURCE).is_file()


def test_explicitly_named_archive_must_match_the_trace(bundle):
    root, _, verify_args, _, verified = bundle
    result = _single(root, verify_args, verified,
                     "Verify other.tar.gz against canonical/manifest.json")
    assert result["semantic_acceptance_complete"] is False


def test_explicitly_named_manifest_must_match_the_trace(bundle):
    root, _, verify_args, _, verified = bundle
    result = _single(root, verify_args, verified,
                     "Verify bundle.tar.gz against canonical/other.json")
    assert result["semantic_acceptance_complete"] is False


def _single_create(root, create_args, created, goal):
    return verify_trace(
        goal=goal, compiled_plan={"selected_capability": CREATE},
        execution=[{"plan": {"args": create_args}, "result": created},
                   {"result": {"type": "finish"}}],
        raw_contract=_contract(goal), root=root,
    )


def test_named_create_sentence_is_accepted_only_with_both_matching_paths(bundle):
    root, create_args, _, created, _ = bundle
    goal = f"Create a tar.gz archive from {MANIFEST} and save it to {ARCHIVE}."
    result = _single_create(root, create_args, created, goal)
    assert result["semantic_acceptance_complete"] is True, result
    assert result["independent_reinspection"] is True


@pytest.mark.parametrize("goal", [
    f"Create a tar.gz archive from canonical/other.json and save it to {ARCHIVE}.",
    f"Create a tar.gz archive from {MANIFEST} and save it to other.tar.gz.",
    f"Create a tar.gz archive from {MANIFEST} and save it to {ARCHIVE}. Delete {SOURCE}.",
    f"Create a tar.gz archive from {MANIFEST} and save it to {ARCHIVE} and delete {SOURCE}.",
])
def test_named_create_does_not_accept_mismatches_or_additional_instructions(bundle, goal):
    root, create_args, _, created, _ = bundle
    result = _single_create(root, create_args, created, goal)
    assert result["semantic_acceptance_complete"] is False
    assert (root / SOURCE).is_file()
