import json
import pathlib
import shutil
import tempfile

from canonical.runtime.p3_bound_binary_db_admission_soundness_v1 import (
    TOP_LAW_PATH,
    MEMBERSHIP_PATH,
    POLICY_PATH,
    MEMBERSHIP_VERIFY_PATH,
    POLICY_VERIFY_PATH,
    evaluate,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILES = [
    TOP_LAW_PATH,
    MEMBERSHIP_PATH,
    POLICY_PATH,
    MEMBERSHIP_VERIFY_PATH,
    POLICY_VERIFY_PATH,
]


def copied_root():
    td = tempfile.TemporaryDirectory()
    root = pathlib.Path(td.name)
    for rel in FILES:
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return td, root


def test_current_exact_bytes_pass():
    out = evaluate(repo_root=ROOT)
    assert out["pass"] is True, out
    assert out["admission_implies_route_adequacy"] is True
    assert out["db_admission_authorized"] is True
    assert out["u_empty_authorized"] is False
    assert out["terminal_credit_delta"] == 0


def test_top_law_byte_drift_fails_closed():
    td, root = copied_root()
    try:
        p = root / TOP_LAW_PATH
        p.write_bytes(p.read_bytes() + b"\n")
        out = evaluate(repo_root=root)
        assert out["pass"] is False
        assert out["reason"] == "CONTENT_BINDING_INVALID"
    finally:
        td.cleanup()


def test_membership_runtime_byte_drift_fails_closed():
    td, root = copied_root()
    try:
        p = root / MEMBERSHIP_PATH
        p.write_bytes(p.read_bytes() + b"# drift\n")
        out = evaluate(repo_root=root)
        assert out["reason"] == "CONTENT_BINDING_INVALID"
    finally:
        td.cleanup()


def test_membership_verification_byte_drift_fails_closed():
    td, root = copied_root()
    try:
        p = root / MEMBERSHIP_VERIFY_PATH
        doc = json.loads(p.read_text())
        doc["status"] = "PASS_FAKE"
        p.write_text(json.dumps(doc, sort_keys=True))
        out = evaluate(repo_root=root)
        assert out["reason"] == "CONTENT_BINDING_INVALID"
    finally:
        td.cleanup()


def test_policy_runtime_byte_drift_fails_closed():
    td, root = copied_root()
    try:
        p = root / POLICY_PATH
        p.write_bytes(p.read_bytes() + b"# drift\n")
        out = evaluate(repo_root=root)
        assert out["reason"] == "CONTENT_BINDING_INVALID"
    finally:
        td.cleanup()


def test_policy_verification_byte_drift_fails_closed():
    td, root = copied_root()
    try:
        p = root / POLICY_VERIFY_PATH
        p.write_bytes(p.read_bytes() + b"\n")
        out = evaluate(repo_root=root)
        assert out["reason"] == "CONTENT_BINDING_INVALID"
    finally:
        td.cleanup()
