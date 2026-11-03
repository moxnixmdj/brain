#!/usr/bin/env python3
"""A write's success bit is not the file's postcondition.

The check executes separately from the adapter, reopens the stated destination,
compares the claimed digest to disk, and applies the source and archive rules
specified in the registry. These are code-independent checks, not independent
personnel verification. Mutants must fail through every expectation entry point.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import io
import pathlib
import sys
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import astra_runtime as kernel  # noqa: E402
from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import capability_execution_trace_capsule_v1 as capsule  # noqa: E402
from canonical.runtime import file_artifact_expectation_v1 as checker  # noqa: E402
from canonical.runtime import grounded_action_v1 as ground  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as front  # noqa: E402

WORLD = ROOT / "canonical/astra_runtime/tmp"
SOURCE = b"alpha\nbeta\n"
CIDS = ("file.copy.v1", "file.rename.v1", "file.backup.v1", "file.uppercased.v1",
        "file.line.appended.v1", "file.compressed.gzip.v1", "file.archive.tar_gz.v1")


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _execute(base: pathlib.Path, cid: str):
    source = base / "source.txt"
    source.write_bytes(SOURCE)
    dest = base / ("out.tar.gz" if cid == "file.archive.tar_gz.v1" else "out.txt")
    path, out = _rel(source), _rel(dest)
    if cid == "file.copy.v1":
        args = {"command": "copy", "path": path, "output_path": out, "goal": "Copy %s to %s" % (path, out)}
    elif cid == "file.rename.v1":
        args = {"command": "rename", "path": path, "output_path": out, "goal": "Rename %s to %s" % (path, out)}
    elif cid == "file.backup.v1":
        args = {"command": "backup", "path": path, "goal": "Make a backup of " + path}
        dest = source.with_name(source.name + ".bak")
    elif cid == "file.uppercased.v1":
        args = {"command": "uppercase", "path": path, "goal": "Uppercase " + path}
        dest = source
    elif cid == "file.line.appended.v1":
        args = {"command": "append_line", "path": path, "goal": "Append 'gamma' to " + path}
        dest = source
    elif cid == "file.compressed.gzip.v1":
        args = {"command": "compress", "path": path, "goal": "Compress " + path}
        dest = source.with_name(source.name + ".gz")
    else:
        args = {"command": "compress", "path": path, "output_path": out,
                "goal": "Compress %s into %s" % (path, out)}
    entry = dict(graph.load_registry()[cid])
    entry["capability_id"] = cid
    expect = entry["action_template"]["expect"]
    result = front.run_adapter_locally(entry, {"args": args, "expect": expect})
    return source, dest, args, expect, result


def _all_verdicts(expect, result, args):
    action = {"args": args, "expect": expect}
    independent = checker.verify(expect, result, args, ROOT)[0]
    try:
        front._check_expectation(expect, result, args)
    except front.LocalExecutionFailure:
        live = False
    else:
        live = True
    try:
        kernel._verify_action_expectation(action, result)
    except kernel.Blocker:
        astra = False
    else:
        astra = True
    grounded = ground._check_expect(expect, result, args, ROOT)[0]
    cap = capsule._expectation_passes(action, result)
    return independent, live, astra, grounded, cap


def test_all_seven_real_writes_are_rechecked_and_mutated_outputs_refuse() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for cid in CIDS:
        with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
            source, destination, args, expect, result = _execute(pathlib.Path(tmp), cid)
            assert _all_verdicts(expect, result, args) == (True,) * 5, cid
            destination.write_bytes(b"tampered after the adapter returned")
            assert _all_verdicts(expect, result, args) == (False,) * 5, cid


def test_a_false_success_flag_missing_hash_or_changed_destination_refuses() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
        _source, destination, args, expect, result = _execute(pathlib.Path(tmp), "file.copy.v1")
        mutant = copy.deepcopy(result)
        mutant["output_verified"] = False
        assert _all_verdicts(expect, mutant, args) == (False,) * 5
        mutant = copy.deepcopy(result)
        mutant.pop(expect["field"])
        assert _all_verdicts(expect, mutant, args) == (False,) * 5
        other = destination.with_name("other.txt")
        other.write_bytes(destination.read_bytes())
        mutant = copy.deepcopy(result)
        mutant[expect["path_field"]] = _rel(other)
        assert _all_verdicts(expect, mutant, args) == (False,) * 5
        mutant[expect["path_field"]] = "/etc/passwd"
        assert _all_verdicts(expect, mutant, args) == (False,) * 5


def test_retained_source_modification_and_removed_source_reappearance_refuse() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for cid in ("file.copy.v1", "file.backup.v1", "file.archive.tar_gz.v1",
                "file.rename.v1", "file.compressed.gzip.v1"):
        with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
            source, _destination, args, expect, result = _execute(pathlib.Path(tmp), cid)
            source.write_bytes(b"changed or unexpectedly recreated")
            assert _all_verdicts(expect, result, args) == (False,) * 5, cid


def test_wrong_archive_content_is_refused_even_if_its_new_digest_is_claimed() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for cid in ("file.compressed.gzip.v1", "file.archive.tar_gz.v1"):
        with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
            source, destination, args, expect, result = _execute(pathlib.Path(tmp), cid)
            bad = b"different content"
            if cid == "file.compressed.gzip.v1":
                destination.write_bytes(gzip.compress(bad))
            else:
                with tarfile.open(destination, "w:gz") as archive:
                    info = tarfile.TarInfo(source.name)
                    info.size = len(bad)
                    archive.addfile(info, io.BytesIO(bad))
            mutant = copy.deepcopy(result)
            mutant[expect["field"]] = hashlib.sha256(destination.read_bytes()).hexdigest()
            assert _all_verdicts(expect, mutant, args) == (False,) * 5, cid


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("%d/%d passed" % (len(tests) - failures, len(tests)))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
