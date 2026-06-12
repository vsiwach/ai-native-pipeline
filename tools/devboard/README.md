# devboard

A single-file developer dashboard over the pipeline: CI runs, deployments,
inference economics (live from the router's `/v1/costs`), and agent activity.
React via CDN, zero build step, zero backend — it talks straight to the
GitHub API and the router.

![devboard screenshot](screenshot.png)

## Setup (3 lines)

```bash
python3 -m http.server 8400 --directory tools/devboard   # serve it
open "http://localhost:8400/?mock=true"                  # tour with mock data
# live data: Settings → owner/repo + a PAT (repo+actions scopes) + router URL
```

The PAT lives in memory only — never localStorage; a refresh forgets it.
The "Deploy staging" button fires `deploy-staging.yml` via workflow_dispatch;
its confirm dialog quotes the exact governance policy line being invoked.
Lighthouse accessibility: 100 (see repo history for the run).
