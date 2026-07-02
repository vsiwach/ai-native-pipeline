# API keys
Source: https://docs.baseten.co/organization/api-keys

Authenticate requests to Baseten for deployment, inference, and management.

API keys authenticate your requests to Baseten. You need an API key to:

* Deploy models, Chains, and training projects with the Truss CLI.
* Call model endpoints for inference.
* Use the management API.

## API key types

Baseten supports two types of API keys:

**Personal API keys** are tied to your user account. Actions performed with a personal key are attributed to you. Use personal keys for local development and testing. Personal keys are revoked when a user is [deprovisioned](/organization/sso-and-scim#deprovisioning), so don't use them for production workloads.

**Team API keys** are not tied to an individual user. When your organization has [teams](/organization/teams) enabled, team keys can be scoped to a specific team. Team keys can have different permission levels:

* **Full access**: Deploy models, call endpoints, and manage resources.
* **Inference only**: Call model endpoints but cannot deploy or manage.
* **Metrics only**: Export metrics but cannot deploy or call models.

Use team keys for CI/CD pipelines, production applications, and shared automation.

<Note>
  If your organization uses [teams](/organization/teams), Team Admins can create team API keys scoped to their team. See [Teams](/organization/teams) for more information.
</Note>

### Environment-scoped API keys

Environment-scoped API keys are team API keys restricted to specific [environments](/deployment/environments). Use them for least-privilege access when sharing keys with external partners or production integrations.

You can scope a key in two ways:

* **By environment**: The key can only call models in the selected environments (for example, `production` only, or `production` and `staging`).
* **By environment and model**: The key can only call specific models within the selected environments.

To create an environment-scoped key, select **Manage and call all team models** or **Call certain models** when [creating a team API key](#create-an-api-key), then choose the environments from the **Environment access** dropdown.

## Create an API key

1. Navigate to [API keys](https://app.baseten.co/settings/api_keys) in your account settings.
2. Select **Create API key**.

<Tabs>
  <Tab title="Personal">
    3) Select **Personal** and click **Next**.
    4) Enter a name for the key (lowercase letters, numbers, and hyphens only).
    5) Select **Create API key**.
  </Tab>

  <Tab title="Team">
    3. Select **Team** and click **Next**.
    4. If your organization has multiple teams, select the team.
    5. Enter a name for the key (lowercase letters, numbers, and hyphens only).
    6. Select the permission level:
       * **Manage and call all team models**: Full access to deploy, call, and manage.
       * **Call certain models**: Inference-only access to selected models. Choose **All models** so the key can call every model in the team, including models you add later.
       * **Export model metrics**: Metrics-only access.
    7. For **Manage and call all team models** or **Call certain models**, optionally use the **Environment access** dropdown to restrict the key to specific environments.
    8. Select **Create API key**.
  </Tab>
</Tabs>

Copy the key immediately. You won't be able to view it again.

## Use API keys with the CLI

The first time you run `truss push`, the CLI prompts you to choose how to authenticate. Choose **Paste an API key** to use a key from this page, or **Log in via browser (OAuth)** to authenticate without a long-lived secret on disk:

```
$ truss push
💻 Let's add a Baseten remote!
? How would you like to authenticate?
  Paste an API key
> Log in via browser (OAuth)
```

You can also log in ahead of time with `truss login` (or its alias `truss auth login`). For details on credential storage, OAuth, and managing multiple remotes, see [`truss auth`](/reference/cli/truss/auth).

To configure or update an API key manually, edit `~/.trussrc`:

```sh theme={"system"}
[baseten]
remote_provider = baseten
api_key = YOUR_API_KEY
```

## Use API keys with endpoints

Pass your API key in the `Authorization` header using the `Bearer` scheme:

```sh theme={"system"}
Authorization: Bearer $BASETEN_API_KEY
```

`Bearer` works with OpenAI-style clients and AI gateways such as LiteLLM and OpenRouter without extra configuration. Baseten also accepts the legacy `Api-Key` scheme on every endpoint, so existing scripts using `Authorization: Api-Key <key>` continue to work:

```sh theme={"system"}
Authorization: Api-Key $BASETEN_API_KEY
```

For runnable examples, see [Call your model](/inference/calling-your-model).

<Note>
  [Frontier Gateway](/frontier-gateway/get-started) federated API keys are the exception: they only accept the `Api-Key` scheme. Workspace API keys used to manage gateway groups still accept either scheme.
</Note>

## Manage API keys

The [API keys page](https://app.baseten.co/settings/api_keys) shows all your keys with their creation date and last used timestamp. Use this information to identify unused keys.

API keys don't automatically expire. To maintain security, rotate keys periodically and revoke any that are no longer in use.

To rename a key, select the pencil icon next to the key name.

To rotate a key, create a new key, update your applications to use it, then revoke the old key.

To revoke a key, select the trash icon next to the key. Revoked keys cannot be restored.

You can also manage API keys programmatically with the [REST API](/reference/management-api/api-keys/creates-an-api-key).

### Security recommendations

* Store API keys in environment variables or secret managers, not in code.
* Never commit API keys to version control.
* Use [environment-scoped keys](#environment-scoped-api-keys) to limit access to specific environments and models.
* Use team keys with minimal permissions for production applications.
* Rotate keys periodically and revoke unused keys.
* Monitor key creation, deletion, and use through the [audit log](/organization/audit-logs).
