# Billing and usage
Source: https://docs.baseten.co/organization/billing

How Baseten meters per-minute usage, and how to manage payment, credits, and invoices for your workspace.

Manage payment, credits, and invoices for your workspace from the [billing and usage dashboard](https://app.baseten.co/settings/billing). Usage is tracked per deployment and updated hourly. For organizations on teams, usage is aggregated at the organization level and visible only to admins.

## Account billing

### Payment method

Add or update payment details on the [billing dashboard](https://app.baseten.co/settings/billing). Your card and bank information is stored with our payments processor, not by Baseten directly.

### Credits

New workspaces receive free credits for testing and deployment. Credits are applied automatically to your running invoice before any card charge. If your credits run out and you have not added a payment method, Baseten deactivates your models until you add one.

### Invoices and payment cadence

Invoices are issued when usage exceeds \$50 or at the end of the calendar month, whichever comes first. After a history of successful payments, billing moves to a monthly cadence.

You can view past invoices and payments in the billing dashboard. For questions about a specific invoice, [contact support](mailto:support@baseten.co).

### Discounts

Volume discounts are available on the Pro plan. Education and nonprofit ML projects qualify for additional discounts. [Contact support](mailto:support@baseten.co) to apply.

***

## What's billed

Baseten meters usage by the minute. For every minute a replica is observed as up on a node, the per-minute price for its instance type applies. The same rule covers the builder workload that produces your image after a `truss push` and the training workloads that run a fine-tune. The detail that catches people off guard: the builder counts, and failed boots do not.

What is not metered: anything that happens before a workload is observed as up (image pull onto the node, scheduling) or after it terminates (drain, cleanup, recycling).

### Replica lifecycle

When you run `truss push`, Baseten runs your image build as a workload. Like serving replicas and training containers, it is metered from the moment it is observed as up.

Cold starts are billed too. Model load happens after the replica is observed as up but before it is healthy enough to serve, so those minutes are on the bill. This is the cost side of the cold-start tradeoff: keeping `min_replica` at zero saves money during idle periods but pushes load time into your customer's first request after a quiet stretch.

The full mapping:

| Lifecycle phase                                                                         | Billed                 |
| --------------------------------------------------------------------------------------- | ---------------------- |
| Image build after `truss push` (runs in a builder workload)                             | Yes                    |
| Image pull onto the node                                                                | No                     |
| Cold start and model load                                                               | Yes                    |
| Serving requests                                                                        | Yes                    |
| Idle warm replicas (`min_replica` ≥ 1)                                                  | Yes                    |
| Replica terminated by autoscaling                                                       | Yes, up to termination |
| Replica killed mid-request (OOM, crash)                                                 | Yes, up to termination |
| Failed boot (replica was never observed as up)                                          | No                     |
| Scaled to zero (`min_replica: 0`, no traffic)                                           | No                     |
| [Development deployments](/development/model/deploy-and-iterate) (`truss push --watch`) | No                     |

A few clarifications on the rows that surprise people:

**Why image build costs money.** The build runs as its own workload, metered the same way as your serving replicas. Faster builds save money. Heavy or unnecessary install steps in your `config.yaml` are paying for themselves on every push.

**Why cold starts cost money.** The replica is observed as up during model load, so those minutes are billed. See [Cold starts](/deployment/autoscaling/cold-starts) for techniques to shrink that window.

**Why failed boots are free.** If the replica was never observed as up, no minutes are billed. Image-build failures that happen inside the builder workload, on the other hand, are billed up to the moment the build fails.

**What happens if a replica is killed mid-request.** Usage is billed up to the moment the replica terminates. Partial minutes are rounded up.

### Training and fine-tuning

Training and fine-tuning runs are metered the same way as serving. A run is billed for the wall-clock time between the training workload being observed as up and the job completing or being cancelled. For how training storage works, see [Training storage](/training/concepts/storage).

### Instance pricing

Per-minute prices for every available instance type are listed on the [instance type reference](/deployment/resources#instance-type-reference). To convert per-minute to per-hour, multiply by 60.

***

## The billing and usage dashboard

The [billing and usage dashboard](https://app.baseten.co/settings/billing) shows per-deployment usage updated hourly, your current invoice balance, any credit applied, and historical invoices.
