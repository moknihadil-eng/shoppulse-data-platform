select p.product_key, p.product_name, sum(i.quantity) units_sold,
  sum(i.line_total)::numeric(12,2) paid_revenue
from {{ ref('fact_order_items') }} i
join {{ ref('fact_orders') }} o using(order_id)
join {{ ref('dim_product') }} p using(product_key)
where o.status='paid' group by 1,2
