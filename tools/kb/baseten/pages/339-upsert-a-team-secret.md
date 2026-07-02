# Upsert a team secret
Source: https://docs.baseten.co/reference/management-api/teams/upserts-a-team-secret

post /v1/teams/{team_id}/secrets
Creates a new secret or updates an existing secret if one with the provided name already exists. The name and creation date of the created or updated secret is returned. This secret belongs to the specified team
