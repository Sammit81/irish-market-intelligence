-- fct_returns_history: full price and returns history for all tickers.
-- Used by the Streamlit chart pages for time series plots.

SELECT
    ticker,
    name,
    price_date,
    close_price,
    volume,
    daily_return,
    ma_7d,
    ma_30d,
    volatility_30d,
    -- Cumulative return from the earliest date in the dataset
    EXP(SUM(log_return) OVER (
        PARTITION BY ticker
        ORDER BY price_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )) - 1                                          AS cumulative_return
FROM FINANCIAL_MARKETS.PUBLIC.int_daily_returns