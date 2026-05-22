"""
Tickers tracked by the pipeline.

Groups:
  INDICES   — major market indices
  IRISH     — Irish-listed stocks (Dublin Stock Exchange / London)
  DUBLIN_TECH — US tech companies with major Dublin/EMEA HQs
  ETFS      — broad market ETFs
"""

INDICES = {
    "^GSPC":    "S&P 500",
    "^FTSE":    "FTSE 100",
    "^STOXX50E":"Euro Stoxx 50",
    "^IXIC":    "NASDAQ Composite",
}

IRISH = {
    # Large caps
    "CRH":      "CRH (NYSE)",           # moved primary listing to NYSE in 2023
    "BIRG.IR":  "Bank of Ireland",
    "RYA.IR":   "Ryanair",
    "KYGA.L":   "Kerry Group",
    "FLTR.L":   "Flutter Entertainment",
    "SKG.L":    "Smurfit Kappa",
    "A5G.IR":   "AIB Group",
    # Mid caps
    "KRX.IR":   "Kingspan Group",
    "GL9.IR":   "Glanbia",
    "DPLM.L":   "Diploma",
    "GNC.L":    "Greencore",
    "GFTU.L":   "Grafton Group",
    "C5H.IR":   "Cairn Homes",
    "IR5B.IR":  "Irish Continental Group",
}

DUBLIN_TECH = {
    "GOOGL": "Alphabet (Google)",
    "META":  "Meta",
    "MSFT":  "Microsoft",
    "AAPL":  "Apple",
    "AMZN":  "Amazon",
}

ETFS = {
    "SPY":    "SPDR S&P 500 ETF",
    "QQQ":    "Invesco NASDAQ ETF",
    "VWRL.L": "Vanguard All-World ETF",
    "CSPX.L": "iShares Core S&P 500 ETF",
}

# All tickers used in the pipeline
ALL_TICKERS = {
    **INDICES,
    **IRISH,
    **DUBLIN_TECH,
    **ETFS,
}
