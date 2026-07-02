# Configuration
Source: https://docs.baseten.co/development/model/configuration

Configure model dependencies, resources, and build environment in config.yaml

ML models depend on external libraries, data files, and specific hardware. The `config.yaml` file defines all of this for your model. This guide covers the most common options.

## Environment variables

To set environment variables in the model serving environment, use the `environment_variables` key:

```yaml config.yaml theme={"system"}
environment_variables:
  MY_ENV_VAR: my_value
```

## Python packages

Specify Python packages in `config.yaml` using either `requirements` (an inline list) or `requirements_file` (a path to a file). These two options are mutually exclusive.

## Inline list

List packages directly in `config.yaml`:

```yaml config.yaml theme={"system"}
requirements:
  - package_name
  - package_name2
```

Pin package versions with `==`:

```yaml config.yaml theme={"system"}
requirements:
  - package_name==1.0.0
  - package_name2==2.0.0
```

## Requirements file

Point `requirements_file` at a dependency file. Truss supports three formats:

<Tabs>
  <Tab title="requirements.txt">
    Use a standard pip requirements file for full control over pip options and repositories.

    ```yaml config.yaml theme={"system"}
    requirements_file: ./requirements.txt
    ```
  </Tab>

  <Tab title="pyproject.toml">
    Use a `pyproject.toml` to install dependencies from the `[project.dependencies]` table.

    ```yaml config.yaml theme={"system"}
    requirements_file: ./pyproject.toml
    ```

    Truss reads only the `[project.dependencies]` list. Optional dependency groups are ignored.
  </Tab>

  <Tab title="uv.lock">
    Use a `uv.lock` file for fully pinned, reproducible installs managed by [uv](https://docs.astral.sh/uv/).

    ```yaml config.yaml theme={"system"}
    requirements_file: ./uv.lock
    ```

    <Note>
      The `uv.lock` file must have a sibling `pyproject.toml` in the same directory. Truss copies both files into the build context.
    </Note>
  </Tab>
</Tabs>

### Dependency constraints

Truss uses a `constraints.txt` file to enforce version bounds on base server dependencies. If you specify a package that overlaps with base dependencies (for example, `numpy` or `fastapi`), your version is respected but must fall within the bounds defined in `constraints.txt`. If you specify a version outside these bounds, the build will fail with an unsatisfiable error. This applies to both `requirements` (inline list) and `requirements_file`.

### Chains

Chains supports the same three formats through `DockerImage.requirements_file`. Use [`make_abs_path_here`](/reference/sdk/chains#function-truss_chains-make_abs_path_here) to resolve the path relative to the source file:

```python chainlet.py theme={"system"}
import truss_chains as chains

class MyChainlet(chains.ChainletBase):
    remote_config = chains.RemoteConfig(
        docker_image=chains.DockerImage(
            requirements_file=chains.make_abs_path_here("requirements.txt"),
        ),
    )
```

`pyproject.toml` and `uv.lock` work the same way:

```python chainlet.py theme={"system"}
docker_image=chains.DockerImage(
    requirements_file=chains.make_abs_path_here("pyproject.toml"),
)
```

```python chainlet.py theme={"system"}
docker_image=chains.DockerImage(
    requirements_file=chains.make_abs_path_here("uv.lock"),
)
```

<Note>
  `pip_requirements_file` is deprecated. Use `requirements_file` instead. You can't combine `pip_requirements` with `pyproject.toml` or `uv.lock` files; manage all dependencies in your `pyproject.toml`.
</Note>

## System packages

Truss supports installing apt-installable Debian packages. To add system packages to your model serving environment, add them to your `config.yaml` file:

```yaml config.yaml theme={"system"}
system_packages:
  - package_name
  - package_name2
```

For example, to install Tesseract OCR:

```yaml config.yaml theme={"system"}
system_packages:
  - tesseract-ocr
```

## Resources

Specify hardware resources in the `resources` section.

### Individual resource fields

For a CPU model:

```yaml config.yaml theme={"system"}
resources:
  cpu: "1"
  memory: 2Gi
```

For a GPU model:

```yaml config.yaml theme={"system"}
resources:
  accelerator: "L4"
```

When you push your model, it's assigned an instance type matching the required specifications.

### Exact instance type

```yaml config.yaml theme={"system"}
resources:
  instance_type: "L4:4x16"
```

Using `instance_type` lets you select an exact SKU. When specified, other resource fields are ignored.

See the [Resources](/deployment/resources) page for more information on
options available.

## Advanced configuration

Your model has many other configuration options. See the related guides:

* [Secrets](/development/model/secrets)
* [Data](/development/model/model-class#bundled-data)
* [Custom build commands](/development/model/dependencies#build-commands)
* [Base Docker images](/development/model/dependencies#base-images)
* [Custom servers](/development/model/custom-server)
* [Custom health checks](/development/model/health-checks)
