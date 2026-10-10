"""R2 direct adequacy for exact plain-semantic Markdown-to-PDF conversion.

Admitted scope:
- repository-local ASCII Markdown source;
- exact "Convert <canonical/*.md> to <canonical/*.pdf>." raw goal;
- Markdown subset containing headings and plain paragraph lines only;
- verified Pandoc+WeasyPrint producer;
- producer-independent pypdf text-layer readback.

The output is transactional. A preexisting destination is restored, or a newly
created destination removed, unless source bytes remain unchanged and independent
readback proves the exact visible text sequence. No typography, layout, links,
images, arbitrary Markdown, OCR, or professional-quality claim is made.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import pdf_pypdf
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_MARKDOWN_PDF_DIRECT_ADEQUACY_V1"
ROOT=Path(__file__).resolve().parents[2]
PRODUCER="document.convert.markdown_pdf.pandoc_weasyprint"
VERIFIER="pdf.extract.text.pypdf"
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
    r"^Convert (?P<markdown>"+_PATH+r"\.(?:md|markdown)) to "
    r"(?P<output>"+_PATH+r"\.pdf)\.?$",
    re.IGNORECASE,
)
_PLAIN_LINE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,;:?!/()+%=-]*$")
_HEADING=re.compile(r"^#{1,6}[ \t]+(?P<text>[A-Za-z0-9][A-Za-z0-9 .,;:?!/()+%=-]*)$")


def _base(status:str, passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "policy_adequacy_authority":False,
        "execution_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _inside(root:Path, rel:str)->Path:
    rr=root.resolve()
    p=(rr/rel).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _sha(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _visible_text(markdown_bytes:bytes)->str:
    if len(markdown_bytes)>16384:
        raise ValueError("MARKDOWN_SOURCE_TOO_LARGE_FOR_EXACT_FAMILY")
    try:
        text=markdown_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("MARKDOWN_SOURCE_MUST_BE_ASCII_FOR_EXACT_FAMILY") from exc
    if "\x00" in text or "\r" in text:
        raise ValueError("MARKDOWN_CONTROL_CHARACTER_UNSUPPORTED")
    chunks=[]
    for raw in text.split("\n"):
        line=raw.strip()
        if not line:
            continue
        heading=_HEADING.fullmatch(line)
        if heading is not None:
            chunks.append(heading.group("text"))
            continue
        if _PLAIN_LINE.fullmatch(line) is None:
            raise ValueError("MARKDOWN_LINE_OUTSIDE_PLAIN_SEMANTIC_SUBSET:"+line[:80])
        chunks.append(line)
    if not chunks:
        raise ValueError("MARKDOWN_VISIBLE_TEXT_REQUIRED")
    return " ".join(chunks)


def _norm(text:Any)->str:
    return " ".join(str(text or "").split())


def _verified_entry(registry:Mapping[str,Any], capability_id:str)->Mapping[str,Any]:
    entry=registry.get(capability_id)
    if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        raise ValueError("VERIFIED_BOUND_CAPABILITY_REQUIRED:"+capability_id)
    return entry


def preflight(request:Mapping[str,Any], *, repo_root:str|Path=ROOT)->dict[str,Any]:
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
    task_id=str(request.get("task_id") or "").strip()
    goal=str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    match=GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"),"matched":False}

    root=Path(repo_root).resolve()
    markdown_path=match.group("markdown")
    output_path=match.group("output")
    try:
        source=_inside(root,markdown_path)
        destination=_inside(root,output_path)
        if not source.is_file():
            raise ValueError("MARKDOWN_SOURCE_MISSING")
        if source==destination:
            raise ValueError("INPUT_OUTPUT_COLLISION")
        source_bytes=source.read_bytes()
        visible=_visible_text(source_bytes)

        registry=live_bound.load_verified_registry()
        producer=_verified_entry(registry,PRODUCER)
        verifier=_verified_entry(registry,VERIFIER)
        if str(producer.get("adapter_module") or "")!="pandoc_weasyprint":
            raise ValueError("MARKDOWN_PDF_PRODUCER_ADAPTER_MISMATCH")
        if str(verifier.get("adapter_module") or "")!="pdf_pypdf":
            raise ValueError("MARKDOWN_PDF_VERIFIER_ADAPTER_MISMATCH")
        verification=producer.get("verification")
        if (
            not isinstance(verification,Mapping)
            or verification.get("independent_verified") is not True
            or verification.get("independent_verifier_capability")!=VERIFIER
        ):
            raise ValueError("MARKDOWN_PDF_PRODUCER_INDEPENDENT_VERIFICATION_BINDING_MISSING")

        admissible=goal_compiler._platform_admissible_registry(dict(registry))
        compiled=goal_compiler.compile_goal(goal,admissible,root)
        if compiled.get("controller_actions") is not None:
            raise ValueError("COMPOUND_CONTROLLER_NOT_ALLOWED")
        if compiled.get("selected_capability")!=PRODUCER:
            raise ValueError("COMPILED_CAPABILITY_MISMATCH")
        inputs=compiled.get("inputs")
        if not isinstance(inputs,Mapping):
            raise ValueError("COMPILED_INPUTS_INVALID")
        if inputs.get("markdown_path")!=markdown_path or inputs.get("output_path")!=output_path:
            raise ValueError("COMPILED_PATH_BINDING_MISMATCH")
        targets=compiled.get("target_effects")
        if not isinstance(targets,list) or not targets:
            raise ValueError("COMPILED_TARGETS_INVALID")
        contract=compile_contract(goal,source_id="user",routing_target_effects=targets)
        if contract.get("pass") is not True:
            raise ValueError("LOSSLESS_RAW_CONTRACT_FAILED")

        return {
            **_base("DIRECT_MARKDOWN_PDF_ADEQUACY_ROUTE_MATCHED"),
            "matched":True,
            "task_id":task_id,
            "goal":goal,
            "goal_sha256":sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id":goal_scoped_policy_id(PRODUCER,goal),
            "capability_id":PRODUCER,
            "verifier_capability_id":VERIFIER,
            "markdown_path":markdown_path,
            "output_path":output_path,
            "source_sha256":sha256(source_bytes).hexdigest(),
            "visible_text":visible,
            "visible_text_sha256":sha256(visible.encode("utf-8")).hexdigest(),
            "raw_contract":contract,
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "acceptance_obligation_count":len(contract["acceptance_contract"]["obligations"]),
            "transaction_scope":"ONE_REPOSITORY_LOCAL_OUTPUT_FILE",
            "preflight_execution_authority":False,
            "destination_existed_before":destination.exists(),
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "reason":type(exc).__name__+":"+str(exc),
        }


def _independent_verify(pf:Mapping[str,Any], *, repo_root:str|Path)->Mapping[str,Any]:
    out=pdf_pypdf.run(
        {"path":pf["output_path"],"max_pages":200},
        repo_root,
    )
    extracted=_norm(out.get("text"))
    expected=_norm(pf["visible_text"])
    verified=(
        out.get("text_truncated") is False
        and int(out.get("pages_processed") or 0)>0
        and extracted==expected
    )
    return {
        "verified":verified,
        "producer_independent_verifier":True,
        "verifier_capability_id":VERIFIER,
        "expected_visible_text_sha256":pf["visible_text_sha256"],
        "observed_visible_text_sha256":sha256(extracted.encode("utf-8")).hexdigest(),
        "pages_processed":out.get("pages_processed"),
        "text_truncated":out.get("text_truncated"),
    }


def _restore(path:Path, existed:bool, prior:bytes|None)->None:
    if existed:
        assert prior is not None
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def run(
    request:Mapping[str,Any],
    *,
    repo_root:str|Path=ROOT,
    verifier_provider:Callable[[Mapping[str,Any]],Mapping[str,Any]]|None=None,
)->dict[str,Any]:
    pf=preflight(request,repo_root=repo_root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf

    root=Path(repo_root).resolve()
    source=_inside(root,str(pf["markdown_path"]))
    destination=_inside(root,str(pf["output_path"]))
    existed=destination.exists()
    prior=destination.read_bytes() if existed else None

    try:
        raw=live_bound.run_raw_goal(request)
        if not isinstance(raw,Mapping) or raw.get("pass") is not True:
            _restore(destination,existed,prior)
            return {
                **_base("OPEN__TRANSACTIONAL_MARKDOWN_PDF_EXECUTION_DID_NOT_VERIFY"),
                "matched":True,
                "policy_id":pf["policy_id"],
                "capability_id":PRODUCER,
                "transaction_rolled_back":True,
                "raw_result":deepcopy(dict(raw)) if isinstance(raw,Mapping) else raw,
            }
        if (
            raw.get("compiled_capability_id")!=PRODUCER
            or raw.get("raw_goal_sha256")!=pf["goal_sha256"]
            or raw.get("raw_source_coverage_complete") is not True
            or not destination.is_file()
            or _sha(source)!=pf["source_sha256"]
        ):
            _restore(destination,existed,prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched":True,
                "reason":"EXECUTION_IDENTITY_OUTPUT_OR_SOURCE_IMMUTABILITY_MISMATCH",
                "transaction_rolled_back":True,
            }

        evidence=(
            verifier_provider(pf)
            if verifier_provider is not None
            else _independent_verify(pf,repo_root=root)
        )
        if (
            not isinstance(evidence,Mapping)
            or evidence.get("verified") is not True
            or evidence.get("producer_independent_verifier") is not True
            or evidence.get("verifier_capability_id")!=VERIFIER
        ):
            _restore(destination,existed,prior)
            return {
                **_base("OPEN__INDEPENDENT_MARKDOWN_PDF_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched":True,
                "policy_id":pf["policy_id"],
                "capability_id":PRODUCER,
                "transaction_rolled_back":True,
                "independent_verification":deepcopy(dict(evidence))
                if isinstance(evidence,Mapping) else None,
            }

        obligations=pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids=[str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_MARKDOWN_PDF_POLICY_ADEQUACY_VERIFIED",True),
            "matched":True,
            "policy_id":pf["policy_id"],
            "capability_id":PRODUCER,
            "verifier_capability_id":VERIFIER,
            "goal_sha256":pf["goal_sha256"],
            "raw_task_contract_sha256":pf["raw_task_contract_sha256"],
            "markdown_path":pf["markdown_path"],
            "output_path":pf["output_path"],
            "source_sha256":pf["source_sha256"],
            "visible_text_sha256":pf["visible_text_sha256"],
            "accepted_raw_obligation_ids":accepted_ids,
            "raw_acceptance_obligation_count":len(accepted_ids),
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "policy_adequacy_authority":True,
            "transaction_committed":True,
            "transaction_rolled_back":False,
            "independent_verification":deepcopy(dict(evidence)),
            "raw_result":deepcopy(dict(raw)),
            "authority_boundary":(
                "ONLY_EXACT_REPOSITORY_LOCAL_PLAIN_SEMANTIC_MARKDOWN_TO_PDF_GRAMMAR;"
                "ASCII_HEADINGS_AND_PLAIN_PARAGRAPHS_ONLY;"
                "VERIFIED_PANDOC_WEASYPRINT_PRODUCER;"
                "PRODUCER_INDEPENDENT_PYPDF_TEXT_READBACK;"
                "SOURCE_BYTES_IMMUTABLE;"
                "NO_LAYOUT_TYPOGRAPHY_LINK_IMAGE_OCR_OR_PROFESSIONAL_QUALITY_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(destination,existed,prior)
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "policy_id":pf.get("policy_id"),
            "capability_id":PRODUCER,
            "reason":type(exc).__name__+":"+str(exc),
            "transaction_rolled_back":True,
        }
