"""Download SEC EDGAR companyfacts and ticker mappings.

SEC requires a descriptive User-Agent with a contact email:
https://www.sec.gov/os/webmaster-faq#code-support
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

USER_AGENT = (
    "StatementLens/0.1 (Santos Linares; student project; santos9linares@gmail.com)"
)
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "statementlens"


class FetchError(RuntimeError):
    """Raised when the SEC cannot be reached or the ticker is unknown."""


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }
    )
    return session


def _read_json_cache(path: Path, max_age_seconds: int) -> Any | None:
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > max_age_seconds:
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json_cache(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def load_ticker_map(
    cache_dir: Path | None = None,
    max_age_seconds: int = 24 * 60 * 60,
    session: requests.Session | None = None,
) -> dict[str, dict[str, Any]]:
    """Return ticker -> {cik, title} using the SEC company_tickers file."""
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cached = _read_json_cache(cache_dir / "company_tickers.json", max_age_seconds)
    if cached is None:
        sess = session or _session()
        response = sess.get(TICKERS_URL, timeout=30)
        if response.status_code != 200:
            raise FetchError(
                f"Could not download SEC ticker map (HTTP {response.status_code})."
            )
        cached = response.json()
        _write_json_cache(cache_dir / "company_tickers.json", cached)
        time.sleep(0.15)

    mapping: dict[str, dict[str, Any]] = {}
    for row in cached.values():
        ticker = str(row["ticker"]).upper()
        mapping[ticker] = {
            "cik": int(row["cik_str"]),
            "title": row.get("title", ticker),
        }
    return mapping


def resolve_ticker(
    ticker: str,
    cache_dir: Path | None = None,
    session: requests.Session | None = None,
) -> tuple[str, int, str]:
    ticker_u = ticker.strip().upper()
    mapping = load_ticker_map(cache_dir=cache_dir, session=session)
    if ticker_u not in mapping:
        raise FetchError(
            f"Ticker {ticker_u!r} was not found in the SEC company_tickers list."
        )
    info = mapping[ticker_u]
    return ticker_u, info["cik"], info["title"]


def fetch_companyfacts(
    cik: int,
    cache_dir: Path | None = None,
    max_age_seconds: int = 24 * 60 * 60,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Return the companyfacts JSON for a zero-padded CIK."""
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    padded = f"{int(cik):010d}"
    cache_path = cache_dir / f"companyfacts_{padded}.json"
    cached = _read_json_cache(cache_path, max_age_seconds)
    if cached is not None:
        return cached

    sess = session or _session()
    url = COMPANYFACTS_URL.format(cik=padded)
    response = sess.get(url, timeout=45)
    if response.status_code != 200:
        raise FetchError(
            f"Could not download companyfacts for CIK {padded} "
            f"(HTTP {response.status_code})."
        )
    payload = response.json()
    _write_json_cache(cache_path, payload)
    time.sleep(0.15)
    return payload


def load_companyfacts_file(path: Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or "facts" not in data:
        raise FetchError(f"{path} does not look like an SEC companyfacts document.")
    return data
