
    
    

select
    ticker as unique_field,
    count(*) as n_records

from FINANCIAL_MARKETS.PUBLIC.fct_market_summary
where ticker is not null
group by ticker
having count(*) > 1


