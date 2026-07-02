# truss download
Source: https://docs.baseten.co/reference/cli/truss/download

Download the Truss for a deployed model.

```sh theme={"system"}
truss download [OPTIONS]
```

Downloads the Truss for a deployed model as a tar file or extracts it into a directory. Use this to inspect the exact configuration and code that is running for a deployment, or to recover a Truss when the original source is unavailable.

You must pass exactly one of `--out-file` or `--out-dir`.

### Options

<ParamField type="TEXT">
  Name of the remote in `.trussrc`. If omitted, Truss prompts to select one.
</ParamField>

<ParamField type="TEXT">
  ID of the model.
</ParamField>

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="FILE">
  Save the Truss as a tar file at this path. Mutually exclusive with `--out-dir`.
</ParamField>

<ParamField type="DIRECTORY">
  Extract the Truss into this directory. Mutually exclusive with `--out-file`.
</ParamField>

<ParamField>
  Allow overwriting an existing file or non-empty directory. Without this flag, the command fails if the target file exists or the target directory is non-empty.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

**Examples:**

Download a Truss as a tar file:

```sh theme={"system"}
truss download --model-id YOUR_MODEL_ID --deployment-id YOUR_DEPLOYMENT_ID --out-file my-truss.tar
```

Extract a Truss into a directory:

```sh theme={"system"}
truss download --model-id YOUR_MODEL_ID --deployment-id YOUR_DEPLOYMENT_ID --out-dir ./my-truss
```

Overwrite an existing tar file:

```sh theme={"system"}
truss download --model-id YOUR_MODEL_ID --deployment-id YOUR_DEPLOYMENT_ID --out-file my-truss.tar --overwrite
```
