from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_subordinate_live_runtime_routes_reached_state_through_construction_audit():
    text = _text("canonical/runtime/live_brain_runtime_v1.py")
    assert "REACHED_ESCAPE_STATE_CONSTRUCTION_AUDIT_V1" in text
    assert "from canonical.runtime.reached_escape_state_construction_audit_v1 import audit" in text
    helper = text.split("def _reached_escape_state", 1)[1].split("def _causal_synthesize", 1)[0]
    assert "return audit(payload)" in helper
    assert "reached_escape_state_kernel_v1" not in helper


def test_canonical_unified_fabric_routes_reached_state_through_construction_audit():
    text = _text("canonical/runtime/unified_cognitive_fabric_v1.py")
    assert '"REACHED_ESCAPE_STATE": "reached_escape_state_construction_audit_v1.audit"' in text
    handler = text.split('elif mode == "REACHED_ESCAPE_STATE":', 1)[1].split(
        'elif mode == "CERTIFIED_ROUTE":', 1
    )[0]
    assert "reached_escape_state_construction_audit_v1" in handler
    assert "out = reached_escape_state.audit(payload)" in handler
    assert "reached_escape_state_kernel_v1" not in handler
