from statementlens.flags import evaluate_flags
from statementlens.ratios import compute_ratios


def test_stressco_triggers_quality_flags(stressco) -> None:
    flags = evaluate_flags(stressco, compute_ratios(stressco))
    codes = {flag.code for flag in flags}
    assert "receivables_vs_sales" in codes
    assert "inventory_vs_cogs" in codes
    assert "working_capital_deterioration" in codes
    assert "interest_coverage_worsening" in codes
    assert "accruals_earnings_quality" in codes


def test_growco_does_not_raise_stress_flags(growco) -> None:
    flags = evaluate_flags(growco, compute_ratios(growco))
    codes = {flag.code for flag in flags}
    assert "receivables_vs_sales" not in codes
    assert "inventory_vs_cogs" not in codes
    assert "working_capital_deterioration" not in codes
    assert "interest_coverage_worsening" not in codes
    assert "accruals_earnings_quality" not in codes
