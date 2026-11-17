select (payload->>'order_item_id')::int order_item_id, (payload->>'order_id')::int order_id,
  (payload->>'product_id')::int product_id, (payload->>'quantity')::int quantity,
  (payload->>'unit_price')::numeric(12,2) unit_price, source_updated_at updated_at
from ({{ latest('postgres/order_items', 'order_item_id') }}) t
