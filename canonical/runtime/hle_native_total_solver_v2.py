#!/usr/bin/env python3
"""Total Brain-native HLE proposal/commitment orchestrator V2.

V2 composes the frozen SymPy/Lark symbolic solver before the older bounded
symbolic surface, then deterministic retrieval. It emits UNKNOWN when all
Brain-owned lanes fail. No external reasoning-model solver output is admitted.
"""
from __future__ import annotations
import hashlib,json,re
from typing import Any,Callable,Mapping

SCHEMA="PROJECT_BRAIN_HLE_NATIVE_TOTAL_SOLVER_V2"
_MCQ=re.compile(r"(?mi)^\s*Answer Choices:\s*$")

def _sha(v:str)->str:return hashlib.sha256(v.encode("utf-8")).hexdigest()
def _confidence(r:Mapping[str,Any]|None,lane:str)->int:
    if not r:return 0
    b=str(r.get("confidence_band") or "").upper()
    if b=="HIGH":return 70
    if b=="MEDIUM":return 50
    if b=="LOW":return 25
    if lane in {"SYMBOLIC_LARK_V2","SYMBOLIC_SURFACE_V1"}:return 60
    return 35

def solve(*,task_id:str,question:str,image:str="",
          search_fn:Callable[...,Mapping[str,Any]]|None=None,
          fetch_fn:Callable[...,Mapping[str,Any]]|None=None,
          ocr_fn:Callable[[Any],str]|None=None,
          mcq_proposer:Callable[...,Mapping[str,Any]]|None=None,
          symbolic_lark_proposer:Callable[...,Mapping[str,Any]]|None=None,
          symbolic_surface_proposer:Callable[...,Mapping[str,Any]]|None=None,
          retrieval_proposer:Callable[...,Mapping[str,Any]]|None=None,
          image_observer:Callable[...,Mapping[str,Any]]|None=None)->dict[str,Any]:
    if not isinstance(task_id,str) or not task_id.strip():raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question,str) or not question.strip():raise ValueError("QUESTION_REQUIRED")
    if not isinstance(image,str):raise ValueError("IMAGE_MUST_BE_STRING")
    if mcq_proposer is None:
        from canonical.runtime.hle_mcq_retrieval_vote_v1 import propose as mcq_proposer
    if symbolic_lark_proposer is None:
        from canonical.runtime.hle_symbolic_lark_solver_v2 import propose as symbolic_lark_proposer
    if symbolic_surface_proposer is None:
        from canonical.runtime.hle_symbolic_surface_solver_v1 import propose as symbolic_surface_proposer
    if retrieval_proposer is None:
        from canonical.runtime.hle_exact_retrieval_extract_v2 import propose as retrieval_proposer
    if image_observer is None:
        from canonical.runtime.hle_image_observation_v1 import observe as image_observer

    original_image=bool(image);image_receipt=None;augmented=question;image_text_available=False
    if original_image:
        try:image_receipt=image_observer(image_data_uri=image,ocr_fn=ocr_fn)
        except Exception as exc:image_receipt={"status":"FAIL_CLOSED__IMAGE_OBSERVATION_FAILED","error_class":type(exc).__name__,"intrinsic_brain_vision_claimed":False,"external_reasoning_model_calls":0}
        if image_receipt.get("status")=="OBSERVED":
            text=str(image_receipt.get("ocr_text") or "").strip()
            if text:
                augmented="[LOCAL OCR TOOL OBSERVATION]\n"+text+"\n[END LOCAL OCR TOOL OBSERVATION]\n"+question
                image_text_available=True

    attempts=[];chosen=None;chosen_lane=None
    def attempt(name,fn,kwargs):
        nonlocal chosen,chosen_lane
        try:r=dict(fn(**kwargs))
        except Exception as exc:r={"status":"LANE_EXCEPTION","error_class":type(exc).__name__,"candidate_answer":None}
        cand=r.get("candidate_answer")
        attempts.append({"lane":name,"status":r.get("status"),"candidate_present":isinstance(cand,str) and bool(cand),
                         "candidate_answer_authority":bool(r.get("candidate_answer_authority",False)),
                         "external_model_calls":int(r.get("external_model_calls",0) or 0),
                         "external_reasoning_model_calls":int(r.get("external_reasoning_model_calls",0) or 0),
                         "model_dependency_count":int(r.get("model_dependency_count",0) or 0)})
        if chosen is None and isinstance(cand,str) and cand:
            chosen=(cand,r);chosen_lane=name

    transformed_image_flag=original_image and not image_text_available
    if _MCQ.search(question):
        attempt("MCQ_RETRIEVAL_VOTE",mcq_proposer,{"task_id":task_id,"question":augmented,
                "has_nonempty_image_payload":transformed_image_flag,"search_fn":search_fn,"fetch_fn":fetch_fn})
    else:
        attempt("SYMBOLIC_LARK_V2",symbolic_lark_proposer,{"task_id":task_id,"question":augmented,
                "has_nonempty_image_payload":transformed_image_flag})
        if chosen is None:
            attempt("SYMBOLIC_SURFACE_V1",symbolic_surface_proposer,{"task_id":task_id,"question":augmented,
                    "has_nonempty_image_payload":transformed_image_flag})
        if chosen is None:
            attempt("EXACT_RETRIEVAL_V2",retrieval_proposer,{"task_id":task_id,"question":augmented,
                    "has_nonempty_image_payload":transformed_image_flag,"search_fn":search_fn,"fetch_fn":fetch_fn})

    if chosen is None:
        answer="UNKNOWN";abstained=True;confidence=0;explanation="No Brain-native supported proposal lane produced a candidate."
    else:
        answer,receipt=chosen;abstained=False;confidence=_confidence(receipt,chosen_lane or "");explanation=f"Brain-native proposal lane: {chosen_lane}."
    response=f"Explanation: {explanation}\nAnswer: {answer}\nConfidence: {confidence}%"
    binding={"task_id":task_id,"question_sha256":_sha(question),"image_data_uri_sha256":_sha(image) if image else None}
    return {"schema":SCHEMA,"status":"PRECOMMITTABLE_CANDIDATE" if not abstained else "PRECOMMITTABLE_ABSTENTION",
            "task_id":task_id,"input_sha256":_sha(json.dumps(binding,sort_keys=True,separators=(",",":"))),
            "question_sha256":binding["question_sha256"],"image_data_uri_sha256":binding["image_data_uri_sha256"],
            "final_answer":answer,"final_answer_sha256":_sha(answer),"final_response":response,
            "final_response_sha256":_sha(response),"confidence_percent":confidence,"abstained":abstained,
            "selected_lane":chosen_lane,"attempts":attempts,
            "image_observation":({"status":image_receipt.get("status"),"image_sha256":image_receipt.get("image_sha256"),
                                  "ocr_text_sha256":image_receipt.get("ocr_text_sha256"),"ocr_chars":image_receipt.get("ocr_chars"),
                                  "local_ocr_tool_used":image_receipt.get("local_ocr_tool_used",False),
                                  "intrinsic_brain_vision_claimed":False} if image_receipt else None),
            "answer_type_metadata_used":False,"answer_type_inferred_from_visible_question_only":True,
            "precommittable":True,"gold_accessed":False,"external_reasoning_model_calls":0,
            "external_model_solver_output_used":False,"brain_capability_claim_from_external_model":False,
            "correctness_claimed":False,"target_score_claimed":False,"terminal_authority":False,"terminal_credit_delta":0,
            "hard_nonclaim":"TOTAL_PRECOMMITTABLE_OUTPUT_DOES_NOT_IMPLY_SCORE_ADEQUACY_OR_CORRECTNESS"}
