FROM python:3.11-slim
WORKDIR /srv
COPY services/docs_assist/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/docs_assist/app.py ./app.py
COPY services/docs_assist/retrieval.py ./retrieval.py
COPY services/docs_assist/kb ./kb
RUN useradd --create-home --uid 10001 appuser
USER appuser
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
