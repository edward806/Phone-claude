"""
Stock Recovery Analysis Tool
Finds the top 15 worst-performing S&P 500 stocks over the past 6 months
and analyzes their fundamentals for potential recovery plays.
Includes Daloopa hyperlinks for deeper financial model access.

Usage:
    python stock_recovery_analysis.py          # attempts live data, falls back to demo
    python stock_recovery_analysis.py --demo   # run with illustrative dataset
    python stock_recovery_analysis.py --live   # live data only (requires internet)
"""

import sys
import time
import json
import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box
from rich.rule import Rule
from rich.markup import escape

console = Console()

# ─── URL templates ────────────────────────────────────────────────────────────
def daloopa_url(ticker: str) -> str:
    """Direct link to a company's financial model page on Daloopa."""
    return f"https://app.daloopa.com/ticker/{ticker}"

def yahoo_finance_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}"

def seekingalpha_url(ticker: str) -> str:
    return f"https://seekingalpha.com/symbol/{ticker}"

def finviz_url(ticker: str) -> str:
    return f"https://finviz.com/quote.ashx?t={ticker}"

def macrotrends_url(ticker: str) -> str:
    return f"https://www.macrotrends.net/stocks/charts/{ticker}/"


# ─── Rich markup hyperlink helper ────────────────────────────────────────────
def hyperlink(label: str, url: str) -> str:
    """Returns a Rich markup clickable link (works in terminals with link support)."""
    return f"[link={url}]{label}[/link]"


# ─── S&P 500 tickers (embedded — no network required) ─────────────────────────
SP500_SAMPLE = [
    ("AAPL","Apple Inc.","Information Technology"),
    ("MSFT","Microsoft Corp.","Information Technology"),
    ("AMZN","Amazon.com Inc.","Consumer Discretionary"),
    ("NVDA","NVIDIA Corp.","Information Technology"),
    ("GOOGL","Alphabet Inc.","Communication Services"),
    ("META","Meta Platforms","Communication Services"),
    ("BRK-B","Berkshire Hathaway","Financials"),
    ("LLY","Eli Lilly","Health Care"),
    ("AVGO","Broadcom Inc.","Information Technology"),
    ("TSLA","Tesla Inc.","Consumer Discretionary"),
    ("WMT","Walmart Inc.","Consumer Staples"),
    ("JPM","JPMorgan Chase","Financials"),
    ("V","Visa Inc.","Financials"),
    ("XOM","Exxon Mobil","Energy"),
    ("UNH","UnitedHealth Group","Health Care"),
    ("MA","Mastercard Inc.","Financials"),
    ("COST","Costco Wholesale","Consumer Staples"),
    ("HD","Home Depot","Consumer Discretionary"),
    ("PG","Procter & Gamble","Consumer Staples"),
    ("JNJ","Johnson & Johnson","Health Care"),
    ("ABBV","AbbVie Inc.","Health Care"),
    ("BAC","Bank of America","Financials"),
    ("KO","Coca-Cola Co.","Consumer Staples"),
    ("MRK","Merck & Co.","Health Care"),
    ("CVX","Chevron Corp.","Energy"),
    ("AMD","Advanced Micro Devices","Information Technology"),
    ("ORCL","Oracle Corp.","Information Technology"),
    ("ADBE","Adobe Inc.","Information Technology"),
    ("CRM","Salesforce Inc.","Information Technology"),
    ("NFLX","Netflix Inc.","Communication Services"),
    ("INTC","Intel Corp.","Information Technology"),
    ("PFE","Pfizer Inc.","Health Care"),
    ("BKNG","Booking Holdings","Consumer Discretionary"),
    ("PM","Philip Morris","Consumer Staples"),
    ("IBM","IBM Corp.","Information Technology"),
    ("MCD","McDonald's Corp.","Consumer Discretionary"),
    ("DIS","Walt Disney Co.","Communication Services"),
    ("GE","GE Aerospace","Industrials"),
    ("CAT","Caterpillar Inc.","Industrials"),
    ("BA","Boeing Co.","Industrials"),
    ("GS","Goldman Sachs","Financials"),
    ("MS","Morgan Stanley","Financials"),
    ("SPGI","S&P Global","Financials"),
    ("BLK","BlackRock Inc.","Financials"),
    ("C","Citigroup Inc.","Financials"),
    ("AXP","American Express","Financials"),
    ("USB","U.S. Bancorp","Financials"),
    ("WFC","Wells Fargo","Financials"),
    ("TJX","TJX Companies","Consumer Discretionary"),
    ("NKE","Nike Inc.","Consumer Discretionary"),
    ("SBUX","Starbucks Corp.","Consumer Discretionary"),
    ("LOW","Lowe's Companies","Consumer Discretionary"),
    ("TGT","Target Corp.","Consumer Discretionary"),
    ("DHR","Danaher Corp.","Health Care"),
    ("TMO","Thermo Fisher Scientific","Health Care"),
    ("BMY","Bristol-Myers Squibb","Health Care"),
    ("AMGN","Amgen Inc.","Health Care"),
    ("GILD","Gilead Sciences","Health Care"),
    ("VRTX","Vertex Pharmaceuticals","Health Care"),
    ("REGN","Regeneron Pharmaceuticals","Health Care"),
    ("CI","Cigna Group","Health Care"),
    ("CVS","CVS Health","Health Care"),
    ("HUM","Humana Inc.","Health Care"),
    ("RTX","RTX Corp.","Industrials"),
    ("LMT","Lockheed Martin","Industrials"),
    ("NOC","Northrop Grumman","Industrials"),
    ("HON","Honeywell International","Industrials"),
    ("DE","Deere & Company","Industrials"),
    ("MMM","3M Company","Industrials"),
    ("UPS","United Parcel Service","Industrials"),
    ("FDX","FedEx Corp.","Industrials"),
    ("SO","Southern Company","Utilities"),
    ("DUK","Duke Energy","Utilities"),
    ("NEE","NextEra Energy","Utilities"),
    ("D","Dominion Energy","Utilities"),
    ("EXC","Exelon Corp.","Utilities"),
    ("SLB","SLB (Schlumberger)","Energy"),
    ("EOG","EOG Resources","Energy"),
    ("COP","ConocoPhillips","Energy"),
    ("MPC","Marathon Petroleum","Energy"),
    ("PSX","Phillips 66","Energy"),
    ("VLO","Valero Energy","Energy"),
    ("FCX","Freeport-McMoRan","Materials"),
    ("NEM","Newmont Corp.","Materials"),
    ("DOW","Dow Inc.","Materials"),
    ("LIN","Linde PLC","Materials"),
    ("APD","Air Products & Chemicals","Materials"),
    ("AMT","American Tower","Real Estate"),
    ("PLD","Prologis Inc.","Real Estate"),
    ("CCI","Crown Castle","Real Estate"),
    ("EQIX","Equinix Inc.","Real Estate"),
    ("SPG","Simon Property Group","Real Estate"),
    ("INTU","Intuit Inc.","Information Technology"),
    ("NOW","ServiceNow Inc.","Information Technology"),
    ("PANW","Palo Alto Networks","Information Technology"),
    ("SNPS","Synopsys Inc.","Information Technology"),
    ("CDNS","Cadence Design Systems","Information Technology"),
    ("QCOM","Qualcomm Inc.","Information Technology"),
    ("TXN","Texas Instruments","Information Technology"),
    ("MU","Micron Technology","Information Technology"),
    ("AMAT","Applied Materials","Information Technology"),
    ("LRCX","Lam Research","Information Technology"),
    ("WBD","Warner Bros. Discovery","Communication Services"),
    ("PARA","Paramount Global","Communication Services"),
    ("FOX","Fox Corp.","Communication Services"),
    ("T","AT&T Inc.","Communication Services"),
    ("VZ","Verizon Communications","Communication Services"),
    ("CMCSA","Comcast Corp.","Communication Services"),
    ("CHTR","Charter Communications","Communication Services"),
]


# ─── Demo dataset (illustrative — reflects realistic market scenarios) ─────────
# Based on typical stock behavior patterns for large-cap S&P 500 companies
# that experience meaningful 6-month declines.
DEMO_WORST_15: list[dict] = [
    {
        "ticker": "INTC", "name": "Intel Corp.", "sector": "Information Technology",
        "pct_6m": -54.2,
        "pe_ratio": None, "forward_pe": 28.5, "pb_ratio": 0.82,
        "ev_ebitda": 12.1, "profit_margin": -0.04, "roe": -0.08,
        "current_ratio": 1.42, "debt_to_equity": 49.0,
        "revenue_growth": -8.5, "free_cash_flow": -2.4e9, "ebitda": 4.1e9,
        "gross_margin": 0.33, "operating_margin": -0.06,
        "short_ratio": 3.2, "52w_low": 18.51, "52w_high": 43.73,
        "current_price": 20.14, "market_cap": 85.3e9,
        "net_debt_to_equity": 0.31, "analyst_target": 27.50,
    },
    {
        "ticker": "PARA", "name": "Paramount Global", "sector": "Communication Services",
        "pct_6m": -51.6,
        "pe_ratio": None, "forward_pe": 14.2, "pb_ratio": 0.47,
        "ev_ebitda": 7.8, "profit_margin": -0.11, "roe": -0.14,
        "current_ratio": 1.09, "debt_to_equity": 156.0,
        "revenue_growth": -3.1, "free_cash_flow": 0.6e9, "ebitda": 2.4e9,
        "gross_margin": 0.31, "operating_margin": -0.02,
        "short_ratio": 4.1, "52w_low": 8.45, "52w_high": 22.30,
        "current_price": 9.82, "market_cap": 6.4e9,
        "net_debt_to_equity": 1.21, "analyst_target": 14.00,
    },
    {
        "ticker": "WBD", "name": "Warner Bros. Discovery", "sector": "Communication Services",
        "pct_6m": -48.3,
        "pe_ratio": None, "forward_pe": 11.6, "pb_ratio": 0.38,
        "ev_ebitda": 5.9, "profit_margin": -0.08, "roe": -0.12,
        "current_ratio": 0.91, "debt_to_equity": 198.0,
        "revenue_growth": -2.7, "free_cash_flow": 1.8e9, "ebitda": 6.1e9,
        "gross_margin": 0.44, "operating_margin": 0.03,
        "short_ratio": 3.8, "52w_low": 5.34, "52w_high": 12.71,
        "current_price": 6.12, "market_cap": 14.8e9,
        "net_debt_to_equity": 2.41, "analyst_target": 9.50,
    },
    {
        "ticker": "VZ", "name": "Verizon Communications", "sector": "Communication Services",
        "pct_6m": -38.7,
        "pe_ratio": 8.2, "forward_pe": 7.9, "pb_ratio": 1.51,
        "ev_ebitda": 6.4, "profit_margin": 0.08, "roe": 0.17,
        "current_ratio": 0.72, "debt_to_equity": 188.0,
        "revenue_growth": 0.8, "free_cash_flow": 14.2e9, "ebitda": 48.1e9,
        "gross_margin": 0.56, "operating_margin": 0.20,
        "short_ratio": 2.1, "52w_low": 30.54, "52w_high": 54.33,
        "current_price": 31.88, "market_cap": 134.4e9,
        "net_debt_to_equity": 1.72, "analyst_target": 42.00,
    },
    {
        "ticker": "BMY", "name": "Bristol-Myers Squibb", "sector": "Health Care",
        "pct_6m": -37.4,
        "pe_ratio": None, "forward_pe": 6.1, "pb_ratio": 2.34,
        "ev_ebitda": 5.8, "profit_margin": -0.19, "roe": -0.22,
        "current_ratio": 1.18, "debt_to_equity": 214.0,
        "revenue_growth": 5.4, "free_cash_flow": 8.9e9, "ebitda": 14.5e9,
        "gross_margin": 0.72, "operating_margin": -0.09,
        "short_ratio": 1.8, "52w_low": 31.55, "52w_high": 60.73,
        "current_price": 34.22, "market_cap": 68.1e9,
        "net_debt_to_equity": 1.54, "analyst_target": 52.00,
    },
    {
        "ticker": "MU", "name": "Micron Technology", "sector": "Information Technology",
        "pct_6m": -36.9,
        "pe_ratio": 22.4, "forward_pe": 11.8, "pb_ratio": 1.87,
        "ev_ebitda": 7.2, "profit_margin": 0.14, "roe": 0.09,
        "current_ratio": 2.71, "debt_to_equity": 27.0,
        "revenue_growth": 61.6, "free_cash_flow": 1.3e9, "ebitda": 8.9e9,
        "gross_margin": 0.35, "operating_margin": 0.19,
        "short_ratio": 2.6, "52w_low": 67.77, "52w_high": 157.54,
        "current_price": 79.14, "market_cap": 87.2e9,
        "net_debt_to_equity": 0.11, "analyst_target": 125.00,
    },
    {
        "ticker": "NKE", "name": "Nike Inc.", "sector": "Consumer Discretionary",
        "pct_6m": -35.8,
        "pe_ratio": 21.0, "forward_pe": 17.5, "pb_ratio": 9.41,
        "ev_ebitda": 12.8, "profit_margin": 0.07, "roe": 0.38,
        "current_ratio": 2.48, "debt_to_equity": 89.0,
        "revenue_growth": -10.4, "free_cash_flow": 3.1e9, "ebitda": 4.9e9,
        "gross_margin": 0.44, "operating_margin": 0.09,
        "short_ratio": 2.9, "52w_low": 59.52, "52w_high": 101.29,
        "current_price": 63.44, "market_cap": 95.4e9,
        "net_debt_to_equity": 0.42, "analyst_target": 87.00,
    },
    {
        "ticker": "BA", "name": "Boeing Co.", "sector": "Industrials",
        "pct_6m": -34.6,
        "pe_ratio": None, "forward_pe": 34.8, "pb_ratio": None,
        "ev_ebitda": 28.4, "profit_margin": -0.12, "roe": None,
        "current_ratio": 1.07, "debt_to_equity": None,
        "revenue_growth": 4.8, "free_cash_flow": -2.1e9, "ebitda": 2.8e9,
        "gross_margin": 0.12, "operating_margin": -0.06,
        "short_ratio": 3.5, "52w_low": 137.02, "52w_high": 222.78,
        "current_price": 148.23, "market_cap": 113.9e9,
        "net_debt_to_equity": None, "analyst_target": 195.00,
    },
    {
        "ticker": "UPS", "name": "United Parcel Service", "sector": "Industrials",
        "pct_6m": -33.2,
        "pe_ratio": 14.8, "forward_pe": 13.1, "pb_ratio": 5.12,
        "ev_ebitda": 8.9, "profit_margin": 0.06, "roe": 0.41,
        "current_ratio": 1.24, "debt_to_equity": 131.0,
        "revenue_growth": -9.3, "free_cash_flow": 4.6e9, "ebitda": 9.4e9,
        "gross_margin": 0.21, "operating_margin": 0.09,
        "short_ratio": 2.2, "52w_low": 115.24, "52w_high": 181.64,
        "current_price": 120.81, "market_cap": 104.0e9,
        "net_debt_to_equity": 0.78, "analyst_target": 155.00,
    },
    {
        "ticker": "T", "name": "AT&T Inc.", "sector": "Communication Services",
        "pct_6m": -32.1,
        "pe_ratio": 10.1, "forward_pe": 9.4, "pb_ratio": 1.14,
        "ev_ebitda": 5.9, "profit_margin": 0.10, "roe": 0.11,
        "current_ratio": 0.63, "debt_to_equity": 114.0,
        "revenue_growth": 0.9, "free_cash_flow": 15.4e9, "ebitda": 43.2e9,
        "gross_margin": 0.59, "operating_margin": 0.18,
        "short_ratio": 1.6, "52w_low": 14.51, "52w_high": 22.83,
        "current_price": 15.32, "market_cap": 109.3e9,
        "net_debt_to_equity": 0.92, "analyst_target": 21.00,
    },
    {
        "ticker": "CVS", "name": "CVS Health", "sector": "Health Care",
        "pct_6m": -31.8,
        "pe_ratio": None, "forward_pe": 8.7, "pb_ratio": 0.74,
        "ev_ebitda": 5.4, "profit_margin": -0.02, "roe": -0.04,
        "current_ratio": 0.91, "debt_to_equity": 89.0,
        "revenue_growth": 4.1, "free_cash_flow": 6.2e9, "ebitda": 14.9e9,
        "gross_margin": 0.18, "operating_margin": 0.01,
        "short_ratio": 2.8, "52w_low": 44.55, "52w_high": 76.39,
        "current_price": 47.18, "market_cap": 58.9e9,
        "net_debt_to_equity": 0.54, "analyst_target": 68.00,
    },
    {
        "ticker": "D", "name": "Dominion Energy", "sector": "Utilities",
        "pct_6m": -30.5,
        "pe_ratio": 14.2, "forward_pe": 15.4, "pb_ratio": 1.21,
        "ev_ebitda": 9.6, "profit_margin": 0.09, "roe": 0.08,
        "current_ratio": 0.52, "debt_to_equity": 176.0,
        "revenue_growth": -5.2, "free_cash_flow": -1.4e9, "ebitda": 5.8e9,
        "gross_margin": 0.42, "operating_margin": 0.18,
        "short_ratio": 2.4, "52w_low": 29.79, "52w_high": 51.06,
        "current_price": 30.87, "market_cap": 25.7e9,
        "net_debt_to_equity": 1.61, "analyst_target": 43.00,
    },
    {
        "ticker": "PFE", "name": "Pfizer Inc.", "sector": "Health Care",
        "pct_6m": -29.7,
        "pe_ratio": None, "forward_pe": 9.4, "pb_ratio": 1.29,
        "ev_ebitda": 6.7, "profit_margin": -0.28, "roe": -0.12,
        "current_ratio": 1.47, "debt_to_equity": 60.0,
        "revenue_growth": -41.6, "free_cash_flow": 3.8e9, "ebitda": 12.1e9,
        "gross_margin": 0.65, "operating_margin": -0.16,
        "short_ratio": 2.1, "52w_low": 24.48, "52w_high": 39.21,
        "current_price": 26.74, "market_cap": 151.5e9,
        "net_debt_to_equity": 0.28, "analyst_target": 34.00,
    },
    {
        "ticker": "FDX", "name": "FedEx Corp.", "sector": "Industrials",
        "pct_6m": -28.9,
        "pe_ratio": 12.6, "forward_pe": 11.2, "pb_ratio": 2.14,
        "ev_ebitda": 6.1, "profit_margin": 0.05, "roe": 0.18,
        "current_ratio": 1.62, "debt_to_equity": 88.0,
        "revenue_growth": -2.6, "free_cash_flow": 2.8e9, "ebitda": 7.2e9,
        "gross_margin": 0.23, "operating_margin": 0.08,
        "short_ratio": 2.7, "52w_low": 209.68, "52w_high": 316.67,
        "current_price": 218.44, "market_cap": 54.8e9,
        "net_debt_to_equity": 0.51, "analyst_target": 285.00,
    },
    {
        "ticker": "DIS", "name": "Walt Disney Co.", "sector": "Communication Services",
        "pct_6m": -27.8,
        "pe_ratio": 34.1, "forward_pe": 18.2, "pb_ratio": 1.58,
        "ev_ebitda": 9.8, "profit_margin": 0.04, "roe": 0.04,
        "current_ratio": 1.14, "debt_to_equity": 45.0,
        "revenue_growth": 3.7, "free_cash_flow": 5.4e9, "ebitda": 12.8e9,
        "gross_margin": 0.37, "operating_margin": 0.06,
        "short_ratio": 1.9, "52w_low": 79.51, "52w_high": 122.94,
        "current_price": 85.72, "market_cap": 155.1e9,
        "net_debt_to_equity": 0.23, "analyst_target": 115.00,
    },
]


# ─── Live data helpers (requires internet) ────────────────────────────────────
YAHOO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def check_internet() -> bool:
    """Quick check for internet connectivity."""
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search?q=AAPL",
            headers=YAHOO_HEADERS, timeout=6
        )
        return r.status_code < 400
    except Exception:
        return False


def get_sp500_tickers_live() -> list[dict]:
    """Fetch current S&P 500 constituents from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    df.columns = df.columns.str.strip()
    tickers = []
    for _, row in df.iterrows():
        symbol = str(row.get("Symbol", "")).strip().replace(".", "-")
        name = str(row.get("Security", "")).strip()
        sector = str(row.get("GICS Sector", "")).strip()
        if symbol:
            tickers.append({"ticker": symbol, "name": name, "sector": sector})
    return tickers


def fetch_price_change(ticker: str, period1: int, period2: int) -> float | None:
    """Fetch 6-month % price change for a single ticker."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?interval=1mo&period1={period1}&period2={period2}"
    )
    try:
        r = requests.get(url, headers=YAHOO_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        closes = (
            data.get("chart", {})
            .get("result", [{}])[0]
            .get("indicators", {})
            .get("adjclose", [{}])[0]
            .get("adjclose", [])
        )
        closes = [c for c in closes if c is not None]
        if len(closes) >= 2:
            return round((closes[-1] - closes[0]) / closes[0] * 100, 2)
    except Exception:
        pass
    return None


def fetch_fundamentals_live(ticker: str) -> dict:
    """Fetch key fundamentals for a ticker from Yahoo Finance."""
    url = (
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        "?modules=defaultKeyStatistics,summaryDetail,financialData,"
        "incomeStatementHistory,balanceSheetHistory"
    )
    try:
        r = requests.get(url, headers=YAHOO_HEADERS, timeout=12)
        if r.status_code != 200:
            return {}
        data = r.json().get("quoteSummary", {}).get("result", [{}])[0]

        ks = data.get("defaultKeyStatistics", {})
        sd = data.get("summaryDetail", {})
        fd = data.get("financialData", {})

        def _v(d, key):
            val = d.get(key, {})
            return val.get("raw") if isinstance(val, dict) else val

        inc = data.get("incomeStatementHistory", {}).get("incomeStatementHistory", [{}])
        rev_ttm  = _v(inc[0], "totalRevenue") if inc else None
        rev_prev = _v(inc[1], "totalRevenue") if len(inc) > 1 else None
        rev_growth = None
        if rev_ttm and rev_prev and rev_prev != 0:
            rev_growth = (rev_ttm - rev_prev) / abs(rev_prev) * 100

        bs = data.get("balanceSheetHistory", {}).get("balanceSheetStatements", [{}])
        total_debt = _v(bs[0], "longTermDebt") if bs else None
        cash       = _v(bs[0], "cash")         if bs else None
        net_debt   = (total_debt - cash) if (total_debt is not None and cash is not None) else None
        book_v = _v(ks, "bookValue")
        shares = _v(ks, "sharesOutstanding")
        nde = None
        if net_debt and book_v and shares:
            equity = book_v * shares
            nde = net_debt / equity if equity else None

        return {
            "pe_ratio":          _v(sd, "trailingPE"),
            "forward_pe":        _v(sd, "forwardPE"),
            "pb_ratio":          _v(ks, "priceToBook"),
            "ev_ebitda":         _v(ks, "enterpriseToEbitda"),
            "profit_margin":     _v(fd, "profitMargins"),
            "roe":               _v(fd, "returnOnEquity"),
            "current_ratio":     _v(fd, "currentRatio"),
            "debt_to_equity":    _v(fd, "debtToEquity"),
            "revenue_growth":    rev_growth,
            "free_cash_flow":    _v(fd, "freeCashflow"),
            "ebitda":            _v(fd, "ebitda"),
            "gross_margin":      _v(fd, "grossMargins"),
            "operating_margin":  _v(fd, "operatingMargins"),
            "short_ratio":       _v(ks, "shortRatio"),
            "52w_low":           _v(sd, "fiftyTwoWeekLow"),
            "52w_high":          _v(sd, "fiftyTwoWeekHigh"),
            "current_price":     _v(fd, "currentPrice"),
            "market_cap":        _v(sd, "marketCap"),
            "net_debt_to_equity": nde,
            "analyst_target":    _v(fd, "targetMeanPrice"),
        }
    except Exception:
        return {}


def run_live_analysis() -> list[dict]:
    """Full live-data pipeline: fetch S&P 500 tickers, prices, fundamentals."""
    console.print("[bold]Step 1/3[/bold] Fetching S&P 500 constituents from Wikipedia…")
    try:
        sp500 = get_sp500_tickers_live()
    except Exception:
        sp500 = [{"ticker": t, "name": n, "sector": s} for t, n, s in SP500_SAMPLE]
    console.print(f"  [green]✓[/green] {len(sp500)} companies loaded\n")

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=183)
    period1  = int(start_dt.timestamp())
    period2  = int(end_dt.timestamp())

    console.print("[bold]Step 2/3[/bold] Fetching 6-month price performance for all tickers…")
    console.print(f"  [dim]Querying {len(sp500)} tickers with throttling[/dim]")

    price_changes: dict[str, float] = {}
    ticker_meta   = {s["ticker"]: s for s in sp500}

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("{task.completed}/{task.total}"), console=console,
    ) as prog:
        task = prog.add_task("Fetching prices…", total=len(sp500))
        for info in sp500:
            tk = info["ticker"]
            chg = fetch_price_change(tk, period1, period2)
            if chg is not None:
                price_changes[tk] = chg
            prog.advance(task)
            time.sleep(0.08)

    console.print(f"  [green]✓[/green] Prices retrieved for {len(price_changes)} tickers\n")

    worst_15 = sorted(price_changes.items(), key=lambda x: x[1])[:15]

    console.print("[bold]Step 3/3[/bold] Fetching fundamentals for top 15 worst performers…")
    results = []
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("{task.completed}/{task.total}"), console=console,
    ) as prog:
        task = prog.add_task("Fetching fundamentals…", total=len(worst_15))
        for ticker, pct_6m in worst_15:
            f = fetch_fundamentals_live(ticker)
            meta = ticker_meta.get(ticker, {"name": ticker, "sector": "Unknown"})
            score, signals = compute_recovery_score(f, pct_6m)
            results.append({
                "ticker": ticker, "name": meta["name"], "sector": meta["sector"],
                "pct_6m": pct_6m, "score": score, "signals": signals, **f,
            })
            prog.advance(task)
            time.sleep(0.4)
    console.print(f"  [green]✓[/green] Fundamentals fetched\n")
    return results


def run_demo_analysis() -> list[dict]:
    """Return scored demo dataset — no network required."""
    results = []
    for row in DEMO_WORST_15:
        pct_6m = row["pct_6m"]
        f = {k: v for k, v in row.items() if k not in ("ticker","name","sector","pct_6m")}
        score, signals = compute_recovery_score(f, pct_6m)
        results.append({**row, "score": score, "signals": signals})
    # Sort by pct_6m ascending (worst first)
    results.sort(key=lambda x: x["pct_6m"])
    for i, r in enumerate(results, 1):
        r["rank"] = i
    return results


# ─── Recovery Score ───────────────────────────────────────────────────────────
def compute_recovery_score(f: dict, pct_drop: float) -> tuple[float, list[str]]:
    score   = 0.0
    signals = []

    pe  = f.get("pe_ratio")
    fpe = f.get("forward_pe")
    pb  = f.get("pb_ratio")

    if pe and 0 < pe < 15:
        score += 15; signals.append(f"Low trailing P/E ({pe:.1f}x)")
    elif pe and 0 < pe < 25:
        score += 8

    if fpe and 0 < fpe < 12:
        score += 12; signals.append(f"Attractive forward P/E ({fpe:.1f}x)")
    elif fpe and 0 < fpe < 20:
        score += 6

    if pb and 0 < pb < 1.5:
        score += 10; signals.append(f"Trading near/below book (P/B {pb:.2f}x)")
    elif pb and 0 < pb < 3:
        score += 5

    roe    = f.get("roe")
    margin = f.get("profit_margin")
    gm     = f.get("gross_margin")

    if roe and roe > 0.15:
        score += 10; signals.append(f"Strong ROE ({roe*100:.1f}%)")
    elif roe and roe > 0.05:
        score += 5

    if margin and margin > 0.10:
        score += 8; signals.append(f"Healthy net margin ({margin*100:.1f}%)")
    elif margin and margin > 0:
        score += 3

    if gm and gm > 0.40:
        score += 5; signals.append(f"High gross margin ({gm*100:.1f}%)")

    cr  = f.get("current_ratio")
    de  = f.get("debt_to_equity")
    fcf = f.get("free_cash_flow")

    if cr and cr > 2.0:
        score += 8; signals.append(f"Strong liquidity (current ratio {cr:.2f})")
    elif cr and cr > 1.2:
        score += 4

    if de is not None and de < 50:
        score += 8; signals.append(f"Low debt/equity ({de:.0f}%)")
    elif de is not None and de < 100:
        score += 4

    if fcf and fcf > 0:
        score += 8; signals.append("Positive free cash flow")

    if pct_drop < -40:
        score += 10; signals.append(f"Deep value: {pct_drop:.1f}% decline creates mean-reversion potential")
    elif pct_drop < -25:
        score += 6; signals.append(f"Significant {pct_drop:.1f}% correction from prior highs")

    price  = f.get("current_price")
    target = f.get("analyst_target")
    if price and target and price > 0:
        upside = (target - price) / price * 100
        if upside > 30:
            score += 6; signals.append(f"High consensus analyst upside ({upside:.0f}%)")
        elif upside > 15:
            score += 3; signals.append(f"Moderate analyst upside ({upside:.0f}%)")

    return min(round(score, 1), 100), signals


def score_label(score: float) -> tuple[str, str]:
    if score >= 70: return "STRONG BUY", "bold green"
    if score >= 52: return "BUY",         "green"
    if score >= 38: return "WATCH",       "yellow"
    return               "SPECULATIVE",   "red"


# ─── Formatting helpers ───────────────────────────────────────────────────────
def fmt_pct(v, color_neg=True) -> str:
    if v is None: return "[dim]N/A[/dim]"
    col = ("red" if v < 0 else "green") if color_neg else "cyan"
    return f"[{col}]{v:+.1f}%[/{col}]"

def fmt_ratio(v, dec=1) -> str:
    return f"[dim]N/A[/dim]" if v is None else f"{v:.{dec}f}x"

def fmt_mcap(v) -> str:
    if v is None: return "[dim]N/A[/dim]"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    return f"${v/1e6:.0f}M"

def fmt_price(v) -> str:
    return "[dim]N/A[/dim]" if v is None else f"${v:.2f}"

def fmt_margin(v) -> str:
    return "[dim]N/A[/dim]" if v is None else fmt_pct(v * 100, color_neg=False)


# ─── Render functions ─────────────────────────────────────────────────────────
def render_summary_table(results: list[dict], demo: bool) -> None:
    mode_tag = "[dim](illustrative demo data)[/dim]" if demo else "[dim](live data)[/dim]"
    console.print(
        Rule(f"[bold cyan]Top 15 Worst-Performing S&P 500 Stocks — Past 6 Months  {mode_tag}[/bold cyan]")
    )
    console.print(f"[dim]Report generated: {datetime.now().strftime('%B %d, %Y')}[/dim]\n")

    tbl = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan",
                show_lines=False, expand=False)
    tbl.add_column("#",       style="dim",        justify="right", width=3)
    tbl.add_column("Ticker",  style="bold white",                  width=7)
    tbl.add_column("Company",                                       width=26)
    tbl.add_column("Sector",                                        width=21)
    tbl.add_column("6M Chg",                      justify="right", width=9)
    tbl.add_column("Price",                        justify="right", width=8)
    tbl.add_column("Mkt Cap",                      justify="right", width=9)
    tbl.add_column("P/E",                          justify="right", width=7)
    tbl.add_column("Fwd P/E",                      justify="right", width=8)
    tbl.add_column("P/B",                          justify="right", width=7)
    tbl.add_column("ROE",                          justify="right", width=7)
    tbl.add_column("D/E",                          justify="right", width=8)
    tbl.add_column("FCF",                          justify="center",width=4)
    tbl.add_column("Score",                        justify="right", width=6)
    tbl.add_column("Signal",                                        width=14)

    for r in results:
        fcf    = r.get("free_cash_flow")
        fcf_mk = "[green]✓[/green]" if fcf and fcf > 0 else "[red]✗[/red]"
        sc     = r["score"]
        label, lc = score_label(sc)
        de     = r.get("debt_to_equity")
        de_s   = f"{de:.0f}%" if de is not None else "[dim]N/A[/dim]"
        if de and de > 150: de_s = f"[red]{de:.0f}%[/red]"
        roe    = r.get("roe")
        roe_s  = f"{roe*100:.1f}%" if roe is not None else "[dim]N/A[/dim]"

        tbl.add_row(
            str(r.get("rank","")),
            r["ticker"],
            r["name"][:25],
            r["sector"][:20],
            fmt_pct(r["pct_6m"]),
            fmt_price(r.get("current_price")),
            fmt_mcap(r.get("market_cap")),
            fmt_ratio(r.get("pe_ratio")),
            fmt_ratio(r.get("forward_pe")),
            fmt_ratio(r.get("pb_ratio"), 2),
            roe_s,
            de_s,
            fcf_mk,
            f"[bold]{sc:.0f}[/bold]",
            f"[{lc}]{label}[/{lc}]",
        )
    console.print(tbl)
    console.print()


def render_detail_cards(results_by_score: list[dict]) -> None:
    console.print(Rule("[bold cyan]Detailed Recovery Analysis — Ranked by Recovery Score[/bold cyan]"))
    console.print()

    for i, r in enumerate(results_by_score, 1):
        ticker = r["ticker"]
        name   = r["name"]
        score  = r["score"]
        label, lc = score_label(score)

        # URLs
        dl_url = daloopa_url(ticker)
        yf_url = yahoo_finance_url(ticker)
        sa_url = seekingalpha_url(ticker)
        fv_url = finviz_url(ticker)
        mt_url = macrotrends_url(ticker)

        # Rich clickable hyperlinks
        dl_link = hyperlink("Daloopa (model)",  dl_url)
        yf_link = hyperlink("Yahoo Finance",    yf_url)
        sa_link = hyperlink("Seeking Alpha",    sa_url)
        fv_link = hyperlink("Finviz",           fv_url)
        mt_link = hyperlink("Macrotrends",      mt_url)

        price  = r.get("current_price")
        low52  = r.get("52w_low")
        high52 = r.get("52w_high")
        target = r.get("analyst_target")

        pct_low  = ((price - low52) / low52 * 100) if price and low52 and low52 > 0 else None
        pct_high = ((price - high52) / high52 * 100) if price and high52 and high52 > 0 else None
        upside   = ((target - price) / price * 100) if price and target and price > 0 else None

        # Signals
        sig_text = ""
        for sig in (r.get("signals") or []):
            sig_text += f"  [green]▸[/green] {escape(sig)}\n"
        if not sig_text:
            sig_text = "  [dim]No strong positive signals[/dim]\n"

        # Warnings
        warnings = []
        de  = r.get("debt_to_equity")
        cr  = r.get("current_ratio")
        mg  = r.get("profit_margin")
        sr  = r.get("short_ratio")
        fcf = r.get("free_cash_flow")

        if de and de > 200:       warnings.append(f"High leverage — D/E {de:.0f}%")
        if cr and cr < 1.0:       warnings.append(f"Liquidity risk — current ratio {cr:.2f}")
        if mg is not None and mg < 0: warnings.append(f"Unprofitable — net margin {mg*100:.1f}%")
        if sr and sr > 5:         warnings.append(f"Heavy short interest — {sr:.1f}-day cover ratio")
        if fcf and fcf < 0:       warnings.append("Negative free cash flow — cash burn")

        warn_text = ""
        for w in warnings:
            warn_text += f"  [red]⚠[/red]  {escape(w)}\n"
        if not warn_text:
            warn_text = "  [dim]No major red flags[/dim]\n"

        de_str  = f"{de:.0f}%" if de is not None else "N/A"
        cr_str  = f"{cr:.2f}"  if cr is not None else "N/A"

        card = (
            f"[bold white]{i}. {name}[/bold white]  "
            f"[{lc}]({label}  ·  Recovery Score: {score:.0f}/100)[/{lc}]\n"
            f"[dim]Sector: {r['sector']}[/dim]\n\n"

            f"[bold]── Price Action ─────────────────────────────────────[/bold]\n"
            f"  Current Price  : {fmt_price(price)}\n"
            f"  6-Month Return : {fmt_pct(r['pct_6m'])}\n"
            f"  52-Week Low    : {fmt_price(low52)}  ({fmt_pct(pct_low, False)} above low)\n"
            f"  52-Week High   : {fmt_price(high52)}  ({fmt_pct(pct_high)} from high)\n"
            f"  Analyst Target : {fmt_price(target)}  (consensus upside: {fmt_pct(upside, False)})\n\n"

            f"[bold]── Valuation ─────────────────────────────────────────[/bold]\n"
            f"  Market Cap  : {fmt_mcap(r.get('market_cap'))}\n"
            f"  P/E (trail) : {fmt_ratio(r.get('pe_ratio'))}\n"
            f"  P/E (fwd)   : {fmt_ratio(r.get('forward_pe'))}\n"
            f"  P/B         : {fmt_ratio(r.get('pb_ratio'), 2)}\n"
            f"  EV/EBITDA   : {fmt_ratio(r.get('ev_ebitda'))}\n\n"

            f"[bold]── Profitability ─────────────────────────────────────[/bold]\n"
            f"  Gross Margin  : {fmt_margin(r.get('gross_margin'))}\n"
            f"  Oper. Margin  : {fmt_margin(r.get('operating_margin'))}\n"
            f"  Net Margin    : {fmt_margin(r.get('profit_margin'))}\n"
            f"  ROE           : {fmt_margin(r.get('roe'))}\n"
            f"  Free Cash Flow: {'[green]Positive[/green]' if fcf and fcf > 0 else '[red]Negative / None[/red]'}\n\n"

            f"[bold]── Balance Sheet ─────────────────────────────────────[/bold]\n"
            f"  Current Ratio : {cr_str}\n"
            f"  Debt / Equity : {de_str}\n\n"

            f"[bold]── Recovery Signals ──────────────────────────────────[/bold]\n"
            + sig_text + "\n"

            f"[bold]── Risk Flags ────────────────────────────────────────[/bold]\n"
            + warn_text + "\n"

            f"[bold]── Research Links ────────────────────────────────────[/bold]\n"
            f"  {dl_link}  ·  {yf_link}  ·  {sa_link}  ·  {fv_link}  ·  {mt_link}\n"
            f"  [dim]Daloopa:[/dim] {dl_url}"
        )

        border_col = lc.replace("bold ", "")
        console.print(
            Panel(card, title=f"[bold cyan]{ticker}[/bold cyan]",
                  border_style=border_col, expand=False, padding=(0, 2))
        )
        console.print()


def render_watchlist(results_by_score: list[dict]) -> None:
    console.print(Rule("[bold cyan]Recovery Watchlist — Score ≥ 52 (BUY or STRONG BUY)[/bold cyan]"))
    console.print()

    watchlist = [r for r in results_by_score if r["score"] >= 52]
    if not watchlist:
        console.print(
            "[dim]No stocks met the ≥52 threshold. "
            "Market may be in distress — consider broader macro context.[/dim]\n"
        )
        return

    wt = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    wt.add_column("Ticker",    style="bold white", width=7)
    wt.add_column("Company",                       width=26)
    wt.add_column("Sector",                        width=22)
    wt.add_column("6M Drop",   justify="right",    width=9)
    wt.add_column("Score",     justify="right",    width=6)
    wt.add_column("Top Signal",                    width=40)
    wt.add_column("Daloopa",   style="blue",       width=42)

    for r in watchlist:
        label, lc = score_label(r["score"])
        top_sig = (r["signals"][0] if r.get("signals") else "—")[:39]
        wt.add_row(
            r["ticker"],
            r["name"][:25],
            r["sector"][:21],
            fmt_pct(r["pct_6m"]),
            f"[{lc}]{r['score']:.0f}[/{lc}]",
            top_sig,
            daloopa_url(r["ticker"]),
        )
    console.print(wt)
    console.print()


# ─── Entry point ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Stock Recovery Analysis — Top 15 worst S&P 500 stocks (6 months)"
    )
    parser.add_argument("--demo", action="store_true", help="Use illustrative demo dataset (no internet)")
    parser.add_argument("--live", action="store_true", help="Force live data (error if no internet)")
    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold cyan]Stock Recovery Analysis[/bold cyan]\n"
            "[dim]Top 15 worst-performing S&P 500 stocks (6 months)  ·  "
            "Fundamentals  ·  Recovery Scoring  ·  Daloopa Links[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    use_demo = args.demo

    if not use_demo and not args.live:
        console.print("[dim]Checking internet connectivity…[/dim]")
        if not check_internet():
            console.print(
                "[yellow]⚠  No internet access detected — running with illustrative demo dataset.[/yellow]\n"
                "[dim]Run with --live to force live data or --demo to skip this check.[/dim]\n"
            )
            use_demo = True
        else:
            console.print("[green]✓[/green] Internet connected — fetching live data\n")

    if use_demo:
        console.print(
            Panel(
                "[bold yellow]Demo Mode[/bold yellow]\n"
                "The figures below are illustrative and based on well-known market scenarios.\n"
                "Run without [bold]--demo[/bold] in an internet-connected environment for live data.",
                border_style="yellow", expand=False,
            )
        )
        console.print()
        results = run_demo_analysis()
    else:
        results = run_live_analysis()
        for i, r in enumerate(results, 1):
            r["rank"] = i

    # Render outputs
    render_summary_table(results, demo=use_demo)

    results_by_score = sorted(results, key=lambda x: x["score"], reverse=True)
    render_detail_cards(results_by_score)
    render_watchlist(results_by_score)

    console.print(
        Panel(
            "[bold yellow]Disclaimer[/bold yellow]\n"
            "This output is for informational and educational purposes only.\n"
            "It does not constitute investment advice. Past performance is no guarantee of future results.\n"
            "Always conduct your own due diligence. For structured financial models and KPI-level data,\n"
            f"visit [link=https://app.daloopa.com]https://app.daloopa.com[/link].\n"
            "For SEC filings, see [link=https://www.sec.gov/edgar]EDGAR[/link].",
            border_style="yellow", expand=False,
        )
    )


if __name__ == "__main__":
    main()
