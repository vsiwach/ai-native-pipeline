# Status and health
Source: https://docs.baseten.co/observability/health

Every model deployment in your Baseten workspace has a status to represent its activity and health.

## Model statuses

**Healthy states:**

* **Active**: The deployment is active and available. It can be called with `truss predict` or from its API endpoints.
* **Scaled to zero**: The deployment is active but is not consuming resources. It will automatically start up when called, then scale back to zero after traffic ceases.
* **Starting up**: The deployment is starting up from a scaled to zero state after receiving a request.
* **Inactive**: The deployment is unavailable and is not consuming resources. It may be manually reactivated.

**Error states:**

* **Unhealthy**: The deployment is active but is in an unhealthy state due to errors while running, such as an external service it relies on going down or a problem in your Truss that prevents it from responding to requests.
* **Build failed**: The deployment is not active due to a Docker build failure.
* **Deployment failed**: The deployment is not active due to a model deployment failure.

## Fix unhealthy deployments

If you have an unhealthy or failed deployment, check the model logs to see if there's any indication of what the problem is. You can try deactivating and reactivating your deployment to see if the issue goes away. In the case of an external service outage, you may need to wait for the service to come back up before your deployment works again. For issues inside your Truss, you'll need to diagnose your code to see what is making it unresponsive.
