
  create or replace   view FINANCIAL_MARKETS.PUBLIC.stg_prices
  
  
  
  
  as (
    -- stg_prices: clean and type-cast the raw price data.
--
-- In dbt, staging models are the first layer after raw data.
-- They don't add business logic — they just clean and standardise.
-- Think of it as the equivalent of our stg_* tables in previous projects,
-- but dbt manages running it and tracking dependencies automatically.

SELECT
    TICKER,
    NAME,
    PRICE_DATE::DATE                        AS price_date,
    ROUND(OPEN::FLOAT, 4)                   AS open_price,
    ROUND(HIGH::FLOAT, 4)                   AS high_price,
    ROUND(LOW::FLOAT, 4)                    AS low_price,
    ROUND(CLOSE::FLOAT, 4)                  AS close_price,
    VOLUME::BIGINT                          AS volume
FROM FINANCIAL_MARKETS.PUBLIC.RAW_PRICES
WHERE CLOSE IS NOT NULL
  AND CLOSE > 0
  );

