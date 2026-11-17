select to_char(day, 'YYYYMMDD')::int date_key, day::date date_day,
  extract(year from day)::int as calendar_year, extract(month from day)::int as month_number,
  extract(isodow from day)::int day_of_week
from generate_series(
  (select date_trunc('year', min(ordered_at)) from {{ ref('stg_orders') }}),
  (select date_trunc('year', max(ordered_at)) + interval '1 year' - interval '1 day' from {{ ref('stg_orders') }}),
  interval '1 day') day
