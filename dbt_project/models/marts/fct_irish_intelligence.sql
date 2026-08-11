-- fct_irish_intelligence: joins fundamentals with latest price data.
-- One row per ticker with everything needed for the intelligence page.

SELECT
    f.TICKER,
    f.NAME,
    f.FETCH_DATE,
    s.LATEST_PRICE,
    s.DAILY_RETURN,
    s.YTD_RETURN,
    s.VOLATILITY_30D,

    -- Fundamentals
    f.MARKET_CAP,
    f.PE_RATIO,
    f.FORWARD_PE,
    f.EPS,
    f.DIVIDEND_YIELD,
    f.REVENUE,
    f.PROFIT_MARGIN,
    f.SECTOR,
    f.INDUSTRY,
    f.COUNTRY,
    f.EMPLOYEES,
    f.DESCRIPTION,

    -- Analyst ratings
    COALESCE(f.ANALYST_STRONG_BUY, 0)  AS analyst_strong_buy,
    COALESCE(f.ANALYST_BUY, 0)         AS analyst_buy,
    COALESCE(f.ANALYST_HOLD, 0)        AS analyst_hold,
    COALESCE(f.ANALYST_SELL, 0)        AS analyst_sell,
    COALESCE(f.ANALYST_STRONG_SELL, 0) AS analyst_strong_sell,

    -- Total analyst count and consensus label
    COALESCE(f.ANALYST_STRONG_BUY, 0) + COALESCE(f.ANALYST_BUY, 0)
        + COALESCE(f.ANALYST_HOLD, 0) + COALESCE(f.ANALYST_SELL, 0)
        + COALESCE(f.ANALYST_STRONG_SELL, 0)                        AS total_analysts,

    CASE
        WHEN (COALESCE(f.ANALYST_STRONG_BUY,0) + COALESCE(f.ANALYST_BUY,0)) >
             (COALESCE(f.ANALYST_SELL,0) + COALESCE(f.ANALYST_STRONG_SELL,0)) * 2
        THEN 'Strong Buy'
        WHEN (COALESCE(f.ANALYST_STRONG_BUY,0) + COALESCE(f.ANALYST_BUY,0)) >
             (COALESCE(f.ANALYST_SELL,0) + COALESCE(f.ANALYST_STRONG_SELL,0))
        THEN 'Buy'
        WHEN COALESCE(f.ANALYST_HOLD,0) >=
             (COALESCE(f.ANALYST_STRONG_BUY,0) + COALESCE(f.ANALYST_BUY,0) +
              COALESCE(f.ANALYST_SELL,0) + COALESCE(f.ANALYST_STRONG_SELL,0))
        THEN 'Hold'
        WHEN (COALESCE(f.ANALYST_SELL,0) + COALESCE(f.ANALYST_STRONG_SELL,0)) >
             (COALESCE(f.ANALYST_STRONG_BUY,0) + COALESCE(f.ANALYST_BUY,0))
        THEN 'Sell'
        ELSE 'No Rating'
    END AS analyst_consensus

FROM {{ source('raw', 'RAW_FUNDAMENTALS') }} f
LEFT JOIN {{ ref('fct_market_summary') }} s
    ON f.TICKER = s.TICKER
WHERE f.FETCH_DATE = (SELECT MAX(FETCH_DATE) FROM {{ source('raw', 'RAW_FUNDAMENTALS') }})
