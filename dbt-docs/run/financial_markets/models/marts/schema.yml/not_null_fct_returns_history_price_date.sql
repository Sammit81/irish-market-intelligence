
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select price_date
from `irish-market-intelligence`.`FINANCIAL_MARKETS`.`fct_returns_history`
where price_date is null



  
  
      
    ) dbt_internal_test