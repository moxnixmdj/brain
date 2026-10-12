from canonical.runtime.bound_capability_problem_compiler_v1 import ROOT, REGISTRY_PATH, _git_blob, compile_problem
from canonical.runtime.capability_planner import plan_actions


def valid_spec():
    return {
        "initial_facts": [],
        "target_effects": ["image.ready"],
        "capability_instances": [{
            "instance_id": "make-image",
            "capability_id": "auto.apt.zint",
            "inputs": {
                "output_path": "canonical/astra_runtime/tmp/UVAS_QR.png",
                "text": "hello",
            },
            "provides_as": {
                "auto.effect.zint": "image.ready",
            },
        }],
        "finish_summary": "BOUND_EXECUTION_COMPLETE",
    }


def test_verified_registry_instance_compiles_to_explicit_problem():
    out = compile_problem(valid_spec())
    assert out["pass"] is True, out
    cap = out["problem"]["capabilities"][0]
    assert cap["source_capability_id"] == "auto.apt.zint"
    assert cap["provides"] == ["image.ready"]
    assert cap["action"]["type"] == "invoke_capability"
    assert "hello" in cap["action"]["args"]["argv"]
    assert out["manual_capability_action_injection_permitted"] is False


def test_compiled_problem_is_directly_plannable():
    out = compile_problem(valid_spec())
    planned = plan_actions(out["problem"])
    assert planned["planning"]["plan"] == ["make-image"]
    assert planned["actions"][0]["capability_id"] == "make-image"


def test_unknown_capability_fails_closed():
    x = valid_spec()
    x["capability_instances"][0]["capability_id"] = "not.real"
    out = compile_problem(x)
    assert out["pass"] is False
    assert any("SOURCE_CAPABILITY_NOT_VERIFIED:not.real" in e for e in out["errors"])


def test_missing_template_input_fails_closed():
    x = valid_spec()
    del x["capability_instances"][0]["inputs"]["text"]
    out = compile_problem(x)
    assert out["pass"] is False
    assert any("BOUND_CAPABILITY_INPUT_MISSING:text" in e for e in out["errors"])


def test_alias_source_must_exist_in_registry_contract():
    x = valid_spec()
    x["capability_instances"][0]["provides_as"] = {
        "invented.effect": "image.ready",
    }
    out = compile_problem(x)
    assert out["pass"] is False
    assert any("SOURCE_UNKNOWN:invented.effect" in e for e in out["errors"])


def test_manual_capability_injection_is_not_an_input_surface():
    x = valid_spec()
    x["capabilities"] = [{
        "id": "fake",
        "requires": [],
        "provides": ["image.ready"],
        "action": {"type": "shell"},
    }]
    out = compile_problem(x)
    assert out["pass"] is False
    assert any("SPEC_FIELDS_UNSUPPORTED:capabilities" in e for e in out["errors"])


def test_compiler_binds_exact_registry_bytes_from_current_commit():
    out = compile_problem(valid_spec())
    assert out["pass"] is True, out
    raw = (ROOT / REGISTRY_PATH).read_bytes()
    assert out["registry_git_blob_sha"] == _git_blob(raw)
