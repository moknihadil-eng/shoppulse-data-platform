-- Point-in-time features; no labels and no events after the feature cutoff.
with orders as (
  select customer_id, count(*) orders_30d,
    count(*) filter(where status='paid') paid_orders_30d,
    coalesce(sum(order_total) filter(where status='paid'),0) spend_30d,
    max(ordered_at) last_order_at
  from {{ ref('fact_orders') }}
  where ordered_at >= '{{ var('as_of_date') }}'::timestamptz - interval '30 days'
    and ordered_at < '{{ var('as_of_date') }}'::timestamptz
  group by customer_id
), events as (
  select customer_id, count(*) events_30d from {{ ref('stg_events') }}
  where event_at >= '{{ var('as_of_date') }}'::timestamptz - interval '30 days'
    and event_at < '{{ var('as_of_date') }}'::timestamptz group by customer_id
)
select c.customer_id, '{{ var('as_of_date') }}'::date as_of_date,
  coalesce(o.orders_30d,0) orders_30d, coalesce(o.paid_orders_30d,0) paid_orders_30d,
  coalesce(o.spend_30d,0)::numeric(12,2) spend_30d,
  coalesce(e.events_30d,0) events_30d,
  '{{ var('as_of_date') }}'::date - o.last_order_at::date days_since_last_order
from {{ ref('dim_customer') }} c
left join orders o using(customer_id) left join events e using(customer_id)
where c.valid_from < '{{ var('as_of_date') }}'::timestamptz
  and (c.valid_to >= '{{ var('as_of_date') }}'::timestamptz or c.valid_to is null)
