select 'orders_missing_or_duplicated' problem
where (select count(*) from {{ ref('fact_orders') }}) <> (select count(*) from {{ ref('stg_orders') }})
union all
select 'payments_missing_or_duplicated'
where (select count(*) from {{ ref('fact_payments') }}) <> (select count(*) from {{ ref('stg_payments') }})
union all
select 'order_line_totals'
where (select sum(order_total) from {{ ref('fact_orders') }}) <> (select sum(line_total) from {{ ref('fact_order_items') }})
