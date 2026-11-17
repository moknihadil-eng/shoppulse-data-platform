select p.payment_id from {{ ref('stg_payments') }} p
join {{ ref('int_order_totals') }} t using(order_id)
where p.amount <> t.order_total or p.amount <= 0
