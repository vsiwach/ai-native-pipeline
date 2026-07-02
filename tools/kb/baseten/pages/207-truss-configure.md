# truss configure
Source: https://docs.baseten.co/reference/cli/truss/configure

Configure Truss settings.

```sh theme={"system"}
truss configure [OPTIONS]
```

Opens the `.trussrc` configuration file in your system editor. Use this command to view or modify your local Truss configuration (API keys, remote URLs, etc.).

**Example:**

Open the Truss configuration file:

```sh theme={"system"}
truss configure
```

You should see a configuration file that you can edit, for example:

```yaml ~/.trussrc theme={"system"}
[baseten]
remote_provider = baseten
api_key = EMPTY
remote_url = https://app.baseten.co
```
