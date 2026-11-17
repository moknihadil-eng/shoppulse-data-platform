FROM python:3.13.7-slim-bookworm
WORKDIR /app
COPY platform/requirements.txt /app/requirements.txt
COPY platform/requirements.lock.txt /app/requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock.txt && pip check
COPY ingestion /app/ingestion
COPY dbt /app/dbt
COPY orchestration /app/orchestration
COPY dashboards /app/dashboards
COPY platform /app/platform
ENV PYTHONPATH=/app/ingestion:/app/orchestration:/app/platform DAGSTER_HOME=/dagster/home DBT_PROFILES_DIR=/app/dbt
RUN mkdir -p /dagster/home /reports
COPY orchestration/dagster.yaml /dagster/home/dagster.yaml
ENTRYPOINT ["python", "/app/platform/manage.py"]
