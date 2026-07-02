# Secure model inference
Source: https://docs.baseten.co/observability/security

Keeping your models safe and private

Baseten maintains [SOC 2 Type II certification](https://www.baseten.co/blog/soc-2-type-2) and [HIPAA compliance](https://www.baseten.co/blog/baseten-announces-hipaa-compliance), with robust security measures beyond compliance.

## Data privacy

Baseten does not store model inputs, outputs, or weights by default. This zero data retention (ZDR) posture applies to synchronous inference out of the box.

* **Model inputs/outputs**: Inputs for [async inference](/inference/async) are temporarily stored until processed. Outputs are never stored.
* **Model weights**: Loaded dynamically from sources like Hugging Face, GCS, or S3, moving directly to GPU memory.
  * Users can enable caching through Truss. You can permanently delete cached weights on request.
* **KV cache**: The attention KV cache is an in-memory, GPU-resident structure used during inference. It is not persisted to disk and is discarded when a replica restarts or scales down.
* **Postgres data tables**: Existing users may store data in Baseten’s hosted Postgres tables, which can be deleted anytime.

Baseten’s network accelerator optimizes model downloads. [Contact support](mailto:support@baseten.co) to disable it.

To learn more and access official policies and certifications, visit the [Baseten Trust Center](https://trust.baseten.co/).

## View your compliance policy

If Baseten has set a compliance policy for your account, the policy appears in your **Organization** and **Team** settings under the General tab, and on the model environment detail view. The policy shows the boundaries your inference workloads run within:

* **Framework**: the compliance programs your workloads are restricted to.
* **Region**: the geographic regions where your workloads can run.

Compliance policies are read-only and managed by Baseten. To set or change a policy, [contact support](mailto:support@baseten.co).

For Baseten's certifications and official compliance posture, visit the [Baseten Trust Center](https://trust.baseten.co/).

## Workload security

Baseten isolates inference workloads to protect users and Baseten’s infrastructure.

* **Container security**:
  * Baseten never shares GPUs across users.
  * Security tooling: Falco (Sysdig), Gatekeeper (Pod Security Policies).
  * Minimal privileges for workloads and nodes to limit incident impact.
* **Network security**:
  * Each customer has a dedicated Kubernetes namespace.
  * Isolation enforced through [Calico](https://docs.tigera.io/calico/latest/about) and [Cilium](https://docs.cilium.io/en/stable/overview/intro/).
  * Nodes run in a private subnet with firewall protections.
* **Pentesting**:
  * Extended pentesting by [RunSybil](https://www.runsybil.com/) (ex-OpenAI and CrowdStrike experts).
  * Malicious model deployments tested in a dedicated prod-like environment.

## Self-hosted model inference

Baseten offers single-tenant environments and self-hosted deployments. The cloud version is recommended for ease of setup, cost efficiency, and elastic GPU access.

For self-hosting, [contact support](mailto:support@baseten.co).
