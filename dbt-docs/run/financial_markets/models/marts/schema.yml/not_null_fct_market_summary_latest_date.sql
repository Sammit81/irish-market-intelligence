
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select latest_date
from FINANCIAL_MARKETS.PUBLIC.fct_market_summary
where latest_date is null



  
  
      
    ) dbt_internal_test