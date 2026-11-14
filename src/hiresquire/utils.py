"""Shared utilities: candidate comparison and idempotency helpers."""

from typing import Any, Dict, List


def compare_candidates(
    candidates: List[Dict[str, Any]],
    candidate_ids: List[int],
) -> Dict[str, Any]:
    """Compare candidates side-by-side with a delta analysis (local, no API call)."""
    selected = [c for c in candidates if c.get("id") in candidate_ids]
    if len(selected) < 2:
        raise ValueError("Need at least 2 candidates to compare")

    sorted_candidates = sorted(selected, key=lambda x: x.get("score", 0), reverse=True)
    score_diff = sorted_candidates[0].get("score", 0) - sorted_candidates[-1].get("score", 0)

    return {
        "compared_count": len(selected),
        "top_candidate": sorted_candidates[0].get("name"),
        "top_score": sorted_candidates[0].get("score"),
        "score_range": score_diff,
        "candidates": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "score": c.get("score"),
                "summary": c.get("summary", "")[:100],
            }
            for c in sorted_candidates
        ],
    }


def generate_idempotency_key() -> str:
    import uuid

    return str(uuid.uuid4())
