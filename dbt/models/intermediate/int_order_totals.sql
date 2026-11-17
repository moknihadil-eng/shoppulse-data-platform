select order_id, sum(quantity * unit_price)::numeric(12,2) order_total,
  sum(quantity) units, count(*) line_count
from {{ ref('stg_order_items') }} group by order_id
