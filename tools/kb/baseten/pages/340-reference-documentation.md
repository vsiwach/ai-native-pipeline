# Reference documentation
Source: https://docs.baseten.co/reference/overview

For deploying, managing, and interacting with machine learning models on Baseten.

This reference section documents our API, CLI, and Python SDK for deploying models, managing inference chains, and calling endpoints in production.

## API Reference

Baseten provides two sets of API endpoints:

<CardGroup>
  <Card title="Inference API" href="/reference/inference-api/overview">
    For calling deployed models and chains.
  </Card>

  <Card title="Management API" href="/reference/management-api/overview">
    For managing models, workspaces, and training jobs.
  </Card>
</CardGroup>

## CLI Reference

The CLI provides a command-line interface for managing deployments, running local inference, and configuring Truss models.

* [Truss CLI reference](/reference/cli/truss/overview): Commands for initializing, deploying, and managing models.
* [Chains CLI reference](/reference/cli/chains/chains-cli): Commands for orchestrating multi-model workflows.
* [Training CLI reference](/reference/cli/training/training-cli): Commands for managing training jobs.

***

## SDK Reference

The Python SDK provides an abstraction for deploying models, managing deployments, and interacting with models through code.

* [Truss SDK reference](/reference/sdk/truss): Deploy and interact with Truss models using Python.
* [Chains SDK reference](/reference/sdk/chains): Build and manage inference chains programmatically.
* [Training SDK reference](/reference/sdk/training): Deploy and interact with trained models using Python.
