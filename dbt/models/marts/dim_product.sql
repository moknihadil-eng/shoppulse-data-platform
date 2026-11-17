select product_id product_key, product_id, product_name, price from {{ ref('stg_products') }}
