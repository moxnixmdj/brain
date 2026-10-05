"""H100 UniChart storage-feasibility arithmetic.

This is a storage-only, zero-credit candidate. It proves a conditional byte bound:
if the released checkpoint's persistent learned tensors are FP32 as advertised
by the published config, then an all-W3 packed representation with frozen
group-256 FP16 scale+zero metadata plus the complete observed ancillary bundle
fits below the 100,000,000-byte H100 persistent learned-state ceiling.

It does NOT prove capability preservation, exact state-dict tensor count,
Chartography performance, or terminal/H100 acceptance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

H100_BUDGET_BYTES = 100_000_000
CHECKPOINT_BYTES = 809_199_995
BITS_PER_SOURCE_WEIGHT = 32
TARGET_BITS_PER_WEIGHT = 3
GROUP_SIZE = 256
METADATA_BYTES_PER_GROUP = 4  # FP16 scale + FP16 zero-point
ANCILLARY_BYTES = 5_317_996

@dataclass(frozen=True)
class Bound:
    checkpoint_bytes: int
    max_fp32_values_from_file_size: int
    packed_weight_bytes: int
    quant_metadata_bytes: int
    ancillary_bytes: int
    total_bytes: int
    margin_bytes: int


def compute_bound() -> Bound:
    # File bytes include serialization overhead, so floor(file_bytes/4) is an
    # upper bound on the number of FP32 values only under the explicit
    # all-learned-tensors-FP32 premise.
    max_values = CHECKPOINT_BYTES // 4
    packed = math.ceil(max_values * TARGET_BITS_PER_WEIGHT / 8)
    groups = math.ceil(max_values / GROUP_SIZE)
    metadata = groups * METADATA_BYTES_PER_GROUP
    total = packed + metadata + ANCILLARY_BYTES
    return Bound(
        checkpoint_bytes=CHECKPOINT_BYTES,
        max_fp32_values_from_file_size=max_values,
        packed_weight_bytes=packed,
        quant_metadata_bytes=metadata,
        ancillary_bytes=ANCILLARY_BYTES,
        total_bytes=total,
        margin_bytes=H100_BUDGET_BYTES-total,
    )


def audit() -> dict:
    b=compute_bound()
    return {
        "schema":"PROJECT_BRAIN_H100_UNICHART_STORAGE_FEASIBILITY_OUTPUT_V1",
        "status":"CONDITIONAL_STORAGE_FEASIBILITY_PASS" if b.total_bytes <= H100_BUDGET_BYTES else "STORAGE_FEASIBILITY_FAIL",
        "premise":"ALL_PERSISTENT_LEARNED_CHECKPOINT_TENSORS_COUNTED_BY_THIS_BOUND_ARE_FP32_AS_ADVERTISED__EXACT_STATE_DICT_ENUMERATION_STILL_REQUIRED",
        "h100_budget_bytes":H100_BUDGET_BYTES,
        "checkpoint_bytes":b.checkpoint_bytes,
        "max_fp32_values_from_file_size":b.max_fp32_values_from_file_size,
        "target_bits_per_weight":TARGET_BITS_PER_WEIGHT,
        "group_size":GROUP_SIZE,
        "metadata_bytes_per_group":METADATA_BYTES_PER_GROUP,
        "packed_weight_bytes":b.packed_weight_bytes,
        "quant_metadata_bytes":b.quant_metadata_bytes,
        "ancillary_bytes":b.ancillary_bytes,
        "total_candidate_bytes":b.total_bytes,
        "margin_bytes":b.margin_bytes,
        "hard_nonclaims":[
            "NO_CLAIM_EXACT_STATE_DICT_PARAMETER_COUNT",
            "NO_CLAIM_W3_PRESERVES_UNICHART_CAPABILITY",
            "NO_CLAIM_CHARTOGRAPHY_GE_89",
            "NO_H100_TERMINAL_CREDIT",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "h100_credit_delta":0,
    }


if __name__=="__main__":
    import json
    print(json.dumps(audit(),indent=2,sort_keys=True))
