# CI/CD
Source: https://docs.baseten.co/deployment/ci-cd

Automate Truss deployments with GitHub Actions.

Manual `truss push` works when one person deploys one model. When your model code lives in a shared repository with multiple contributors, deploys drift out of sync: someone pushes from a stale branch, a config change skips review, a broken model reaches production because nobody ran a predict check first.

The [Truss Push GitHub Action](https://github.com/marketplace/actions/truss-push) ties deployment to your Git workflow. Every push or pull request can trigger a deploy, validate the model with a predict request, and clean up automatically. The action supports both Truss models and [chains](/development/chain/deploy).

## What happens during a run

The action runs through four phases, each in a collapsible log group in the GitHub Actions UI:

1. **Load config**: For models, reads `config.yaml` from the Truss directory and extracts `model_metadata.example_model_input` for the predict step (unless you override it with `predict-payload`). For chains, detects the entrypoint class from the `.py` file.
2. **Deploy**: Pushes the model or chain to Baseten and streams deployment logs directly into the GitHub Actions output. You don't need to open the Baseten dashboard to watch the build. The action names each deployment from git context: `PR-42_abc1234` for pull requests, `abc1234` for direct pushes (customizable with `deployment-name`).
3. **Predict**: Sends a predict request and reports latency. For streaming models (when the payload includes `"stream": true`), reports time-to-first-byte, token count, and tokens per second.
4. **Cleanup**: Deactivates the newly created deployment if `cleanup: true`. Set `cleanup: false` when deploying to an environment or when you want to inspect the deployment manually.

After every run, the action writes a summary table to the GitHub Actions job summary with deploy time, predict metrics, and a direct link to the deployment logs on Baseten.

## Prerequisites

Store your Baseten API key as an [encrypted secret](https://docs.github.com/en/actions/security-guides/encrypted-secrets) named `BASETEN_API_KEY` in your repository or organization settings. See [API keys](/organization/api-keys) for how to generate one.

## Deploy to an environment on merge

Deploy a validated model to a specific environment every time code merges to `main`.

Create `.github/workflows/deploy.yml` and add the following:

```yaml .github/workflows/deploy.yml theme={"system"}
name: Deploy to production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: basetenlabs/action-truss-push@v0.1
        with:
          truss-directory: "./my-model"
          baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
          environment: "production"
          cleanup: false
```

Setting `environment` publishes the deployment to the specified environment. Setting `cleanup: false` keeps the deployment active so it can serve traffic.

## Validate on pull request

Catch model regressions before they reach production. The action deploys, runs a predict request, and tears down the deployment inside the PR check.

Create `.github/workflows/validate-model.yml` and add the following:

```yaml .github/workflows/validate-model.yml theme={"system"}
name: Validate model

on:
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: basetenlabs/action-truss-push@v0.1
        with:
          truss-directory: "./my-model"
          baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
```

The action reads `model_metadata.example_model_input` from your `config.yaml` to build the predict request. With the default (`cleanup: true`), the deployment is deactivated after validation, so no resources are left running.

## Deploy a chain

Deploy a Baseten chain from a Python source file. The action auto-detects chains when `truss-directory` points to a `.py` file:

```yaml theme={"system"}
- uses: basetenlabs/action-truss-push@v0.1
  with:
    truss-directory: "./chains/my_chain.py"
    baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
    model-name: "my-rag-chain"
    cleanup: false
    predict-payload: '{"query": "What is Baseten?"}'
```

For chains, the predict payload must be provided explicitly with `predict-payload` because there's no `config.yaml` to read example input from.

## Deploy multiple models

Use a matrix strategy to deploy each model in your repository as a separate job.

Create `.github/workflows/deploy-all.yml` and add the following:

```yaml .github/workflows/deploy-all.yml theme={"system"}
name: Deploy models

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        model:
          - path: models/text-classifier
          - path: models/image-generator
          - path: models/embeddings
    steps:
      - uses: actions/checkout@v4

      - uses: basetenlabs/action-truss-push@v0.1
        with:
          truss-directory: ${{ matrix.model.path }}
          baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
          environment: "production"
          cleanup: false
```

Each matrix entry runs as a separate job. If one model fails, the others still deploy.

## Custom predict validation

Override the default predict payload when your model needs a specific input shape that differs from `model_metadata.example_model_input`:

```yaml theme={"system"}
- uses: basetenlabs/action-truss-push@v0.1
  with:
    truss-directory: "./my-model"
    baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
    predict-payload: '{"prompt": "Hello, world!", "max_new_tokens": 128}'
    predict-timeout: 60
```

If neither `predict-payload` nor `model_metadata.example_model_input` is set, the action skips the predict step entirely and the deployment isn't validated.

## Deploy with labels

Attach metadata labels to track deployments in your CI pipeline:

```yaml theme={"system"}
- uses: basetenlabs/action-truss-push@v0.1
  with:
    truss-directory: "./my-model"
    baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
    labels: '{"team": "ml-platform", "triggered-by": "ci"}'
```

## Override model name

Set a custom model name instead of using the name from `config.yaml`:

```yaml theme={"system"}
- uses: basetenlabs/action-truss-push@v0.1
  with:
    truss-directory: "./my-model"
    baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
    model-name: "my-custom-name"
```

## Use action outputs

The action exposes outputs you can reference in downstream steps. This example posts the deploy time as a PR comment:

```yaml theme={"system"}
steps:
  - uses: actions/checkout@v4

  - uses: basetenlabs/action-truss-push@v0.1
    id: deploy
    with:
      truss-directory: "./my-model"
      baseten-api-key: ${{ secrets.BASETEN_API_KEY }}

  - name: Comment on PR
    if: github.event_name == 'pull_request'
    uses: actions/github-script@v7
    with:
      script: |
        github.rest.issues.createComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          issue_number: context.issue.number,
          body: `Model deployed in ${{ steps.deploy.outputs.deploy-time-seconds }}s. Status: ${{ steps.deploy.outputs.status }}`
        })
```

See the full list of inputs and outputs in the [Truss Push GitHub Action reference](/reference/ci/github-action).

## Next steps

<CardGroup>
  <Card title="Rolling deployments" href="/deployment/rolling-deployments">
    Promote validated deployments to production without downtime.
  </Card>

  <Card title="Environments" href="/deployment/environments">
    Manage staging and production environments for your models.
  </Card>
</CardGroup>

## Troubleshooting

**`deploy_timeout`:** The default timeout is 45 minutes, which accommodates large builds like TRT-LLM. For smaller models, reduce `deploy-timeout-minutes` to fail faster. If your model legitimately needs more time, increase the value.

**`deploy_failed`:** Check your `config.yaml` for syntax errors and verify the `BASETEN_API_KEY` secret is set correctly. The action logs the full build output in collapsible sections. Expand them in the GitHub Actions UI to see the exact error.

**`predict_failed`:** Verify the predict payload shape matches what your model expects. Check `model_metadata.example_model_input` in `config.yaml`, or override it with `predict-payload`. For chains, the predict payload must be provided explicitly.

**`cleanup_failed`:** The deployment may still be running. Deactivate it manually from the [Baseten dashboard](https://app.baseten.co).

**`429 Too Many Requests`:** The action calls management API endpoints that are rate limited per API key. Matrix jobs that fan out across many models can exceed the per-endpoint limits. See [management API rate limits](/reference/management-api/rate-limits) for thresholds and backoff guidance.

**No predict output:** If neither `predict-payload` nor `model_metadata.example_model_input` is configured, the action skips prediction entirely. The deployment runs but isn't validated. Add an example input to your `config.yaml` (models) or set `predict-payload` (chains) to enable validation.

**`Team selection required but running in a non-interactive context`:** Your API key has access to multiple teams and Truss can't infer a single target team without a prompt. Pass the team explicitly with the `team` input on the action (or `--team <name>` if you invoke `truss push` directly):

```yaml theme={"system"}
- uses: basetenlabs/action-truss-push@v0.1
  with:
    truss-directory: "./my-model"
    baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
    team: "ml-platform"
```

See [Deploy to a team](/organization/teams#use-the-truss-cli) for the team-resolution rules. Requires Truss `0.18.3` or later.
