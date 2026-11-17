with history as (
  select *, lag(valid_to) over(partition by customer_id order by valid_from) previous_end
  from {{ ref('dim_customer') }}
)
select customer_id from history
where valid_to <= valid_from or (previous_end is not null and previous_end <> valid_from)
union all
select customer_id from {{ ref('dim_customer') }} group by customer_id
having count(*) filter(where is_current) <> 1
