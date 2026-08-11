-- fct_market_summary: one row per ticker with latest price and key metrics.

WITH latest_date AS (
    SELECT ticker, MAX(price_date) AS max_date
    FROM {{ ref('int_daily_returns') }}
    GROUP BY ticker
),
week52 AS (
    -- 52-week high and low aggregated separately — avoids fan-out from self-join
    SELECT
        ticker,
        MAX(close_price) AS WEEK52_HIGH,
        MIN(close_price) AS WEEK52_LOW
    FROM {{ ref('int_daily_returns') }}
    WHERE price_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
    GROUP BY ticker
),
ytd_start AS (
    SELECT ticker, MIN(price_date) AS ytd_start_date
    FROM {{ ref('int_daily_returns') }}
    WHERE EXTRACT(YEAR FROM price_date) = EXTRACT(YEAR FROM CURRENT_DATE())
    GROUP BY ticker
),
ytd_price AS (
    SELECT r.ticker, r.close_price AS ytd_open_price
    FROM {{ ref('int_daily_returns') }} r
    JOIN ytd_start y ON r.ticker = y.ticker AND r.price_date = y.ytd_start_date
)
SELECT
    r.ticker         AS TICKER,
    r.name           AS NAME,
    r.price_date                                                            AS LATEST_DATE,
    r.close_price                                                           AS LATEST_PRICE,
    r.daily_return   AS DAILY_RETURN,
    r.ma_7d          AS MA_7D,
    r.ma_30d         AS MA_30D,
    r.volatility_30d AS VOLATILITY_30D,
    w.week52_high    AS WEEK52_HIGH,
    w.week52_low     AS WEEK52_LOW,
    ROUND((r.close_price - y.ytd_open_price) / NULLIF(y.ytd_open_price, 0), 4)  AS YTD_RETURN,
    ROUND((r.close_price - w.week52_high) / NULLIF(w.week52_high, 0), 4)        AS FROM_52W_HIGH
FROM {{ ref('int_daily_returns') }} r
JOIN latest_date l  ON r.ticker = l.ticker AND r.price_date = l.max_date
JOIN week52 w       ON r.ticker = w.ticker
JOIN ytd_price y    ON r.ticker = y.ticker
