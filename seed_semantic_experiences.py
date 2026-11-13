#!/usr/bin/env python3
"""
Seed the semantic generalization engine with initial experiences.
This gives the system examples to generalize from.
"""

import sys
sys.path.insert(0, '/home/user/brain')

from canonical.swe_kernel.semantic_generalization_engine_v1 import SemanticGeneralizationEngine

def seed_experiences():
    engine = SemanticGeneralizationEngine()
    
    # Seed with information retrieval tasks
    experiences = [
        {
            "task": "Read canonical/runtime/solve_v1.py and count functions",
            "trajectory": [
                {"action": "read file canonical/runtime/solve_v1.py"},
                {"action": "parse file with ast.parse()"},
                {"action": "traverse all FunctionDef nodes"},
                {"action": "count and return result"}
            ],
            "outcome": "success",
            "strategy": {
                "type": "success_heuristic",
                "task_type": "information_retrieval",
                "trigger_conditions": ["task_type:information_retrieval", "patterns:file_read,ast_parse"],
                "recommended_actions": ["read file", "parse with ast", "traverse nodes", "count"]
            }
        },
        {
            "task": "Find classes in canonical/runtime/brain_unified_model_v1.py",
            "trajectory": [
                {"action": "read file canonical/runtime/brain_unified_model_v1.py"},
                {"action": "parse file with ast.parse()"},
                {"action": "traverse all ClassDef nodes"},
                {"action": "count and return result"}
            ],
            "outcome": "success",
            "strategy": {
                "type": "success_heuristic",
                "task_type": "information_retrieval",
                "trigger_conditions": ["task_type:information_retrieval", "patterns:file_read,ast_parse"],
                "recommended_actions": ["read file", "parse with ast", "traverse nodes", "count"]
            }
        },
        {
            "task": "List methods in canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py",
            "trajectory": [
                {"action": "read file canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py"},
                {"action": "parse file with ast.parse()"},
                {"action": "traverse all FunctionDef nodes inside ClassDef"},
                {"action": "count and return result"}
            ],
            "outcome": "success",
            "strategy": {
                "type": "success_heuristic",
                "task_type": "information_retrieval",
                "trigger_conditions": ["task_type:information_retrieval", "patterns:file_read,ast_parse"],
                "recommended_actions": ["read file", "parse with ast", "traverse nested nodes", "count"]
            }
        }
    ]
    
    for exp in experiences:
        stored = engine.store_experience(
            task_description=exp["task"],
            trajectory=exp["trajectory"],
            outcome=exp["outcome"],
            strategy=exp["strategy"]
        )
        print(f"✓ Stored: {exp['task']}")
    
    print(f"\n✓ Seeded {len(experiences)} experiences for semantic generalization")
    return len(experiences)

if __name__ == "__main__":
    count = seed_experiences()
    sys.exit(0)
