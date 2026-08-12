
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select close_price
from `irish-market-intelligence`.`FINANCIAL_MARKETS`.`fct_returns_history`
where close_price is null



  
  
      
    ) dbt_internal_test