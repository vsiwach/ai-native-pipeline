FROM python:3.11-slim

WORKDIR /srv
COPY services/inference/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/inference/inference_app ./inference_app
COPY services/inference/sample_model ./sample_model
COPY services/inference/LICENSE .

RUN useradd --create-home --uid 10001 appuser
USER appuser

ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD \
  python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz')"

CMD ["uvicorn", "inference_app.main:app", "--host", "0.0.0.0", "--port", "8080"]
