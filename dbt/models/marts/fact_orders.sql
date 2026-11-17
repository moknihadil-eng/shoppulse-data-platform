-- Grain: one row per order. Avoid payment/line joins multiplying revenue.
select o.order_id, c.customer_key, o.customer_id,
  to_char(o.ordered_at at time zone 'UTC','YYYYMMDD')::int date_key,
  o.ordered_at, o.status, o.currency, t.order_total, t.units, t.line_count
from {{ ref('stg_orders') }} o
join {{ ref('int_order_totals') }} t using(order_id)
join {{ ref('dim_customer') }} c on o.customer_id=c.customer_id
  and o.ordered_at >= c.valid_from and (o.ordered_at < c.valid_to or c.valid_to is null)
