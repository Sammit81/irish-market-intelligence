
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select latest_price
from `irish-market-intelligence`.`FINANCIAL_MARKETS`.`fct_market_summary`
where latest_price is null



  
  
      
    ) dbt_internal_test