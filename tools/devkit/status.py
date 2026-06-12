"""`./dev status` — where the repo is in the phase plan, and what to do next."""

from pathlib import Path

import registry
import ui

# (phase, title, prompt file, artifact that proves it's done)
PHASES = (
    (1, "Vendor inference app", "PHASE_1_vendor_inference_app.md",
     "services/inference"),
    (2, "CI/CD containers", "PHASE_2_cicd_containers.md",
     ".github/workflows"),
    (3, "Cost-optimal inference", "PHASE_3_cost_optimal_inference.md",
     "services/router"),
    (4, "Multi-cloud deploy", "PHASE_4_multicloud_deploy.md",
     "deploy/terraform"),
    (5, "Developer dashboard", "PHASE_5_devtool_ux.md",
     "tools/devboard"),
)


def run(repo_root: Path) -> int:
    ui.heading("Phase progress")
    next_phase = None
    for num, title, prompt, artifact in PHASES:
        done = (repo_root / artifact).exists()
        if done:
            ui.ok(f"Phase {num}: {title}")
        else:
            ui.info(f"Phase {num}: {title} — not started ({ui.dim(prompt)})")
            if next_phase is None:
                next_phase = (num, prompt)

    backends = registry.load(repo_root)
    if backends:
        ui.heading("Registered backends")
        for b in backends:
            ui.ok(f"{b.get('name')}  tier={b.get('tier')}  target={b.get('target')}")

    print()
    if next_phase:
        num, prompt = next_phase
        print(f"Next: paste {ui.bold(prompt)} into a fresh Claude Code session "
              f"(one phase per session — see README).")
    else:
        print(ui.green("All five phases complete."))
    return 0
