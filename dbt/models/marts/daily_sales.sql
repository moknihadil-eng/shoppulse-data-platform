{{ config(materialized='incremental', unique_key='sales_date', incremental_strategy='delete+insert') }}
select (ordered_at at time zone 'UTC')::date sales_date, count(*) order_count,
  count(*) filter (where status='paid') paid_order_count,
  sum(order_total)::numeric(12,2) ordered_value,
  coalesce(sum(order_total) filter (where status='paid'),0)::numeric(12,2) paid_revenue
from {{ ref('fact_orders') }}
{% if var('backfill_date', none) %}
where (ordered_at at time zone 'UTC')::date = '{{ var('backfill_date') }}'::date
{% endif %}
group by 1
