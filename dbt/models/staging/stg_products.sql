select (payload->>'product_id')::int product_id, payload->>'name' product_name,
  (payload->>'price')::numeric(12,2) price, source_updated_at updated_at
from ({{ latest('postgres/products', 'product_id') }}) t
