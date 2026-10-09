from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import secrets
import shutil
import sys
import unittest

INPUT_ROOT = pathlib.Path("/input")
WORK_ROOT = pathlib.Path("/work")
REPO_INPUT = INPUT_ROOT / "repo"
REPO_WORK = WORK_ROOT / "repo"
MANIFEST = INPUT_ROOT / "material_manifest.json"
EXPECTED_MANIFEST_GIT_BLOB = "2c517cab595bc050de67d6f6bb86ab0545ed7dd3"


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def emit(value: dict) -> None:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = int(os.environ["PROJECT_BRAIN_BROKER_FD"])
    offset = 0
    while offset < len(raw):
        offset += os.write(fd, raw[offset:])


def verify_input_materials() -> tuple[dict[str, bool], dict[str, str]]:
    manifest_raw = MANIFEST.read_bytes()
    if git_blob(manifest_raw) != EXPECTED_MANIFEST_GIT_BLOB:
        raise RuntimeError("MATERIAL_MANIFEST_BLOB_MISMATCH")
    doc = json.loads(manifest_raw.decode("utf-8"))
    rows = doc.get("materials")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("MATERIAL_MANIFEST_INVALID")
    checks: dict[str, bool] = {}
    observed: dict[str, str] = {}
    for row in rows:
        rel = str(row.get("path") or "")
        expected = str(row.get("git_blob_sha") or "")
        path = REPO_INPUT / rel
        actual = git_blob(path.read_bytes())
        observed[rel] = actual
        checks[rel] = actual == expected
        if actual != expected:
            raise RuntimeError("MATERIAL_BLOB_MISMATCH:" + rel)
    return checks, observed


def main() -> int:
    material_checks, observed = verify_input_materials()
    if REPO_WORK.exists():
        shutil.rmtree(REPO_WORK)
    shutil.copytree(REPO_INPUT, REPO_WORK)
    os.chdir(REPO_WORK)
    sys.path.insert(0, str(REPO_WORK))

    from canonical.runtime import d_final_stdlib_bound_executor_v1 as ex

    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromName(
        "canonical.tests.test_d_final_stdlib_bound_executor_v1"
    )
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)

    nonce = secrets.token_hex(24)
    tmp = ex.ROOT / "canonical/astra_runtime/tmp/d-final-provider-fresh"
    tmp.mkdir(parents=True, exist_ok=True)
    source = tmp / "source.txt"
    manifest = tmp / "manifest.json"
    output = tmp / "bundle.tar.gz"
    source.write_text("provider-fresh:" + nonce + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps({
            "records": [{
                "verification_paths": [source.relative_to(ex.ROOT).as_posix()]
            }],
            "nonce": nonce,
        }, sort_keys=True),
        encoding="utf-8",
    )
    inputs = {
        "manifest_path": manifest.relative_to(ex.ROOT).as_posix(),
        "output_path": output.relative_to(ex.ROOT).as_posix(),
    }
    prepared = ex.prepare("archive.tar_gz.create_from_manifest", inputs=inputs)
    fresh = ex.execute(
        "archive.tar_gz.create_from_manifest",
        inputs=inputs,
        expected_registry_file_sha256=prepared["registry_file_sha256"],
        expected_registry_entry_sha256=prepared["registry_entry_sha256"],
        expected_rendered_action_sha256=prepared["rendered_action_sha256"],
    )

    nonstdlib_rejected = False
    nonstdlib_reason = None
    try:
        ex.inspect("pdf.extract.text.pypdf")
    except Exception as exc:
        nonstdlib_reason = type(exc).__name__ + ":" + str(exc)
        nonstdlib_rejected = "NON_STDLIB_SOURCE_REJECTED" in str(exc)

    checks = {
        "material_hashes_match": all(material_checks.values()),
        "hostile_suite_pass": result.wasSuccessful(),
        "hostile_suite_count_five": result.testsRun == 5,
        "fresh_archive_execution_pass": fresh.get("pass") is True,
        "fresh_archive_trace_reverified": (
            (fresh.get("execution_verification") or {}).get("pass") is True
        ),
        "fresh_archive_has_capsule": bool(fresh.get("composition_capsule_head_hash")),
        "nonstdlib_rejected": nonstdlib_rejected,
        "environment_minimal": set(os.environ).issubset({
            "PATH",
            "HOME",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONHASHSEED",
            "TZ",
            "LANG",
            "PROJECT_BRAIN_BROKER_FD",
        }),
    }
    passed = all(checks.values())
    emit({
        "schema": "PROJECT_BRAIN_D_FINAL_STDLIB_BOUND_PROVIDER_ZERO_AMBIENT_REPLAY_V1",
        "pass": passed,
        "status": (
            "PASS__FRESH_ZERO_AMBIENT_PROVIDER_REPLAY"
            if passed else "FAIL"
        ),
        "checks": checks,
        "material_observed_git_blobs": observed,
        "hostile_suite_output": stream.getvalue(),
        "fresh_nonce_sha256": hashlib.sha256(nonce.encode()).hexdigest(),
        "fresh_archive_result_sha256": fresh.get("result_sha256"),
        "fresh_archive_capsule_head_hash": fresh.get("composition_capsule_head_hash"),
        "registry_file_sha256": fresh.get("registry_file_sha256"),
        "registry_entry_sha256": fresh.get("registry_entry_sha256"),
        "rendered_action_sha256": fresh.get("rendered_action_sha256"),
        "nonstdlib_reason": nonstdlib_reason,
    })
    return 0 if passed else 5


if __name__ == "__main__":
    raise SystemExit(main())
