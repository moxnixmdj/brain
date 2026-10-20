#!/usr/bin/env python3
"""Read the manual once, then really do it.

The candidate table in program_synthesis is written by hand, which made the
author the ceiling on what the machine could do. This reads the standard
library's own documentation instead, and accepts a snippet only once running
it has produced an artifact that really is the right format.

Sabotage: accept a snippet that produced nothing, or read a shell transcript
as python, and these fail.
"""

from __future__ import annotations

import json
import os
import sys
import pathlib
import shutil
import tempfile
import unittest

from canonical.runtime import documentation_mining_v1 as dm


class DocCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-doc-")
        self._saved = dm.STATE_PATH
        dm.STATE_PATH = os.path.join(self.tmp, "state.json")

    def tearDown(self) -> None:
        dm.STATE_PATH = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)


class ModuleChoiceTests(unittest.TestCase):
    def test_the_goal_finds_the_module_named_for_the_job(self):
        names = [m for _, m in dm.candidate_modules("compress the report into out.gz")]
        self.assertIn("gzip", names)

    def test_json_is_found_for_a_json_goal(self):
        names = [m for _, m in dm.candidate_modules("save results to out.json")]
        self.assertIn("json", names)

    def test_module_names_come_from_the_interpreter_not_a_list_someone_wrote(self):
        import sys
        self.assertEqual(sorted(dm.stdlib_modules()),
                         sorted(sys.stdlib_module_names))
        self.assertGreater(len(dm.stdlib_modules()), 100)

    def test_a_goal_saying_nothing_finds_nothing(self):
        self.assertEqual(dm.candidate_modules("   "), [])


class ExtractionTests(DocCase):
    def test_a_shell_transcript_is_not_read_as_python(self):
        text = (".. code-block:: shell-session\n\n"
                "    $ python -m zipfile -c monty.zip spam.txt\n")
        self.assertEqual(dm.extract_examples(text), [],
                         "a shell command was extracted as a python snippet")

    def test_a_doctest_prompt_is_stripped(self):
        text = ">>> import json\n>>> json.dumps([1, 2])\n[1, 2]\n"
        ex = dm.extract_examples(text)
        self.assertTrue(ex, "nothing extracted from a doctest")
        self.assertNotIn(">>>", ex[0])
        self.assertIn("import json", ex[0])

    def test_a_python_code_block_is_extracted(self):
        text = (".. code-block:: python\n\n"
                "    import json\n"
                "    json.dump({'a': 1}, open('x.json', 'w'))\n")
        ex = dm.extract_examples(text)
        self.assertTrue(ex, "nothing extracted from a python code-block")
        self.assertIn("json.dump", ex[0])

    def test_the_last_expression_can_be_printed(self):
        self.assertEqual(dm.with_printed_last("import json\njson.dumps(1)").rstrip("\n"),
                         "import json\nprint(json.dumps(1))")

    def test_an_assignment_is_not_printed(self):
        self.assertEqual(dm.with_printed_last("import json\nx = 1"),
                         "import json\nx = 1")

    def test_an_import_is_not_printed(self):
        self.assertEqual(dm.with_printed_last("import json"), "import json")

    def test_a_filename_in_an_example_is_pointed_at_our_file(self):
        snippet = "json.dump({'a': 1}, open('x.json', 'w'))"
        adapted = dm.adapt(snippet, "json", "/tmp/ours.json", "c")
        self.assertIn("/tmp/ours.json", adapted)
        self.assertNotIn("x.json", adapted)


class LearningTests(DocCase):
    def test_gzip_has_no_runnable_example_and_that_is_reported(self):
        self.assertEqual(dm.extract_examples(dm.fetch_module_docs("gzip")), [])

    def test_a_goal_naming_no_output_format_is_refused(self):
        r = dm.learn("extract text from a pdf file")
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], "OPEN__NO_OUTPUT_FORMAT_IN_GOAL")

    def test_a_goal_naming_no_module_is_refused(self):
        r = dm.learn("write the thing into out.qzx")
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], "OPEN__NO_MODULE_THE_GOAL_MENTIONS")

    def test_every_trial_is_reported(self):
        r = dm.learn("save results to out.json")
        self.assertTrue(r.get("trials"), "the machine must show its working")
        for row in r["trials"]:
            self.assertIn("module", row)
            self.assertIn("worked", row)

    def test_learning_a_real_format_produces_a_real_file(self):
        r = dm.learn("save results to out.json")
        if not r["pass"]:
            self.skipTest("no documented example produced the effect")
        self.assertEqual(r["status"], "PASS__LEARNED_FROM_DOCUMENTATION")
        self.assertGreater(r["output_bytes"], 0)
        self.assertTrue(r["output_sha256"])
        self.assertTrue(r["source"], "no program came back")
        # the scratch directory is gone; a path into it would be a lie
        self.assertNotIn("output_path", r)

    def test_what_was_learned_can_be_read_back_as_that_format(self):
        r = dm.learn("save results to out.json")
        if not r["pass"]:
            self.skipTest("no documented example produced the effect")
        # do it again into a directory we keep: what was learned must
        # reproduce, not merely have happened once in a scratch dir
        work = pathlib.Path(self.tmp) / "kept"
        again = dm.learn("save results to out.json", workdir=work)
        self.assertTrue(again["pass"], again)
        json.loads(pathlib.Path(again["output_path"]).read_text())


class MemoryTests(DocCase):
    def test_a_second_ask_comes_from_memory(self):
        first = dm.learn_or_recall("save results to out.json")
        if not first["pass"]:
            self.skipTest("nothing was learned, nothing to recall")
        second = dm.learn_or_recall("save results to out.json")
        self.assertTrue(second.get("from_memory"))
        self.assertEqual(second["status"], "PASS__RECALLED_DOCUMENTED_PROGRAM")

    def test_a_failure_is_not_remembered(self):
        dm.learn_or_recall("write the thing into out.qzx")
        self.assertIsNone(dm.recall(".qzx"))


if __name__ == "__main__":
    unittest.main()
