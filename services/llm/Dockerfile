FROM python:3.11-slim
WORKDIR /srv
COPY services/llm/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/llm/llm_app ./llm_app
RUN useradd --create-home --uid 10001 appuser
USER appuser
ENV PORT=8080
ENV ENGINE=max
ENV TARGET=cpu
ENV MODEL_NAME=llm-sim
ENV COLD_START_S=8.0
ENV KV_TTL_S=300.0
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["uvicorn", "llm_app.main:app", "--host", "0.0.0.0", "--port", "8080"]
