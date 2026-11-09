import pytest

from statementlens.ratios import compute_ratios, ratios_by_name


def test_growco_2023_margins_and_returns(growco) -> None:
    grouped = ratios_by_name(compute_ratios(growco))
    assert grouped["gross_margin"][2023].value == pytest.approx(510 / 1210)
    assert grouped["operating_margin"][2023].value == pytest.approx(260 / 1210)
    assert grouped["net_margin"][2023].value == pytest.approx(195 / 1210)
    assert grouped["roe"][2023].value == pytest.approx(195 / 565)
    assert grouped["roa"][2023].value == pytest.approx(195 / 930)
    assert grouped["current_ratio"][2023].value == pytest.approx(490 / 220)
    assert grouped["quick_ratio"][2023].value == pytest.approx((490 - 90) / 220)
    assert grouped["debt_to_equity"][2023].value == pytest.approx(140 / 565)
    assert grouped["interest_coverage"][2023].value == pytest.approx(260 / 9)
    assert grouped["fcf_margin"][2023].value == pytest.approx(170 / 1210)
    assert grouped["ocf_to_net_income"][2023].value == pytest.approx(230 / 195)
    nopat = 260 * (1 - 0.21)
    invested = 565 + 140 - 165
    assert grouped["roic"][2023].value == pytest.approx(nopat / invested)
    assert grouped["debt_to_ebitda"][2023].value == pytest.approx(140 / (260 + 35))
