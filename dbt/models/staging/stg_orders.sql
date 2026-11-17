select (payload->>'order_id')::int order_id, (payload->>'customer_id')::int customer_id,
  payload->>'status' status, payload->>'currency' currency,
  (payload->>'created_at')::timestamptz ordered_at, source_updated_at updated_at
from ({{ latest('postgres/orders', 'order_id') }}) t
