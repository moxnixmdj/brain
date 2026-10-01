from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DIRECT=ROOT/"canonical/runtime/bound_capabilities/image_ocr_tesseract.py"
PDF=ROOT/"canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py"
STATE=ROOT/"canonical/astra_runtime/state/ASTRA-RUNTIME-BOUND-PDF-OCR-001.json"

EXPECTED_VERSION="5.3.4-1build5"
EXPECTED_ARCHIVE_SHA256="2dfac382d77215aee0c3de4a2a2205505d5f2195e72e79b54ad32154fc08da77"

def _command_tokens(path: Path):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    return ast.dump(tree,include_attributes=False)

def verify():
    state=json.loads(STATE.read_text(encoding="utf-8"))
    observed=state["history"][1]["result"]["trace"][0]["result"]
    attempts=observed["attempts"][0]["candidates"]
    successful={str(x["psm"]) for x in attempts if x["returncode"]==0}
    dep=observed["dependency"]["packages"][0]
    direct_text=_command_tokens(DIRECT)
    pdf_text=_command_tokens(PDF)
    required=("tesseract","stdout","--psm")
    command_equivalent=all(x in direct_text and x in pdf_text for x in required)
    dependency_match=(
        dep["name"]=="tesseract-ocr"
        and dep["version"]==EXPECTED_VERSION
        and dep["archive_sha256"]==EXPECTED_ARCHIVE_SHA256
    )
    passed=command_equivalent and dependency_match and {"6","7","11","3"} <= successful
    return {
        "schema":"PROJECT_BRAIN_IMAGE_OCR_TESSERACT_DEDUCTIVE_REUSE_VERIFICATION_V1",
        "pass":passed,
        "command_equivalent_to_observed_inner_route":command_equivalent,
        "dependency_match":dependency_match,
        "observed_successful_psm":sorted(successful),
        "new_reality_units_consumed":0,
        "terminal_semantic_authority":False,
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
