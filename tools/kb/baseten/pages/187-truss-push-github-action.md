# Truss Push GitHub Action
Source: https://docs.baseten.co/reference/ci/github-action

Deploy and validate a Truss model or chain on Baseten from GitHub Actions.

```yaml theme={"system"}
- uses: basetenlabs/action-truss-push@v0.1
  with:
    truss-directory: "./my-model"
    baseten-api-key: ${{ secrets.BASETEN_API_KEY }}
```

Deploys a Truss model or chain to Baseten, waits for the deployment to become active, optionally validates it with a predict request, and cleans up the deployment. For workflow examples, see [CI/CD](/deployment/ci-cd).

**Models** are detected when `truss-directory` points to a directory containing `config.yaml`. **Chains** are detected when `truss-directory` points to a `.py` file containing a `@chains.mark_entrypoint` class.

Pin to a specific release tag. Don't use `@main` because the action API may change between releases.

## Inputs

<ParamField type="string">
  Path to a model directory containing `config.yaml`, or a `.py` file for chain deployments.
</ParamField>

<ParamField type="string">
  Baseten API key. Store this as an [encrypted secret](https://docs.github.com/en/actions/security-guides/encrypted-secrets). Never hardcode it in your workflow file.
</ParamField>

<ParamField type="string">
  Override the model or chain name. For models, maps to `truss push --model-name`. For chains, sets the `chain_name`. If empty, the action uses `model_name` from `config.yaml` for models, or the entrypoint class name for chains.
</ParamField>

<ParamField type="string">
  Publish to a specific environment. Implies publish. If empty, no environment is set.
</ParamField>

<ParamField type="string">
  Attach git versioning info (SHA, branch, tag) to the deployment.
</ParamField>

<ParamField type="string">
  JSON string of labels as key-value pairs, for example `{"team": "ml", "project": "llm"}`. Attach metadata to track deployments in your CI pipeline.
</ParamField>

<ParamField type="string">
  Name of the deployment. If empty, defaults to `PR-{number}_{sha}` on pull requests or `{sha}` on direct pushes.
</ParamField>

<ParamField type="string">
  Deactivate the newly created deployment after validation. Useful for PR checks where you deploy, validate with a predict request, and tear down. Set to `false` when you want the deployment to remain active for manual inspection or when deploying to an environment.

  The activate and deactivate calls this action makes are rate limited to 20 requests/minute per API key. See [management API rate limits](/reference/management-api/rate-limits) if you run high-volume CI.
</ParamField>

<ParamField type="string">
  JSON override for the predict request payload. For models, if empty, the action reads `model_metadata.example_model_input` from `config.yaml`. For chains, the predict payload must be provided explicitly. If neither is set, the predict step is skipped entirely and the deployment isn't validated.
</ParamField>

<ParamField type="string">
  Maximum minutes to wait for the deployment to become active. The default (45 minutes) accommodates large model builds like TRT-LLM. Reduce this for smaller models to fail faster.
</ParamField>

<ParamField type="string">
  Timeout in seconds for the predict request.
</ParamField>

## Outputs

<ParamField type="string">
  Baseten deployment ID. Use this to reference the deployment in downstream steps or API calls.
</ParamField>

<ParamField type="string">
  Baseten model ID. Set for model deployments only.
</ParamField>

<ParamField type="string">
  Baseten chain ID. Set for chain deployments only.
</ParamField>

<ParamField type="string">
  Model or chain name.
</ParamField>

<ParamField type="string">
  Wall-clock seconds from push to active. Useful for tracking build performance over time.
</ParamField>

<ParamField type="string">
  Response body from the predict call, truncated to 4 KB.
</ParamField>

<ParamField type="string">
  Final status of the action run. One of: `success`, `deploy_failed`, `deploy_timeout`, `predict_failed`, `cleanup_failed`.
</ParamField>

## Status codes

| Status           | Description                                                                                                                                         |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `success`        | Deployment active, predict passed (if payload configured), cleanup completed.                                                                       |
| `deploy_failed`  | `truss push` or image build failed. Check `config.yaml` syntax and API key. Build logs appear in collapsible sections in the GitHub Actions output. |
| `deploy_timeout` | Deployment didn't become active within `deploy-timeout-minutes`. Increase the timeout for large models.                                             |
| `predict_failed` | Predict request returned an error or timed out. Verify the payload shape matches what the model expects.                                            |
| `cleanup_failed` | Deployment deactivation failed. The deployment may still be running. Deactivate it manually from the dashboard.                                     |

## Deployment naming

The action generates deployment names from Git context unless you override with `deployment-name`:

* **Pull requests:** `PR-{number}_{short_sha}` (for example, `PR-42_abc1234`).
* **Direct pushes:** `{short_sha}` (for example, `abc1234`).

## Permissions

The action requires only `contents: read` permission. No additional GitHub token permissions are needed.

```yaml theme={"system"}
permissions:
  contents: read
```
