# Loops API reference
Source: https://docs.baseten.co/reference/loops-api/overview

HTTP routes for Loops sessions, runs, samplers, checkpoints, and deployments.

Every Loops API call is authenticated with `BASETEN_API_KEY`. Resources nest as: sessions own runs and samplers; runs own checkpoints; deployments are produced from checkpoints.

Each route's request body, query parameters, response shape, and an interactive playground live on its own page in this section. This overview covers the resource model. Pass your key as `Authorization: Bearer $BASETEN_API_KEY`; the playground on each route page prefills this header.

Both the HTTP API and the Python SDK refer to a trainer server as a `run_id`.
