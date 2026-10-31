"""Static scope checks, not a claim that the runner isolates untrusted code."""
from pathlib import Path
import re

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/capability-receipt-verification.yml"


def test_app_secrets_are_only_mapped_to_the_landing_step():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert not re.search(r"^env:\s*$", text, re.MULTILINE)
    before, landing = text.split("      - name: Land the verification records", 1)
    for name in ("AUTOMATION_APP_ID", "AUTOMATION_APP_PRIVATE_KEY"):
        assert not re.search(r"^\s*" + name + r":", before, re.MULTILINE)
        assert re.search(r"^\s*" + name + r":\s*\$\{\{\s*secrets\." + name, landing, re.MULTILINE)


def test_checkout_does_not_persist_credentials_and_github_token_is_read_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^  contents: read\s*$", text, re.MULTILINE)
    checkout = text.split("      - uses: actions/checkout@v4", 1)[1].split("      - ", 1)[0]
    assert re.search(r"^\s*persist-credentials: false\s*$", checkout, re.MULTILINE)


def test_oidc_token_response_is_unset_before_receipt_code_runs():
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("      - name: Re-execute producer receipts as an independent identity", 1)[1]
    token_clear = step.index("unset TOKEN_JSON")
    verifier = step.index("python3 canonical/runtime/capability_receipt_lane_v1.py")
    assert token_clear < verifier


def test_workflow_refuses_unauthenticated_reference_before_running_receipts():
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("      - name: Re-execute producer receipts as an independent identity", 1)[1]
    preflight = step.index("if not run_reference_is_attested(reference):")
    refusal = step.index("raise SystemExit", preflight)
    verifier = step.index("python3 canonical/runtime/capability_receipt_lane_v1.py")
    assert preflight < refusal < verifier
    artifact = text.split("      - name: Publish the verification records as an artifact", 1)[1].split("      - name: Land", 1)[0]
    assert "if: always()" not in artifact
