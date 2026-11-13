"""Lexical experience retrieval (TF-IDF + n-grams), not an executor.

Historically this module was labelled "true generalization" and the controller used a
retrieved strategy plus keyword presence in the current goal to choose an AST operation.
That produced measured wrong answers: "count methods" counted free functions, "count
functions and classes" counted only functions, and "do not count functions" counted
functions.  The live controller no longer executes from this retrieval path; bounded
read-only Python AST queries go through `canonical.runtime.python_ast_query_v1`, which
binds the operation from the current request and checks the current bytes.

What remains real here:
1. TF-IDF / character-n-gram similarity over stored task descriptions.
2. Retrieval of candidate experiences and their recorded strategies.
3. Persistence of new experience records.

What is not claimed:
* embeddings from a neural semantic model (these are lexical features);
* conceptual understanding or transfer across arbitrary domains;
* verification of a stored outcome (the caller supplies `outcome`);
* model-weight updates.

Usage:
  engine = SemanticGeneralizationEngine()
  similar_experiences = engine.retrieve_similar("novel task description", top_k=5)
  adapted_strategy = engine.adapt_strategy(similar_experiences, novel_task)
"""
from __future__ import annotations

import json
import re
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping
from datetime import datetime, timezone
from collections import Counter

SCHEMA = "BRAIN_SEMANTIC_GENERALIZATION_ENGINE_V1"

class SemanticGeneralizationEngine:
    """Lexical similarity retrieval over recorded experiences.

    The name is kept for compatibility.  Similarity ranks hints; it does not authorize
    execution and does not establish that a stored outcome was verified.
    """
    
    def __init__(
        self,
        experiences_path: Path | None = None,
        embeddings_path: Path | None = None
    ):
        self.experiences_path = experiences_path or (
            Path(__file__).parent.parent / "astra_runtime" / "generalization" / "GENERALIZATION_EXPERIENCES_V1.json"
        )
        self.embeddings_path = embeddings_path or (
            Path(__file__).parent.parent / "astra_runtime" / "generalization" / "TASK_EMBEDDINGS_V1.json"
        )
        
        # Synonym groups for semantic expansion
        self.synonyms = {
            "count": ["count", "enumerate", "find", "identify", "list", "get", "retrieve"],
            "function": ["function", "functions", "method", "methods", "subroutine", "subroutines", "def", "definition"],
            "class": ["class", "classes", "type", "types", "object", "objects"],
            "file": ["file", "module", "script", "code", "source", ".py"],
            "read": ["read", "open", "load", "parse", "analyze", "inspect"],
            "fix": ["fix", "debug", "repair", "resolve", "correct", "patch"],
            "error": ["error", "bug", "issue", "problem", "fault", "defect"]
        }
        
        self.experiences = self._load_experiences()
        self.embeddings = self._load_embeddings()
        
        # Build vocabulary from all experiences
        self.vocab = self._build_vocabulary()
        self.idf = self._compute_idf()
    
    def _load_experiences(self) -> dict[str, Any]:
        """Load stored experiences."""
        if self.experiences_path.exists():
            with open(self.experiences_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "schema": SCHEMA,
            "experiences": [],
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0"
            }
        }
    
    def _load_embeddings(self) -> dict[str, Any]:
        """Load task embeddings."""
        if self.embeddings_path.exists():
            with open(self.embeddings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"embeddings": {}}
    
    def _save_experiences(self) -> None:
        """Persist experiences."""
        self.experiences_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.experiences_path, "w", encoding="utf-8") as f:
            json.dump(self.experiences, f, indent=2, ensure_ascii=False)
    
    def _save_embeddings(self) -> None:
        """Persist embeddings."""
        self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.embeddings_path, "w", encoding="utf-8") as f:
            json.dump(self.embeddings, f, indent=2, ensure_ascii=False)
    
    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text with synonym expansion and character n-grams."""
        # Lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Add unigrams with synonym expansion
        tokens = []
        for word in words:
            tokens.append(word)
            # Expand synonyms
            for group_words in self.synonyms.values():
                if word in group_words:
                    tokens.extend(group_words)
        
        # Add bigrams for context
        tokens.extend([f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)])
        
        # Add trigrams for more context
        tokens.extend([f"{words[i]}_{words[i+1]}_{words[i+2]}" for i in range(len(words)-2)])
        
        # Add character 3-grams for morphological similarity
        for word in words:
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    tokens.append(f"char:{word[i:i+3]}")
        
        return tokens
    
    def _build_vocabulary(self) -> dict[str, int]:
        """Build vocabulary from all experiences."""
        vocab = {}
        for exp in self.experiences["experiences"]:
            tokens = self._tokenize(exp["task_description"])
            for token in tokens:
                if token not in vocab:
                    vocab[token] = len(vocab)
        return vocab
    
    def _compute_idf(self) -> dict[str, float]:
        """Compute inverse document frequency for each token."""
        doc_count = len(self.experiences["experiences"])
        if doc_count == 0:
            return {}
        
        # Count document frequency
        df = Counter()
        for exp in self.experiences["experiences"]:
            tokens = set(self._tokenize(exp["task_description"]))
            for token in tokens:
                df[token] += 1
        
        # Compute IDF with smoothing
        idf = {}
        for token, freq in df.items():
            idf[token] = math.log((doc_count + 1) / (freq + 1)) + 1
        
        return idf
    
    def _embed_task(self, task_description: str) -> dict[str, float]:
        """Compute TF-IDF embedding for a task description."""
        tokens = self._tokenize(task_description)
        
        # Compute term frequency
        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1
        
        # Compute TF-IDF vector
        embedding = {}
        for token, count in tf.items():
            tf_normalized = count / max_tf
            idf_value = self.idf.get(token, 1.0)
            embedding[token] = tf_normalized * idf_value
        
        return embedding
    
    def _cosine_similarity(self, emb1: dict[str, float], emb2: dict[str, float]) -> float:
        """Compute cosine similarity between two embeddings."""
        # Get common dimensions
        common_tokens = set(emb1.keys()) & set(emb2.keys())
        
        if not common_tokens:
            return 0.0
        
        # Compute dot product
        dot_product = sum(emb1[token] * emb2[token] for token in common_tokens)
        
        # Compute magnitudes
        mag1 = math.sqrt(sum(v**2 for v in emb1.values()))
        mag2 = math.sqrt(sum(v**2 for v in emb2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def store_experience(
        self,
        task_description: str,
        trajectory: list[dict[str, Any]],
        outcome: str,
        strategy: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Store a new experience with its semantic embedding.
        
        Args:
            task_description: Description of the task
            trajectory: List of actions taken
            outcome: "success" or "failure"
            strategy: Optional extracted strategy (from strategy extractor)
            
        Returns:
            Stored experience with ID
        """
        # Compute semantic embedding
        embedding = self._embed_task(task_description)
        
        # Create experience record
        exp_id = hashlib.sha256(task_description.encode()).hexdigest()[:16]
        experience = {
            "id": exp_id,
            "task_description": task_description,
            "trajectory": trajectory,
            "outcome": outcome,
            "strategy": strategy,
            "embedding": embedding,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store
        self.experiences["experiences"].append(experience)
        self.embeddings["embeddings"][exp_id] = embedding
        
        # Rebuild vocabulary and IDF
        self.vocab = self._build_vocabulary()
        self.idf = self._compute_idf()
        
        # Persist
        self._save_experiences()
        self._save_embeddings()
        
        return experience
    
    def retrieve_similar(
        self,
        task_description: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> list[dict[str, Any]]:
        """Retrieve most similar experiences using semantic similarity.
        
        Args:
            task_description: Novel task description
            top_k: Number of experiences to retrieve
            min_similarity: Minimum cosine similarity threshold
            
        Returns:
            List of similar experiences sorted by similarity
        """
        # Compute embedding for novel task
        novel_embedding = self._embed_task(task_description)
        
        # Compute similarity to all stored experiences
        scored_experiences = []
        for exp in self.experiences["experiences"]:
            exp_embedding = self.embeddings["embeddings"].get(exp["id"], {})
            similarity = self._cosine_similarity(novel_embedding, exp_embedding)
            
            if similarity >= min_similarity:
                scored_experiences.append((similarity, exp))
        
        # Sort by similarity descending
        scored_experiences.sort(key=lambda x: x[0], reverse=True)
        
        # Return top K with similarity scores
        return [
            {**exp, "similarity_score": score}
            for score, exp in scored_experiences[:top_k]
        ]
    
    def adapt_strategy(
        self,
        similar_experiences: list[dict[str, Any]],
        novel_task: str
    ) -> dict[str, Any] | None:
        """Adapt strategies from similar experiences for the novel task.
        
        Uses compositional reasoning to combine strategies from multiple
        similar experiences into a unified approach for the novel task.
        
        Args:
            similar_experiences: Retrieved similar experiences
            novel_task: The novel task description
            
        Returns:
            Adapted strategy or None if no suitable strategy found
        """
        if not similar_experiences:
            return None
        
        # Collect all successful strategies
        successful_strategies = [
            exp for exp in similar_experiences
            if exp["outcome"] == "success" and exp.get("strategy")
        ]
        
        if not successful_strategies:
            return None
        
        # Take the most similar successful strategy as base
        base_strategy = successful_strategies[0]["strategy"]
        
        # Extract common patterns across all similar experiences
        common_patterns = self._extract_common_patterns(similar_experiences)
        
        # Create adapted strategy
        adapted = {
            "base_strategy": base_strategy,
            "common_patterns": common_patterns,
            "adaptation_notes": f"Adapted from {len(similar_experiences)} similar experiences",
            "source_experiences": [exp["id"] for exp in similar_experiences[:3]],
            "novel_task": novel_task,
            "adapted_at": datetime.now(timezone.utc).isoformat()
        }
        
        return adapted
    
    def _extract_common_patterns(
        self,
        experiences: list[dict[str, Any]]
    ) -> list[str]:
        """Extract common action patterns across experiences."""
        all_actions = []
        for exp in experiences:
            trajectory = exp.get("trajectory", [])
            for step in trajectory:
                action = step.get("action", "")
                if action:
                    all_actions.append(action.lower())
        
        # Find most common action patterns
        action_counts = Counter(all_actions)
        common = action_counts.most_common(5)
        
        return [action for action, count in common if count >= 2]
    
    def generalize_and_solve(
        self,
        task_description: str,
        top_k: int = 5
    ) -> dict[str, Any]:
        """Complete generalization pipeline: retrieve similar + adapt strategy.
        
        This is the main entry point for using semantic generalization.
        
        Args:
            task_description: Novel task to solve
            top_k: Number of similar experiences to consider
            
        Returns:
            Result with retrieved experiences and adapted strategy
        """
        # Retrieve similar experiences
        similar = self.retrieve_similar(task_description, top_k=top_k)
        
        # Adapt strategy
        adapted_strategy = self.adapt_strategy(similar, task_description)
        
        return {
            "novel_task": task_description,
            "similar_experiences_found": len(similar),
            "top_similarities": [exp["similarity_score"] for exp in similar[:3]],
            "adapted_strategy": adapted_strategy,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
