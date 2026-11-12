from __future__ import annotations

import json
import unittest
from urllib.parse import unquote

from canonical.runtime.automationbench_grounded_update_compiler_v1 import (
    SURFACE,
    compile_grounded_update,
)


class GroundedUpdateCompilerTests(unittest.TestCase):
    def sf(self, **kw):
        data = {
            "surface": SURFACE,
            "app": "SALESFORCE",
            "object_type": "Opportunity",
            "record_id": "006xx000004MER1",
            "fields": {"StageName": "Closed Won"},
            "grounding_complete": True,
            "provenance_bound": True,
            "provenance": ["OBSERVED_RECORD:006xx000004MER1", "PROMPT:MARK_WON"],
        }
        data.update(kw)
        return data

    def sheet(self, **kw):
        data = {
            "surface": SURFACE,
            "app": "GOOGLE_SHEETS",
            "spreadsheet_id": "ss_ic",
            "range_a1": "February 2026!G2:G2",
            "values": [["Processed"]],
            "grounding_complete": True,
            "provenance_bound": True,
            "provenance": ["ROW:2", "POLICY:APPROVED_ONLY"],
        }
        data.update(kw)
        return data

    def test_salesforce_patch_is_exact_and_preserves_value(self):
        out = compile_grounded_update(self.sf())
        self.assertTrue(out["pass"], out)
        call = out["tool_call"]
        self.assertEqual(call["arguments"]["method"], "PATCH")
        self.assertTrue(call["arguments"]["url"].endswith("/Opportunity/006xx000004MER1"))
        self.assertEqual(json.loads(call["arguments"]["body"]), {"StageName": "Closed Won"})

    def test_salesforce_supports_other_public_sobjects(self):
        out = compile_grounded_update(self.sf(
            object_type="Contact",
            record_id="003xx000004AR01",
            fields={"Title": "Senior Vice President"},
        ))
        self.assertTrue(out["pass"], out)
        self.assertIn("/Contact/003xx000004AR01", out["tool_call"]["arguments"]["url"])

    def test_sheets_put_percent_encodes_a1_path_and_keeps_body_range(self):
        out = compile_grounded_update(self.sheet())
        self.assertTrue(out["pass"], out)
        call = out["tool_call"]
        self.assertEqual(call["arguments"]["method"], "PUT")
        self.assertTrue(call["arguments"]["url"].endswith("/values/February%202026%21G2%3AG2"))
        self.assertEqual(
            unquote(call["arguments"]["url"].split("/values/", 1)[1]),
            "February 2026!G2:G2",
        )
        self.assertEqual(json.loads(call["arguments"]["body"])["values"], [["Processed"]])

    def test_sheets_supports_multi_cell_rectangles(self):
        out = compile_grounded_update(self.sheet(
            range_a1="February 2026!G2:H2",
            values=[["Processed", "1.05"]],
        ))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["grounding"]["shape"], [1, 2])

    def test_real_world_surface_is_rejected(self):
        out = compile_grounded_update(self.sf(surface="REAL_WORLD"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "BENCHMARK_SIMULATED_SURFACE_REQUIRED")

    def test_unbound_provenance_is_rejected(self):
        out = compile_grounded_update(self.sf(provenance_bound=False))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "GROUNDING_PROVENANCE_REQUIRED")

    def test_incomplete_grounding_is_rejected(self):
        out = compile_grounded_update(self.sheet(grounding_complete=False))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "GROUNDING_INCOMPLETE")

    def test_placeholders_fail_closed_even_when_flag_claims_grounded(self):
        out = compile_grounded_update(self.sf(fields={"Amount": "$X"}))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "PLACEHOLDER_OR_UNRESOLVED_VALUE")

    def test_unknown_salesforce_object_fails_closed(self):
        out = compile_grounded_update(self.sf(object_type="MagicObject"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SALESFORCE_OBJECT_TYPE_UNSUPPORTED")

    def test_non_rectangular_sheet_values_fail_closed(self):
        out = compile_grounded_update(self.sheet(values=[["a", "b"], ["c"]]))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "RECTANGULAR_2D_VALUES_REQUIRED")

    def test_empty_fields_fail_closed(self):
        out = compile_grounded_update(self.sf(fields={}))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SALESFORCE_FIELDS_REQUIRED")


    def test_sheets_named_row_update_uses_benchmark_row_route(self):
        out = compile_grounded_update({
            "surface": SURFACE,
            "app": "GOOGLE_SHEETS",
            "spreadsheet_id": "ss_ic",
            "worksheet_id": "ws_feb_ic",
            "row_id": 2,
            "cells": {"Status": "Processed"},
            "grounding_complete": True,
            "provenance_bound": True,
            "provenance": ["ROW:2", "POLICY:APPROVED_ONLY"],
        })
        self.assertTrue(out["pass"], out)
        call = out["tool_call"]["arguments"]
        self.assertEqual(call["method"], "PUT")
        self.assertTrue(call["url"].endswith("/values/ws_feb_ic/rows/2"))
        self.assertEqual(json.loads(call["body"]), {"cells": {"Status": "Processed"}})

    def test_sheets_named_row_update_rejects_missing_worksheet(self):
        out = compile_grounded_update({
            "surface": SURFACE,
            "app": "GOOGLE_SHEETS",
            "spreadsheet_id": "ss_ic",
            "worksheet_id": "",
            "row_id": 2,
            "cells": {"Status": "Processed"},
            "grounding_complete": True,
            "provenance_bound": True,
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WORKSHEET_ID_INVALID")

    def test_sheets_named_row_update_rejects_empty_cells(self):
        out = compile_grounded_update({
            "surface": SURFACE,
            "app": "GOOGLE_SHEETS",
            "spreadsheet_id": "ss_ic",
            "worksheet_id": "ws_feb_ic",
            "row_id": 2,
            "cells": {},
            "grounding_complete": True,
            "provenance_bound": True,
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "NAMED_CELLS_REQUIRED")

    def test_no_self_promotion_authority(self):
        for spec in (self.sf(), self.sheet()):
            out = compile_grounded_update(spec)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["promotion_authority"])
            self.assertFalse(out["network_io_performed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
