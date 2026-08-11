-- fct_returns_history: full price and returns history for all tickers.
-- Used by the Streamlit chart pages for time series plots.

SELECT
    ticker         AS TICKER,
    name           AS NAME,
    price_date     AS PRICE_DATE,
    close_price    AS CLOSE_PRICE,
    volume         AS VOLUME,
    daily_return   AS DAILY_RETURN,
    ma_7d          AS MA_7D,
    ma_30d         AS MA_30D,
    volatility_30d AS VOLATILITY_30D,
    -- Cumulative return from the earliest date in the dataset
    EXP(SUM(log_return) OVER (
        PARTITION BY ticker
        ORDER BY price_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )) - 1                                          AS CUMULATIVE_RETURN
FROM {{ ref('int_daily_returns') }}
