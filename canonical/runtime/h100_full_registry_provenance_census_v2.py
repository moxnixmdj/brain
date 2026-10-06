"""Chronology-resolved successor to the H100 Registry provenance census."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_H100_FULL_REGISTRY_PROVENANCE_CENSUS_V2"
BASE=ROOT/"canonical/verification/H100_FULL_REGISTRY_PROVENANCE_CENSUS_SECOND_CARRIER_VERIFICATION_20261006_V1.json"
CHRON=ROOT/"canonical/verification/H100_REGISTRY_PROVENANCE_CHRONOLOGY_20261006_V1.json"

STRICT="STRICT_OUTCOME_SELECTED"
POST="DEVELOPMENT_CONDITIONED_POSTOUTCOME_IMPLEMENTATION"
PRE="DEVELOPMENT_CONDITIONED_PREOUTCOME_FIXED"
EXT="EXTERNAL_CAPABILITY_DEFINITION_PREOUTCOME_FIXED"

class CensusV2Error(ValueError): pass

def _j(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text())
    if not isinstance(x,dict): raise CensusV2Error("JSON_OBJECT_REQUIRED")
    return x

def run()->dict[str,Any]:
    base=_j(BASE); chron=_j(CHRON)
    if base["observed"]["registry_record_count"]!=21:
        raise CensusV2Error("BASE_RECORD_COUNT_CHANGED")
    cons=chron["consequence"]
    post=set(cons["v1_postoutcome_entries"])
    pre=set(cons["v1_preoutcome_fixed_entries"])
    if len(post)!=4 or len(pre)!=3 or post & pre:
        raise CensusV2Error("CHRONOLOGY_PARTITION_INVALID")
    # V2+ counts from verified V1 full census.
    base_counts=base["observed"]["category_counts"]
    if base_counts["STRICT_OUTCOME_SELECTED"]!=9 or base_counts["EXTERNAL_CAPABILITY_DEFINITION_PREOUTCOME_FIXED"]!=5:
        raise CensusV2Error("BASE_V2PLUS_COUNTS_CHANGED")
    src_bytes=int(chron["source_size_upper_bounds"]["aggregate_postoutcome_runtime_utf8_bytes"])
    strict_bits=int(base["observed"]["strict_selection_code"]["aggregate_bits"])
    bits=src_bytes*8+strict_bits
    return {
      "schema":SCHEMA,
      "status":"PASS__CHRONOLOGY_RESOLVED_21_RECORD_PROVENANCE_CENSUS__ZERO_UNRESOLVED__KNOWN_OUTCOME_DEPENDENT_REPRESENTATION_CEILING_15203_BYTES",
      "record_count":21,
      "category_counts":{
        STRICT:9,
        POST:4,
        PRE:3,
        EXT:5,
        "PROVENANCE_UNRESOLVED":0,
      },
      "postoutcome_v1_entries":sorted(post),
      "preoutcome_fixed_v1_entries":sorted(pre),
      "known_outcome_dependent_representation_ceiling":{
        "strict_selection_index_bits":strict_bits,
        "postoutcome_implementation_source_bytes":src_bytes,
        "aggregate_bits":bits,
        "ceil_bytes":(bits+7)//8,
      },
      "interpretation":[
        "THIS_IS_A_CONSERVATIVE_CODE_LENGTH_CEILING_FOR_KNOWN_OUTCOME_DEPENDENT_PERSISTED_REPRESENTATIONS",
        "IT_IS_NOT_MINIMUM_NECESSARY_PERSISTENT_STATE",
        "IT_IS_NOT_MUTUAL_INFORMATION",
        "PREOUTCOME_FIXED_AND_EXTERNAL_CAPABILITY_DEFINITIONS_ARE_ACCOUNTED_SEPARATELY",
      ],
      "h100_terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
