# Baseten command-line tools
Source: https://docs.baseten.co/reference/cli/index

Baseten ships two open-source CLIs: Truss for authoring model code and the Baseten CLI for managing your workspace. This page covers what each one is for, when they overlap, and how to use them together.

Baseten provides command-line tools to author and ship models and to manage the workspace around them. Two CLIs do that work, and both are open source and actively developed.

The **Truss CLI** is the model-development tool. You use it to write a `config.yaml`, package a `model.py` and its dependencies into a Truss bundle, iterate against your code with `truss watch`, and push releases to Baseten. It also includes the framework workflows for [Chains](/reference/cli/chains/chains-cli), [Training](/reference/cli/training/training-cli), and [Loops](/reference/cli/loops/loops-cli). Truss is Python; install with `uvx truss` or `pip install truss`.

The **Baseten CLI** <span>Beta</span> is the workspace-operations tool. You use it to manage organizations, API keys, secrets, and the deployment lifecycle: promoting development deployments to production, activating or deactivating environments, terminating individual replicas, and so on. It also calls models and the Baseten API. Every Baseten-native command supports `--output json` and `--jq` filtering, which makes it the right tool to reach for in CI pipelines, scripts, and runbooks. The Baseten CLI is [open source](https://github.com/basetenlabs/baseten-cli); install it by downloading a [release](https://github.com/basetenlabs/baseten-cli/releases).

Both CLIs authenticate against the same Baseten backend and the two are designed to coexist.

## Which one do I use?

Most of the time the answer is clear from your context.

| You're doing this...                                                   | CLI                                                  |
| ---------------------------------------------------------------------- | ---------------------------------------------------- |
| Authoring `model.py` or `config.yaml` and iterating with `truss watch` | Truss                                                |
| Deploying a model from your editor                                     | Truss (`truss push`)                                 |
| Deploying a model from a CI workflow that parses output                | Baseten CLI (`baseten model push`)                   |
| Authoring a Chain, Training job, or Loop                               | Truss (`truss chains`, `truss train`, `truss loops`) |
| Creating or deleting an org API key                                    | Baseten CLI (`baseten org api-key`)                  |
| Promoting a development deployment to production                       | Baseten CLI (`baseten model deployment promote`)     |
| Querying a model from a shell pipeline                                 | Baseten CLI (`baseten model predict --jq ...`)       |
| Managing org secrets                                                   | Baseten CLI (`baseten org secret`)                   |
| Terminating a deployment replica                                       | Baseten CLI (`baseten model deployment replica`)     |

## Overlapping commands

A small set of commands intentionally exists in both CLIs so each is self-sufficient.

| Action         | Truss              | Baseten CLI                     | Pick based on                                                                                                                   |
| -------------- | ------------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Authenticate   | `truss login`      | `baseten auth login`            | Whichever CLI you already have installed. Both hit the same backend.                                                            |
| Deploy a model | `truss push`       | `baseten model push`            | `truss push` while iterating locally (supports `--watch`). `baseten model push` from CI (structured output, scriptable errors). |
| Tail logs      | `truss model-logs` | `baseten model deployment logs` | Match the workflow you're already in.                                                                                           |

## Use both together

The Baseten CLI ships with a `baseten truss` passthrough that forwards arguments to the `truss` binary on your `PATH`. If you prefer a single command in muscle memory, run `baseten truss push` as a synonym for `truss push`. The passthrough is permanent: the Baseten CLI composes with Truss without absorbing it.

## Next steps

<CardGroup>
  <Card title="Author a model" icon="code" href="/development/model/build-your-first-model">
    Use Truss to package and deploy your first model.
  </Card>

  <Card title="Manage your workspace" icon="terminal" href="/reference/cli/baseten/overview">
    Use the Baseten CLI for orgs, deployments, and automation.
  </Card>

  <Card title="Build a Chain" icon="link" href="/development/chain/getting-started">
    Create multi-step inference pipelines with `truss chains`.
  </Card>

  <Card title="Wire CI/CD" icon="gear" href="/deployment/ci-cd">
    Use `baseten model push` in GitHub Actions and other pipelines.
  </Card>
</CardGroup>
