from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import professional_structured_task_obligation_scope_v1 as s


def target():
    return {
        "objective": "Prepare a grounded executive recommendation",
        "audience": "Chief operating officer",
        "source_evidence": [{"id": "E1", "claim": "verified"}],
        "artifact_type": "DOCX",
        "constraints": {"max_pages": 3, "must_cite_sources": True},
        "current_draft_or_render": {"sha256": "a" * 64},
    }


class StructuredTaskObligationScopeV1Tests(unittest.TestCase):
    def test_valid_structured_target_compiles_exact_semantic_slice(self):
        out=s.compile_scope("task-x",target())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["obligation_count"],7)
        self.assertTrue(out["requirement_graph"]["pass"])
        self.assertTrue(out["requirement_mutation_score"]["pass"])
        self.assertEqual(out["requirement_mutation_score"]["kill_fraction"],1.0)
        self.assertFalse(out["scope_certificate"]["verified"])
        self.assertFalse(out["scope_certificate"]["independent"])
        self.assertFalse(out["arbitrary_prompt_semantic_completeness"])
        self.assertFalse(out["presentation_quality_authority"])
        self.assertFalse(out["owner_evaluator_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)

    def test_scope_id_matches_task_fulfillment_bridge_contract(self):
        out=s.compile_scope("task-x",target())
        material={
            "task_id":"task-x",
            "task_sha256":out["task_sha256"],
            "obligation_universe_digest":out["obligation_universe_digest"],
        }
        raw=json.dumps(material,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        expected="scope://professional-task-fulfillment/"+sha256(raw).hexdigest()
        self.assertEqual(out["target_scope_id"],expected)
        self.assertEqual(out["scope_certificate"]["target_scope_id"],expected)

    def test_every_declared_target_field_is_bound_or_explicit_context(self):
        out=s.compile_scope("task-x",target())
        joined="\n".join(x["semantics"] for x in out["obligations"])
        for field in ("objective","audience","source_evidence","artifact_type","constraints","current_draft_or_render"):
            value=target()[field]
            if isinstance(value,str):
                self.assertIn(value,joined)
            else:
                canonical=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
                self.assertIn(canonical,joined)

    def test_presentation_and_comparative_quality_remain_outside_semantic_slice(self):
        out=s.compile_scope("task-x",target())
        self.assertEqual(
            out["excluded_nonsemantic_or_comparative_atoms"],
            ["layout choice obscures information","revisions do not improve independent quality"],
        )
        self.assertNotIn(
            "layout choice obscures information",
            [x["semantics"] for x in out["obligations"]],
        )

    def test_missing_required_field_fails_closed(self):
        x=target();x.pop("audience")
        with self.assertRaisesRegex(s.StructuredTaskScopeError,"TARGET_INSTANCE_MISSING_FIELDS"):
            s.compile_scope("task-x",x)

    def test_unknown_field_fails_closed(self):
        x=target();x["silent_extra"]="bad"
        with self.assertRaisesRegex(s.StructuredTaskScopeError,"TARGET_INSTANCE_UNKNOWN_FIELDS"):
            s.compile_scope("task-x",x)

    def test_null_evidence_and_constraints_fail_closed(self):
        for field in ("source_evidence","constraints"):
            x=target();x[field]=None
            with self.assertRaisesRegex(s.StructuredTaskScopeError,"TARGET_REQUIRED_VALUE_MISSING"):
                s.compile_scope("task-x",x)

    def test_empty_text_roles_fail_closed(self):
        for field in ("objective","audience","artifact_type"):
            x=target();x[field]=" "
            with self.assertRaisesRegex(s.StructuredTaskScopeError,"TARGET_REQUIRED_TEXT_INVALID"):
                s.compile_scope("task-x",x)

    def test_task_id_required(self):
        with self.assertRaisesRegex(s.StructuredTaskScopeError,"TASK_ID_REQUIRED"):
            s.compile_scope("",target())

    def test_obligation_ids_are_exact_and_unique(self):
        out=s.compile_scope("task-x",target())
        ids=[x["obligation_id"] for x in out["obligations"]]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(
            set(ids),
            {
              "SEM_OBJECTIVE_AND_REQUIRED_ACTION","SEM_AUDIENCE_FIT",
              "SEM_EVIDENCE_GROUNDING","SEM_ARTIFACT_TYPE",
              "SEM_DECLARED_CONSTRAINTS","SEM_REVISION_CONTEXT",
              "SEM_REQUIRED_ANALYSIS_COMPLETENESS",
            },
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
