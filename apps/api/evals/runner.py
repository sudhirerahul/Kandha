# runner.py — CLI runner for Kandha eval suite
# Usage: cd apps/api && python -m evals.runner
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from evals.framework import run_eval_suite, results_to_dict
from evals.test_cases import EVAL_CASES
from services.gmi import GMIClient


async def main() -> int:
    """Run the full eval suite and output results."""
    print("=" * 60)
    print("Kandha LLM Evaluation Suite")
    print(f"Running {len(EVAL_CASES)} test cases...")
    print("=" * 60)

    client = GMIClient()

    async def llm_fn(prompt: str) -> str:
        return await client.complete(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )

    start = time.perf_counter()
    results = await run_eval_suite(EVAL_CASES, llm_fn)
    total_time = time.perf_counter() - start

    report = results_to_dict(results)
    summary = report["summary"]

    # Print results
    print()
    print("-" * 60)
    print(f"Total:       {summary['total']}")
    print(f"Passed:      {summary['passed']}")
    print(f"Failed:      {summary['failed']}")
    print(f"Pass Rate:   {summary['pass_rate']:.0%}")
    print(f"Avg Score:   {summary['avg_score']:.3f}")
    print(f"Avg Latency: {summary['avg_latency_ms']:.0f}ms")
    print(f"Total Time:  {total_time:.1f}s")
    print("-" * 60)

    # Per-category breakdown
    for category, cases in report["by_category"].items():
        passed = sum(1 for c in cases if c["passed"])
        print(f"  {category}: {passed}/{len(cases)} passed")

    # Print failures
    failed = [r for r in results if not r.passed]
    if failed:
        print()
        print("FAILURES:")
        for r in failed:
            print(f"  [{r.case_id}] score={r.overall_score:.3f} scores={r.scores}")

    # Save results to file
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"eval_{timestamp}.json"
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nResults saved to: {output_path}")

    # Exit code: 1 if any case failed
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
