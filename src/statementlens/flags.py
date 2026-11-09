"""Quality / red-flag rules that go beyond a raw ratio dump."""

from __future__ import annotations

from dataclasses import dataclass

from statementlens.normalize import CompanyFinancials
from statementlens.ratios import RatioPoint, ratios_by_name


@dataclass(frozen=True)
class RedFlag:
    code: str
    severity: str
    title: str
    explanation: str
    years: tuple[int, int] | None = None
    evidence: str | None = None


def _growth(old: float, new: float) -> float | None:
    if old == 0:
        return None
    return (new - old) / abs(old)


def _latest_pair(series: dict[int, float]) -> tuple[int, float, int, float] | None:
    years = sorted(series)
    if len(years) < 2:
        return None
    older, newer = years[-2], years[-1]
    return older, series[older], newer, series[newer]


def evaluate_flags(
    fin: CompanyFinancials, ratio_points: list[RatioPoint]
) -> list[RedFlag]:
    flags: list[RedFlag] = []
    grouped = ratios_by_name(ratio_points)

    receivables = fin.series("balance", "receivables")
    revenue = fin.series("income", "revenue")
    pair_ar = _latest_pair(receivables)
    pair_rev = _latest_pair(revenue)
    if pair_ar and pair_rev and pair_ar[0] == pair_rev[0] and pair_ar[2] == pair_rev[2]:
        g_ar = _growth(pair_ar[1], pair_ar[3])
        g_rev = _growth(pair_rev[1], pair_rev[3])
        if g_ar is not None and g_rev is not None and g_ar > g_rev + 0.05:
            flags.append(
                RedFlag(
                    code="receivables_vs_sales",
                    severity="high" if g_ar > g_rev + 0.15 else "medium",
                    title="Receivables growing faster than sales",
                    explanation=(
                        "Accounts receivable increased faster than revenue, which can mean "
                        "sales quality is weaker than the top line suggests (channel stuffing, "
                        "looser credit, or slower collections)."
                    ),
                    years=(pair_ar[0], pair_ar[2]),
                    evidence=(
                        f"Receivables grew {g_ar:.1%} vs revenue {g_rev:.1%} "
                        f"from {pair_ar[0]} to {pair_ar[2]}."
                    ),
                )
            )

    inventory = fin.series("balance", "inventory")
    cogs = fin.series("income", "cogs")
    baseline = cogs if len(cogs) >= 2 else revenue
    baseline_label = "COGS" if cogs is baseline else "revenue"
    pair_inv = _latest_pair(inventory)
    pair_base = _latest_pair(baseline)
    if pair_inv and pair_base and pair_inv[0] == pair_base[0] and pair_inv[2] == pair_base[2]:
        g_inv = _growth(pair_inv[1], pair_inv[3])
        g_base = _growth(pair_base[1], pair_base[3])
        if g_inv is not None and g_base is not None and g_inv > g_base + 0.05:
            flags.append(
                RedFlag(
                    code="inventory_vs_cogs",
                    severity="high" if g_inv > g_base + 0.15 else "medium",
                    title="Inventory growing faster than cost of sales",
                    explanation=(
                        "Inventory grew faster than "
                        f"{baseline_label}, which can point to slowing demand, "
                        "obsolete stock, or production that is outrunning sales."
                    ),
                    years=(pair_inv[0], pair_inv[2]),
                    evidence=(
                        f"Inventory grew {g_inv:.1%} vs {baseline_label} {g_base:.1%} "
                        f"from {pair_inv[0]} to {pair_inv[2]}."
                    ),
                )
            )

    ca = fin.series("balance", "current_assets")
    cl = fin.series("balance", "current_liabilities")
    wc = {
        year: ca[year] - cl[year]
        for year in set(ca) & set(cl)
    }
    pair_wc = _latest_pair(wc)
    if pair_wc and pair_wc[3] < pair_wc[1]:
        drop = pair_wc[1] - pair_wc[3]
        flags.append(
            RedFlag(
                code="working_capital_deterioration",
                severity="high" if pair_wc[3] < 0 else "medium",
                title="Working capital deteriorated",
                explanation=(
                    "Current assets minus current liabilities declined over the latest year, "
                    "which can signal tighter liquidity or a heavier short-term funding need."
                ),
                years=(pair_wc[0], pair_wc[2]),
                evidence=(
                    f"Working capital fell from {pair_wc[1]:,.0f} to {pair_wc[3]:,.0f} "
                    f"(change { -drop:,.0f}) between {pair_wc[0]} and {pair_wc[2]}."
                ),
            )
        )

    coverage = {
        year: point.value
        for year, point in grouped.get("interest_coverage", {}).items()
        if point.value is not None
    }
    pair_cov = _latest_pair(coverage)
    if pair_cov and pair_cov[3] < pair_cov[1] * 0.9:
        severity = "high" if pair_cov[3] < 2 else "medium"
        flags.append(
            RedFlag(
                code="interest_coverage_worsening",
                severity=severity,
                title="Interest coverage weakened",
                explanation=(
                    "EBIT covers interest expense by a smaller multiple than a year earlier. "
                    "That leaves less room if earnings fall or borrowing costs rise."
                ),
                years=(pair_cov[0], pair_cov[2]),
                evidence=(
                    f"Interest coverage moved from {pair_cov[1]:.2f}x to {pair_cov[3]:.2f}x "
                    f"between {pair_cov[0]} and {pair_cov[2]}."
                ),
            )
        )

    ocf_ni = {
        year: point.value
        for year, point in grouped.get("ocf_to_net_income", {}).items()
        if point.value is not None
    }
    latest_year = fin.years[-1] if fin.years else None
    if latest_year is not None and latest_year in ocf_ni:
        ratio = ocf_ni[latest_year]
        ni = fin.value("income", "net_income", latest_year)
        if ni is not None and ni > 0 and ratio < 0.8:
            flags.append(
                RedFlag(
                    code="accruals_earnings_quality",
                    severity="high" if ratio < 0.5 else "medium",
                    title="Earnings outpaced operating cash flow",
                    explanation=(
                        "Net income is well above operating cash flow, so a larger share of "
                        "reported profit is coming from accruals rather than cash generated "
                        "by the business."
                    ),
                    years=(latest_year, latest_year),
                    evidence=(
                        f"In {latest_year}, operating cash flow / net income was {ratio:.2f} "
                        "(flag if below 0.80 while net income is positive)."
                    ),
                )
            )

    return flags
