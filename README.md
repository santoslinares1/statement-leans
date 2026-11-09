# StatementLens

StatementLens turns SEC EDGAR company filings into a short equity/credit-style analyst memo. It downloads standardized US-GAAP company facts, rebuilds a multi-year income statement, balance sheet and cash flow statement, computes the ratios a junior analyst actually uses, and then runs a quality layer that flags issues a raw ratio table would miss.

The quality layer is the point of the project. Receivables growing faster than sales, inventory piling up against COGS, shrinking working capital, weaker interest coverage, or earnings that run ahead of operating cash flow are the kinds of checks used in entry-level equity and credit work. Each flag has an explicit rule, a severity, and a one-sentence explanation.

This is an analytical worksheet, not investment advice.

## Demo

```bash
pip install -e .
statementlens AAPL --years 5 -o reports
```

That writes `reports/aapl_analyst_memo.md` plus CSV exports of the statements and ratios.

You can also analyze a local companyfacts file (useful offline, and how the checked-in samples were produced):

```bash
statementlens STRESS --facts tests/fixtures/stressco.companyfacts.json --name "StressCo Inc." -o examples
```

Sample, from the packaged StressCo fixture:

```markdown
### Receivables growing faster than sales (2022–2023)

Severity: high

Accounts receivable increased faster than revenue, which can mean sales quality
is weaker than the top line suggests (channel stuffing, looser credit, or slower
collections).

Receivables grew 38.9% vs revenue 2.9% from 2022 to 2023.
```

Checked-in memos:

- [examples/aapl_analyst_memo.md](examples/aapl_analyst_memo.md) — Apple Inc., generated from live SEC companyfacts on 9 Nov 2026
- [examples/grow_analyst_memo.md](examples/grow_analyst_memo.md) — GrowCo, a packaged fixture with a clean profile
- [examples/stress_analyst_memo.md](examples/stress_analyst_memo.md) — StressCo, a packaged fixture where several quality flags fire

GrowCo and StressCo follow the SEC companyfacts shape so the test suite and those two memos run offline. `statementlens AAPL` hits the live SEC API.

## How it works

1. **Fetch** — resolve a ticker to a CIK with the SEC `company_tickers.json` file, then download [companyfacts](https://data.sec.gov/api/xbrl/companyfacts/) (`https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`). Responses are cached under `~/.cache/statementlens`. Requests use a descriptive User-Agent, which the SEC requires.
2. **Normalize** — read US-GAAP tags, keep annual observations (10-K / FY), and map them onto a common set of line items. If more than one tag could represent revenue or debt, a documented waterfall picks the first series that has data.
3. **Ratios** — compute profitability, returns, liquidity, leverage, coverage and cash conversion for each fiscal year. A missing tag skips that ratio and records why; it does not crash the run.
4. **Flags** — compare the latest two fiscal years (and the latest year for accruals) against explicit rules.
5. **Memo** — write a Markdown report a recruiter can read in about two minutes, plus CSVs if an output directory is given.

## Formulas

| Ratio | Formula |
| --- | --- |
| Gross margin | Gross profit / Revenue |
| Operating margin | Operating income / Revenue |
| Net margin | Net income / Revenue |
| ROE | Net income / Equity |
| ROA | Net income / Total assets |
| ROIC | EBIT × (1 − 0.21) / (Equity + Total debt − Cash) |
| Current ratio | Current assets / Current liabilities |
| Quick ratio | (Current assets − Inventory) / Current liabilities |
| Debt / equity | Total debt / Equity |
| Debt / EBITDA | Total debt / EBITDA |
| Interest coverage | EBIT / Interest expense |
| FCF | Operating cash flow − \|Capex\| |
| FCF margin | FCF / Revenue |
| OCF / net income | Operating cash flow / Net income |

ROIC uses the US federal statutory tax rate of 21% when a company-specific rate is not computed. Total debt is the sum of the first available long-term debt tag and the first available current/short-term debt tag. Capex comes from `PaymentsToAcquirePropertyPlantAndEquipment` (and close variants); those amounts are treated as cash outflows, matching how they usually appear in companyfacts.

### Quality flags

| Flag | Rule |
| --- | --- |
| Receivables vs sales | Latest-year receivables growth exceeds revenue growth by more than 5 percentage points |
| Inventory vs COGS | Latest-year inventory growth exceeds COGS growth (or revenue, if COGS is missing) by more than 5 percentage points |
| Working capital | Current assets − current liabilities declined over the latest year |
| Interest coverage | Latest coverage is below 90% of the prior year's coverage |
| Accruals | Latest net income is positive and operating cash flow / net income is below 0.80 |

## Project structure

```text
src/statementlens/
  fetch.py        SEC downloads and cache
  normalize.py    companyfacts → annual statements
  ratios.py       ratio definitions
  flags.py        quality rules
  report.py       Markdown memo and CSV export
  cli.py          `statementlens` command
tests/            offline pytest suite and fixtures
examples/         sample memos
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest
statementlens --help
```

CI runs the same tests on each push and pull request.

## Limitations

- Only US (and some foreign private issuer) filers available through SEC companyfacts.
- Tag coverage varies. Filers do not all use the same US-GAAP concepts, so a line item or ratio may be blank.
- Debt and lease treatment is simplified; hybrid or off-balance-sheet items can be missing.
- Annual figures are taken from 10-K / FY observations. Interim quarters are ignored.
- The tool does not provide investment advice.

## License

MIT. Copyright (c) 2026 Santos Linares.
