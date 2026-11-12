"""Experiential Strategy Extraction — converts trajectories into generalizable heuristics.

Based on 2026 state-of-the-art (ERL, ReasoningBank, Counterfactual Distillation):
  - ERL (ICLR 2026 MemAgents): Distills trajectories into reusable heuristics
  - ReasoningBank (Google, ICLR 2026): Extracts strategic guardrails from success AND failure
  - Counterfactual Distillation: Learns from what went wrong at decision points

This module adds the missing generalization layer to solve_or_learn:
  - Exact recall: "Task X → Actions Y" (works for exact matches)
  - Strategy recall: "Tasks LIKE X → Strategy Y" (works for similar tasks)

The key insight from 2026 research: heuristics generalize (+5.5% Execution, +23.8% Search)
while raw trajectories don't. This converts specific solutions into transferable principles.

Usage:
  extractor = ExperientialStrategyExtractor()
  heuristic = extractor.extract_from_trajectory(trajectory, outcome)
  strategies = extractor.retrieve_similar_strategies(novel_task_description)
"""
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from typing import Any, Mapping
from datetime import datetime, timezone

SCHEMA = "BRAIN_EXPERIENTIAL_STRATEGY_EXTRACTOR_V1"

class ExperientialStrategyExtractor:
    """Extracts generalizable strategies from specific task trajectories.
    
    Converts the repo's instant learning system from exact-recall to strategy-recall,
    enabling generalization to novel but similar tasks.
    """
    
    def __init__(self, strategies_path: Path | None = None):
        self.strategies_path = strategies_path or (
            Path(__file__).parent.parent / "astra_runtime" / "strategies" / "EXTRACTED_STRATEGIES_V1.json"
        )
        self.strategies = self._load_strategies()
    
    def _load_strategies(self) -> dict[str, Any]:
        """Load existing extracted strategies."""
        if self.strategies_path.exists():
            with open(self.strategies_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "schema": SCHEMA,
            "strategies": [],
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "description": "Generalizable strategies extracted from task trajectories"
            }
        }
    
    def _save_strategies(self) -> None:
        """Persist extracted strategies."""
        self.strategies_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.strategies_path, "w", encoding="utf-8") as f:
            json.dump(self.strategies, f, indent=2, ensure_ascii=False)
    
    def extract_from_trajectory(
        self,
        task_description: str,
        trajectory: list[dict[str, Any]],
        outcome: str,
        error_if_failed: str | None = None
    ) -> dict[str, Any]:
        """Extract a generalizable heuristic from a specific task trajectory.
        
        Based on ERL/ReasoningBank: converts specific actions into transferable principles.
        
        Args:
            task_description: What the task was trying to accomplish
            trajectory: List of {action, observation, timestamp} dicts
            outcome: "success" or "failure"
            error_if_failed: Error message if outcome was failure
            
        Returns:
            Extracted heuristic with trigger conditions and recommended actions
        """
        # Extract task type and key patterns
        task_type = self._classify_task_type(task_description)
        key_patterns = self._extract_key_patterns(trajectory)
        
        # Generate heuristic based on outcome
        if outcome == "success":
            heuristic = self._extract_success_heuristic(
                task_description, task_type, key_patterns, trajectory
            )
        else:
            heuristic = self._extract_failure_heuristic(
                task_description, task_type, key_patterns, error_if_failed or "unknown error"
            )
        
        # Add to strategies and persist
        strategy_id = self._compute_strategy_id(heuristic)
        heuristic["id"] = strategy_id
        heuristic["extracted_at"] = datetime.now(timezone.utc).isoformat()
        
        self.strategies["strategies"].append(heuristic)
        self._save_strategies()
        
        return heuristic
    
    def _classify_task_type(self, task_description: str) -> str:
        """Classify task into broad category for heuristic extraction."""
        desc_lower = task_description.lower()
        
        if any(kw in desc_lower for kw in ["read", "count", "find", "search"]):
            return "information_retrieval"
        elif any(kw in desc_lower for kw in ["create", "write", "add", "implement"]):
            return "creation"
        elif any(kw in desc_lower for kw in ["fix", "repair", "debug", "resolve"]):
            return "repair"
        elif any(kw in desc_lower for kw in ["test", "verify", "check"]):
            return "verification"
        else:
            return "general"
    
    def _extract_key_patterns(self, trajectory: list[dict[str, Any]]) -> list[str]:
        """Extract key action patterns from trajectory."""
        patterns = []
        for step in trajectory:
            action = step.get("action", "")
            # Extract file operations
            if "read" in action.lower() or "open" in action.lower():
                patterns.append("file_read")
            elif "write" in action.lower() or "create" in action.lower():
                patterns.append("file_write")
            elif "search" in action.lower() or "find" in action.lower():
                patterns.append("pattern_search")
            elif "execute" in action.lower() or "run" in action.lower():
                patterns.append("execution")
        return list(set(patterns))  # deduplicate
    
    def _extract_success_heuristic(
        self,
        task_description: str,
        task_type: str,
        key_patterns: list[str],
        trajectory: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract a positive heuristic from a successful trajectory."""
        # Extract trigger conditions (when to apply this strategy)
        trigger_conditions = [
            f"task_type:{task_type}",
            f"patterns:{','.join(key_patterns)}"
        ]
        
        # Extract recommended actions (what to do)
        recommended_actions = []
        for i, step in enumerate(trajectory[:5]):  # Limit to first 5 steps
            action = step.get("action", "")
            if action:
                recommended_actions.append(f"Step {i+1}: {action[:100]}")
        
        return {
            "type": "success_heuristic",
            "task_type": task_type,
            "trigger_conditions": trigger_conditions,
            "recommended_actions": recommended_actions,
            "rationale": f"Successfully applied to {task_description[:100]}",
            "confidence": 0.8,  # High confidence for success
            "outcome": "success"
        }
    
    def _extract_failure_heuristic(
        self,
        task_description: str,
        task_type: str,
        key_patterns: list[str],
        error_message: str
    ) -> dict[str, Any]:
        """Extract a failure heuristic (what NOT to do) from a failed trajectory."""
        # Extract negative trigger conditions (when to AVOID this pattern)
        trigger_conditions = [
            f"task_type:{task_type}",
            f"patterns:{','.join(key_patterns)}"
        ]
        
        return {
            "type": "failure_heuristic",
            "task_type": task_type,
            "trigger_conditions": trigger_conditions,
            "avoid_patterns": [error_message[:200]],
            "rationale": f"Failed on {task_description[:100]}: {error_message[:100]}",
            "confidence": 0.9,  # Very high confidence for failures
            "outcome": "failure"
        }
    
    def _compute_strategy_id(self, heuristic: dict[str, Any]) -> str:
        """Compute deterministic ID for heuristic."""
        content = json.dumps(heuristic, sort_keys=True, ensure_ascii=False)
        return f"strategy_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    def retrieve_similar_strategies(
        self,
        task_description: str,
        top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Retrieve most relevant strategies for a novel task.
        
        Based on ERL: uses task type and pattern matching to find relevant heuristics.
        
        Args:
            task_description: Description of the novel task
            top_k: Number of strategies to retrieve
            
        Returns:
            List of relevant strategies sorted by relevance
        """
        task_type = self._classify_task_type(task_description)
        
        # Score each strategy by relevance
        scored_strategies = []
        for strategy in self.strategies["strategies"]:
            score = self._compute_relevance_score(strategy, task_description, task_type)
            scored_strategies.append((score, strategy))
        
        # Sort by score descending
        scored_strategies.sort(key=lambda x: x[0], reverse=True)
        
        # Return top K
        return [strategy for _, strategy in scored_strategies[:top_k]]
    
    def _compute_relevance_score(
        self,
        strategy: dict[str, Any],
        task_description: str,
        task_type: str
    ) -> float:
        """Compute relevance score for a strategy."""
        score = 0.0
        
        # Task type match (high weight)
        if strategy.get("task_type") == task_type:
            score += 0.5
        
        # Trigger condition pattern match
        strategy_triggers = strategy.get("trigger_conditions", [])
        for trigger in strategy_triggers:
            if trigger.startswith("patterns:"):
                patterns = trigger.split(":")[1].split(",")
                # Check if any pattern keywords appear in task description
                for pattern in patterns:
                    if pattern.replace("_", " ") in task_description.lower():
                        score += 0.3
                        break
        
        # Confidence weighting
        confidence = strategy.get("confidence", 0.5)
        score *= confidence
        
        # Failure heuristics have higher impact (avoid mistakes)
        if strategy.get("type") == "failure_heuristic":
            score *= 1.2
        
        return score
