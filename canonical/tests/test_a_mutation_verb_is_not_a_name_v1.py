"""A mutation sentence must not be answered by a capability that only reads.

Independent oracle: the filesystem.  Two false PASSes were measured on 0dccc6c --
"Inline the function line_total into its caller" and "Add a parameter qty ...
and update every caller" -- each returning ``pass: True`` with the file the
sentence named byte-identical, because the promise gate that takes a source
digest before a run only recognised four repair verbs.  This pins the two laws
that closed them:

  1. a verb promises different bytes only when it cannot be discharged any other
     way, and it must be used AS a verb -- `add` in "the function add" is a name;
  2. if such a sentence gets a PASS anyway, the file it named must have changed.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "canonical/astra_runtime/tmp/test_mutation_verb_is_a_verb"


def _tree(tag: str) -> pathlib.Path:
    d = BASE / tag
    if d.exists():
        shutil.rmtree(d)
    (d / "app").mkdir(parents=True)
    (d / "app/__init__.py").write_text("", encoding="utf-8")
    (d / "app/models.py").write_text(
        "class Item:\n"
        "    def __init__(self, price_cents, qty=1):\n"
        "        self.price_cents = price_cents\n"
        "        self.qty = qty\n"
        "\n\n"
        "def line_total(item):\n"
        "    return item.price_cents * item.qty\n",
        encoding="utf-8")
    (d / "app/service.py").write_text(
        "from app.models import line_total\n"
        "\n\n"
        "def cart_total(items):\n"
        "    return sum(line_total(i) for i in items)\n",
        encoding="utf-8")
    return d


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


class MutationVerbIsAVerbTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(BASE, ignore_errors=True)

    def test_every_mutation_verb_takes_the_named_file_as_a_promise(self):
        base = _tree("verbs")
        models = _rel(base / "app/models.py")
        service = _rel(base / "app/service.py")
        cases = {
            "Inline the function line_total into its caller in %s." % service: service,
            "Add a parameter qty with a default to line_total in %s." % models: models,
            "Rename the parameter price_cents to cents in %s." % models: models,
            "Refactor the module %s." % models: models,
        }
        for goal, expected in cases.items():
            with self.subTest(goal=goal):
                self.assertIn(expected, door._promised_source_files(goal))

    def test_a_verb_used_as_a_name_promises_nothing_about_the_file(self):
        base = _tree("names")
        models = _rel(base / "app/models.py")
        for goal in (
            "Find every caller of the function add in %s." % models,
            "Name the function in %s whose cost is quadratic." % models,
            "Report the class move in %s." % models,
        ):
            with self.subTest(goal=goal):
                self.assertNotIn(models, door._promised_source_files(goal))

    def test_a_verb_followed_by_a_call_is_a_call(self):
        base = _tree("calls")
        models = _rel(base / "app/models.py")
        self.assertNotIn(models, door._promised_source_files(
            "Explain what add(1, 2) does in %s." % models))

    def test_an_inline_sentence_cannot_pass_with_the_file_unchanged(self):
        """The measured false PASS, end to end, judged by the bytes."""
        base = _tree("inline")
        service = _rel(base / "app/service.py")
        before = _sha(service)
        result = door.solve({
            "task_id": "MUTATION_VERB_inline",
            "goal": "Inline the function line_total into its caller in %s." % service,
        })
        unchanged = _sha(service) == before
        if result.get("pass") is True:
            self.assertFalse(unchanged,
                             "reported PASS with the named file byte-identical")
        else:
            self.assertIs(unchanged, True,
                          "refused AND changed the file: a refusal must leave the tree alone")


if __name__ == "__main__":
    unittest.main()
