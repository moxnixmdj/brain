from canonical.runtime.smaug_mini_delta_header_probe_v1 import (
    TensorMeta,
    candidate_lora_factor_bytes,
    compare_geometry,
    declared_unchanged_surface,
)


def tm(name, shape, nbytes, shard="s.safetensors", dtype="BF16"):
    return TensorMeta(name=name, shard=shard, dtype=dtype, shape=tuple(shape), nbytes=nbytes)


def test_factor_storage_formula():
    assert candidate_lora_factor_bytes([10, 20], rank=4, bytes_per_factor=2) == 240
    assert candidate_lora_factor_bytes([10], rank=4, bytes_per_factor=2) is None


def test_public_unchanged_surface_classifier():
    assert declared_unchanged_surface("model.visual.blocks.0.attn.qkv.weight")
    assert declared_unchanged_surface("mtp.fc.weight")
    assert declared_unchanged_surface("model.language_model.layers.0.mlp.up_proj.weight") is None


def test_geometry_fails_closed_on_name_mismatch():
    out = compare_geometry({"a": tm("a", [2, 2], 8)}, {"b": tm("b", [2, 2], 8)})
    assert out["status"] == "FAIL_CLOSED"


def test_geometry_reports_rank_bound_without_claiming_exact_delta():
    base = {
        "model.visual.x.weight": tm("model.visual.x.weight", [2, 2], 8),
        "model.language_model.layers.0.mlp.up_proj.weight": tm(
            "model.language_model.layers.0.mlp.up_proj.weight", [4, 6], 48
        ),
        "model.language_model.layers.0.input_layernorm.weight": tm(
            "model.language_model.layers.0.input_layernorm.weight", [4], 8
        ),
    }
    tuned = dict(base)
    out = compare_geometry(base, tuned, ranks=(2,))
    assert out["status"] == "PASS_GEOMETRY_ONLY"
    assert out["full_tensor_bytes_from_headers"] == 64
    assert out["declared_unchanged_bytes"] == 8
    assert out["delta_candidate_bytes"] == 56
    assert out["candidate_2d_matrix_count"] == 1
    assert out["rank_storage_bounds"]["2"]["bf16_factor_bytes_if_every_2d_delta_candidate_rank_le_r"] == 40
    assert "NOT_EXACT" in out["rank_storage_bounds"]["2"]["hard_nonclaim"]
