-- Reconstruct every observed revision, even if dbt was not running at the time.
with versions as (
  select distinct (payload->>'customer_id')::int customer_id,
    payload->>'email' email, payload->>'country_code' country_code,
    (payload->>'created_at')::timestamptz created_at, source_updated_at updated_at
  from {{ source('bronze', 'raw_records') }} where source_name='postgres/customers'
), changes as (
  select *, row_number() over (partition by customer_id order by updated_at) version_number,
    lag(email || '|' || country_code) over (partition by customer_id order by updated_at) previous_attributes
  from versions
), effective as (
  select *, case when version_number=1 then created_at else updated_at end valid_from
  from changes where previous_attributes is null or previous_attributes <> email || '|' || country_code
)
select md5(customer_id::text || '|' || valid_from::text) customer_key,
  customer_id, email, country_code, valid_from,
  lead(valid_from) over (partition by customer_id order by valid_from) valid_to
from effective
