"""Unsigned claim dictionaries cannot mint independent-verification records."""
import json

import pytest

from canonical.runtime import capability_receipt_lane_v1 as lane
from execution_guard.oidc_claim_authenticity_probe_v1 import REFERENCES


@pytest.mark.parametrize("reference", list(REFERENCES.values()), ids=list(REFERENCES))
def test_unsigned_claims_do_not_reexecute_a_real_module_or_issue_a_record(tmp_path, reference):
    module = tmp_path / "canonical/runtime/bound_capabilities/probe.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "from pathlib import Path\n"
        "def run(args, root):\n"
        "    (Path(root) / 'executed_again').write_text('yes')\n"
        "    return {'status': 'OK'}\n"
    )
    (tmp_path / lane.RECEIPT_DIR).mkdir(parents=True)
    module_path = "canonical/runtime/bound_capabilities/probe.py"
    receipt = lane.execute_and_receipt("probe.v1", module_path, "run", str(tmp_path), "producer")
    path = lane.receipt_path_for("probe.v1")
    (tmp_path / path).write_text(json.dumps(receipt))
    marker = tmp_path / "executed_again"
    assert marker.is_file()  # the producer really executed the fixture
    marker.unlink()

    result = lane.verify_producer_receipts(str(tmp_path), "claimed-verifier", reference)
    assert result["producer_receipts"] == 1
    assert result["reproduced"] == 0
    assert result["execution_skipped"] is True
    assert result["run_reference_claim_shape_valid"] is True
    assert result["run_reference_attested"] is False
    assert result["records_written"] == 0
    assert not marker.exists()  # receipt-specified code did not run again
    assert not (tmp_path / lane.verification_path_for(path)).exists()
