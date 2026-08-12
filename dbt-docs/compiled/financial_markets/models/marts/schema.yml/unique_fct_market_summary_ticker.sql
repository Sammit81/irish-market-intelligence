
    
    

with dbt_test__target as (

  select ticker as unique_field
  from `irish-market-intelligence`.`FINANCIAL_MARKETS`.`fct_market_summary`
  where ticker is not null

)

select
    unique_field,
    count(*) as n_records

from dbt_test__target
group by unique_field
having count(*) > 1


