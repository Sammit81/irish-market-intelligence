
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select fetch_date
from `irish-market-intelligence`.`FINANCIAL_MARKETS`.`fct_irish_intelligence`
where fetch_date is null



  
  
      
    ) dbt_internal_test