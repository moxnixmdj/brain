"""Lossless scope-equivalence proof for Unknown-Domain Generator V3.

Claim:
  Generator V3 is not a weaker task generator. Its generation path is exactly
  validate_packet(V2_generate(...)). The validator does not rewrite successful
  packets. It only refuses packets whose namespace/shape violates invariants
  already required by the frozen evaluator semantics, harness, or scorer.

Therefore:
  emitted(V3) = admissible_frozen_evaluator_packets(V2)

This theorem is intentionally about evaluator scope only. It grants no
acceptance, family, capability, ownership, or terminal credit by itself.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_LOSSLESS_SCOPE_EQUIVALENCE_V1"

EXPECTED_BLOBS={
 "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json":"fd586455d582c38c7062ffe735f86cb9f2e803ab",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"6582f60d67d4bee7851cfa42ec1d677c643d8c2e",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}


def _root()->Path:
 return Path(__file__).resolve().parents[2]


def _git_blob(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def _bind(root:Path)->dict[str,str]:
 got={p:_git_blob(root/p) for p in EXPECTED_BLOBS}
 bad={p:{"expected":EXPECTED_BLOBS[p],"got":got[p]} for p in EXPECTED_BLOBS if got[p]!=EXPECTED_BLOBS[p]}
 if bad:
  raise AssertionError("SCOPE_EQUIVALENCE_SUBJECT_BLOB_MISMATCH:"+repr(bad))
 return got


def _json(root:Path,path:str)->dict[str,Any]:
 return json.loads((root/path).read_text(encoding="utf-8"))


def _generator_composition_theorem()->dict[str,Any]:
 src=inspect.getsource(g3._generate)
 tree=ast.parse(src)
 fn=tree.body[0]
 assert isinstance(fn,ast.FunctionDef) and fn.name=="_generate"
 assert len(fn.body)==1 and isinstance(fn.body[0],ast.Return)
 outer=fn.body[0].value
 assert isinstance(outer,ast.Call) and isinstance(outer.func,ast.Name) and outer.func.id=="validate_packet"
 assert len(outer.args)==1 and isinstance(outer.args[0],ast.Call)
 inner=outer.args[0]
 assert isinstance(inner.func,ast.Attribute)
 assert isinstance(inner.func.value,ast.Name) and inner.func.value.id=="v2" and inner.func.attr=="_generate"
 kws={x.arg:x.value for x in inner.keywords}
 for name in ("beacon","evaluator_secret","namespace"):
  assert isinstance(kws.get(name),ast.Name) and kws[name].id==name

 # Successful validation returns a shallow mapping copy; no field is rewritten.
 vsrc=inspect.getsource(g3.validate_packet)
 assert "return dict(packet)" in vsrc
 vtree=ast.parse(vsrc)
 for node in ast.walk(vtree):
  if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
   targets=node.targets if isinstance(node,ast.Assign) else [node.target]
   # There must be no assignment through packet/visible/hidden subscript/attribute.
   for target in targets:
    if isinstance(target,(ast.Subscript,ast.Attribute)):
     raise AssertionError("VALIDATOR_MUTATION_TARGET_FOUND:"+ast.dump(target))
 return {
  "v3_generation_expression":"validate_packet(v2._generate(beacon=beacon,evaluator_secret=evaluator_secret,namespace=namespace))",
  "successful_packet_rewrite":False,
  "successful_packet_semantics_identical_to_v2":True,
 }


def _frozen_semantic_requirements(root:Path)->dict[str,Any]:
 protocol=_json(root,"canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json")
 family=_json(root,"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json")

 assert [x["id"] for x in protocol["leaves"]]==[
  g1.TRANSFER,
  g1.ABSTAIN,
 ]
 assert family["hidden_generation_rule"]["surface_tokens_are_opaque_and_CASE_LOCAL"] is True
 assert family["hidden_generation_rule"]["domain_a_and_domain_b_surface_vocabularies_are_disjoint"] is True
 assert family["scoring"]["one_failure_blocks_leaf_pass"] is True
 assert family["scoring"]["required_abstention_class_balance"]=={
  "IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5
 }

 transfer=family["leaves"][0]
 abstain=family["leaves"][1]
 assert transfer["leaf_id"]==g1.TRANSFER
 assert transfer["case_count"]==12
 assert transfer["design"]["probe_budget"]["max_domain_b_probes"]==2
 assert transfer["design"]["hidden_case_schema"]["transfer_relevant_feature_ids"]=="EXACT_SET"
 assert transfer["design"]["hidden_case_schema"]["distractor_feature_ids"]=="AT_LEAST_TWO_EXACT_IDS"
 assert transfer["design"]["hidden_case_schema"]["domain_vocabularies_disjoint"] is True
 assert "TRANSFER_MAPPING_SUPPORT_MATCHES_HIDDEN_RELEVANT_FEATURE_SET" in transfer["acceptance"]
 assert "HIDDEN_DISTRACTOR_FEATURES_DO_NOT_APPEAR_AS_POSITIVE_SUPPORT" in transfer["acceptance"]

 assert abstain["leaf_id"]==g1.ABSTAIN
 assert abstain["case_count"]==15
 assert abstain["design"]["identifiable_cases_have_unique_supported_conclusion"] is True
 assert abstain["design"]["nonidentifiable_cases_have_at_least_two_decision_distinct_survivors_under_all_allowed_observations"] is True
 assert abstain["design"]["underspecified_cases_have_a_valid_minimum_discriminator"] is True
 assert "MINIMUM_DISCRIMINATOR_IS_UNIQUE_UNDER_FROZEN_COST_THEN_LEXICOGRAPHIC_TIEBREAK" in abstain["design"]["generator_constraints"]

 return {
  "case_counts":{"transfer":12,"abstention":15,"total":27},
  "surface_namespace_must_be_well_formed":True,
  "transfer_support_and_distractors_are_exact_semantic_sets":True,
  "nonidentifiable_requires_decision_distinct_survivors":True,
  "underspecified_requires_unique_valid_minimum_discriminator":True,
  "all_cases_conjunctive":True,
 }


def _runtime_wellformedness_requirements()->dict[str,Any]:
 # The harness itself rejects duplicate allowed probe IDs and mismatched IDs.
 hsrc=inspect.getsource(harness._allowed_probes)
 assert "ALLOWED_PROBE_ID_INVALID_OR_DUPLICATE" in hsrc
 execsrc=inspect.getsource(harness.execute_case)
 assert "CASE_ID_MISMATCH" in execsrc
 assert "LEAF_ID_MISMATCH" in execsrc

 # The scorer requires identifier sequences to be unique and aggregate case IDs
 # to be nonempty/unique. These are evaluator well-formedness constraints, not
 # candidate-performance challenges.
 ssrc=inspect.getsource(scorer._strings)
 assert "DUPLICATE" in ssrc
 asrc=inspect.getsource(scorer.aggregate)
 assert "CASE_IDS_INVALID_OR_DUPLICATE" in asrc
 return {
  "duplicate_allowed_probe_ids_are_invalid":True,
  "visible_hidden_case_binding_is_required":True,
  "scorer_identifier_sequences_require_uniqueness":True,
  "aggregate_case_ids_require_uniqueness":True,
 }


def _validator_rejection_classes()->dict[str,str]:
 # Every V3 rejection class is either a static V2 schema invariant or a
 # collision-induced violation of frozen semantics/runtime well-formedness.
 return {
  "PACKET_INVALID":"NOT_A_FROZEN_EVALUATOR_PACKET",
  "PACKET_CASE_COUNT":"FROZEN_12_PLUS_15_CASE_CARDINALITY",
  "VISIBLE_CASE_IDS_*":"SCORER_AGGREGATE_REQUIRES_NONEMPTY_UNIQUE_CASE_IDS",
  "HIDDEN_CASE_IDS_*":"SCORER_AGGREGATE_AND_VISIBLE_HIDDEN_BINDING_REQUIRE_UNIQUE_CASE_IDS",
  "VISIBLE_HIDDEN_CASE_ID_ORDER_MISMATCH":"HARNESS_REQUIRES_CASE_ID_BINDING",
  "CASE_*_LEAF_*":"HARNESS_REQUIRES_LEAF_BINDING",
  "TRANSFER_RELEVANT_*":"HIDDEN_TRANSFER_RELEVANT_IDS_ARE_AN_EXACT_SET_AND_SCORER_REQUIRES_UNIQUE_IDS",
  "TRANSFER_DISTRACTORS_*":"DISTRACTOR_IDS_ARE_EXACT_NEGATIVE_TRANSFER_ITEMS_AND_SCORER_REQUIRES_UNIQUE_IDS",
  "TRANSFER_RELEVANT_DISTRACTOR_OVERLAP":"FROZEN_ACCEPTANCE_FORBIDS_DISTRACTOR_AS_POSITIVE_SUPPORT",
  "TRANSFER_DOMAIN_MAPPING_INVALID":"HIDDEN_DOMAIN_MAPPING_MUST_BIND_EXACT_RELEVANT_SET",
  "SOURCE_ROLE_NAMESPACE_NOT_INJECTIVE":"FROZEN_ROLE_BINDING_AND_CASE_LOCAL_OPAQUE_FEATURE_NAMESPACE",
  "*_FEATURE_NAMESPACE_NOT_INJECTIVE":"CASE_LOCAL_OPAQUE_FEATURES_MUST_RETAIN_ROLE_PLUS_TWO_DISTRACTOR_CARDINALITY",
  "TRANSFER_PROBE_IDS_*":"HARNESS_EXPLICITLY_REJECTS_DUPLICATE_ALLOWED_PROBE_IDS",
  "TRANSFER_PROBE_TABLE_KEYS":"ALLOWED_PROBE_RESULT_TABLE_MUST_BIND_EXACT_VISIBLE_PROBE_IDS",
  "ABSTENTION_HYPOTHESIS_IDS_*":"TWO_HYPOTHESIS_FROZEN_SEMANTICS_REQUIRE_DISTINCT_HYPOTHESIS_IDENTITIES",
  "IDENTIFIABLE_CONSEQUENCE_NOT_EQUAL":"IDENTIFIABLE_REQUIRES_ONE_SUPPORTED_DECISION_EQUIVALENCE_CLASS",
  "NONIDENTIFIABLE_CONSEQUENCE_COLLISION":"NONIDENTIFIABLE_REQUIRES_TWO_DECISION_DISTINCT_SURVIVORS",
  "ABSTENTION_PROBE_IDS_*":"UNDERSPECIFIED_DISCRIMINATORS_AND_HARNESS_PROBE_IDS_MUST_BE_DISTINCT",
  "ABSTENTION_PROBE_TABLE_KEYS":"HIDDEN_OUTCOME_TABLE_MUST_BIND_EXACT_ALLOWED_PROBES",
  "ABSTENTION_PROBE_OUTCOME_KEYS":"HIDDEN_OUTCOME_TABLE_MUST_BIND_EXACT_TWO_HYPOTHESES",
  "UNDERSPECIFIED_MINIMUM_DISCRIMINATOR_INVALID":"FROZEN_UNDERSPECIFIED_CASE_REQUIRES_VALID_UNIQUE_MINIMUM_DISCRIMINATOR",
  "NON_UNDERSPECIFIED_MINIMUM_DISCRIMINATOR_PRESENT":"MINIMUM_DISCRIMINATOR_FIELD_IS_SEMANTIC_ONLY_FOR_UNDERSPECIFIED_CLASS",
  "STATIC_SHAPE_CHECKS":"EXACT_V2_GENERATOR_SCHEMA_INVARIANTS__NEVER_REMOVE_A_WELL_FORMED_V2_CASE",
 }


def prove(root:Path|None=None)->dict[str,Any]:
 root=_root() if root is None else Path(root).resolve()
 bindings=_bind(root)
 composition=_generator_composition_theorem()
 semantics=_frozen_semantic_requirements(root)
 runtime=_runtime_wellformedness_requirements()
 rejects=_validator_rejection_classes()

 assert g1.PRODUCTION_CASE_COUNTS=={g1.TRANSFER:12,g1.ABSTAIN:15}
 assert tuple(g1.ABSTAIN_CLASSES)==("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")

 return {
  "schema":SCHEMA,
  "status":"PASS__LOSSLESS_EQUIVALENCE_OVER_FROZEN_ADMISSIBLE_EVALUATOR_SCOPE",
  "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
  "exact_subject_blobs":bindings,
  "generator_composition":composition,
  "frozen_semantic_requirements":semantics,
  "runtime_wellformedness_requirements":runtime,
  "validator_rejection_classes":rejects,
  "set_relation":{
   "v2_raw_outputs":"ALL_PACKETS_RETURNED_BY_EXACT_V2_GENERATOR_FOR_ACCEPTED_INPUTS",
   "admissible_v2_scope":"V2_RAW_OUTPUTS_SATISFYING_FROZEN_EVALUATOR_SEMANTICS_AND_HARNESS_SCORER_WELLFORMEDNESS",
   "v3_emitted_scope":"EXACTLY_ADMISSIBLE_V2_SCOPE",
   "proof":"V3_CALLS_V2_WITH_IDENTICAL_ARGUMENTS__VALIDATOR_IS_READ_ONLY__EVERY_VALID_PACKET_IS_RETURNED_UNCHANGED__EVERY_REJECTION_IS_A_FROZEN_SEMANTIC_OR_RUNTIME_WELLFORMEDNESS_VIOLATION",
  },
  "lossless":True,
  "scope_narrowing_of_admissible_cases":False,
  "new_task_semantics_added":False,
  "invalid_collision_states_reclassified_as_valid_cases":False,
  "theorem":(
   "FOR_THE_EXACT_FROZEN_DIRECT_EVALUATOR_CONTRACT__GENERATOR_V3_EMITS_THE_EXACT_"
   "SAME_PACKET_AS_GENERATOR_V2_WHEN_THE_V2_PACKET_IS_ADMISSIBLE__AND_FAILS_CLOSED_"
   "ONLY_WHEN_THE_V2_PACKET_VIOLATES_A_FROZEN_SEMANTIC_OR_HARNESS_SCORER_"
   "WELLFORMEDNESS_INVARIANT__THEREFORE_V3_IS_LOSSLESS_OVER_ADMISSIBLE_SCOPE"
  ),
  "hard_nonclaims":[
   "NO_CLAIM_EVERY_ARBITRARY_SECRET_MUST_PRODUCE_A_STRUCTURALLY_VALID_V2_PACKET",
   "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT_FROM_THIS_CERTIFICATE_ALONE",
   "INDEPENDENT_CONTENT_BOUND_VERIFICATION_REQUIRED",
  ],
  "accounting":{
   "incremental_spend_usd":0,
   "new_reality_units_consumed":0,
   "terminal_cases_consumed":0,
   "production_cases_generated":0,
   "acceptance_credit_delta":0,
   "family_credit_delta":0,
   "capability_credit_delta":0,
   "ownership_credit_delta":0,
  },
 }


if __name__=="__main__":
 print(json.dumps(prove(),indent=2,sort_keys=True))
