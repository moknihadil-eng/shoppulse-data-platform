select customer_id from {{ ref('customer_features') }}
where orders_30d < paid_orders_30d or spend_30d < 0 or days_since_last_order < 0
