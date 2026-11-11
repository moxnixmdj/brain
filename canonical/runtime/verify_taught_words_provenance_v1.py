#!/usr/bin/env python3
"""Check the claim behind ``file.question.taught_words.v1`` and write the receipt that pins it.

The claim, the method and its limits are in
``canonical/verification/TAUGHT_WORDS_PROVENANCE_MISSION_V1.md``.  In short: the world is built here, so
every expected answer is a literal known by construction; the row is reached through the real
dispatcher with its declared expectation, so the door's own recomputation runs on every case; where
wc and grep exist the answers are compared with theirs.

Independence is code-level only: this file, the checker and the producer were written by one agent
session.  It is NOT independent-personnel verification, and the receipt says so.

usage: verify_taught_words_provenance_v1.py --write | --check
"""
from __future__ import annotations

import hashlib
import itertools
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CID = "file.question.taught_words.v1"
MISSION_ID = "ASTRA-VERIFY-FILE-QUESTION-TAUGHT-WORDS-001"
SCHEMA = "PROJECT_BRAIN_TAUGHT_WORDS_PROVENANCE_V1"
RECEIPT = ROOT / "canonical/astra_runtime/evidence" / (MISSION_ID + "__RECEIPT.json")
MISSION = ROOT / "canonical/verification/TAUGHT_WORDS_PROVENANCE_MISSION_V1.md"
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ADAPTER = "canonical/runtime/bound_capabilities/file_question_taught_words.py"
PINNED = [ADAPTER, "canonical/runtime/taught_words_v1.py", "canonical/runtime/taught_words_check_v1.py",
          "canonical/runtime/TAUGHT_WORD_LESSONS_V1.json", "canonical/runtime/TAUGHT_WORD_LEXICON_V1.json"]

# The world.  Seven lines, the last without a newline: two blank, three with ERROR, five different.
NOTES = "ERROR disk full\nalpha beta\n\nERROR disk full\ngamma\n\nthe last ERROR line"
NUMBERS = "500\n4\n9\n9\n20\n"
NOT_TEXT = b"\xff\xfe\x00binary"

# sentence, file, the answer known by construction, and whether any lesson shows this sentence
CASES = [
    ("how many lines are in {f}", "notes.txt", 7, True),
    ("how many blank lines are in {f}", "notes.txt", 2, True),
    ("how many unique lines are in {f}", "notes.txt", 5, True),
    ("how many lines contain ERROR in {f}", "notes.txt", 3, True),
    ("how many words are in {f}", "notes.txt", 13, True),
    ("how many characters are in {f}", "notes.txt", 70, True),
    ("what is the length of the longest line in {f}", "notes.txt", 19, True),
    ("what is the sum of the numbers in {f}", "numbers.txt", 542, True),
    ("how many unique words are in {f}", "notes.txt", 9, False),
    ("how many unique lines contain ERROR in {f}", "notes.txt", 2, False),
    ("how many lines are in {f} after the first", "notes.txt", 6, False),
    ("how many words contain ERROR in {f}", "notes.txt", 3, False),
    ("how many lines mention 'disk full' in {f}", "notes.txt", 2, False),
    ("what is the length of the shortest line in {f} after the first", "notes.txt", 0, False),
    ("what is the sum of the numbers in {f} after the first", "numbers.txt", 42, True),
    ("what is the largest number in {f} after the first", "numbers.txt", 20, False),
    ("how many unique numbers are in {f}", "numbers.txt", 4, False),
    ("what is the sum of the unique numbers in {f}", "numbers.txt", 533, False),
    ("what is the smallest number in {f}", "numbers.txt", 4, True),
]
REFUSALS = [
    ("an unknown word", "how many lines are in {f} today", "notes.txt", {}),
    ("a negation", "how many lines are not blank in {f}", "notes.txt", {}),
    ("a word that needs its partner", "how lines are in {f}", "notes.txt", {}),
    ("two things to look at", "how many words are in the longest line in {f}", "notes.txt", {}),
    ("a request to change the file", "delete the blank lines in {f}", "notes.txt", {}),
    ("a file that is not text", "how many lines are in {f}", "binary.bin", {}),
    ("a directory", "how many lines are in {f}", "", {}),
    ("a report path", "how many lines are in {f}", "notes.txt", {"output_path": "report.txt"}),
]
COMMANDS = [   # sentence, real command, on notes_nl.txt (the same text with a final newline)
    ("how many lines are in {f}", ["wc", "-l"]),
    ("how many words are in {f}", ["wc", "-w"]),
    ("how many bytes are in {f}", ["wc", "-c"]),
    ("how many lines contain ERROR in {f}", ["grep", "-c", "ERROR"]),
]


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _row():
    entry = dict(json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"][CID])
    entry.setdefault("capability_id", CID)
    return entry


def _ask(sentence, rel, extra=None):
    """Through the real dispatcher, with the row's declared expectation."""
    from canonical.runtime import live_brain_route_admission_v1 as door
    entry = _row()
    args = {"goal": sentence, "path": rel}
    args.update(extra or {})
    return door.run_adapter_locally(entry, {"args": args, "expect": entry["action_template"]["expect"]})


def run_checks():
    from canonical.runtime import taught_words_check_v1 as checker
    from canonical.runtime import taught_words_v1 as taught
    checks = []

    def record(name, ok, **detail):
        checks.append({"name": name, "ok": bool(ok), **detail})

    seed_raw = taught.SEED_LESSONS.read_bytes()
    lessons = taught._parse_lessons(seed_raw, b"")
    fresh, set_aside = taught.learn(lessons)
    stored = json.loads(taught.SEED_LEXICON.read_text(encoding="utf-8"))
    record("the stored lexicon is what the lessons give", fresh == stored["lexicon"]
           and stored["lessons_sha256"] == hashlib.sha256(seed_raw + b"\0").hexdigest(),
           lessons=len(lessons), set_aside=[n["lesson"] for n in set_aside],
           words_known=len(taught._settled(fresh)))
    skipped = {n["index"] for n in set_aside}
    reproduced = sum(1 for i, (sentence, examples) in enumerate(lessons) if i not in skipped
                     and all(taught.interpret(fresh, sentence, text).get("value") == answer for text, answer in examples))
    record("every accepted lesson is reproduced on its own files", reproduced == len(lessons) - len(skipped),
           reproduced=reproduced, accepted=len(lessons) - len(skipped))

    base = ROOT / "canonical/astra_runtime/tmp"
    base.mkdir(parents=True, exist_ok=True)
    world = pathlib.Path(tempfile.mkdtemp(prefix="taught_words_provenance_", dir=base))
    try:
        (world / "notes.txt").write_text(NOTES, encoding="utf-8")
        (world / "notes_nl.txt").write_text(NOTES + "\n", encoding="utf-8")
        (world / "numbers.txt").write_text(NUMBERS, encoding="utf-8")
        (world / "binary.bin").write_bytes(NOT_TEXT)
        rel = lambda name: (world / name).relative_to(ROOT).as_posix() if name else world.relative_to(ROOT).as_posix()
        before = {p.name: _sha(p) for p in sorted(world.iterdir())}

        for sentence, name, expected, shown in CASES:
            try:
                result = _ask(sentence.format(f=rel(name)), rel(name))
                got, program = result.get("answer"), result.get("program")
                recomputed = checker.recompute(program, result.get("data"), (world / name).read_bytes())
            except Exception as exc:  # noqa: BLE001 - a refusal here is a failed check
                got, program, recomputed = "REFUSED:" + str(exc)[:120], None, None
            record("answers: " + sentence.format(f=name), got == expected and recomputed == expected,
                   adapter_returned=got, expected_by_construction=expected, recomputed_by_the_checker=recomputed,
                   operation=program, shown_in_a_lesson=shown)

        for label, sentence, name, extra in REFUSALS:
            try:
                result = _ask(sentence.format(f=rel(name)), rel(name), extra)
                refused, why = False, "ANSWERED:" + str(result.get("answer"))
            except Exception as exc:  # noqa: BLE001
                refused, why = True, str(exc)[:160].replace(str(ROOT), "<root>").replace(world.name, "<world>")
            record("refuses " + label, refused, sentence=sentence.format(f=name or "<directory>"), refusal=why)
        try:
            _ask("how many lines are in " + rel("notes.txt"), "../outside.txt")
            record("refuses a path outside the repository", False)
        except Exception as exc:  # noqa: BLE001
            record("refuses a path outside the repository", True, refusal=str(exc)[:100])
        try:
            _ask("how many lines are in " + rel("notes.txt"), rel("numbers.txt"))
            record("refuses a sentence that names another file", False)
        except Exception as exc:  # noqa: BLE001
            record("refuses a sentence that names another file", True, refusal=str(exc)[:100])

        honest = _ask("how many unique lines are in " + rel("notes.txt"), rel("notes.txt"))
        expect = _row()["action_template"]["expect"]
        ok_true, _ = checker.verify(expect, honest, {"path": rel("notes.txt")}, ROOT)
        ok_false, detail = checker.verify(expect, dict(honest, answer=honest["answer"] + 1), {"path": rel("notes.txt")}, ROOT)
        record("the checker confirms a right answer and catches one that is off by one", ok_true and not ok_false,
               caught_as=detail)

        for sentence, command in COMMANDS:
            target = world / "notes_nl.txt"
            if shutil.which(command[0]) is None:
                record("agrees with " + " ".join(command), True, skipped="PROGRAM_NOT_INSTALLED")
                continue
            real = subprocess.run(command + [str(target)], capture_output=True, text=True, timeout=20).stdout.split()
            got = _ask(sentence.format(f=rel("notes_nl.txt")), rel("notes_nl.txt")).get("answer")
            record("agrees with " + " ".join(command), bool(real) and str(got) == real[0], adapter_returned=got,
                   program_printed=real[0] if real else None)

        compared = disagreements = 0
        texts = [NOTES, NOTES + "\n", NUMBERS, "", "\n\n", "a", "caf\u00e9 \u00a0 b\x1cc\n\u0663 5\n"]
        for unit in taught.UNITS:
            for k in range(len(taught.FILTERS) + 1):
                for filters in itertools.combinations(taught.FILTERS, k):
                    for measure in ((), taught.MEASURES):
                        for reducer in taught.REDUCERS:
                            parts = frozenset((unit,) + filters + measure + (reducer,))
                            for text in texts:
                                data = "ERROR" if "containing" in parts else None
                                try:
                                    produced = taught.run(parts, text, data)
                                except taught.Refuse:
                                    produced = None
                                compared += 1
                                if produced != checker.recompute(sorted(parts), data, text.encode("utf-8")):
                                    disagreements += 1
        record("the producer and the checker agree on every operation", disagreements == 0,
               compared=compared, disagreements=disagreements)

        after = {p.name: _sha(p) for p in sorted(world.iterdir())}
        record("nothing in the world was written", before == after, files=len(after))

        with tempfile.TemporaryDirectory() as live:
            one = taught.teach("what is the size of t.txt", [(NOTES, 70)], live_dir=live)
            wrong = taught.teach("how many lines are in t.txt", [(NOTES, 8), (NUMBERS, 6)], live_dir=live)
            good = taught.teach("what is the size of t.txt", [(NOTES, 70), ("caf\u00e9\n", 6)], live_dir=live)
            taught._CACHE.clear()
            kept = taught.interpret(taught.load_lexicon(live_dir=live)[0], "what is the size of x.txt", "ab\n")
            taught._CACHE.clear()
            record("the teacher entry refuses one example file and a wrong answer, and keeps a good lesson",
                   one["taught"] is False and wrong["taught"] is False and good["taught"] is True
                   and kept.get("value") == 3, one_file=one.get("reason"), wrong_answer=wrong.get("reason"),
                   taught=good.get("words_now_known"))
    finally:
        shutil.rmtree(world, ignore_errors=True)
    return checks


def receipt(checks):
    return {
        "schema": SCHEMA, "mission_id": MISSION_ID, "capability_id": CID,
        "claim": "answers a file question only when taught words account for every word of the sentence, "
                 "with the value of the operation those words make, and refuses anything else by name",
        "adapter_path": ADAPTER, "adapter_sha256": _sha(ROOT / ADAPTER),
        "pinned_sha256": {path: _sha(ROOT / path) for path in PINNED},
        "mission_path": MISSION.relative_to(ROOT).as_posix(), "mission_sha256": _sha(MISSION),
        "checks": checks, "check_count": len(checks), "checks_ok": sum(c["ok"] for c in checks),
        "independence": "code-level only: expected answers are literals fixed by construction of a world this "
                        "file builds; the row is reached through the real dispatcher with its declared "
                        "expectation; the checker shares no code with the producer; wc and grep are compared "
                        "where they exist. Producer, checker and verifier come from one agent session.",
        "independent_personnel_verification": False, "model_dependency_count": 0, "incremental_spend_usd": 0,
        "producer": "arena agent session, 2026-11-11",
        "replay": "python3 canonical/runtime/verify_taught_words_provenance_v1.py --check",
        "status": "COMPLETE" if all(c["ok"] for c in checks) else "FAILED",
    }


def main(argv):
    mode = argv[1] if len(argv) > 1 else "--check"
    checks = run_checks()
    document = receipt(checks)
    failed = [c for c in checks if not c["ok"]]
    for c in failed:
        print("FAILED:", json.dumps(c, ensure_ascii=True)[:400])
    if mode == "--write":
        if failed:
            print("%d/%d checks passed; receipt NOT written" % (len(checks) - len(failed), len(checks)))
            return 1
        RECEIPT.write_text(json.dumps(document, indent=1, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
        print("%d/%d checks passed; receipt written" % (len(checks), len(checks)))
        return 0
    try:
        stored = json.loads(RECEIPT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("receipt missing or unreadable")
        return 1
    drift = sorted(p for p, digest in document["pinned_sha256"].items() if stored.get("pinned_sha256", {}).get(p) != digest)
    if stored.get("mission_sha256") != document["mission_sha256"]:
        drift.append(document["mission_path"])
    print("%d/%d checks passed; pinned files that differ from the receipt: %s" % (len(checks) - len(failed), len(checks), drift or "none"))
    return 0 if not failed and not drift and stored.get("status") == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
