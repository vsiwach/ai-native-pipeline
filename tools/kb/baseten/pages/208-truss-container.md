# truss container
Source: https://docs.baseten.co/reference/cli/truss/container

Run and manage Truss containers locally.

```sh theme={"system"}
truss container [OPTIONS] COMMAND [ARGS]...
```

Manage Docker containers for your Truss.

***

## `kill`

Kill containers related to a specific Truss.

```sh theme={"system"}
truss container kill [OPTIONS] [TARGET_DIRECTORY]
```

### Arguments

<ParamField type="TEXT">
  A Truss directory. Defaults to current directory.
</ParamField>

**Example:**

Kill containers for the current Truss:

```sh theme={"system"}
truss container kill
```

***

## `kill-all`

Kill all Truss containers that are not manually persisted.

```sh theme={"system"}
truss container kill-all [OPTIONS]
```

**Example:**

Kill all Truss containers:

```sh theme={"system"}
truss container kill-all
```

***

## `logs`

Get logs from a running Truss container.

```sh theme={"system"}
truss container logs [OPTIONS] [TARGET_DIRECTORY]
```

### Options

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

### Arguments

<ParamField type="TEXT">
  A Truss directory. Defaults to current directory.
</ParamField>

**Example:**

View logs from the current Truss container:

```sh theme={"system"}
truss container logs
```
