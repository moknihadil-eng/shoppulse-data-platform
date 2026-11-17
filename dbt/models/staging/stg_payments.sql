select (payload->>'payment_id')::int payment_id, (payload->>'order_id')::int order_id,
  (payload->>'amount')::numeric(12,2) amount, payload->>'status' status,
  (payload->>'created_at')::timestamptz paid_at, source_updated_at updated_at
from ({{ latest('postgres/payments', 'payment_id') }}) t
