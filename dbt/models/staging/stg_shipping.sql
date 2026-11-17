select (payload->>'shipping_id')::int shipping_id, (payload->>'order_id')::int order_id,
  payload->>'carrier' carrier, payload->>'status' status, source_updated_at updated_at
from ({{ latest('file/shipping', 'shipping_id') }}) t
