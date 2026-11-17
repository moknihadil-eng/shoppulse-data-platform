select *, valid_to is null is_current from {{ ref('int_customer_history') }}
