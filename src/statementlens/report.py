"""Markdown memos and CSV exports."""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path

from statementlens.flags import RedFlag
from statementlens.normalize import CompanyFinancials
from statementlens.ratios import RatioPoint, ratios_by_name


RATIO_ORDER = [
    ("gross_margin", "Gross margin"),
    ("operating_margin", "Operating margin"),
    ("net_margin", "Net margin"),
    ("roe", "ROE"),
    ("roa", "ROA"),
    ("roic", "ROIC"),
    ("current_ratio", "Current ratio"),
    ("quick_ratio", "Quick ratio"),
    ("debt_to_equity", "Debt / equity"),
    ("debt_to_ebitda", "Debt / EBITDA"),
    ("interest_coverage", "Interest coverage"),
    ("fcf_margin", "FCF margin"),
    ("ocf_to_net_income", "OCF / net income"),
]

STATEMENT_ROWS = {
    "income": [
        ("revenue", "Revenue"),
        ("cogs", "Cost of revenue"),
        ("gross_profit", "Gross profit"),
        ("operating_income", "Operating income"),
        ("ebit", "EBIT"),
        ("ebitda", "EBITDA"),
        ("interest_expense", "Interest expense"),
        ("net_income", "Net income"),
    ],
    "balance": [
        ("cash", "Cash"),
        ("receivables", "Accounts receivable"),
        ("inventory", "Inventory"),
        ("current_assets", "Current assets"),
        ("total_assets", "Total assets"),
        ("current_liabilities", "Current liabilities"),
        ("total_debt", "Total debt"),
        ("equity", "Equity"),
    ],
    "cashflow": [
        ("operating_cash_flow", "Operating cash flow"),
        ("capex", "Capital expenditure"),
        ("free_cash_flow", "Free cash flow"),
    ],
}


def _fmt_number(value: float | None) -> str:
    if value is None:
        return "—"
    abs_val = abs(value)
    if abs_val >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f}B"
    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _fmt_ratio(name: str, value: float | None) -> str:
    if value is None:
        return "—"
    if name in {
        "gross_margin",
        "operating_margin",
        "net_margin",
        "roe",
        "roa",
        "roic",
        "fcf_margin",
    }:
        return f"{value * 100:.1f}%"
    if name == "interest_coverage":
        return f"{value:.2f}x"
    return f"{value:.2f}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_memo(
    fin: CompanyFinancials,
    ratio_points: list[RatioPoint],
    flags: list[RedFlag],
    generated_on: date | None = None,
) -> str:
    generated_on = generated_on or datetime.now(timezone.utc).date()
    years = fin.years
    year_headers = [str(year) for year in years]
    grouped = ratios_by_name(ratio_points)

    lines = [
        f"# StatementLens memo: {fin.name} ({fin.ticker})",
        "",
        f"- CIK: {fin.cik or 'n/a'}",
        f"- Fiscal years: {years[0]}–{years[-1]}" if years else "- Fiscal years: n/a",
        "- Source: SEC EDGAR Company Facts (US-GAAP tags), annual filings",
        f"- Generated: {generated_on.isoformat()} (UTC)",
        "",
        "This memo is an analytical worksheet, not investment advice.",
        "",
        "## Income statement",
        "",
        _statement_table(fin, "income", year_headers),
        "",
        "## Balance sheet",
        "",
        _statement_table(fin, "balance", year_headers),
        "",
        "## Cash flow",
        "",
        _statement_table(fin, "cashflow", year_headers),
        "",
        "## Ratios",
        "",
    ]

    ratio_rows: list[list[str]] = []
    for key, label in RATIO_ORDER:
        row = [label]
        series = grouped.get(key, {})
        for year in years:
            point = series.get(year)
            row.append(_fmt_ratio(key, point.value if point else None))
        ratio_rows.append(row)
    lines.append(_table(["Ratio", *year_headers], ratio_rows))
    lines.append("")
    if ratio_points:
        sample = next((p for p in ratio_points if p.formula), None)
        if sample:
            lines.append("Formulas used:")
            seen: set[str] = set()
            for key, label in RATIO_ORDER:
                for point in ratio_points:
                    if point.name == key and key not in seen:
                        lines.append(f"- {label}: `{point.formula}`")
                        seen.add(key)
                        break
            lines.append(
                "- ROIC uses a 21% tax rate on EBIT when a company-specific rate is not computed."
            )
            lines.append("")

    lines.extend(["## Quality flags", ""])
    if not flags:
        lines.append(
            "No quantitative quality flags fired under the documented rules "
            "for the years analyzed."
        )
    else:
        for flag in flags:
            span = (
                f"{flag.years[0]}"
                if flag.years and flag.years[0] == flag.years[1]
                else f"{flag.years[0]}–{flag.years[1]}"
                if flag.years
                else ""
            )
            title = f"### {flag.title}"
            if span:
                title += f" ({span})"
            lines.append(title)
            lines.append("")
            lines.append(f"Severity: {flag.severity}")
            lines.append("")
            lines.append(flag.explanation)
            if flag.evidence:
                lines.append("")
                lines.append(flag.evidence)
            lines.append("")

    interesting = [
        "revenue",
        "net_income",
        "equity",
        "operating_cash_flow",
        "total_debt",
        "interest_expense",
    ]
    absent = [key for key in interesting if key not in fin.sources]
    lines.extend(["## Coverage notes", ""])
    if fin.sources:
        lines.append("US-GAAP tags selected:")
        for key, tag in sorted(fin.sources.items()):
            lines.append(f"- {key}: `{tag}`")
        lines.append("")
    if absent:
        lines.append(
            "These items could not be mapped from the filing tags: "
            + ", ".join(absent)
            + "."
        )
        lines.append("")
    lines.append(
        "Limitations: coverage depends on how the filer tagged the 10-K; "
        "totals such as debt are summed from common current and long-term debt "
        "concepts and may omit some lease or hybrid instruments."
    )
    lines.append("")
    return "\n".join(lines)


def _statement_table(
    fin: CompanyFinancials, statement: str, year_headers: list[str]
) -> str:
    rows: list[list[str]] = []
    for key, label in STATEMENT_ROWS[statement]:
        series = fin.series(statement, key)
        row = [label]
        for year in fin.years:
            row.append(_fmt_number(series.get(year)))
        rows.append(row)
    return _table(["Line", *year_headers], rows)


def export_statement_csv(
    fin: CompanyFinancials, statement: str, path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["item", *[str(year) for year in fin.years]]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key, label in STATEMENT_ROWS[statement]:
            row = {"item": label}
            series = fin.series(statement, key)
            for year in fin.years:
                value = series.get(year)
                row[str(year)] = "" if value is None else f"{value:.2f}"
            writer.writerow(row)


def export_ratios_csv(points: list[RatioPoint], path: Path, years: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped = ratios_by_name(points)
    fieldnames = ["ratio", "formula", *[str(year) for year in years]]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key, label in RATIO_ORDER:
            series = grouped.get(key, {})
            row = {"ratio": label, "formula": ""}
            for year, point in series.items():
                row["formula"] = point.formula
                row[str(year)] = "" if point.value is None else f"{point.value:.6f}"
            writer.writerow(row)


def write_outputs(
    fin: CompanyFinancials,
    ratio_points: list[RatioPoint],
    flags: list[RedFlag],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = fin.ticker.lower()
    paths = {
        "memo": output_dir / f"{stem}_analyst_memo.md",
        "income": output_dir / f"{stem}_income_statement.csv",
        "balance": output_dir / f"{stem}_balance_sheet.csv",
        "cashflow": output_dir / f"{stem}_cash_flow.csv",
        "ratios": output_dir / f"{stem}_ratios.csv",
    }
    paths["memo"].write_text(render_memo(fin, ratio_points, flags), encoding="utf-8")
    export_statement_csv(fin, "income", paths["income"])
    export_statement_csv(fin, "balance", paths["balance"])
    export_statement_csv(fin, "cashflow", paths["cashflow"])
    export_ratios_csv(ratio_points, paths["ratios"], fin.years)
    return paths
