FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements-runtime.txt requirements-models.txt ./
ARG LOCAL_MODELS=false
RUN pip install --no-cache-dir -r requirements-runtime.txt && \
    if [ "$LOCAL_MODELS" = "true" ]; then pip install --no-cache-dir -r requirements-models.txt; fi
RUN useradd --create-home --uid 10001 tera && mkdir -p /app/data/local && chown -R tera:tera /app/data
COPY --chown=tera:tera app ./app
USER tera
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
