FROM python:3.13.7-slim-bookworm
RUN pip install --no-cache-dir boto3==1.40.30 "psycopg[binary]==3.2.10"
COPY foundation.py /app/foundation.py
ENTRYPOINT ["python", "/app/foundation.py"]
