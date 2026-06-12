# devkit — `./dev`

The developer productivity layer for this repo. One command, stdlib-only
Python 3.11, zero install. Run `./dev` from the repo root for help.

## Commands

| Command | What it does |
|---|---|
| `./dev status` | Phase progress (1–5) and the exact next step |
| `./dev doctor` | Toolchain + repo health check |
| `./dev new service <name>` | Scaffold a full contract-compliant service |
| `./dev test` | `bazel test //...`, or unittest discovery before Bazel exists |
| `./dev build` | `bazel build //...` |
| `./dev run <name>` | Docker build + run a service, probe `/healthz` |
| `./dev check` | Everything you must pass before pushing |

## The 30-second workflow

```bash
./dev new service sentiment --tier standard --target cpu
# edit services/sentiment/app.py → predict()
./dev test
./dev run sentiment
./dev check          # registry + artifacts + governance + tests
```

`new service` generates **every** artifact the conventions require: `app.py`
(implements `GET /healthz`, `GET /v1/info`, `POST /v1/predict`), tests
runnable via Bazel *and* plain python, Dockerfile, BUILD.bazel, README,
`requirements.txt`, a CI workflow that boots the container and probes
`/healthz`, and an `inference-registry.yaml` entry. The only thing left to a
human is the model code and a README table row.

## Design constraints

- **Stdlib only.** devkit must work on a fresh machine before Bazel, Docker,
  or pip are set up — it's the tool that tells you those are missing.
- **Graceful on an incomplete repo.** Phases 1–5 land over time; every check
  that depends on a not-yet-built artifact reports "skipping", never an error.
- **Conventions are enforced, not documented.** `./dev check` fails on a
  service missing its Dockerfile/tests/registry entry, on invalid tiers, on
  duplicate backends — the same rules CLAUDE.md states in prose.

## Testing devkit itself

```bash
python3 -m unittest discover -s tools/devkit/tests -v
# or, once a Bazel workspace exists:
bazel test //tools/devkit:all
```
