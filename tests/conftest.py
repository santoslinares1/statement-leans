from pathlib import Path

import pytest

from statementlens.fetch import load_companyfacts_file
from statementlens.normalize import normalize_companyfacts

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def growco():
    doc = load_companyfacts_file(FIXTURES / "growco.companyfacts.json")
    return normalize_companyfacts(doc, ticker="GROW", years=5)


@pytest.fixture
def stressco():
    doc = load_companyfacts_file(FIXTURES / "stressco.companyfacts.json")
    return normalize_companyfacts(doc, ticker="STRESS", years=5)
