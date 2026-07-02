# Baseten CLI overview
Source: https://docs.baseten.co/reference/cli/baseten/overview

Manage your Baseten workspace from the command line: organizations, API keys, secrets, deployment lifecycle, replicas, and raw API access. Designed for automation.

The Baseten CLI manages your Baseten workspace from the command line: models, deployments, environments, secrets, API keys, and raw API access. Every Baseten-native command supports `--output json` and `--jq` filtering, so anything you do interactively is scriptable.

The CLI is open source on [GitHub](https://github.com/basetenlabs/baseten-cli), where you can browse the code, watch for new releases, and file issues.

<Note>
  The Baseten CLI is in **beta** and under active development. Commands, flags, output schemas, and the install path may change before general availability.
</Note>

For authoring Chains and Training jobs, use the [Truss CLI](/reference/cli/truss/overview). The two CLIs coexist; the [CLI router page](/reference/cli) explains when to reach for each.

## Install

Install with Homebrew on macOS or Linux:

```sh theme={"system"}
brew tap basetenlabs/baseten
brew trust basetenlabs/baseten
brew install baseten
```

Upgrade later with `brew upgrade baseten`.

<Accordion title="Manual install (Windows, or a specific version)">
  Download and extract the `baseten` binary for your platform, then place it on your `PATH`.

  <Tabs>
    <Tab title="macOS (arm64)">
      Download and extract `baseten` into `/usr/local/bin`:

      ```sh theme={"system"}
      curl -sL https://github.com/basetenlabs/baseten-cli/releases/download/v0.2.0/baseten_0.2.0_darwin_arm64.tar.gz \
        | sudo tar xz -C /usr/local/bin baseten
      ```
    </Tab>

    <Tab title="Linux (x64)">
      Download and extract `baseten` into `/usr/local/bin`:

      ```sh theme={"system"}
      curl -sL https://github.com/basetenlabs/baseten-cli/releases/download/v0.2.0/baseten_0.2.0_linux_amd64.tar.gz \
        | sudo tar xz -C /usr/local/bin baseten
      ```
    </Tab>

    <Tab title="Windows (x64)">
      Download and extract the archive, then move `baseten.exe` to a directory on your `PATH`:

      ```powershell theme={"system"}
      Invoke-WebRequest `
        https://github.com/basetenlabs/baseten-cli/releases/download/v0.2.0/baseten_0.2.0_windows_amd64.zip `
        -OutFile baseten.zip; Expand-Archive -Force baseten.zip .
      ```
    </Tab>
  </Tabs>

  For other platforms or a specific version, download an archive from [GitHub releases](https://github.com/basetenlabs/baseten-cli/releases) and move `baseten` onto your `PATH`.
</Accordion>

Verify the install:

```sh theme={"system"}
baseten version
```

## Authenticate

Log in interactively:

```sh theme={"system"}
baseten auth login
```

For automation, set `BASETEN_API_KEY` in the environment instead. See [`baseten auth`](/reference/cli/baseten/auth) for browser login, reading a key from stdin, switching accounts, and credential storage.

## Output and filtering

Every Baseten-native command supports four output formats through `--output`:

* `text` (default): human-readable narrative.
* `json`: a single JSON document. Pair with `--jq EXPR` to extract one field.
* `jsonl`: one JSON record per line. Used by commands that stream results.
* `none`: suppress stdout entirely.

```sh theme={"system"}
baseten model push --jq '.predict_url'
```

`--jq` implies `--output json` (or `jsonl` for streamed commands), so a single flag turns any command into a clean value for the next stage of your pipeline.

## Global flags

These flags work on every Baseten-native command:

| Flag              | Description                                                                                           |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| `--profile`       | Use a specific stored profile for this command, overriding `BASETEN_PROFILE` and the current profile. |
| `--output`, `-o`  | Output format: `text`, `json`, `jsonl`, or `none`. See [Output and filtering](#output-and-filtering). |
| `--jq`, `-q`      | Filter JSON output with a jq expression. See [Output and filtering](#output-and-filtering).           |
| `--verbose`, `-v` | Enable verbose logging.                                                                               |

## Command groups

The `baseten` CLI organizes commands by resource:

```
baseten [OPTIONS] COMMAND [SUBCOMMAND] [ARGS]...
```

Start from the resource you need to manage.

| Command group                                                                         | Use it to                                                                                                            |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| [`baseten api`](/reference/cli/baseten/api)                                           | Make raw management or inference API requests.                                                                       |
| [`baseten auth`](/reference/cli/baseten/auth)                                         | Log in, log out, switch accounts, and inspect the active account.                                                    |
| [`baseten model`](/reference/cli/baseten/model)                                       | Push, watch, list, describe, predict against, and delete models.                                                     |
| [`baseten model deployment`](/reference/cli/baseten/model-deployment)                 | Activate, configure, download, promote, delete, describe, list, stream logs from, and fetch metrics for deployments. |
| [`baseten model deployment replica`](/reference/cli/baseten/model-deployment-replica) | Terminate an individual deployment replica.                                                                          |
| [`baseten model environment`](/reference/cli/baseten/model-environment)               | Activate, deactivate, describe, and list model environments.                                                         |
| [`baseten model-api`](/reference/cli/baseten/model-api)                               | List and inspect Baseten Model APIs.                                                                                 |
| [`baseten org api-key`](/reference/cli/baseten/org-api-key)                           | List, create, and delete organization API keys.                                                                      |
| [`baseten org billing`](/reference/cli/baseten/org-billing)                           | Inspect organization billing usage.                                                                                  |
| [`baseten org secret`](/reference/cli/baseten/org-secret)                             | List, set, and delete organization secrets.                                                                          |
| [`baseten truss`](/reference/cli/baseten/truss)                                       | Forward commands to the `truss` binary on your `PATH`.                                                               |
| [`baseten version`](/reference/cli/baseten/version)                                   | Print Baseten CLI version information.                                                                               |

## Next steps

<CardGroup>
  <Card title="Deploy from CI" icon="github" href="/deployment/ci-cd">
    Use `baseten model push` from GitHub Actions and other CI runners.
  </Card>

  <Card title="Compare with Truss" icon="scale-balanced" href="/reference/cli">
    See when to reach for `baseten` vs `truss` for each task.
  </Card>
</CardGroup>
