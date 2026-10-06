from __future__ import annotations
import json

SCHEMA="PROJECT_BRAIN_H100_FINITE_BENCHMARK_COMPILER_LOOPHOLE_V1"

class CompilerLoopholeError(ValueError): pass

def compile_lookup(pairs):
    table={}
    for x,y in pairs:
        k=json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        if k in table and table[k]!=y:
            raise CompilerLoopholeError("NONFUNCTIONAL_BENCHMARK")
        table[k]=y
    if not table: raise CompilerLoopholeError("EMPTY_BENCHMARK")
    return table

def run_lookup(table,x):
    k=json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    if k not in table: raise CompilerLoopholeError("UNSEEN_INPUT")
    return table[k]

def benchmark_accuracy(pairs):
    table=compile_lookup(pairs)
    correct=sum(run_lookup(table,x)==y for x,y in pairs)
    return correct/len(pairs)

def canonical_code_bytes(pairs):
    table=compile_lookup(pairs)
    return len(json.dumps(table,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())

def certificate(pairs):
    acc=benchmark_accuracy(pairs)
    return {
        "schema":SCHEMA,
        "finite_benchmark_size":len(pairs),
        "benchmark_accuracy":acc,
        "persistent_learned_bytes":0,
        "capability_bearing_deterministic_code_bytes":canonical_code_bytes(pairs),
        "unseen_input_behavior":"FAIL_CLOSED",
        "deduction":[
            "FINITE_BENCHMARK_CAN_BE_PERFECTLY_MEMORIZED_IN_UNCHARGED_DETERMINISTIC_CODE",
            "ZERO_LEARNED_BYTES_ON_FINITE_TASKS_IS_NOT_SUFFICIENT_EVIDENCE_OF_GENERALIZATION",
            "FRESHNESS_SCOPE_COMPLETENESS_AND_DETERMINISTIC_CODE_ACCOUNTING_ARE_REQUIRED_FOR_METRIC_VALIDITY"
        ],
        "h100_terminal_credit_delta":0
    }
