{% macro latest(source_name, primary_key) %}
select payload, source_updated_at, loaded_at from (
  select payload, source_updated_at, loaded_at,
    row_number() over (partition by payload->>'{{ primary_key }}'
                      order by source_updated_at desc, object_key desc) as version_rank
  from {{ source('bronze', 'raw_records') }} where source_name = '{{ source_name }}'
) versions where version_rank = 1
{% endmacro %}
