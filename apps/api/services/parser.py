# parser.py — Cloud bill CSV parser for AWS, GCP, and Azure exports
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()

# ── Column name mappings per provider ───────────────────────────────────────

_AWS_COLS = {
    "service": ["lineItem/ProductCode", "ProductName", "product/ProductName"],
    "cost": ["lineItem/UnblendedCost", "TotalCost", "lineItem/BlendedCost"],
    "usage": ["lineItem/UsageAmount", "UsageQuantity"],
    "region": ["lineItem/AvailabilityZone", "product/region"],
}

_GCP_COLS = {
    "service": ["service.description", "Service description"],
    "cost": ["cost", "Cost"],
    "usage": ["usage.amount", "Usage amount"],
    "region": ["location.region", "Region"],
}

_AZURE_COLS = {
    "service": ["ServiceName", "MeterCategory", "ConsumedService"],
    "cost": ["CostInBillingCurrency", "Cost", "PreTaxCost"],
    "usage": ["Quantity", "UsageQuantity"],
    "region": ["ResourceLocation", "Location"],
}

_PROVIDER_COLS = {"aws": _AWS_COLS, "gcp": _GCP_COLS, "azure": _AZURE_COLS}


@dataclass
class ServiceSpend:
    """Aggregated spend for a single cloud service."""

    service: str
    cost_usd: float
    usage: float = 0.0
    region: str = "global"


@dataclass
class ParsedBill:
    """Structured output of a parsed cloud bill."""

    provider: str
    total_usd: float
    line_items: int
    services: list[ServiceSpend] = field(default_factory=list)
    raw_rows: list[dict[str, Any]] = field(default_factory=list)

    def top_services(self, n: int = 10) -> list[ServiceSpend]:
        return sorted(self.services, key=lambda s: s.cost_usd, reverse=True)[:n]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "total_usd": round(self.total_usd, 2),
            "line_items": self.line_items,
            "services": [
                {
                    "service": s.service,
                    "cost_usd": round(s.cost_usd, 2),
                    "usage": round(s.usage, 4),
                    "region": s.region,
                }
                for s in self.top_services(20)
            ],
        }


def _detect_provider(headers: list[str]) -> str:
    """Detect cloud provider from CSV column names."""
    header_set = {h.lower() for h in headers}
    if any("lineitem" in h or "blendedcost" in h for h in header_set):
        return "aws"
    if any("service.description" in h or "billingaccountid" in h for h in header_set):
        return "gcp"
    if any("costinbillingcurrency" in h or "meterid" in h for h in header_set):
        return "azure"
    return "unknown"


def _find_col(row: dict[str, Any], candidates: list[str]) -> str | None:
    """Find the first matching column from a list of candidates."""
    for col in candidates:
        if col in row:
            return col
    return None


def parse_bill_csv(content: bytes) -> ParsedBill:
    """Parse a cloud bill CSV and return aggregated spend by service."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        log.warning("parser.empty_csv")
        return ParsedBill(provider="unknown", total_usd=0.0, line_items=0)

    headers = list(rows[0].keys())
    provider = _detect_provider(headers)
    cols = _PROVIDER_COLS.get(provider, _AWS_COLS)

    log.info("parser.detected_provider", provider=provider, rows=len(rows))

    # Aggregate spend by service name
    service_spend: dict[str, ServiceSpend] = {}
    skipped = 0

    for row in rows:
        svc_col = _find_col(row, cols["service"])
        cost_col = _find_col(row, cols["cost"])

        if not svc_col or not cost_col:
            skipped += 1
            continue

        svc_name = str(row.get(svc_col, "Unknown")).strip() or "Unknown"
        try:
            cost = float(row.get(cost_col, 0) or 0)
        except (ValueError, TypeError):
            continue

        if cost <= 0:
            continue

        region_col = _find_col(row, cols.get("region", []))
        region = str(row.get(region_col, "global")).strip() if region_col else "global"
        usage_col = _find_col(row, cols.get("usage", []))
        usage = float(row.get(usage_col, 0) or 0) if usage_col else 0.0

        if svc_name not in service_spend:
            service_spend[svc_name] = ServiceSpend(service=svc_name, cost_usd=0.0, region=region)
        service_spend[svc_name].cost_usd += cost
        service_spend[svc_name].usage += usage

    if skipped:
        log.warning("parser.skipped_rows", count=skipped)

    services = sorted(service_spend.values(), key=lambda s: s.cost_usd, reverse=True)
    total = sum(s.cost_usd for s in services)

    return ParsedBill(
        provider=provider,
        total_usd=total,
        line_items=len(rows),
        services=services,
        raw_rows=rows[:100],  # keep first 100 rows for Dify context
    )
