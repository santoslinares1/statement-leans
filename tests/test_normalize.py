from statementlens.normalize import CompanyFinancials


def test_growco_core_lines(growco: CompanyFinancials) -> None:
    assert growco.years == [2021, 2022, 2023]
    assert growco.value("income", "revenue", 2023) == 1210
    assert growco.value("income", "cogs", 2023) == 700
    assert growco.value("income", "gross_profit", 2023) == 510
    assert growco.value("income", "net_income", 2021) == 150
    assert growco.value("balance", "total_debt", 2023) == 140  # 130 + 10
    assert growco.value("cashflow", "free_cash_flow", 2023) == 170  # 230 - 60
    assert growco.sources["revenue"] == (
        "RevenueFromContractWithCustomerExcludingAssessedTax"
    )


def test_missing_tag_does_not_appear(growco: CompanyFinancials) -> None:
    assert growco.value("income", "revenue", 1999) is None
