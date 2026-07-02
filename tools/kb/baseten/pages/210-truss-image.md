# truss image
Source: https://docs.baseten.co/reference/cli/truss/image

Build and manage Truss Docker images.

```sh theme={"system"}
truss image [OPTIONS] COMMAND [ARGS]...
```

Build and manage Docker images for your Truss.

***

## `build`

Build the Docker image for a Truss.

```sh theme={"system"}
truss image build [OPTIONS] [TARGET_DIRECTORY] [BUILD_DIR]
```

### Options

<ParamField type="TEXT">
  Docker image tag.
</ParamField>

<ParamField>
  Use the host network for the Docker build.
</ParamField>

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

<ParamField type="TEXT">
  Image context directory. If not provided, a temp directory is created.
</ParamField>

**Example:**

Build a Docker image for your Truss:

```sh theme={"system"}
truss image build
```

Build with a custom tag:

```sh theme={"system"}
truss image build --tag my-model:v1
```

***

## `build-context`

Create a Docker build context for a Truss without building the image.

```sh theme={"system"}
truss image build-context [OPTIONS] BUILD_DIR [TARGET_DIRECTORY]
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
  Directory where image context is created.
</ParamField>

<ParamField type="TEXT">
  A Truss directory. Defaults to current directory.
</ParamField>

**Example:**

Create a build context in a specific directory:

```sh theme={"system"}
truss image build-context ./build-context
```

***

## `run`

Run the Docker image for a Truss locally.

```sh theme={"system"}
truss image run [OPTIONS] [TARGET_DIRECTORY] [BUILD_DIR]
```

### Options

<ParamField type="TEXT">
  Docker image tag to run.
</ParamField>

<ParamField type="INTEGER">
  Local port to expose the model on.
</ParamField>

<ParamField>
  Attach to the container process.
</ParamField>

<ParamField>
  Use the host network for the Docker build and run.
</ParamField>

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

<ParamField type="TEXT">
  Image context directory. If not provided, a temp directory is created.
</ParamField>

**Example:**

Build and run a Truss locally:

```sh theme={"system"}
truss image run
```

Run on a custom port:

```sh theme={"system"}
truss image run --port 9000
```

Run in attached mode:

```sh theme={"system"}
truss image run --attach
```
