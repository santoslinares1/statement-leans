"""Ratio calculations used in an entry-level equity or credit review."""

from __future__ import annotations

from dataclasses import dataclass

from statementlens.normalize import CompanyFinancials

# Used only when a company-specific tax rate cannot be computed.
# Documented in the README: US federal statutory rate as a simplification.
DEFAULT_TAX_RATE = 0.21


@dataclass(frozen=True)
class RatioPoint:
    name: str
    year: int
    value: float | None
    formula: str
    missing: str | None = None


def _ratio(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None or denom == 0:
        return None
    return numer / denom


def compute_ratios(fin: CompanyFinancials) -> list[RatioPoint]:
    points: list[RatioPoint] = []
    for year in fin.years:
        rev = fin.value("income", "revenue", year)
        gp = fin.value("income", "gross_profit", year)
        opinc = fin.value("income", "operating_income", year)
        ebit = fin.value("income", "ebit", year)
        ebitda = fin.value("income", "ebitda", year)
        ni = fin.value("income", "net_income", year)
        interest = fin.value("income", "interest_expense", year)
        assets = fin.value("balance", "total_assets", year)
        equity = fin.value("balance", "equity", year)
        cash = fin.value("balance", "cash", year)
        inventory = fin.value("balance", "inventory", year)
        ca = fin.value("balance", "current_assets", year)
        cl = fin.value("balance", "current_liabilities", year)
        debt = fin.value("balance", "total_debt", year)
        ocf = fin.value("cashflow", "operating_cash_flow", year)
        fcf = fin.value("cashflow", "free_cash_flow", year)

        invested = None
        if equity is not None:
            invested = equity + (debt or 0.0) - (cash or 0.0)
            if invested <= 0:
                invested = None
        nopat = None
        if ebit is not None:
            nopat = ebit * (1.0 - DEFAULT_TAX_RATE)

        specs = [
            ("gross_margin", _ratio(gp, rev), "gross_profit / revenue", (gp, rev)),
            ("operating_margin", _ratio(opinc, rev), "operating_income / revenue", (opinc, rev)),
            ("net_margin", _ratio(ni, rev), "net_income / revenue", (ni, rev)),
            ("roe", _ratio(ni, equity), "net_income / equity", (ni, equity)),
            ("roa", _ratio(ni, assets), "net_income / total_assets", (ni, assets)),
            (
                "roic",
                _ratio(nopat, invested),
                "ebit * (1 - 0.21) / (equity + total_debt - cash)",
                (nopat, invested),
            ),
            ("current_ratio", _ratio(ca, cl), "current_assets / current_liabilities", (ca, cl)),
            (
                "quick_ratio",
                _ratio(None if ca is None or inventory is None else ca - inventory, cl),
                "(current_assets - inventory) / current_liabilities",
                (ca, inventory, cl),
            ),
            ("debt_to_equity", _ratio(debt, equity), "total_debt / equity", (debt, equity)),
            ("debt_to_ebitda", _ratio(debt, ebitda), "total_debt / ebitda", (debt, ebitda)),
            (
                "interest_coverage",
                _ratio(ebit, interest),
                "ebit / interest_expense",
                (ebit, interest),
            ),
            ("fcf_margin", _ratio(fcf, rev), "free_cash_flow / revenue", (fcf, rev)),
            (
                "ocf_to_net_income",
                _ratio(ocf, ni),
                "operating_cash_flow / net_income",
                (ocf, ni),
            ),
        ]
        for name, value, formula, inputs in specs:
            missing = None
            if value is None:
                missing = "missing or zero denominator among: " + ", ".join(
                    "n/a" if item is None else "ok" for item in inputs
                )
                if any(item is None for item in inputs):
                    missing = "a required input was not present in the filing tags"
                elif any(item == 0 for item in inputs if isinstance(item, (int, float))):
                    missing = "denominator was zero"
            points.append(
                RatioPoint(
                    name=name,
                    year=year,
                    value=value,
                    formula=formula,
                    missing=missing,
                )
            )
    return points


def ratios_by_name(points: list[RatioPoint]) -> dict[str, dict[int, RatioPoint]]:
    grouped: dict[str, dict[int, RatioPoint]] = {}
    for point in points:
        grouped.setdefault(point.name, {})[point.year] = point
    return grouped
