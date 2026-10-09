from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import raw_cross_document_effect_bundle_v1 as bundle
from canonical.runtime import r2_raw_cross_document_effect_bundle_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v13 as v13


def _bundle(*,extra_b="",bad_c=False):
    return {
        "schema":bundle.SCHEMA,
        "case_id":"raw-direct",
        "documents":[
            {
                "document_id":"A",
                "source_id":"src:A",
                "source_text":"Effect A.t defines threshold as 10.",
            },
            {
                "document_id":"B",
                "source_id":"src:B",
                "source_text":(
                    "Effect B.t replaces A.t on threshold with 12 "
                    "effective 2026-07-01."+extra_b
                ),
            },
            {
                "document_id":"C",
                "source_id":"src:C",
                "source_text":(
                    "Small firms get special treatment."
                    if bad_c else
                    "Effect C.t excepts B.t on threshold with 8 when small = true "
                    "effective 2026-07-01."
                ),
            },
        ],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-08-01",
            "context":{"small":True},
        },
    }


def _goal():
    return (
        "Using the raw cross-document effect bundle at canonical/tmp/raw.json, "
        "compute and independently verify the effective value and save it to "
        "canonical/tmp/out.json."
    )


def _write(root:Path,**kwargs):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"raw.json").write_text(
        json.dumps(_bundle(**kwargs)),
        encoding="utf-8",
    )


class R2RawCrossDocumentEffectBundleDirectAdequacyV1Tests(unittest.TestCase):
    def test_raw_three_document_bundle_matches_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["effective_value"],8)
            self.assertEqual(pf["certified_effect_sentence_count"],3)
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],8)
            self.assertEqual(out["world_count"],1)
            self.assertTrue(out["query_relative_source_completeness_proved"])
            saved=json.loads((root/"canonical/tmp/out.json").read_text())
            self.assertEqual(saved["effective_value"],8)
            self.assertEqual(saved["certified_effect_sentence_count"],3)

    def test_extra_unknown_line_is_unmatched_with_exact_source_region(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(
                root,
                extra_b="\nThis sentence changes something important.",
            )
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_document_ids"],["B"])
            self.assertEqual(len(pf["blocking_unknown_regions"]),1)
            self.assertFalse(pf["query_relative_source_completeness_proved"])

    def test_document_with_zero_certified_effects_stays_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,bad_c=True)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_document_ids"],["C"])
            self.assertEqual(pf["compiler_status"],"OPEN__NO_CERTIFIED_EFFECT_SENTENCE_IN_DOCUMENT")
            self.assertEqual(len(pf["blocking_unknown_regions"]),1)

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root)
            op=root/"canonical/tmp/out.json"
            op.write_text('{"old":true}\n',encoding="utf-8")
            old=op.read_bytes()
            original=d.verifier.verify
            calls={"n":0}
            def injected(case,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(case,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

    def test_nonmatching_goal_has_no_scope(self):
        with tempfile.TemporaryDirectory() as td:
            out=d.preflight(
                {"task_id":"x","goal":"Read these documents."},
                repo_root=Path(td),
            )
            self.assertFalse(out["matched"])
            self.assertEqual(out["status"],"NOT_APPLICABLE")


class R2DirectEndToEndAdequacyV13Tests(unittest.TestCase):
    def test_v13_selects_raw_bundle_before_v12(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root)
            with patch.object(v13.v12,"preflight") as prior:
                pf=v13.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v13_preserves_raw_open_state_without_v12_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,extra_b="\nUnknown effect prose.")
            with patch.object(v13.v12,"preflight") as prior:
                pf=v13.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_document_ids"],["B"])
            prior.assert_not_called()

    def test_v13_delegates_unrelated_request_to_v12(self):
        request={"task_id":"x","goal":"Do something unrelated."}
        expected={"matched":False,"pass":False,"status":"V12_FALLBACK"}
        with patch.object(v13.v12,"preflight",return_value=expected) as prior:
            out=v13.preflight(request)
        self.assertEqual(out,expected)
        prior.assert_called_once()


if __name__=="__main__":
    unittest.main()
