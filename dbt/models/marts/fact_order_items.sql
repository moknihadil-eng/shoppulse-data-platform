select i.order_item_id, i.order_id, i.product_id product_key, i.quantity,
  i.unit_price, (i.quantity*i.unit_price)::numeric(12,2) line_total
from {{ ref('stg_order_items') }} i
join {{ ref('dim_product') }} p on i.product_id=p.product_key
