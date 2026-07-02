# Update chainlet environment's instance type
Source: https://docs.baseten.co/reference/management-api/environments/update-a-chainlet-environments-instance-type-settings

post /v1/chains/{chain_id}/environments/{env_name}/chainlet_settings/instance_types/update
Updates a chainlet environment's instance type settings. The chainlet environment setting must exist. When updated, a new chain deployment is created and deployed. It is promoted to the chain environment according to promotion settings on the environment.
