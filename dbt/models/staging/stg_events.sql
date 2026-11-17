select (payload->>'event_id')::int event_id, (payload->>'customer_id')::int customer_id,
  payload->>'event_type' event_type, source_updated_at event_at
from ({{ latest('api/events', 'event_id') }}) t
