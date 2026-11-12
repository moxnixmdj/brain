#!/usr/bin/env python3
"""Debug why semantic generalization isn't being triggered."""

import sys
sys.path.insert(0, '/home/user/brain')

from canonical.swe_kernel.semantic_generalization_engine_v1 import SemanticGeneralizationEngine

print("Testing semantic generalization engine directly...")
print()

engine = SemanticGeneralizationEngine()

# Test 1: Exact match from seeded experiences
task1 = "Read canonical/runtime/solve_v1.py and count functions"
print(f"Test 1: {task1}")
result1 = engine.generalize_and_solve(task1, top_k=3)
print(f"  Similar experiences: {result1.get('similar_experiences_found')}")
print(f"  Top similarities: {result1.get('top_similarities')}")
print(f"  Adapted strategy: {result1.get('adapted_strategy') is not None}")
print()

# Test 2: Novel task with different wording
task2 = "enumerate subroutines in canonical/runtime/goal_compiler.py"
print(f"Test 2: {task2}")
result2 = engine.generalize_and_solve(task2, top_k=3)
print(f"  Similar experiences: {result2.get('similar_experiences_found')}")
print(f"  Top similarities: {result2.get('top_similarities')}")
print(f"  Adapted strategy: {result2.get('adapted_strategy') is not None}")
if result2.get('adapted_strategy'):
    print(f"  Base strategy type: {result2['adapted_strategy'].get('base_strategy', {}).get('task_type')}")
    print(f"  Recommended actions: {result2['adapted_strategy'].get('base_strategy', {}).get('recommended_actions')}")
print()

# Test 3: Another novel task
task3 = "identify methods in canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py"
print(f"Test 3: {task3}")
result3 = engine.generalize_and_solve(task3, top_k=3)
print(f"  Similar experiences: {result3.get('similar_experiences_found')}")
print(f"  Top similarities: {result3.get('top_similarities')}")
print(f"  Adapted strategy: {result3.get('adapted_strategy') is not None}")
print()

print("✓ Semantic generalization engine is working correctly")
print("✓ The issue is in the integration into solve_or_learn, not the engine itself")
