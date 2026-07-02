# Chains CLI reference
Source: https://docs.baseten.co/reference/cli/chains/chains-cli

Deploy, manage, and develop Chains using the Truss CLI.

```sh theme={"system"}
truss chains [OPTIONS] COMMAND [ARGS]...
```

| Command           | Description                |
| ----------------- | -------------------------- |
| [`init`](#init)   | Initialize a Chain project |
| [`push`](#push)   | Deploy a Chain             |
| [`watch`](#watch) | Live reload development    |

***

## `init`

Initialize a Chain project.

```sh theme={"system"}
truss chains init [OPTIONS] [DIRECTORY]
```

### Arguments

<ParamField type="PATH">
  Path to a new or empty directory for the Chain. Defaults to the current directory if omitted.
</ParamField>

### Options

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

**Example:**

To create a new Chain project in a directory called `my-chain`, use the following:

```sh theme={"system"}
truss chains init my-chain
```

***

## `push`

Deploy a Chain.

```sh theme={"system"}
truss chains push [OPTIONS] SOURCE [ENTRYPOINT]
```

### Arguments

<ParamField type="PATH">
  Path to a Python file that contains the entrypoint chainlet.
</ParamField>

<ParamField type="TEXT">
  Class name of the entrypoint chainlet. If omitted, the chainlet tagged with `@chains.mark_entrypoint` is used.
</ParamField>

### Options

<ParamField type="TEXT">
  Name of the Chain to deploy. If not given, the entrypoint name is used.
</ParamField>

<ParamField>
  Published deployments are now the default. Use `--watch` for development deployments instead.
</ParamField>

<ParamField>
  Promote newly deployed chainlets into production.
</ParamField>

<ParamField type="TEXT">
  Deploy the Chain as a published deployment to the specified environment. When specified, publish is implied and `--promote` is ignored.
</ParamField>

<ParamField>
  Wait until all chainlets are ready (or deployment fails).
</ParamField>

<ParamField>
  Watch the Chains source code and apply live patches. Implies `--wait` — the command waits for the Chain to be deployed before starting to watch for changes. Requires a development deployment.
</ParamField>

<ParamField>
  Produce only generated files; don't deploy anything.
</ParamField>

<ParamField type="TEXT">
  Name of the remote in `.trussrc` to push to.
</ParamField>

<ParamField type="TEXT">
  Run `watch`, but only apply patches to specified chainlets. Pass a comma-separated list of chainlet display names. Faster dev loops, but may lead to inconsistent deployments. Use with caution and refer to the [chain watch documentation](/development/chain/watch).
</ParamField>

<ParamField>
  Attach git versioning info (sha, branch, tag) to deployments made from within a git repo. Can also be set permanently in `.trussrc`.
</ParamField>

<ParamField>
  Disable downloading of pushed Chain source code from the UI.
</ParamField>

<ParamField type="TEXT">
  Name of the deployment created by the push. Can be used with `--promote`.
</ParamField>

<ParamField type="TEXT">
  Name of the team to deploy to. If not specified, Truss infers the team based on your team membership and existing chains, or prompts for selection when ambiguous.

  <Note>
    The `--team` flag is only available if your organization has teams enabled. [Contact us](mailto:support@baseten.co) to enable teams, or see [Teams](/organization/teams) for more information.
  </Note>
</ParamField>

<ParamField type="BOOLEAN">
  Keep development chainlet models warm by preventing scale-to-zero while watching. Requires --watch.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

**Example:**

To deploy a Chain as a published deployment:

```sh theme={"system"}
truss chains push my_chain.py
```

To create a development deployment and start watching for changes:

```sh theme={"system"}
truss chains push my_chain.py --watch
```

To deploy and promote to production:

```sh theme={"system"}
truss chains push my_chain.py --promote
```

To deploy to a specific team:

```sh theme={"system"}
truss chains push my_chain.py --team my-team-name
```

***

## `watch`

Live reload development.

```sh theme={"system"}
truss chains watch [OPTIONS] SOURCE [ENTRYPOINT]
```

### Arguments

<ParamField type="PATH">
  Path to a Python file containing the entrypoint chainlet.
</ParamField>

<ParamField type="TEXT">
  Class name of the entrypoint chainlet. If omitted, the chainlet tagged with `@chains.mark_entrypoint` is used.
</ParamField>

### Options

<ParamField type="TEXT">
  Name of the Chain to watch. If not given, the entrypoint name is used.
</ParamField>

<ParamField type="TEXT">
  Name of the remote in `.trussrc` to push to.
</ParamField>

<ParamField type="TEXT">
  Run `watch`, but only apply patches to specified chainlets. Pass a comma-separated list of chainlet display names. Faster dev loops, but may lead to inconsistent deployments. Use with caution and refer to the [chain watch documentation](/development/chain/watch).
</ParamField>

<ParamField type="TEXT">
  Name of the team for the Chain to watch. If not specified, Truss infers the team based on your team membership and existing chains, or prompts for selection when ambiguous.

  <Note>
    The `--team` flag is only available if your organization has teams enabled. [Contact us](mailto:support@baseten.co) to enable teams, or see [Teams](/organization/teams) for more information.
  </Note>
</ParamField>

<ParamField type="BOOLEAN">
  Keep development chainlet models warm by preventing scale-to-zero while watching.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

**Example:**

To watch a Chain for live reload during development, use the following:

```sh theme={"system"}
truss chains watch my_chain.py
```

By default, `watch` keeps development Chainlets warm (`--no-sleep` is on) so they don't scale to zero while you iterate. To let idle Chainlets scale to zero, opt out:

```sh theme={"system"}
truss chains watch my_chain.py --no-sleep=false
```
