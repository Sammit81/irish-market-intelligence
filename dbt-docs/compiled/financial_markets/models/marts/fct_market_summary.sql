-- fct_market_summary: one row per ticker with latest price and key metrics.

WITH latest_date AS (
    SELECT ticker, MAX(price_date) AS max_date
    FROM FINANCIAL_MARKETS.PUBLIC.int_daily_returns
    GROUP BY ticker
),
week52 AS (
    -- 52-week high and low aggregated separately — avoids fan-out from self-join
    SELECT
        ticker,
        MAX(close_price) AS week52_high,
        MIN(close_price) AS week52_low
    FROM FINANCIAL_MARKETS.PUBLIC.int_daily_returns
    WHERE price_date >= DATEADD('day', -365, CURRENT_DATE())
    GROUP BY ticker
),
ytd_start AS (
    SELECT ticker, MIN(price_date) AS ytd_start_date
    FROM FINANCIAL_MARKETS.PUBLIC.int_daily_returns
    WHERE YEAR(price_date) = YEAR(CURRENT_DATE())
    GROUP BY ticker
),
ytd_price AS (
    SELECT r.ticker, r.close_price AS ytd_open_price
    FROM FINANCIAL_MARKETS.PUBLIC.int_daily_returns r
    JOIN ytd_start y ON r.ticker = y.ticker AND r.price_date = y.ytd_start_date
)
SELECT
    r.ticker,
    r.name,
    r.price_date                                                            AS latest_date,
    r.close_price                                                           AS latest_price,
    r.daily_return,
    r.ma_7d,
    r.ma_30d,
    r.volatility_30d,
    w.week52_high,
    w.week52_low,
    ROUND((r.close_price - y.ytd_open_price) / NULLIF(y.ytd_open_price, 0), 4)  AS ytd_return,
    ROUND((r.close_price - w.week52_high) / NULLIF(w.week52_high, 0), 4)        AS from_52w_high
FROM FINANCIAL_MARKETS.PUBLIC.int_daily_returns r
JOIN latest_date l  ON r.ticker = l.ticker AND r.price_date = l.max_date
JOIN week52 w       ON r.ticker = w.ticker
JOIN ytd_price y    ON r.ticker = y.ticker