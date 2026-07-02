# truss init
Source: https://docs.baseten.co/reference/cli/truss/init

Create a new Truss project.

```sh theme={"system"}
truss init [OPTIONS] TARGET_DIRECTORY
```

Creates a new Truss project in the specified directory with the standard file structure.

### Options

<ParamField type="TrussServer | TRT_LLM">
  Server type to create. Default: `TrussServer`.
</ParamField>

<ParamField type="TEXT">
  Value assigned to `model_name` in `config.yaml`.
</ParamField>

<ParamField>
  Use code-first tooling to build the model. Default: `--no-python-config`.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

### Arguments

<ParamField type="TEXT">
  Directory where the Truss project is created.
</ParamField>

**Examples:**

Create a new Truss project:

```sh theme={"system"}
truss init my-model
```

You should see:

```
Truss my-model was created in /path/to/my-model
```

This creates the following directory structure:

```
my-model/
├── config.yaml
├── data/
├── model/
│   ├── __init__.py
│   └── model.py
└── packages/
```

Create a Truss with a custom name:

```sh theme={"system"}
truss init --name "My Model" my-model
```

Create a Truss with TRT\_LLM backend:

```sh theme={"system"}
truss init --backend TRT_LLM my-trt-model
```
