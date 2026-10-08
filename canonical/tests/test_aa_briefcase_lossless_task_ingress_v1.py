import unittest

from canonical.runtime.aa_briefcase_lossless_task_ingress_v1 import (
    IngressError,
    compile_ingress,
)


def bundle():
    return {
        "task_id": "w1_t2",
        "task_text": (
            "# Task\n"
            "Create market_model.xlsx as a multi-tab workbook.\n"
            "\n"
            "- Include historical, forecast, scenarios, and assumptions.\n"
            "- Keep assumptions traceable to sources.\n"
        ),
        "deliverables": ["market_model.xlsx"],
        "source_files": [
            {"path": "shared/standards.docx", "sha256": "a" * 64, "size_bytes": 123},
            {"path": "week/input.xlsx", "sha256": "b" * 64, "size_bytes": 456},
        ],
    }


class T(unittest.TestCase):
    def test_preserves_task_deliverables_and_sources(self):
        out = compile_ingress(bundle())
        self.assertEqual(out["deliverables"], ["market_model.xlsx"])
        self.assertEqual(out["source_count"], 2)
        self.assertEqual(out["obligation_count"], 4)
        self.assertTrue(out["all_nonempty_task_lines_preserved_exactly"])
        self.assertFalse(out["semantic_completeness_claimed"])
        self.assertFalse(out["hidden_rubric_information_used"])

    def test_every_nonempty_line_survives_verbatim(self):
        b = bundle()
        out = compile_ingress(b)
        expected = [x.rstrip("\r\n") for x in b["task_text"].splitlines(keepends=True) if x.strip()]
        self.assertEqual([x["text"] for x in out["obligations"]], expected)

    def test_ingress_is_deterministic(self):
        self.assertEqual(compile_ingress(bundle())["ingress_sha256"], compile_ingress(bundle())["ingress_sha256"])

    def test_duplicate_source_fails(self):
        b = bundle()
        b["source_files"].append(dict(b["source_files"][0]))
        with self.assertRaisesRegex(IngressError, "SOURCE_PATH_DUPLICATE"):
            compile_ingress(b)

    def test_source_path_traversal_fails(self):
        b = bundle()
        b["source_files"][0]["path"] = "../secret"
        with self.assertRaisesRegex(IngressError, "SOURCE_PATH.*UNSAFE"):
            compile_ingress(b)

    def test_duplicate_deliverable_fails(self):
        b = bundle()
        b["deliverables"] = ["market_model.xlsx", "market_model.xlsx"]
        with self.assertRaisesRegex(IngressError, "DELIVERABLES_DUPLICATE"):
            compile_ingress(b)

    def test_empty_task_fails(self):
        b = bundle()
        b["task_text"] = "   "
        with self.assertRaisesRegex(IngressError, "TASK_TEXT_INVALID"):
            compile_ingress(b)
