# List deployments
Source: https://docs.baseten.co/reference/loops-api/deployments/list-deployments

get /v1/loops/deployments
List Loops deployments. Defaults to the caller's own; pass ?scope=org to list every deployment in the caller's organization. Returns every deployment regardless of status; clients filter terminal states.
