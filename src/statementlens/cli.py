"""Command-line interface for StatementLens."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from statementlens.fetch import FetchError, fetch_companyfacts, load_companyfacts_file, resolve_ticker
from statementlens.flags import evaluate_flags
from statementlens.normalize import normalize_companyfacts
from statementlens.ratios import compute_ratios
from statementlens.report import render_memo, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="statementlens",
        description=(
            "Download SEC companyfacts for a US-listed ticker and write an "
            "equity/credit-style analyst memo with ratios and quality flags."
        ),
    )
    parser.add_argument(
        "ticker",
        nargs="?",
        help="Ticker symbol (for example AAPL). Optional when --facts is used.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of most recent fiscal years to include (default: 5).",
    )
    parser.add_argument(
        "--facts",
        type=Path,
        help="Load a local SEC companyfacts JSON file instead of calling the SEC.",
    )
    parser.add_argument(
        "--name",
        help="Override the company display name (useful with --facts).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Directory for the markdown memo and CSV exports. Prints the memo if omitted.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Directory for cached SEC downloads (default: ~/.cache/statementlens).",
    )
    return parser


def analyze(
    ticker: str | None,
    years: int = 5,
    facts_path: Path | None = None,
    name: str | None = None,
    cache_dir: Path | None = None,
):
    if facts_path is not None:
        doc = load_companyfacts_file(facts_path)
        symbol = (ticker or "DEMO").upper()
        display = name or str(doc.get("entityName") or symbol)
        cik_display = str(doc.get("cik") or "")
        fin = normalize_companyfacts(doc, ticker=symbol, name=display, years=years)
        if not fin.cik and cik_display:
            fin.cik = str(cik_display).zfill(10) if str(cik_display).isdigit() else str(cik_display)
    else:
        if not ticker:
            raise FetchError("A ticker is required unless you pass --facts.")
        symbol, cik, title = resolve_ticker(ticker, cache_dir=cache_dir)
        doc = fetch_companyfacts(cik, cache_dir=cache_dir)
        fin = normalize_companyfacts(
            doc, ticker=symbol, name=name or title, years=years
        )
    ratios = compute_ratios(fin)
    flags = evaluate_flags(fin, ratios)
    return fin, ratios, flags


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        fin, ratios, flags = analyze(
            ticker=args.ticker,
            years=args.years,
            facts_path=args.facts,
            name=args.name,
            cache_dir=args.cache_dir,
        )
    except (FetchError, ValueError, OSError, FileNotFoundError) as exc:
        print(f"statementlens: {exc}", file=sys.stderr)
        return 1

    if args.output:
        paths = write_outputs(fin, ratios, flags, args.output)
        for label, path in paths.items():
            print(f"Wrote {label}: {path}")
    else:
        print(render_memo(fin, ratios, flags), end="")
    return 0
