from __future__ import annotations
import unittest

from canonical.runtime import raw_cross_document_effect_bundle_v1 as b
from canonical.runtime import cross_document_source_residual_frontier_v1 as combined
from canonical.runtime import cross_document_source_residual_frontier_verify_v1 as combined_verify


def _bundle(*,extra_b="",trailing_newline=False):
    docs=[
        {
            "document_id":"A","source_id":"src:A",
            "source_text":"Effect A.t defines threshold as 10.",
        },
        {
            "document_id":"B","source_id":"src:B",
            "source_text":"Effect B.t replaces A.t on threshold with 12 effective 2026-07-01."+extra_b,
        },
        {
            "document_id":"C","source_id":"src:C",
            "source_text":"Effect C.t excepts B.t on threshold with 8 when small = true effective 2026-07-01.",
        },
    ]
    if trailing_newline:
        for doc in docs:
            doc["source_text"]+="\n"
    return {
        "schema":b.SCHEMA,
        "case_id":"raw-bundle",
        "documents":docs,
        "query":{
            "target_id":"threshold",
            "as_of":"2026-08-01",
            "context":{"small":True},
        },
    }


class RawCrossDocumentEffectBundleV1Tests(unittest.TestCase):
    def test_three_raw_documents_compile_and_close_v12(self):
        out=b.compile_bundle(_bundle())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["certified_effect_sentence_count"],3)
        self.assertEqual(out["open_unknown_region_count"],0)
        result=combined.evaluate(out["v12_case"])
        self.assertTrue(result["pass"],result)
        self.assertEqual(result["effective_value"],8)
        self.assertTrue(combined_verify.verify(out["v12_case"],result)["verified"])

    def test_newlines_are_whitespace_not_unknown_semantics(self):
        out=b.compile_bundle(_bundle(trailing_newline=True))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["open_unknown_region_count"],0)
        for doc in out["v12_case"]["byte_coverage_documents"]:
            self.assertEqual(doc["coverage_regions"][-1]["mode"],"WHITESPACE_NO_EFFECT")
        result=combined.evaluate(out["v12_case"])
        self.assertTrue(result["pass"],result)
        self.assertEqual(result["effective_value"],8)

    def test_extra_unknown_line_reintroduces_source_top(self):
        out=b.compile_bundle(_bundle(extra_b="\nThis sentence changes something important."))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__RAW_BUNDLE_COMPILED_WITH_SOURCE_TOP")
        self.assertEqual(out["open_unknown_region_count"],1)
        result=combined.evaluate(out["v12_case"])
        self.assertFalse(result["pass"],result)
        self.assertEqual(result["status"],"OPEN__QUERY_RELEVANT_SOURCE_TOP_REMAINS")
        self.assertEqual(result["blocking_document_ids"],["B"])
        self.assertEqual(len(result["blocking_unknown_regions"]),1)

    def test_near_miss_effect_wording_remains_unknown(self):
        bundle=_bundle()
        bundle["documents"][1]["source_text"]="Effect B.t changes A.t on threshold to 12 effective 2026-07-01."
        out=b.compile_bundle(bundle)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__NO_CERTIFIED_EFFECT_SENTENCE_IN_DOCUMENT")
        self.assertEqual(out["document_id"],"B")

    def test_document_with_only_arbitrary_prose_does_not_mint_worldset_case(self):
        bundle=_bundle()
        bundle["documents"][2]["source_text"]="Small firms get special treatment."
        out=b.compile_bundle(bundle)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__NO_CERTIFIED_EFFECT_SENTENCE_IN_DOCUMENT")
        self.assertNotIn("v12_case",out)

    def test_multiple_effect_sentences_in_one_document_create_distinct_slots(self):
        bundle={
            "schema":b.SCHEMA,
            "case_id":"multi",
            "documents":[{
                "document_id":"A",
                "source_id":"src:A",
                "source_text":(
                    "Effect A.t defines threshold as 10.\n"
                    "Effect A.x defines other as 2."
                ),
            }],
            "query":{"target_id":"threshold","as_of":"2026-08-01","context":{}},
        }
        out=b.compile_bundle(bundle)
        self.assertTrue(out["pass"],out)
        slots=out["v12_case"]["worldset_problem"]["documents"][0]["effect_slots"]
        self.assertEqual([x["slot_id"] for x in slots],[
            "A.raw_effect.1","A.raw_effect.2",
        ])
        result=combined.evaluate(out["v12_case"])
        self.assertTrue(result["pass"],result)
        self.assertEqual(result["effective_value"],10)

    def test_unicode_unknown_region_uses_byte_offsets(self):
        out=b.compile_bundle(_bundle(extra_b="\nΔ unknown"))
        self.assertFalse(out["pass"])
        case=out["v12_case"]
        bdoc=[x for x in case["byte_coverage_documents"] if x["document_id"]=="B"][0]
        regions=bdoc["coverage_regions"]
        self.assertEqual(regions[-1]["mode"],"OPEN_UNKNOWN_EFFECT")
        self.assertEqual(regions[-1]["end"],len(bdoc["source_text"].encode("utf-8")))


if __name__=="__main__":
    unittest.main()
