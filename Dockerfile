FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN cp dbt/profiles.yml.example dbt/profiles.yml
ENV DBT_PROFILES_DIR=dbt
CMD ["sh", "run_pipeline.sh"]
