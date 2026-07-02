# Dependencies
Source: https://docs.baseten.co/development/model/dependencies

Declare everything your model needs to build and run: Python packages, build commands, base images, and private registries.

Your `config.yaml` is the declarative surface for everything your model bundles, builds, and pulls. Use it to include custom Python packages, run shell commands during the build, swap in a custom Docker base image, and authenticate to private registries.

## Python packages

Truss lets you include custom modules or third-party packages not available on PyPI using two methods:

1. **The `packages` directory**: for bundling small, Truss-specific packages.
2. **The `external_package_dirs` configuration**: for sharing packages across multiple Trusses.

### Use the `packages` directory

Each Truss includes a `packages/` directory where you place Python modules to include at build time. Use this method for lightweight, Truss-specific packages.

**Example directory structure:**

```text Project structure theme={"system"}
stable-diffusion/
    packages/
        package_1/
            subpackage/
                script.py
        package_2/
            utils.py
    model/
        model.py
        __init__.py
    config.yaml
```

**Importing a package in `model.py`:**

```python model.py theme={"system"}
from package_1.subpackage.script import run_script
from package_2.utils import RandomClass

class Model:
    def __init__(self, **kwargs):
        self.random_class = RandomClass()

    def load(self):
        run_script()
```

### Use `external_package_dirs`

If multiple Trusses need access to the same external package, define `external_package_dirs` in `config.yaml`. A package here refers to an importable directory with Python source code.

**Example directory structure:**

```text Project structure theme={"system"}
stable-diffusion/
    model/
        model.py
        __init__.py
    config.yaml
super_cool_awesome_plugin/
    plugin1/
        script.py
    plugin2/
        run.py
```

**Configuring `external_package_dirs` in `config.yaml`:**

```yaml config.yaml theme={"system"}
external_package_dirs:
  - ../super_cool_awesome_plugin/
```

<Tip>Paths must be relative to `config.yaml`.</Tip>

Include any requirements for these packages in your Truss configuration.

**Referencing external packages in `model.py`:**

```python model.py theme={"system"}
from plugin1.script import cool_constant
from plugin2.run import AwesomeRunner

class Model:
    def __init__(self, **kwargs):
        self.awesome_runner = AwesomeRunner()

    def load(self):
        self.awesome_runner.run(cool_constant)
```

## Build commands

The `build_commands` feature runs custom Docker commands during the **build stage**, enabling advanced caching, dependency management, and environment setup.

**Use cases:**

* Clone GitHub repositories.
* Install dependencies.
* Create directories.
* Pre-download model weights.

### Run build commands in `config.yaml`

Add `build_commands` to your `config.yaml`:

```yaml config.yaml theme={"system"}
build_commands:
  - git clone https://github.com/comfyanonymous/ComfyUI.git
  - cd ComfyUI && git checkout b1fd26fe9e55163f780bf9e5f56bf9bf5f035c93 && pip install -r requirements.txt
model_name: Build Commands Demo
python_version: py310
resources:
  accelerator: A100
```

This clones the GitHub repository, checks out the specified commit, and installs dependencies. Everything is cached at build time, reducing deployment cold starts.

### Create directories

Use `build_commands` to create directories directly in the container. This is useful for large codebases requiring additional structure.

```yaml config.yaml theme={"system"}
build_commands:
  - git clone https://github.com/comfyanonymous/ComfyUI.git
  - cd ComfyUI && mkdir ipadapter
  - cd ComfyUI && mkdir instantid
```

### Cache model weights efficiently

<Warning>For large weights (10GB+), use the [Baseten Delivery Network (BDN)](/development/model/bdn) instead of baking them into the image.</Warning>

For smaller weights, use `wget` in `build_commands`:

```yaml config.yaml theme={"system"}
build_commands:
  - git clone https://github.com/comfyanonymous/ComfyUI.git
  - cd ComfyUI && pip install -r requirements.txt
  - cd ComfyUI/models/controlnet && wget -O control-lora-canny-rank256.safetensors https://huggingface.co/stabilityai/control-lora/resolve/main/control-LoRAs-rank256/control-lora-canny-rank256.safetensors
  - cd ComfyUI/models/controlnet && wget -O control-lora-depth-rank256.safetensors https://huggingface.co/stabilityai/control-lora/resolve/main/control-LoRAs-rank256/control-lora-depth-rank256.safetensors
model_name: Build Commands Demo
python_version: py310
resources:
  accelerator: A100
system_packages:
  - wget
```

Preloading model weights during the build stage reduces startup time and ensures availability without runtime downloads.

### Run any shell command

`build_commands` runs any shell command at build time and caches the result, so it doesn't re-run on every cold start.

## Base images

Use a custom base image when you need specific system packages or a different runtime than the default Truss image provides.

### Set a base image in `config.yaml`

Specify a custom base image in `config.yaml`:

```yaml config.yaml theme={"system"}
base_image:
  image: <image_name:tag>
  python_executable_path: <path-to-python>
```

* `image`: the Docker image to use.
* `python_executable_path`: the path to the Python binary inside the container.

#### NVIDIA NeMo model

Use a custom image to deploy the [NVIDIA NeMo TitaNet](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/nemo/models/titanet_large) model:

```yaml config.yaml theme={"system"}
base_image:
  image: nvcr.io/nvidia/nemo:23.03
  python_executable_path: /usr/bin/python
apply_library_patches: true
requirements:
  - PySoundFile
resources:
  accelerator: T4
  cpu: 2500m
  memory: 4512Mi
secrets: {}
system_packages:
  - python3.8-venv
```

### Use private base images

If your base image is private, configure your model to use a [private registry](#private-registries).

### Create a custom base image

Build a new base image using Truss's base images as a foundation. Available images are listed on [Docker Hub](https://hub.docker.com/r/baseten/truss-server-base/tags).

#### Customize a Truss base image

```Dockerfile Dockerfile theme={"system"}
FROM baseten/truss-server-base:3.11-gpu-v0.7.16
RUN pip uninstall cython -y
RUN pip install cython==0.29.30
```

#### Build and push your custom image

Ensure Docker is installed and running. Then build, tag, and push your image:

```sh Terminal theme={"system"}
docker build -t my-custom-base-image:0.1 .
docker tag my-custom-base-image:0.1 your-docker-username/my-custom-base-image:0.1
docker push your-docker-username/my-custom-base-image:0.1
```

## Private registries

When deploying a [custom base image](#base-images) or [custom server](/development/model/custom-server) from a private registry, grant Baseten access to pull the image.

### AWS Elastic Container Registry (ECR)

AWS supports three authentication methods: [OIDC](#aws-oidc-recommended) (recommended), [IAM service accounts](#aws-iam-service-accounts), and [access tokens](#access-token).

#### AWS OIDC (Recommended)

OIDC provides short-lived, narrowly scoped tokens for secure authentication without managing long-lived credentials.

1. [Configure AWS to trust the Baseten OIDC provider](/organization/oidc#aws-setup) and create an IAM role with ECR permissions.

2. Add the OIDC configuration to your `config.yaml`:

```yaml config.yaml theme={"system"}
base_image:
  image: <aws-account-id>.dkr.ecr.<region>.amazonaws.com/path/to/image
  docker_auth:
    auth_method: AWS_OIDC
    aws_oidc_role_arn: arn:aws:iam::<aws-account-id>:role/baseten-ecr-access
    aws_oidc_region: <region>
    registry: <aws-account-id>.dkr.ecr.<region>.amazonaws.com
```

<Note>
  No secrets needed. The `aws_oidc_role_arn` and `aws_oidc_region` are not sensitive and can be committed to your repository.
</Note>

See the [OIDC authentication guide](/organization/oidc) for detailed setup instructions and best practices.

#### AWS IAM service accounts

To use an IAM service account for long-lived access, use the `AWS_IAM` authentication method in Truss.

1. Get an `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from the AWS dashboard.

2. Add these as [secrets](https://app.baseten.co/settings/secrets) in Baseten. Name them `aws_access_key_id` and `aws_secret_access_key`.

3. Configure `docker_auth` in your `config.yaml`:

```yaml config.yaml theme={"system"}
...
  base_image:
    image: <aws-account-id>.dkr.ecr.<region>.amazonaws.com/path/to/image
    docker_auth:
      auth_method: AWS_IAM
      registry: <aws-account-id>.dkr.ecr.<region>.amazonaws.com
  secrets:
    aws_access_key_id: null
    aws_secret_access_key: null
...
```

The `registry` value must match the hostname portion of the `image` URL.

To use different secret names, configure the `aws_access_key_id_secret_name` and `aws_secret_access_key_secret_name` options under `docker_auth`:

```yaml config.yaml theme={"system"}
...
base_image:
  ...
  docker_auth:
    auth_method: AWS_IAM
    registry: <aws-account-id>.dkr.ecr.<region>.amazonaws.com
    aws_access_key_id_secret_name: custom_aws_access_key_secret
    aws_secret_access_key_secret_name: custom_aws_secret_key_secret
secrets:
  custom_aws_access_key_secret: null
  custom_aws_secret_key_secret: null
```

#### Access token

1. Get the **Base64-encoded** secret:

```sh Terminal theme={"system"}
PASSWORD=`aws ecr get-login-password --region <region>`
echo -n "AWS:$PASSWORD" | base64
```

2. Add a new [secret](https://app.baseten.co/settings/secrets) to Baseten named `DOCKER_REGISTRY_<aws-account-id>.dkr.ecr.<region>.amazonaws.com` with the Base64-encoded secret as the value.

3. Add the secret name to the `secrets` section of `config.yaml`:

```yaml config.yaml theme={"system"}
secrets:
  DOCKER_REGISTRY_<aws-account-id>.dkr.ecr.<region>.amazonaws.com: null
```

### Google Cloud Artifact Registry

GCP supports three authentication methods: [OIDC](#gcp-oidc-recommended) (recommended), [service accounts](#service-account), and [access tokens](#access-token-1).

<Note>
  All three methods also work with Google Container Registry (`gcr.io`, `<region>.gcr.io`).
</Note>

#### GCP OIDC (Recommended)

OIDC provides short-lived, narrowly scoped tokens for secure authentication without managing long-lived credentials.

1. [Configure GCP Workload Identity](/organization/oidc#google-cloud-setup) to trust the Baseten OIDC provider and grant Artifact Registry permissions.

2. Add the OIDC configuration to your `config.yaml`:

```yaml config.yaml theme={"system"}
base_image:
  image: gcr.io/my-project/my-image:latest
  docker_auth:
    auth_method: GCP_OIDC
    gcp_oidc_service_account: baseten-oidc@my-project.iam.gserviceaccount.com
    gcp_oidc_workload_id_provider: projects/<project-number>/locations/global/workloadIdentityPools/baseten-pool/providers/baseten-provider
    registry: gcr.io
```

<Note>
  No secrets needed. The service account and workload identity provider are not sensitive and can be committed to your repository.
</Note>

See the [OIDC authentication guide](/organization/oidc) for detailed setup instructions and best practices.

#### Service account

1. Get your [service account key](https://cloud.google.com/artifact-registry/docs/docker/authentication#json-key) as a JSON key blob.

2. Add a new [secret](https://app.baseten.co/settings/secrets) to Baseten named `gcp-service-account` (or similar) with the JSON key blob as the value.

3. Add the secret name to the `secrets` section of `config.yaml`:

```yaml config.yaml theme={"system"}
secrets:
  gcp-service-account: null
```

4. Configure the `docker_auth` section of your `base_image` to use service account authentication:

```yaml config.yaml theme={"system"}
base_image:
  ...
  docker_auth:
    auth_method: GCP_SERVICE_ACCOUNT_JSON
    secret_name: gcp-service-account
    registry: <region>-docker.pkg.dev
```

`secret_name` must match the secret you created in step 2.

#### Access token

1. Get your [access token](https://cloud.google.com/artifact-registry/docs/docker/authentication#token).

2. Add a new [secret](https://app.baseten.co/settings/secrets) to Baseten named `DOCKER_REGISTRY_<region>-docker.pkg.dev` with the Base64-encoded secret as the value.

3. Add the secret name to the `secrets` section of `config.yaml`:

```yaml config.yaml theme={"system"}
secrets:
  DOCKER_REGISTRY_<region>-docker.pkg.dev: null
```

### Docker Hub

1. Get the **Base64-encoded** secret:

```sh Terminal theme={"system"}
echo -n 'username:password' | base64
```

2. Add a new [secret](https://app.baseten.co/settings/secrets) to Baseten named `DOCKER_REGISTRY_https://index.docker.io/v1/` with the Base64-encoded secret as the value.

```yaml theme={"system"}
Name: DOCKER_REGISTRY_https://index.docker.io/v1/
Token: <Base64-encoded secret>
```

3. Add the secret name to the `secrets` section of `config.yaml`:

```yaml config.yaml theme={"system"}
secrets:
  DOCKER_REGISTRY_https://index.docker.io/v1/: null
```

### GitHub Container Registry (GHCR)

1. Create a GitHub [Personal Access Token](https://github.com/settings/tokens) with the `read:packages` scope. Use a **classic** token, not fine-grained.

2. Get the **Base64-encoded** secret:

```sh Terminal theme={"system"}
echo -n 'github_username:ghp_your_personal_access_token' | base64
```

3. Add a new [secret](https://app.baseten.co/settings/secrets) to Baseten named `DOCKER_REGISTRY_ghcr.io` with the Base64-encoded secret as the value.

```yaml theme={"system"}
Name: DOCKER_REGISTRY_ghcr.io
Token: <Base64-encoded secret>
```

4. Add the secret name to the `secrets` section of `config.yaml`:

```yaml config.yaml theme={"system"}
base_image:
  image: ghcr.io/your-org/your-image:tag
secrets:
  DOCKER_REGISTRY_ghcr.io: null
```

### NVIDIA NGC

1. Generate an [NGC API Key](https://org.ngc.nvidia.com/setup/api-key) from your NVIDIA NGC account.

2. Get the **Base64-encoded** secret:

```sh Terminal theme={"system"}
echo -n '$oauthtoken:your_ngc_api_key' | base64
```

<Note>
  The username `$oauthtoken` is a literal string, not a variable. Use it exactly as shown.
</Note>

3. Add a new [secret](https://app.baseten.co/settings/secrets) to Baseten named `DOCKER_REGISTRY_nvcr.io` with the Base64-encoded secret as the value.

```yaml theme={"system"}
Name: DOCKER_REGISTRY_nvcr.io
Token: <Base64-encoded secret>
```

4. Add the secret name to the `secrets` section of `config.yaml`:

```yaml config.yaml theme={"system"}
base_image:
  image: nvcr.io/nvidia/pytorch:24.01-py3
secrets:
  DOCKER_REGISTRY_nvcr.io: null
```

## Next steps

<CardGroup>
  <Card title="Configuration" icon="gear" href="/development/model/configuration">
    The full set of `config.yaml` options for packages, resources, and the build environment.
  </Card>

  <Card title="Secrets" icon="key" href="/development/model/secrets">
    Store and reference API keys and registry credentials securely.
  </Card>

  <Card title="Custom servers" icon="server" href="/development/model/custom-server">
    Run your own server image instead of the default Truss server.
  </Card>

  <Card title="Private registry access" icon="lock" href="/organization/oidc">
    Set up OIDC for short-lived, credential-free registry authentication.
  </Card>
</CardGroup>
