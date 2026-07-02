# Development model deployment
Source: https://docs.baseten.co/reference/management-api/deployments/promote/promotes-a-development-deployment-to-production

post /v1/models/{model_id}/deployments/development/promote
Creates a new production deployment from the development deployment, the currently building deployment is returned.
