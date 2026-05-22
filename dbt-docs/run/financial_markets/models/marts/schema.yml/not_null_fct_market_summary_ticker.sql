
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ticker
from FINANCIAL_MARKETS.PUBLIC.fct_market_summary
where ticker is null



  
  
      
    ) dbt_internal_test