"""Exercise the real receipt executor: input bytes must precede adapter side effects."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402

CAPABILITY = "test.receipt.input_lifecycle"
BEFORE = b"the input before execution\n"


def _execute(tmp_path: Path, body: str, *, declared: bool = True):
    source = tmp_path / "source.txt"
    source.write_bytes(BEFORE)
    module = tmp_path / "adapter.py"
    module.write_text("from pathlib import Path\n\ndef run(args, root):\n" + body)
    registry = tmp_path / lane.BOUND
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({"capabilities": {CAPABILITY: {
        "action_template": {"args": {
            "input_path": "source.txt", "output_path": "new-output.txt"
        }}
    }}} if declared else {"capabilities": {}}))
    return lane.execute_and_receipt(CAPABILITY, "adapter.py", "run", str(tmp_path),
                                    "local-test-producer")


def _stored(tmp_path: Path, receipt: dict) -> bytes:
    digest = receipt["input_digests"]["input_path"]
    blob = (tmp_path / lane.INSTANCE_STORE / (digest + ".bin")).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == digest
    return blob


@pytest.mark.parametrize("effect", ["overwrite", "delete", "unchanged"])
def test_receipt_keeps_pre_execution_input_despite_action_effect(tmp_path, effect):
    mutate = {
        "overwrite": "p.write_bytes(b'changed by action')",
        "delete": "p.unlink()",
        "unchanged": "pass",
    }[effect]
    receipt = _execute(tmp_path,
        "    if not args: raise ValueError('input required')\n"
        "    p = Path(root) / args['input_path']\n"
        "    consumed = p.read_text()\n"
        f"    {mutate}\n"
        "    (Path(root) / args['output_path']).write_text('created output')\n"
        "    return {'status': 'OK', 'consumed': consumed}\n")
    assert receipt is not None
    assert receipt["outcome"] == "EXECUTED"
    assert _stored(tmp_path, receipt) == BEFORE
    assert receipt["input_digests"] == {"input_path": hashlib.sha256(BEFORE).hexdigest()}
    assert receipt["result_sha256"] == lane.sha256_canonical(
        {"status": "OK", "consumed": BEFORE.decode()})
    assert receipt["invoked_args"] == {"input_path": "source.txt", "output_path": "new-output.txt"}
    assert receipt["independent_verifier"] is None
    if effect == "delete":
        assert not (tmp_path / "source.txt").exists()
    elif effect == "overwrite":
        assert (tmp_path / "source.txt").read_bytes() == b"changed by action"


def test_new_output_is_not_mislabeled_as_an_input(tmp_path):
    receipt = _execute(tmp_path,
        "    if not args: raise ValueError('input required')\n"
        "    (Path(root) / args['output_path']).write_text('output only')\n"
        "    return {'status': 'OK'}\n")
    assert (tmp_path / "new-output.txt").exists()
    assert set(receipt["input_digests"]) == {"input_path"}
    assert _stored(tmp_path, receipt) == BEFORE


def test_empty_argument_success_retains_old_receipt_shape(tmp_path):
    receipt = _execute(tmp_path, "    return {'status': 'OK'}\n", declared=False)
    assert receipt["invoked_args"] == {}
    assert "input_digests" not in receipt
    assert not (tmp_path / lane.INSTANCE_STORE).exists()


def test_failed_execution_does_not_issue_a_receipt(tmp_path):
    receipt = _execute(tmp_path,
        "    if not args: raise ValueError('input required')\n"
        "    (Path(root) / args['input_path']).unlink()\n"
        "    raise ValueError('execution failed')\n")
    assert receipt is None
    digest = hashlib.sha256(BEFORE).hexdigest()
    assert (tmp_path / lane.INSTANCE_STORE / (digest + ".bin")).read_bytes() == BEFORE


def test_snapshot_describes_declared_call_not_prior_failed_empty_attempt(tmp_path):
    receipt = _execute(tmp_path,
        "    if not args:\n"
        "        (Path(root) / 'source.txt').write_bytes(b'changed by failed probe')\n"
        "        raise ValueError('input required')\n"
        "    consumed = (Path(root) / args['input_path']).read_text()\n"
        "    (Path(root) / args['input_path']).unlink()\n"
        "    return {'status': 'OK', 'consumed': consumed}\n")
    assert _stored(tmp_path, receipt) == b"changed by failed probe"
    assert receipt["result_sha256"] == lane.sha256_canonical(
        {"status": "OK", "consumed": "changed by failed probe"})
