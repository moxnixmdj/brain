#!/usr/bin/env python3
"""A negated or conditional request must not authorize overwriting a file.

At bcfb98af, both copy and rename destroyed an existing destination for each
of "do not overwrite", "without overwrite", and "never replace". The tests use
real temporary files and assert both the refusal and unchanged bytes.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import file_ops  # noqa: E402

WORLD = ROOT / "canonical/astra_runtime/tmp"
SOURCE = b"NEW SOURCE BYTES\n"
PRECIOUS = b"PRECIOUS DESTINATION BYTES\n"


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _call(command: str, source: pathlib.Path, destination: pathlib.Path, suffix: str):
    goal = "%s %s to %s %s" % (command, _rel(source), _rel(destination), suffix)
    return file_ops.run({"command": command, "path": _rel(source),
                         "output_path": _rel(destination), "goal": goal}, ROOT)


def test_negated_conditional_or_ambiguous_consent_preserves_existing_files() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    phrases = ("and do not overwrite it", "without overwrite", "and never replace it",
               "but don't overwrite it", "and overwrite it only if I confirm",
               "and overwrite it if permitted", "and overwrite the source",
               "do not overwrite it and overwrite it", "and do not replace it")
    for command in ("copy", "rename"):
        for phrase in phrases:
            with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
                base = pathlib.Path(tmp)
                source, destination = base / "src.txt", base / "dst.txt"
                source.write_bytes(SOURCE)
                destination.write_bytes(PRECIOUS)
                try:
                    _call(command, source, destination, phrase)
                except RuntimeError as exc:
                    assert "DESTINATION_EXISTS_AND_THE_SENTENCE_DID_NOT_ASK_TO_OVERWRITE" in str(exc), (command, phrase, exc)
                else:
                    raise AssertionError("%s accepted %s" % (command, phrase))
                assert source.read_bytes() == SOURCE, (command, phrase)
                assert destination.read_bytes() == PRECIOUS, (command, phrase)


def test_keyword_in_a_filename_is_not_consent() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for command in ("copy", "rename"):
        for filename in ("replace.txt", "force.txt", "overwrite.txt"):
            with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
                base = pathlib.Path(tmp)
                source, destination = base / "src.txt", base / filename
                source.write_bytes(SOURCE)
                destination.write_bytes(PRECIOUS)
                try:
                    _call(command, source, destination, "")
                except RuntimeError as exc:
                    assert "DESTINATION_EXISTS_AND_THE_SENTENCE_DID_NOT_ASK_TO_OVERWRITE" in str(exc), (command, filename, exc)
                else:
                    raise AssertionError("%s accepted filename as permission" % command)
                assert source.read_bytes() == SOURCE and destination.read_bytes() == PRECIOUS


def test_unambiguous_explicit_consent_remains_possible() -> None:
    WORLD.mkdir(parents=True, exist_ok=True)
    for command in ("copy", "rename"):
        for phrase in ("and overwrite it", "and replace it."):
            with tempfile.TemporaryDirectory(dir=WORLD) as tmp:
                base = pathlib.Path(tmp)
                source, destination = base / "src.txt", base / "dst.txt"
                source.write_bytes(SOURCE)
                destination.write_bytes(PRECIOUS)
                result = _call(command, source, destination, phrase)
                assert result.get("output_verified") is True, (command, phrase)
                assert destination.read_bytes() == SOURCE, (command, phrase)
                if command == "copy":
                    assert source.read_bytes() == SOURCE
                else:
                    assert not source.exists()


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
