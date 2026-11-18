"""Round 19: the seeds were the wall. Same engines, same parts, only the seed supply changes.

The fire proof is built so that only the SEED can explain the difference. The changed guard sits in `parse`, and
to reach it the call must pass `_check`, which demands a token that is (a) absent from the test, (b) absent from the
enclosing scope the operand channel instruments, and (c) present verbatim in the repository's own data file. Neither
mutation from the test's literal nor the operand channel can produce it; the artifact's own document can.

The honesty proof is the mirror: a token that appears nowhere in the repository either. The corpus must be
reported as having entered the file and still not reached the part -- seed supply, not seed presence, is the claim.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import the_repository_is_the_seed_corpus_v1 as S  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

_CHECK = '''def _check(text):
    if "%s" not in text:
        raise ValueError("bad document")


def parse(text):
    _check(text)
%s    return len(text)
'''

# Exactly ONE behavioural part differs between DEFECTIVE and FIXED: the guard added inside `parse`. `_check` is
# byte-identical on both sides, so the only thing under test is whether the call can get past it at all.
DEFECTIVE = _CHECK % ("zeta-omega", "")
FIXED = _CHECK % ("zeta-omega", '    if text.endswith("!"):\n        raise ValueError("reserved ending")\n')

# The same shape with a token that appears NOWHERE in the repository -- not in the module, not in the data file.
DEFECTIVE_UNPRESENT = _CHECK % ("quux-never-written", "")
FIXED_UNPRESENT = _CHECK % ("quux-never-written", '    if text.endswith("!"):\n        raise ValueError("reserved ending")\n')

TEST = '''from mod import parse


def test_one():
    assert parse("a") == 1
'''

DATA = "alpha\nzeta-omega\nbeta!"


def _tree(tmp_path: pathlib.Path, fixed: str) -> pathlib.Path:
    (tmp_path / "mod.py").write_text(DEFECTIVE_UNPRESENT if "quux" in fixed else DEFECTIVE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    (tmp_path / "tests" / "data").mkdir(parents=True)
    (tmp_path / "tests" / "data" / "sample.txt").write_text(DATA, encoding="utf-8")
    return tmp_path


def _part(fixed: str):
    defective = DEFECTIVE_UNPRESENT if "quux" in fixed else DEFECTIVE
    return next(part for part in PINS.hunks(defective, fixed)
                if PINS.is_behavioural(fixed, part) and not PINS.typing_only(fixed, part))


def test_a_document_the_repository_already_owns_pins_a_part_the_literal_seed_cannot(tmp_path):
    tree = _tree(tmp_path, FIXED)
    part = _part(FIXED)
    mutant = PINS.revert(FIXED, DEFECTIVE, part)
    tiny = S.SYN.calls_from_the_test(TEST)
    documents = S.harvest_documents(tree)
    assert any("zeta-omega" in document["text"] for document in documents)
    kept, stats = S.distil(tree, "mod.py", tiny[0], documents)
    assert "zeta-omega" in "".join(kept) and stats["kept"] >= 1
    enriched = S.calls_from(kept, tiny[0])
    baseline = S.judge(tree, "mod.py", "test_mod.py", FIXED, mutant, part, tiny)
    seeded = S.judge(tree, "mod.py", "test_mod.py", FIXED, mutant, part, enriched)
    assert baseline["state"] != S.R.PINNED          # the test's own literal cannot spell the token
    assert seeded["state"] == S.R.PINNED, seeded     # the repository's own document can
    assert "pytest.raises" in seeded["assertion"]


def test_a_token_absent_from_the_repository_is_not_invented_by_seeding(tmp_path):
    tree = _tree(tmp_path, FIXED_UNPRESENT)
    part = _part(FIXED_UNPRESENT)
    mutant = PINS.revert(FIXED_UNPRESENT, DEFECTIVE_UNPRESENT, part)
    tiny = S.SYN.calls_from_the_test(TEST)
    kept, stats = S.distil(tree, "mod.py", tiny[0], S.harvest_documents(tree))
    assert stats["lines_covered"] > 0               # the corpus did enter the file
    seeded = S.judge(tree, "mod.py", "test_mod.py", FIXED_UNPRESENT, mutant, part, S.calls_from(kept, tiny[0]))
    assert seeded["state"] != S.R.PINNED            # and still could not reach the part


def test_distillation_keeps_only_documents_that_execute_a_new_line(tmp_path):
    (tmp_path / "mod.py").write_text("def parse(text):\n    if text:\n        return 1\n    return 0\n")
    call = {"module": "mod", "function": "parse", "args": ["x"]}
    documents = [{"text": "a"}, {"text": ""}, {"text": "a"}, {"text": "b"}]
    kept, stats = S.distil(tmp_path, "mod.py", call, documents)
    assert 1 <= len(kept) <= 3 and stats["kept"] == len(kept)
    assert stats["candidates"] == 4


def test_harvesting_skips_what_cannot_be_an_input(tmp_path):
    (tmp_path / "mod.py").write_text(DEFECTIVE)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "huge.txt").write_text("x" * (S.MAX_FILE_BYTES + 1))
    (tmp_path / "tests" / "binary.txt").write_bytes(b"\x00\x01\x02")
    documents = S.harvest_documents(tmp_path)
    texts = [document["text"] for document in documents]
    assert not any(len(text) > S.MAX_FILE_BYTES for text in texts)
    assert not any("\x00" in text for text in texts)


def test_calls_are_built_in_the_shape_both_engines_take():
    call = {"module": "mod", "function": "parse", "args": ["x", 3]}
    built = S.calls_from(["alpha"], call)
    assert built == [{"module": "mod", "function": "parse", "args": ["alpha", 3]}]
