"""Turn SEC companyfacts JSON into annual statement series."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from statementlens import tags


@dataclass
class CompanyFinancials:
    ticker: str
    name: str
    cik: str
    years: list[int]
    income: dict[str, dict[int, float]] = field(default_factory=dict)
    balance: dict[str, dict[int, float]] = field(default_factory=dict)
    cashflow: dict[str, dict[int, float]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)

    def value(self, statement: str, item: str, year: int) -> float | None:
        table = {"income": self.income, "balance": self.balance, "cashflow": self.cashflow}[
            statement
        ]
        return table.get(item, {}).get(year)

    def series(self, statement: str, item: str) -> dict[int, float]:
        table = {"income": self.income, "balance": self.balance, "cashflow": self.cashflow}[
            statement
        ]
        return dict(table.get(item, {}))


def _usd_observations(concept: dict[str, Any]) -> list[dict[str, Any]]:
    units = concept.get("units") or {}
    if "USD" in units:
        return list(units["USD"])
    for unit_name, rows in units.items():
        if "share" in unit_name.lower() or "pure" in unit_name.lower():
            continue
        if unit_name.upper().startswith("USD"):
            return list(rows)
    return []


def _is_annual(obs: dict[str, Any]) -> bool:
    form = str(obs.get("form") or "")
    fp = str(obs.get("fp") or "")
    if form in tags.ANNUAL_FORMS:
        return True
    return fp == "FY"


def annual_series(concept: dict[str, Any]) -> dict[int, float]:
    """Pick one USD value per fiscal year, preferring 10-K over amendments."""
    chosen: dict[int, tuple[int, str, float]] = {}
    form_rank = {"10-K": 3, "20-F": 3, "40-F": 3, "10-K/A": 2, "20-F/A": 2, "40-F/A": 2}
    for obs in _usd_observations(concept):
        if not _is_annual(obs):
            continue
        fy = obs.get("fy")
        val = obs.get("val")
        if fy is None or val is None:
            continue
        try:
            year = int(fy)
            value = float(val)
        except (TypeError, ValueError):
            continue
        form = str(obs.get("form") or "")
        filed = str(obs.get("filed") or "")
        rank = form_rank.get(form, 1)
        previous = chosen.get(year)
        if previous is None or (rank, filed) >= (previous[0], previous[1]):
            chosen[year] = (rank, filed, value)
    return {year: row[2] for year, row in sorted(chosen.items())}


def _first_series(
    gaap: dict[str, Any], candidates: Iterable[str]
) -> tuple[dict[int, float], str | None]:
    for tag in candidates:
        concept = gaap.get(tag)
        if not concept:
            continue
        series = annual_series(concept)
        if series:
            return series, tag
    return {}, None


def _add(a: dict[int, float], b: dict[int, float]) -> dict[int, float]:
    years = set(a) | set(b)
    out: dict[int, float] = {}
    for year in years:
        parts = [part for part in (a.get(year), b.get(year)) if part is not None]
        if parts:
            out[year] = sum(parts)
    return out


def _subtract(a: dict[int, float], b: dict[int, float]) -> dict[int, float]:
    out: dict[int, float] = {}
    for year in set(a) | set(b):
        if year in a and year in b:
            out[year] = a[year] - b[year]
    return out


def normalize_companyfacts(
    facts_doc: dict[str, Any],
    ticker: str,
    name: str | None = None,
    years: int | None = None,
) -> CompanyFinancials:
    gaap = (facts_doc.get("facts") or {}).get("us-gaap") or {}
    if not gaap:
        raise ValueError("No us-gaap facts were found in this companyfacts document.")

    cik = str(facts_doc.get("cik") or "").zfill(10) if facts_doc.get("cik") is not None else ""
    display_name = name or str(facts_doc.get("entityName") or ticker)

    revenue, revenue_tag = _first_series(gaap, tags.REVENUE)
    cogs, cogs_tag = _first_series(gaap, tags.COGS)
    gross, gross_tag = _first_series(gaap, tags.GROSS_PROFIT)
    if not gross and revenue and cogs:
        gross = _subtract(revenue, cogs)
        gross_tag = f"{revenue_tag} - {cogs_tag}"

    operating, operating_tag = _first_series(gaap, tags.OPERATING_INCOME)
    net_income, ni_tag = _first_series(gaap, tags.NET_INCOME)
    interest, interest_tag = _first_series(gaap, tags.INTEREST_EXPENSE)
    dep, dep_tag = _first_series(gaap, tags.DEPRECIATION_AMORT)
    pretax, pretax_tag = _first_series(gaap, tags.INCOME_BEFORE_TAX)

    ebit = dict(operating)
    ebit_tag = operating_tag
    if not ebit and pretax and interest:
        ebit = {year: pretax[year] + interest.get(year, 0.0) for year in pretax}
        ebit_tag = f"{pretax_tag} + {interest_tag}" if pretax_tag else None

    ebitda: dict[int, float] = {}
    ebitda_tag = None
    if ebit and dep:
        ebitda = {year: ebit[year] + dep[year] for year in ebit if year in dep}
        ebitda_tag = f"{ebit_tag} + {dep_tag}" if ebit_tag and dep_tag else None

    assets, assets_tag = _first_series(gaap, tags.ASSETS)
    assets_c, assets_c_tag = _first_series(gaap, tags.ASSETS_CURRENT)
    liab, liab_tag = _first_series(gaap, tags.LIABILITIES)
    liab_c, liab_c_tag = _first_series(gaap, tags.LIABILITIES_CURRENT)
    cash, cash_tag = _first_series(gaap, tags.CASH)
    inventory, inv_tag = _first_series(gaap, tags.INVENTORY)
    receivables, ar_tag = _first_series(gaap, tags.RECEIVABLES)
    equity, equity_tag = _first_series(gaap, tags.EQUITY)
    debt_lt, debt_lt_tag = _first_series(gaap, tags.DEBT_LONG_TERM)
    debt_st, debt_st_tag = _first_series(gaap, tags.DEBT_CURRENT)
    debt = _add(debt_lt, debt_st)
    debt_tag = " + ".join(part for part in (debt_lt_tag, debt_st_tag) if part) or None

    ocf, ocf_tag = _first_series(gaap, tags.OPERATING_CASH_FLOW)
    capex_raw, capex_tag = _first_series(gaap, tags.CAPEX)
    # PaymentsToAcquire* are usually positive cash outflows in SEC companyfacts.
    capex = {year: abs(val) for year, val in capex_raw.items()}
    fcf = _subtract(ocf, capex)
    fcf_tag = f"{ocf_tag} - |{capex_tag}|" if ocf_tag and capex_tag else None

    all_years = sorted(
        set(revenue)
        | set(net_income)
        | set(assets)
        | set(equity)
        | set(ocf)
    )
    if years is not None and years > 0:
        all_years = all_years[-years:]

    def clip(series: dict[int, float]) -> dict[int, float]:
        return {year: series[year] for year in all_years if year in series}

    income = {
        "revenue": clip(revenue),
        "cogs": clip(cogs),
        "gross_profit": clip(gross),
        "operating_income": clip(operating),
        "ebit": clip(ebit),
        "ebitda": clip(ebitda),
        "interest_expense": clip(interest),
        "net_income": clip(net_income),
        "depreciation_amortization": clip(dep),
    }
    balance = {
        "cash": clip(cash),
        "receivables": clip(receivables),
        "inventory": clip(inventory),
        "current_assets": clip(assets_c),
        "total_assets": clip(assets),
        "current_liabilities": clip(liab_c),
        "total_liabilities": clip(liab),
        "total_debt": clip(debt),
        "equity": clip(equity),
    }
    cashflow = {
        "operating_cash_flow": clip(ocf),
        "capex": clip(capex),
        "free_cash_flow": clip(fcf),
    }
    sources = {
        "revenue": revenue_tag,
        "cogs": cogs_tag,
        "gross_profit": gross_tag,
        "operating_income": operating_tag,
        "ebit": ebit_tag,
        "ebitda": ebitda_tag,
        "interest_expense": interest_tag,
        "net_income": ni_tag,
        "depreciation_amortization": dep_tag,
        "cash": cash_tag,
        "receivables": ar_tag,
        "inventory": inv_tag,
        "current_assets": assets_c_tag,
        "total_assets": assets_tag,
        "current_liabilities": liab_c_tag,
        "total_liabilities": liab_tag,
        "total_debt": debt_tag,
        "equity": equity_tag,
        "operating_cash_flow": ocf_tag,
        "capex": capex_tag,
        "free_cash_flow": fcf_tag,
    }
    sources = {key: val for key, val in sources.items() if val}

    return CompanyFinancials(
        ticker=ticker.upper(),
        name=display_name,
        cik=cik,
        years=all_years,
        income=income,
        balance=balance,
        cashflow=cashflow,
        sources=sources,
    )
