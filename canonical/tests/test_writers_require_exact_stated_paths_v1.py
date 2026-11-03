#!/usr/bin/env python3
"""The filename in a write request must not merely contain the bound filename.

Before this test all seven writers accepted a different stated filename that
contained the actual source name. Rename and gzip even removed the actual source.
The test builds disposable files, requires a specific refusal, and checks bytes.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import (  # noqa: E402
    file_archive_tar, file_compress, file_edit, file_ops, stated_file_path,
)

WORLD = ROOT / "canonical/astra_runtime/tmp"


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def snapshot(path: pathlib.Path) -> dict[str, bytes | None]:
    return {p.relative_to(path).as_posix(): None if p.is_dir() else p.read_bytes()
            for p in sorted(path.rglob("*"))}


def scenario(kind: str, source: pathlib.Path, destination: pathlib.Path, stated_source: str):
    src, dst = rel(source), rel(destination)
    if kind in ("copy", "rename"):
        return file_ops, {"command": kind, "path": src, "output_path": dst,
                          "goal": "%s %s to %s" % (kind, stated_source, dst)}
    if kind == "backup":
        return file_ops, {"command": kind, "path": src, "goal": "Backup " + stated_source}
    if kind in ("uppercase", "append_line"):
        goal = ("Uppercase " + stated_source if kind == "uppercase" else
                "Append 'gamma' to " + stated_source)
        return file_edit, {"command": kind, "path": src, "goal": goal}
    if kind == "compress":
        return file_compress, {"command": kind, "path": src, "goal": "Compress " + stated_source}
    assert kind == "tar"
    return file_archive_tar, {"command": "compress", "path": src, "output_path": dst,
                              "goal": "Compress %s into %s" % (stated_source, dst)}


def must_refuse(module, args, reason):
    try:
        module.run(args, ROOT)
    except RuntimeError as exc:
        assert reason in str(exc), (args, exc)
    else:
        raise AssertionError("writer accepted an unstated path: %r" % args)


def test_substring_source_names_are_refused_by_all_seven_writers() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for kind in ("copy", "rename", "backup", "uppercase", "append_line", "compress", "tar"):
        with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
            base = pathlib.Path(tmp)
            source = base / "a.txt"
            source.write_bytes(b"alpha\nbeta\n")
            destination = base / ("out.tar.gz" if kind == "tar" else "out.txt")
            before = snapshot(base)
            module, args = scenario(kind, source, destination, "not-a.txt")
            must_refuse(module, args, "PATH_NOT_STATED_IN_THE_SENTENCE")
            assert snapshot(base) == before, kind


def test_a_path_in_a_different_directory_is_not_the_source() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for kind in ("copy", "rename", "backup", "uppercase", "append_line", "compress", "tar"):
        with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
            base = pathlib.Path(tmp)
            actual, stated = base / "actual", base / "stated"
            actual.mkdir()
            stated.mkdir()
            source = actual / "same.txt"
            source.write_bytes(b"actual\n")
            (stated / "same.txt").write_bytes(b"stated\n")
            destination = actual / ("out.tar.gz" if kind == "tar" else "out.txt")
            before = snapshot(base)
            module, args = scenario(kind, source, destination, rel(stated / "same.txt"))
            must_refuse(module, args, "PATH_NOT_STATED_IN_THE_SENTENCE")
            assert snapshot(base) == before, kind


def test_a_different_directory_or_substring_is_not_the_destination() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for kind in ("copy", "rename", "tar"):
        for style in ("directory", "substring"):
            with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
                base = pathlib.Path(tmp)
                actual, stated = base / "actual", base / "stated"
                actual.mkdir()
                stated.mkdir()
                source = actual / "source.txt"
                source.write_bytes(b"source bytes\n")
                name = "out.tar.gz" if kind == "tar" else "out.txt"
                dest = actual / name
                named = rel(stated / name) if style == "directory" else "not-" + name
                module, args = scenario(kind, source, dest, rel(source))
                args["goal"] = "%s %s to %s" % ("Compress" if kind == "tar" else kind, rel(source), named)
                before = snapshot(base)
                reason = "DESTINATION_NOT_STATED_IN_THE_SENTENCE" if kind == "tar" else "PATH_NOT_STATED_IN_THE_SENTENCE"
                must_refuse(module, args, reason)
                assert snapshot(base) == before, (kind, style)


def test_swapped_source_and_destination_roles_are_refused() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for kind in ("copy", "rename", "tar"):
        with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
            base = pathlib.Path(tmp)
            source = base / ("a.tar.gz" if kind == "tar" else "a.txt")
            dest = base / ("b.tar.gz" if kind == "tar" else "b.txt")
            source.write_bytes(b"original source\n")
            dest.write_bytes(b"original destination\n")
            module, args = scenario(kind, dest, source, rel(source))
            args["goal"] = "%s %s to %s and overwrite" % (kind, rel(source), rel(dest))
            before = snapshot(base)
            must_refuse(module, args, "STATED_PATH_ROLES_MISMATCH")
            assert snapshot(base) == before, kind


def test_append_line_content_is_not_an_authorised_path() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
        base = pathlib.Path(tmp)
        actual, named = base / "a.txt", base / "b.txt"
        actual.write_bytes(b"unchanged a\n")
        named.write_bytes(b"unchanged b\n")
        before = snapshot(base)
        args = {"command": "append_line", "path": rel(actual),
                "goal": "Append '%s' to %s" % (rel(actual), rel(named))}
        must_refuse(file_edit, args, "PATH_NOT_STATED_IN_THE_SENTENCE")
        assert snapshot(base) == before


def test_exact_paths_and_stated_sibling_names_are_recognised() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
        base = pathlib.Path(tmp)
        source, dest = base / "a.txt", base / "copy.txt"
        source.write_bytes(b"alpha\n")
        assert stated_file_path.names_path("Copy %s to copy.txt." % rel(source), source, ROOT)
        assert stated_file_path.names_path("Copy %s to copy.txt." % rel(source), dest, ROOT,
                                           sibling_of=source)
        assert not stated_file_path.names_path("Copy %s to copy.txt." % rel(source), dest, ROOT)
        assert stated_file_path.names_path("Copy `%s`" % source, source, ROOT)
        assert not stated_file_path.names_path("Copy not-a.txt", source, ROOT)
        assert not stated_file_path.names_path("Copy other/a.txt", source, ROOT)
        result = file_ops.run({"command": "copy", "path": rel(source), "output_path": rel(dest),
                               "goal": "Copy %s to copy.txt." % rel(source)}, ROOT)
        assert result["output_verified"] is True
        assert dest.read_bytes() == source.read_bytes()


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
