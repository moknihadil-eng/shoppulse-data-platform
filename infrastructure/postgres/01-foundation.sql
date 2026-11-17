BEGIN;
CREATE SCHEMA IF NOT EXISTS shop;
CREATE TABLE IF NOT EXISTS shop.customers (
  customer_id integer PRIMARY KEY,
  email text NOT NULL UNIQUE,
  country_code char(2) NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL CHECK (updated_at >= created_at)
);
CREATE TABLE IF NOT EXISTS shop.products (
  product_id integer PRIMARY KEY,
  name text NOT NULL,
  price numeric(12,2) NOT NULL CHECK (price > 0),
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL CHECK (updated_at >= created_at)
);
CREATE TABLE IF NOT EXISTS shop.orders (
  order_id integer PRIMARY KEY,
  customer_id integer NOT NULL REFERENCES shop.customers,
  status text NOT NULL CHECK (status IN ('paid','pending','cancelled')),
  currency char(3) NOT NULL DEFAULT 'EUR',
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL CHECK (updated_at >= created_at)
);
CREATE TABLE IF NOT EXISTS shop.order_items (
  order_item_id integer PRIMARY KEY,
  order_id integer NOT NULL REFERENCES shop.orders,
  product_id integer NOT NULL REFERENCES shop.products,
  quantity integer NOT NULL CHECK (quantity > 0),
  unit_price numeric(12,2) NOT NULL CHECK (unit_price > 0),
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL CHECK (updated_at >= created_at),
  UNIQUE (order_id, product_id)
);
CREATE TABLE IF NOT EXISTS shop.payments (
  payment_id integer PRIMARY KEY,
  order_id integer NOT NULL UNIQUE REFERENCES shop.orders,
  amount numeric(12,2) NOT NULL CHECK (amount > 0),
  status text NOT NULL CHECK (status IN ('succeeded','pending','failed')),
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL CHECK (updated_at >= created_at)
);

-- Fixed formulas, dates and IDs: no random() or now() in the seed.
INSERT INTO shop.customers
SELECT n, 'customer' || n || '@example.test', 'FR',
       '2027-01-01 08:00:00+00'::timestamptz, '2027-01-01 08:00:00+00'::timestamptz
FROM generate_series(1,10) n ON CONFLICT (customer_id) DO NOTHING;
INSERT INTO shop.products
SELECT n, 'Product ' || n, (n * 10)::numeric(12,2),
       '2027-01-01 08:00:00+00'::timestamptz, '2027-01-01 08:00:00+00'::timestamptz
FROM generate_series(1,5) n ON CONFLICT (product_id) DO NOTHING;
INSERT INTO shop.orders
SELECT n, 1 + (n-1)%10, CASE WHEN n%5=0 THEN 'pending' ELSE 'paid' END, 'EUR',
       '2027-01-02 08:00:00+00'::timestamptz + n * interval '1 hour',
       '2027-01-02 08:00:00+00'::timestamptz + n * interval '1 hour'
FROM generate_series(1,20) n ON CONFLICT (order_id) DO NOTHING;
INSERT INTO shop.order_items
SELECT (o.order_id-1)*2 + k, o.order_id, p.product_id, k, p.price,
       o.created_at, o.updated_at
FROM shop.orders o CROSS JOIN generate_series(1,2) k
JOIN shop.products p ON p.product_id = 1 + (o.order_id+k-2)%5
WHERE o.order_id BETWEEN 1 AND 20
ON CONFLICT (order_item_id) DO NOTHING;
INSERT INTO shop.payments
SELECT o.order_id, o.order_id, sum(i.quantity*i.unit_price),
       CASE WHEN o.status='paid' THEN 'succeeded' ELSE 'pending' END,
       o.created_at, o.updated_at
FROM shop.orders o JOIN shop.order_items i USING (order_id)
WHERE o.order_id BETWEEN 1 AND 20
GROUP BY o.order_id ON CONFLICT (payment_id) DO NOTHING;

-- Future source mutations must advance the incremental watermark.
CREATE OR REPLACE FUNCTION shop.touch_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := GREATEST(clock_timestamp(), OLD.updated_at + interval '1 microsecond');
  RETURN NEW;
END;
$$;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['customers','products','orders','order_items','payments'] LOOP
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON shop.%I (updated_at, %I)',
      t || '_watermark_idx', t, CASE t WHEN 'customers' THEN 'customer_id' WHEN 'products' THEN 'product_id'
      WHEN 'orders' THEN 'order_id' WHEN 'order_items' THEN 'order_item_id' ELSE 'payment_id' END);
    EXECUTE format('DROP TRIGGER IF EXISTS touch_updated_at ON shop.%I', t);
    EXECUTE format('CREATE TRIGGER touch_updated_at BEFORE UPDATE ON shop.%I FOR EACH ROW EXECUTE FUNCTION shop.touch_updated_at()', t);
  END LOOP;
END;
$$;
COMMIT;
