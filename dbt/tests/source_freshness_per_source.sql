with expected(source_name) as (values
 ('postgres/customers'),('postgres/products'),('postgres/orders'),('postgres/order_items'),
 ('postgres/payments'),('api/events'),('file/shipping'))
select e.source_name from expected e
left join {{ source('bronze','ingestion_clock') }} c using(source_name)
where c.checked_at is null or c.checked_at < current_timestamp - interval '24 hours'
