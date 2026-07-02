# truss migrate
Source: https://docs.baseten.co/reference/cli/truss/migrate

Migrate model_cache and external_data to the unified weights API.

```sh theme={"system"}
truss migrate [OPTIONS] [TARGET_DIRECTORY]
```

Converts deprecated `model_cache` and `external_data` entries in `config.yaml` to the unified [weights API](/reference/truss-configuration#weights). Truss prints a colorized diff of the change and asks for confirmation before writing it back to disk.

The command is a no-op if `config.yaml` already defines `weights` or if it has neither `model_cache` nor `external_data`.

### Options

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Skips the `Apply these changes? [y/N]` confirmation and applies the migration. Use in CI/automated contexts.
</ParamField>

### Arguments

<ParamField type="TEXT">
  A Truss directory containing `config.yaml`. Defaults to the current directory.
</ParamField>

**Examples:**

Preview and apply a migration in the current directory:

```sh theme={"system"}
truss migrate
```

You should see a unified diff between the original and migrated `config.yaml`, then a prompt:

```
Apply these changes? [y/N]
```

Migrate a specific Truss directory:

```sh theme={"system"}
truss migrate /path/to/my-truss
```

Run non-interactively (skip the prompt and apply the change), useful in CI:

```sh theme={"system"}
truss --non-interactive migrate
```
