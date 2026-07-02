# Secrets
Source: https://docs.baseten.co/development/model/secrets

Use secrets securely in your models

Truss manages API keys, access tokens, passwords, and other secrets so you don't have to expose them in code.

## Create a secret

<Tabs>
  <Tab title="Baseten UI">
    1. Go to [Secrets](https://app.baseten.co/settings/secrets) in your account settings.
    2. Enter the name and value of the secret, for example `hf_access_token` and `hf_...`.
    3. Select **Add secret**.
  </Tab>

  <Tab title="cURL">
    To create a secret with the API, use the following command:

    ```bash Request theme={"system"}
    curl --request POST \
      --url https://api.baseten.co/v1/secrets \
      --header "Authorization: Bearer $BASETEN_API_KEY" \
      --data '{
        "name": "hf_access_token",
        "value": "hf_..."
      }'
    ```

    For more information, see the
    [Upsert a secret](/reference/management-api/secrets/upserts-a-secret) reference.
  </Tab>
</Tabs>

## Use secrets in your model

Once you've created a secret, declare it in your `config.yaml` and access it in your model code.

<Warning>
  Never store actual secret values in `config.yaml`. Use `null` as a placeholder.
  The secret in your `config.yaml` is a reference to the key in the secret manager.
</Warning>

Specify the reference to the secret in `config.yaml`:

```yaml config.yaml theme={"system"}
secrets:
  hf_access_token: null
```

Secrets are passed as keyword arguments to the `Model` class. To access them, store the secrets in `__init__`:

```python model/model.py theme={"system"}
def __init__(self, **kwargs):
    self._secrets = kwargs["secrets"]
```

Then use the secret in your model's `load` or `predict` method by accessing it with the key:

```python model/model.py theme={"system"}
def load(self):
    self._model = pipeline(
        "fill-mask",
        model="baseten/docs-example-gated-model",
        use_auth_token=self._secrets["hf_access_token"]
    )
```

<Note>
  This pattern works when your `model.py` downloads the weights itself. To authenticate weights loaded through the [Baseten Delivery Network](/development/model/bdn) (the `weights:` config), reference the secret from the per-source [`auth`](/development/model/bdn#param-auth) block instead. A `secrets:` entry alone does not authenticate weight mirroring.
</Note>

## Use secrets in custom Docker images

When using [custom Docker images](/development/model/custom-server), Truss
injects secrets into your container at `/secrets/{secret_name}` instead of
passing them through `kwargs`.

You must specify the reference to the secret and then access it in your `start_command` or application code.

Specify the reference to the secret in `config.yaml`:

```yaml config.yaml theme={"system"}
secrets:
  hf_access_token: null
```

### Read secrets in your `start_command`

To read a secret in your `start_command`:

```yaml config.yaml theme={"system"}
docker_server:
  start_command: sh -c "HF_TOKEN=$(cat /secrets/hf_access_token) my-server --port 8000"
```

### Read secrets in application code

To read a secret in application code:

```python model/model.py theme={"system"}
with open("/secrets/hf_access_token", "r") as f:
    hf_token = f.read().strip()
```
