# Access model environments
Source: https://docs.baseten.co/development/model/environments

Configure model behavior based on environment

Model environments help configure behavior based on deployment stage (for example, production vs. staging). You can access the environment details through `kwargs` in the `Model` class.

## Retrieve the environment

Access the environment in `__init__`:

```python model/model.py theme={"system"}
def __init__(self, **kwargs):
    self._environment = kwargs["environment"]
```

## Configure behavior per environment

Use the environment in your `load()` method to set up environment-specific behavior:

```python model/model.py theme={"system"}
def load(self):
    if self._environment.get("name") == "production":
        self.setup_sentry()
        self.setup_logging(level="INFO")
        self.load_production_weights()
    else:
        self.setup_logging(level="DEBUG")
        self.load_default_weights()
```

This lets you:

* Customize logging levels.
* Load environment-specific model weights.
* Enable monitoring tools (for example, Sentry).

<Note>
  When you promote a deployment without re-deploying, `load()` doesn't re-run, so environment-specific configuration from the original deployment persists. You can configure an environment to create a fresh deployment on every promotion. See [Re-deploy on promotion](/deployment/environments#re-deploy-on-promotion) for details.
</Note>

## Next steps

* [The Model class](/development/model/model-class): Read configuration, secrets, and runtime information in `__init__` and `load`.
* [Environments](/deployment/environments): Promote deployments across stages and configure re-deploy on promotion.
