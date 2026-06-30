FROM python:3.11-slim
WORKDIR /srv
COPY services/router/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/router/router_app ./router_app
COPY inference-registry.yaml .
COPY routing-policy.yaml .
COPY placement-policy.yaml .
RUN useradd --create-home --uid 10001 appuser
USER appuser
ENV PORT=8080
ENV REGISTRY_PATH=/srv/inference-registry.yaml
ENV ROUTING_POLICY_PATH=/srv/routing-policy.yaml
ENV PLACEMENT_POLICY_PATH=/srv/placement-policy.yaml
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["uvicorn", "router_app.main:app", "--host", "0.0.0.0", "--port", "8080"]
