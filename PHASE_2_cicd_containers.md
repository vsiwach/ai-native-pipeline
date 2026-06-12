# PHASE 2 — CI/CD for containers

Paste everything below into Claude Code.

---

Extend our GitHub Actions CI/CD so every service in `inference-registry.yaml`
is container-built, smoke-tested, and published — with deploy gates.

## Tasks
1. New workflow `.github/workflows/containers.yml`:
   - Trigger: PRs touching `services/**` or `contracts/**`, plus pushes to main
   - Matrix over services parsed from `inference-registry.yaml` (use a setup job
     with `fromJSON` output so adding a backend never edits the workflow)
   - Steps per service: docker build → run container → poll `/healthz` (fail after
     30s) → hit `/v1/info` and assert tier/target match the registry entry
   - On main: push to GHCR tagged `sha-<short>` and `latest`
2. Layer caching: `docker/build-push-action` with GHA cache backend.
3. Supply-chain hygiene: generate SBOM (`anchore/sbom-action`) and attach as
   artifact; fail on `CRITICAL` vulnerabilities via `grype` scan.
4. Gate refinement in `deploy-staging.yml`: deploy job now `needs: containers`
   and only proceeds if the smoke-test matrix fully passed.
5. Update `tools/policy_check.py`: new action `container-publish` — agents may
   publish to GHCR only from main, never from PR branches (add to
   governance/agent-policy.yaml).

## Acceptance criteria
- Open a draft PR changing `services/inference/` — containers.yml builds and
  smoke-tests only that service; no GHCR push happens
- Merge to main — image appears in GHCR with both tags; SBOM artifact attached
- `python3 tools/policy_check.py --action container-publish --requested-by claude --ref refs/pull/1` exits 1
- README updated with the container pipeline diagram row
