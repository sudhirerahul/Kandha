# prompt_chains.py — structured multi-step GMI prompt chains (Dify fallback)
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import structlog

from services.gmi import GMIClient

log = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    return (_PROMPTS_DIR / name).read_text()


async def analyze_chain(bill_data: dict[str, Any], gmi: GMIClient) -> dict[str, Any]:
    """Two-step cost analysis chain.

    Step 1: Categorize services into compute/storage/network/database/other.
    Step 2: Generate savings estimate with hardware mapping.
    Returns a structured dict with summary, categories, savings, and source.
    """
    spend_json = json.dumps(bill_data, indent=2)

    # Step 1 — categorize
    categorize_resp = await gmi.complete(
        [
            {
                "role": "user",
                "content": (
                    "You are a cloud billing expert. Categorize the following cloud "
                    "spend into: compute, storage, network, database, other. "
                    "Return ONLY valid JSON: {\"compute\": USD, \"storage\": USD, "
                    "\"network\": USD, \"database\": USD, \"other\": USD}\n\n"
                    f"Spend data:\n{spend_json}"
                ),
            }
        ],
        temperature=0.2,
        max_tokens=512,
    )
    log.info("analyze_chain.step1_done", response_len=len(categorize_resp))

    # Step 2 — full analysis using prompt template
    prompt_template = _load_prompt("analyze_chain.md")
    analysis_resp = await gmi.complete(
        [
            {
                "role": "user",
                "content": prompt_template.replace("{spend_data}", spend_json),
            },
            {
                "role": "assistant",
                "content": f"Based on my categorization: {categorize_resp}\n\nNow generating full analysis:",
            },
            {
                "role": "user",
                "content": "Continue with the full structured JSON analysis.",
            },
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    log.info("analyze_chain.step2_done", response_len=len(analysis_resp))

    # Parse the JSON response, fall back to raw text on failure
    try:
        # Strip markdown code fences if present
        cleaned = analysis_resp.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        result = json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        log.warning("analyze_chain.parse_failed", raw=analysis_resp[:200])
        result = {
            "summary": analysis_resp,
            "categories": {},
            "estimated_savings_pct": 0.0,
        }

    result["source"] = "gmi_chain"
    return result


async def migrate_chain(
    context: dict[str, Any], gmi: GMIClient
) -> AsyncGenerator[str, None]:
    """Three-step streaming migration plan chain.

    Step 1: Identify migration candidates from the architecture.
    Step 2: Sequence by risk (stateless first, stateful last).
    Step 3: Generate phased timeline.
    Streams combined output as markdown.
    """
    ctx_json = json.dumps(context, indent=2)

    steps = [
        (
            "## Migration Candidates\n\n",
            f"You are a cloud migration architect. Analyze this architecture and "
            f"identify which services are candidates for bare-metal migration. "
            f"Group them as: easy (stateless), medium (cache/queue), hard (stateful DB). "
            f"Output markdown.\n\nArchitecture:\n{ctx_json}",
        ),
        (
            "\n\n## Risk-Ordered Sequence\n\n",
            f"Given this architecture context, create a risk-ordered migration sequence. "
            f"Stateless services first, stateful last. For each service list: name, "
            f"risk level, estimated downtime, rollback strategy. Output markdown table.\n\n"
            f"Context:\n{ctx_json}",
        ),
        (
            "\n\n## Phased Timeline\n\n",
            f"Create a phased migration timeline (4 phases over 8-12 weeks) for "
            f"moving from cloud to bare-metal. Include milestones, go/no-go criteria, "
            f"and rollback windows. Output markdown.\n\nContext:\n{ctx_json}",
        ),
    ]

    for header, prompt in steps:
        yield header
        async for chunk in gmi.stream_chat(
            [{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1024,
        ):
            yield chunk

    log.info("migrate_chain.done", steps=len(steps))


async def infra_chain(
    provider: str, workload: str, size: str, gmi: GMIClient
) -> str:
    """Generate production-ready K8s manifests using a structured prompt.

    Returns valid YAML with namespace, deployment, service, ingress, and HPA
    separated by '---'.
    """
    prompt_template = _load_prompt("infra_gen.md")
    prompt = (
        prompt_template
        .replace("{provider}", provider)
        .replace("{workload}", workload)
        .replace("{size}", size)
    )

    result = await gmi.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4096,
    )

    # Strip markdown code fences if present
    cleaned = result.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    log.info("infra_chain.done", provider=provider, workload=workload, size=size)
    return cleaned
