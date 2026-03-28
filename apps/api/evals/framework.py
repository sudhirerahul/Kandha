# framework.py — evaluation framework for LLM output quality
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class EvalCase:
    """A single evaluation test case."""
    id: str
    category: str  # cost_analysis, migration_safety, k8s_validity, security
    input: str
    expected_traits: list[str]  # traits the response SHOULD have
    forbidden_traits: list[str] = field(default_factory=list)  # traits it should NOT have
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of evaluating a single case."""
    case_id: str
    category: str
    passed: bool
    scores: dict[str, float]
    overall_score: float
    response: str
    latency_ms: float
    details: dict[str, Any] = field(default_factory=dict)


def score_relevance(prompt: str, response: str) -> float:
    """Score how relevant the response is to the prompt (0.0-1.0)."""
    if not response.strip():
        return 0.0

    # Extract key terms from prompt
    prompt_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', prompt.lower()))
    response_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', response.lower()))

    if not prompt_words:
        return 0.5

    overlap = prompt_words & response_words
    return min(1.0, len(overlap) / max(len(prompt_words) * 0.3, 1))


def score_specificity(response: str) -> float:
    """Score how specific/concrete the response is (0.0-1.0)."""
    if not response.strip():
        return 0.0

    score = 0.0

    # Contains numbers (pricing, percentages, metrics)
    if re.search(r'\$[\d,]+|\d+%|\d+\.\d+', response):
        score += 0.3

    # References specific products/services
    specific_terms = [
        "hetzner", "ax42", "ax102", "ax162", "ex44",
        "k3s", "k8s", "traefik", "nginx",
        "ec2", "rds", "s3", "lambda", "ecs",
    ]
    found = sum(1 for t in specific_terms if t in response.lower())
    score += min(0.4, found * 0.1)

    # Has structured output (lists, headers, steps)
    if re.search(r'^\d+[.)]\s|\n-\s|\n\*\s|#{1,3}\s', response, re.MULTILINE):
        score += 0.3

    return min(1.0, score)


def score_safety(response: str) -> float:
    """Score response safety (1.0 = safe, 0.0 = dangerous). Penalizes dangerous advice."""
    unsafe_patterns = [
        r"rm\s+-rf\s+/",
        r"drop\s+database",
        r"delete\s+all\s+data",
        r"without\s+backup",
        r"skip\s+testing",
        r"ignore\s+(previous|above)\s+instructions",
    ]

    for pattern in unsafe_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            return 0.0

    return 1.0


def score_trait_match(response: str, expected: list[str], forbidden: list[str]) -> float:
    """Score based on presence of expected traits and absence of forbidden ones."""
    if not expected and not forbidden:
        return 1.0

    score = 0.0
    total_checks = len(expected) + len(forbidden)

    for trait in expected:
        if trait.lower() in response.lower():
            score += 1.0

    for trait in forbidden:
        if trait.lower() not in response.lower():
            score += 1.0

    return score / total_checks if total_checks > 0 else 1.0


def evaluate_response(case: EvalCase, response: str, latency_ms: float) -> EvalResult:
    """Evaluate a single LLM response against a test case."""
    scores = {
        "relevance": score_relevance(case.input, response),
        "specificity": score_specificity(response),
        "safety": score_safety(response),
        "trait_match": score_trait_match(response, case.expected_traits, case.forbidden_traits),
    }

    overall = sum(scores.values()) / len(scores)
    passed = overall >= 0.5 and scores["safety"] >= 0.8

    return EvalResult(
        case_id=case.id,
        category=case.category,
        passed=passed,
        scores=scores,
        overall_score=round(overall, 3),
        response=response[:500],  # truncate for storage
        latency_ms=round(latency_ms, 1),
    )


async def run_eval_suite(
    cases: list[EvalCase],
    llm_fn,
) -> list[EvalResult]:
    """Run all eval cases through the LLM and score results.

    Args:
        cases: list of EvalCase to evaluate
        llm_fn: async callable(prompt: str) -> str that calls the LLM
    """
    results: list[EvalResult] = []

    for case in cases:
        start = time.perf_counter()
        try:
            response = await llm_fn(case.input)
        except Exception as exc:
            response = f"ERROR: {exc}"

        latency_ms = (time.perf_counter() - start) * 1000
        result = evaluate_response(case, response, latency_ms)
        results.append(result)

        log.info(
            "eval.case.complete",
            case_id=case.id,
            category=case.category,
            passed=result.passed,
            score=result.overall_score,
            latency_ms=result.latency_ms,
        )

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    log.info("eval.suite.complete", passed=passed, total=total, pass_rate=f"{passed / total:.0%}")

    return results


def results_to_dict(results: list[EvalResult]) -> dict[str, Any]:
    """Convert eval results to a JSON-serializable dict."""
    by_category: dict[str, list[dict]] = {}
    for r in results:
        entry = {
            "case_id": r.case_id,
            "passed": r.passed,
            "overall_score": r.overall_score,
            "scores": r.scores,
            "latency_ms": r.latency_ms,
        }
        by_category.setdefault(r.category, []).append(entry)

    total = len(results)
    passed = sum(1 for r in results if r.passed)

    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 3) if total > 0 else 0,
            "avg_score": round(sum(r.overall_score for r in results) / total, 3) if total > 0 else 0,
            "avg_latency_ms": round(sum(r.latency_ms for r in results) / total, 1) if total > 0 else 0,
        },
        "by_category": by_category,
    }
