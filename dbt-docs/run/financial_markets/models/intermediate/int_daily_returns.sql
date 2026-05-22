
  create or replace   view FINANCIAL_MARKETS.PUBLIC.int_daily_returns
  
  
  
  
  as (
    -- int_daily_returns: calculate daily and cumulative returns per ticker.
--
-- Daily return = (today's close - yesterday's close) / yesterday's close
-- This is the fundamental metric for all financial analysis.
-- LAG() is a window function — it looks at the previous row's value.

WITH lagged AS (
    SELECT
        ticker,
        name,
        price_date,
        close_price,
        volume,
        LAG(close_price) OVER (
            PARTITION BY ticker
            ORDER BY price_date
        )                                           AS prev_close
    FROM FINANCIAL_MARKETS.PUBLIC.stg_prices
)
SELECT
    ticker,
    name,
    price_date,
    close_price,
    volume,
    prev_close,
    -- Daily return as a decimal (0.02 = 2%)
    ROUND((close_price - prev_close) / NULLIF(prev_close, 0), 6)    AS daily_return,
    -- Log return — better for compounding calculations
    ROUND(LN(close_price / NULLIF(prev_close, 0)), 6)               AS log_return,
    -- 7-day and 30-day moving averages
    ROUND(AVG(close_price) OVER (
        PARTITION BY ticker
        ORDER BY price_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 4)                                                            AS ma_7d,
    ROUND(AVG(close_price) OVER (
        PARTITION BY ticker
        ORDER BY price_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 4)                                                            AS ma_30d,
    -- 30-day rolling volatility (annualised standard deviation of daily returns)
    ROUND(STDDEV(
        (close_price - prev_close) / NULLIF(prev_close, 0)
    ) OVER (
        PARTITION BY ticker
        ORDER BY price_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) * SQRT(252), 4)                                               AS volatility_30d
FROM lagged
WHERE prev_close IS NOT NULL
  );

