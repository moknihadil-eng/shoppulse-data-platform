select (payload->>'customer_id')::int customer_id, payload->>'email' email,
  payload->>'country_code' country_code, (payload->>'created_at')::timestamptz created_at,
  source_updated_at updated_at
from ({{ latest('postgres/customers', 'customer_id') }}) t
