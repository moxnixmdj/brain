import hashlib
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.aa_briefcase_lossless_task_ingress_v1 import (
    IngressError,
    compile_harness_ingress,
    compile_ingress,
    inventory_source_roots,
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
        "context_sections": {
            "scenario_overview": "You are supporting a commercial due diligence engagement.\n",
            "week_overview": "This week focuses on market sizing and target assessment.\n",
        },
        "deliverables": ["market_model.xlsx"],
        "source_files": [
            {"path": "shared/standards.docx", "sha256": "a" * 64, "size_bytes": 123},
            {"path": "week/input.xlsx", "sha256": "b" * 64, "size_bytes": 456},
        ],
    }


class T(unittest.TestCase):
    def test_preserves_full_context_deliverables_and_sources(self):
        out = compile_ingress(bundle())
        self.assertEqual(out["deliverables"], ["market_model.xlsx"])
        self.assertEqual(out["source_count"], 2)
        self.assertEqual(out["obligation_count"], 6)
        self.assertTrue(out["all_nonempty_context_and_task_lines_preserved_exactly"])
        self.assertFalse(out["semantic_completeness_claimed"])
        self.assertFalse(out["hidden_rubric_information_used"])
        self.assertEqual(
            {x["section_id"] for x in out["context_sections"]},
            {"scenario_overview", "week_overview", "task_brief"},
        )

    def test_every_nonempty_line_survives_verbatim_by_section(self):
        b = bundle()
        out = compile_ingress(b)
        by_section = {}
        for row in out["obligations"]:
            by_section.setdefault(row["section_id"], []).append(row["text"])
        self.assertEqual(
            by_section["task_brief"],
            [x.rstrip("\r\n") for x in b["task_text"].splitlines(keepends=True) if x.strip()],
        )
        self.assertEqual(
            by_section["scenario_overview"],
            ["You are supporting a commercial due diligence engagement."],
        )

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

    def test_recursive_mount_inventory_expands_directories(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shared = root / "shared"
            week = root / "week"
            (shared / "slack" / "channel").mkdir(parents=True)
            week.mkdir()
            a = b'{"message":"one"}'
            b = b"BEGIN:VCALENDAR\nEND:VCALENDAR\n"
            (shared / "slack" / "channel" / "m.json").write_bytes(a)
            (week / "calendar.ics").write_bytes(b)
            rows = inventory_source_roots({"shared": shared, "week": week})
            self.assertEqual(
                [x["path"] for x in rows],
                ["shared/slack/channel/m.json", "week/calendar.ics"],
            )
            self.assertEqual(rows[0]["sha256"], hashlib.sha256(a).hexdigest())
            self.assertEqual(rows[1]["size_bytes"], len(b))

    def test_harness_ingress_preserves_overviews_task_and_recursive_mounts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shared = root / "shared"
            week = root / "week"
            shared.mkdir()
            week.mkdir()
            (shared / "a.json").write_text('{"x":1}', encoding="utf-8")
            (week / "b.eml").write_text("Subject: X\n\nBody", encoding="utf-8")
            out = compile_harness_ingress(
                task_id="w1_t2",
                scenario_overview="Scenario context\n",
                week_overview="Week context\n",
                task_brief="Build market_model.xlsx\n",
                deliverables=["market_model.xlsx"],
                shared_root=shared,
                week_root=week,
            )
            self.assertEqual(out["source_count"], 2)
            self.assertEqual(out["obligation_count"], 3)
            self.assertEqual(
                {x["section_id"] for x in out["obligations"]},
                {"scenario_overview", "week_overview", "task_brief"},
            )
