select p.payment_id, p.order_id, o.customer_key, o.date_key,
  p.paid_at, p.amount, p.status
from {{ ref('stg_payments') }} p join {{ ref('fact_orders') }} o using(order_id)
