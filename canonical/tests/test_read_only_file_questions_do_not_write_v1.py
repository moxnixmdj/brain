#!/usr/bin/env python3
"""File-fact rows declared read-only must not write a report.

Before this test, a plain line-count request bound a synthesized output path and
wrote a report the caller never named. Supplying an existing output path directly
to the local dispatcher also overwrote that file. Both are forbidden here.
"""
from __future__ import annotations

import copy
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import astra_runtime as kernel  # noqa: E402
from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import capability_execution_trace_capsule_v1 as capsule  # noqa: E402
from canonical.runtime import file_observation_expectation_v1 as observation  # noqa: E402
from canonical.runtime import grounded_action_v1 as ground  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime.bound_capabilities import (  # noqa: E402
    file_command_view, file_line_count, file_stat, file_survey,
)

WORLD = ROOT / "canonical/astra_runtime/tmp"
PRECIOUS = b"PRECIOUS EXISTING BYTES\n"


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _world(base: pathlib.Path):
    source = base / "source.txt"
    other = base / "other.txt"
    source.write_bytes(b"alpha beta alpha\ngamma\n")
    other.write_bytes(b"different\n")
    data = base / "directory"
    data.mkdir()
    (data / "one.txt").write_bytes(b"alpha\n")
    return source, other, data


def _cases(source, other, directory):
    file_path, other_path, dir_path = map(_rel, (source, other, directory))
    return (
        ("file.line_count.v1", file_line_count, {"path": file_path}),
        ("file.stat.v1", file_stat, {"path": file_path}),
        ("file.contents.v1", file_command_view, {"command": "cat", "path": file_path}),
        ("file.sorted.v1", file_command_view, {"command": "sort", "path": file_path}),
        ("file.reversed.v1", file_command_view, {"command": "tac", "path": file_path}),
        ("file.diff.v1", file_command_view, {"command": "diff", "path": file_path, "other_path": other_path}),
        ("file.word_frequency.v1", file_survey, {"command": "word_frequency", "path": file_path}),
        ("file.directory_listing.v1", file_survey, {"command": "directory_list", "path": dir_path}),
        ("file.directory_search.v1", file_survey, {"command": "directory_search", "path": dir_path,
                                                   "goal": "Which files in %s contain alpha?" % dir_path}),
    )


def _snapshot(base: pathlib.Path):
    return {p.relative_to(base).as_posix(): (None if p.is_dir() else p.read_bytes())
            for p in sorted(base.rglob("*"))}


def test_nine_registered_readers_answer_without_a_file_write() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
        base = pathlib.Path(tmp)
        source, other, directory = _world(base)
        before = _snapshot(base)
        registry = graph.load_registry()
        for cid, _module, args in _cases(source, other, directory):
            entry = dict(registry[cid], capability_id=cid)
            assert entry.get("read_only") is True, cid
            assert "output_path" not in entry["action_template"]["args"], cid
            result = door.run_adapter_locally(entry, {"args": args, "expect": entry["action_template"]["expect"]})
            assert result.get("output_verified") is True, cid
            assert result.get("output_path") is None, (cid, result)
            assert _snapshot(base) == before, cid
            for empty in (None, ""):
                direct = _module.run(dict(args, output_path=empty), ROOT)
                assert direct.get("output_verified") is True, (cid, empty)
                assert direct.get("output_path") is None, (cid, empty)
                assert _snapshot(base) == before, (cid, empty)
            try:
                _module.run(dict(args, output_path="${input.output_path}"), ROOT)
            except RuntimeError as exc:
                assert "READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH" in str(exc), (cid, exc)
            else:
                raise AssertionError("%s accepted unresolved output path" % cid)


def test_all_nine_readers_refuse_even_a_stated_report_path() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
        base = pathlib.Path(tmp)
        source, other, directory = _world(base)
        existing = base / "precious.json"
        existing.write_bytes(PRECIOUS)
        absent = base / "absent.json"
        symlink = base / "report-link.json"
        symlink.symlink_to(existing)
        registry = graph.load_registry()
        before = _snapshot(base)
        for cid, module, args in _cases(source, other, directory):
            for target in (existing, absent, source, symlink):
                call = dict(args, output_path=_rel(target), goal="Save result to " + _rel(target))
                try:
                    module.run(call, ROOT)
                except RuntimeError as exc:
                    assert "READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH" in str(exc), (cid, exc)
                else:
                    raise AssertionError("%s accepted output_path" % cid)
                entry = dict(registry[cid], capability_id=cid)
                try:
                    door.run_adapter_locally(entry, {"args": call})
                except RuntimeError as exc:
                    assert "READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH" in str(exc), (cid, exc)
                else:
                    raise AssertionError("%s dispatcher accepted output_path" % cid)
                assert _snapshot(base) == before, (cid, target)
                assert existing.read_bytes() == PRECIOUS, cid
                assert not absent.exists(), cid


def test_a_plain_line_count_does_not_synthesize_a_report() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
        base = pathlib.Path(tmp)
        source, _other, _directory = _world(base)
        before = _snapshot(base)
        prior_reports = set(WORLD.glob("brain_out__file_line_count_v1__*"))
        result = door.solve({"task_id": "read_only_no_report", "goal": "Count the lines in " + _rel(source)})
        assert result.get("pass") is True, result.get("status")
        assert result.get("compiled_capability_id") == "file.line_count.v1", result.get("compiled_capability_id")
        execution = (result.get("execution") or [])[0]
        assert (execution.get("result") or {}).get("output_path") is None, execution
        action = (execution.get("controller_trace") or [])[0].get("action") or {}
        assert "output_path" not in (action.get("args") or {}), action
        assert _snapshot(base) == before
        assert set(WORLD.glob("brain_out__file_line_count_v1__*")) == prior_reports


def test_a_request_to_save_a_line_count_does_not_overwrite() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
        base = pathlib.Path(tmp)
        source, _other, _directory = _world(base)
        target = base / "precious.json"
        target.write_bytes(PRECIOUS)
        before = _snapshot(base)
        goal = "Count the lines in %s and save the result to %s" % (_rel(source), _rel(target))
        result = door.solve({"task_id": "read_only_explicit_report", "goal": goal})
        assert result.get("pass") is False, result
        assert target.read_bytes() == PRECIOUS
        assert _snapshot(base) == before


def _verdicts(expect, result, args):
    action = {"expect": expect, "args": args}
    independent = observation.verify(expect, result, args, ROOT)[0]
    try:
        door._check_expectation(expect, result, args)
    except door.LocalExecutionFailure:
        live = False
    else:
        live = True
    try:
        kernel._verify_action_expectation(action, result)
    except kernel.Blocker:
        astra = False
    else:
        astra = True
    return independent, live, astra, ground._check_expect(expect, result, args, ROOT)[0], capsule._expectation_passes(action, result)


def test_line_count_and_metadata_are_reobserved_and_mutations_refuse() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for cid in ("file.line_count.v1", "file.stat.v1"):
        with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
            base = pathlib.Path(tmp)
            source, other, _directory = _world(base)
            entry = dict(graph.load_registry()[cid], capability_id=cid)
            expect = entry["action_template"]["expect"]
            args = {"path": _rel(source)}
            result = door.run_adapter_locally(entry, {"args": args, "expect": expect})
            assert _verdicts(expect, result, args) == (True,) * 5, cid
            mutated = copy.deepcopy(result)
            mutated[expect["field"]] += 1
            assert _verdicts(expect, mutated, args) == (False,) * 5, cid
            mutated = copy.deepcopy(result)
            mutated["path"] = _rel(other)
            assert _verdicts(expect, mutated, args) == (False,) * 5, cid
            mutated = copy.deepcopy(result)
            mutated["output_verified"] = False
            assert _verdicts(expect, mutated, args) == (False,) * 5, cid
            assert _verdicts(expect, result, dict(args, output_path=_rel(other))) == (False,) * 5, cid
            assert _verdicts(expect, result, dict(args, path=_rel(other))) == (False,) * 5, cid
            mutated = copy.deepcopy(result)
            mutated["answer" if cid == "file.line_count.v1" else "permissions_octal"] = "wrong"
            assert _verdicts(expect, mutated, args) == (False,) * 5, cid
            source.write_bytes(b"changed source and length\n")
            assert _verdicts(expect, result, args) == (False,) * 5, cid


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
