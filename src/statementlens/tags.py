"""US-GAAP tag waterfalls used to normalize SEC companyfacts.

Order matters: the first tag that has usable annual USD observations wins.
These names are the standard US-GAAP taxonomy concepts, not invented labels.
"""

from __future__ import annotations

REVENUE = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "Revenues",
    "SalesRevenueGoodsNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
)
COGS = (
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "CostOfGoodsSold",
)
GROSS_PROFIT = ("GrossProfit",)
OPERATING_INCOME = ("OperatingIncomeLoss",)
NET_INCOME = (
    "NetIncomeLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
    "ProfitLoss",
)
INTEREST_EXPENSE = (
    "InterestExpense",
    "InterestExpenseNonoperating",
    "InterestAndDebtExpense",
)
DEPRECIATION_AMORT = (
    "DepreciationDepletionAndAmortization",
    "Depreciation",
    "DepreciationAndAmortization",
)
INCOME_BEFORE_TAX = (
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
)

ASSETS = ("Assets",)
ASSETS_CURRENT = ("AssetsCurrent",)
LIABILITIES = ("Liabilities",)
LIABILITIES_CURRENT = ("LiabilitiesCurrent",)
CASH = (
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "Cash",
)
INVENTORY = ("InventoryNet", "InventoryFinishedGoodsNetOfReserves")
RECEIVABLES = (
    "AccountsReceivableNetCurrent",
    "AccountsReceivableNet",
    "ReceivablesNetCurrent",
)
EQUITY = (
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
)
DEBT_LONG_TERM = (
    "LongTermDebtNoncurrent",
    "LongTermDebt",
    "LongTermDebtAndCapitalLeaseObligations",
    "LongTermDebtNoncurrentAndCapitalLeaseObligations",
)
DEBT_CURRENT = (
    "LongTermDebtCurrent",
    "ShortTermBorrowings",
    "CommercialPaper",
    "DebtCurrent",
    "LongTermDebtAndCapitalLeaseObligationsCurrent",
)

OPERATING_CASH_FLOW = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
CAPEX = (
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
)

ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
