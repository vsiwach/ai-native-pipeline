# Truss CLI reference
Source: https://docs.baseten.co/reference/cli/truss/overview

Deploy, manage, and develop models using the Truss CLI.

```sh theme={"system"}
truss [OPTIONS] COMMAND [ARGS]...
```

**Options:**

<ParamField>
  Show the version and exit.
</ParamField>

<ParamField type="[humanfriendly|w|warning|i|info|d|debug]">
  Customize logging verbosity.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI or automated execution contexts.
</ParamField>

<ParamField>
  Show help message and exit.
</ParamField>

### Main commands

| Command                                         | Description                       |
| ----------------------------------------------- | --------------------------------- |
| [`init`](/reference/cli/truss/init)             | Create a new Truss project        |
| [`push`](/reference/cli/truss/push)             | Deploy a model to Baseten         |
| [`watch`](/reference/cli/truss/watch)           | Live reload during development    |
| [`model-logs`](/reference/cli/truss/model-logs) | Fetch logs for the packaged model |

### Advanced commands

| Command                                       | Description                             |
| --------------------------------------------- | --------------------------------------- |
| [`image`](/reference/cli/truss/image)         | Build and manage Truss Docker images    |
| [`container`](/reference/cli/truss/container) | Run and manage Truss containers locally |
| [`cleanup`](/reference/cli/truss/cleanup)     | Clean up Truss data                     |

### Other commands

| Command                                             | Description                                                |
| --------------------------------------------------- | ---------------------------------------------------------- |
| [`auth`](/reference/cli/truss/auth)                 | Manage authentication (login, logout, status)              |
| [`login`](/reference/cli/truss/login)               | Authenticate with Baseten                                  |
| [`configure`](/reference/cli/truss/configure)       | Configure Truss settings                                   |
| [`download`](/reference/cli/truss/download)         | Download the Truss for a deployed model                    |
| [`migrate`](/reference/cli/truss/migrate)           | Migrate `model_cache` / `external_data` to the weights API |
| [`model-config`](/reference/cli/truss/model-config) | Fetch the config of a deployed model                       |
| [`run-python`](/reference/cli/truss/run-python)     | Run a Python script in the Truss environment               |
| [`ssh`](/reference/cli/truss/ssh)                   | Configure SSH access to workloads                          |
| [`upgrade`](/reference/cli/truss/upgrade)           | Upgrade the Truss CLI to the latest version                |
| [`whoami`](/reference/cli/truss/whoami)             | Show user information and exit                             |

<Note>
  All commands support `--help` to display usage information.
</Note>
