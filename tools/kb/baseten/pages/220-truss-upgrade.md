# truss upgrade
Source: https://docs.baseten.co/reference/cli/truss/upgrade

Upgrade the truss package to the latest or a specified version.

```sh theme={"system"}
truss upgrade [OPTIONS] [VERSION]
```

Upgrades the installed `truss` package. Truss detects how the package was installed (for example, `pip`, `uv`, `pipx`, or `uv tool`) and runs the matching upgrade command. By default, it upgrades to the latest published version.

### Options

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Skips the `Proceed with upgrade?` confirmation and applies the upgrade. Use in CI/automated contexts.
</ParamField>

### Arguments

<ParamField type="TEXT">
  Specific version to install (for example, `0.17.0`). If omitted, upgrades to the latest version.
</ParamField>

**Examples:**

Upgrade to the latest version:

```sh theme={"system"}
truss upgrade
```

You should see:

```
Detected installation method: pip
Will run: pip install --upgrade truss
Proceed with upgrade? [Y/n]
```

Pin to a specific version:

```sh theme={"system"}
truss upgrade 0.17.0
```

Upgrade non-interactively (skip the confirmation prompt), useful in CI:

```sh theme={"system"}
truss --non-interactive upgrade
```

<Note>
  If Truss can't detect the installation method (for example, an editable install from source), it exits with a message asking you to upgrade manually.
</Note>
