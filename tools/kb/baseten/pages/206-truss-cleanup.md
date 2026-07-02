# truss cleanup
Source: https://docs.baseten.co/reference/cli/truss/cleanup

Clean up Truss data.

```sh theme={"system"}
truss cleanup [OPTIONS]
```

Clears temporary directories created by Truss for operations like building Docker images. Use this to free up disk space.

### Options

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

**Example:**

Clean up temporary Truss data:

```sh theme={"system"}
truss cleanup
```

This command produces no output on success. Temporary files are removed from `~/.truss/`.
