# Audit logs
Source: https://docs.baseten.co/organization/audit-logs

Track configuration and access changes across your Baseten organization, and export audit events to your SIEM.

Baseten records administrative and configuration events to an audit log. Organization Admins can review the log directly in the Baseten dashboard, and security-conscious organizations can stream audit events to an external SIEM through WorkOS.

## Activity log in the dashboard

Every Baseten organization has an activity log that captures configuration changes and lifecycle events for models, Chains, secrets, API keys, environments, and users.

To view the activity log, navigate to **Organization settings** and select the **Activity** tab.

Each entry includes:

* A description of the action and the user who performed it. System-initiated events, such as a deployment deactivated for inactivity, have no user attribution.
* The affected resource (model, Chain, environment, or other entity).
* The timestamp of the event.

You can search the log by text and filter by event type group, user, and date range.

<Note>
  If your organization uses [teams](/organization/teams), only Organization Admins can view the activity log. Members don't see activity log entries in multi-team organizations.
</Note>

### Filter activity on a model or Chain

Each model and Chain has its own **Activity** tab that shows events scoped to that resource. Open a model or Chain and select the **Activity** tab.

On this tab, you can filter the activity log by:

* **Event type:** one or more groups of event types, such as deployments, promotions, or autoscaling changes.
* **Member:** the user who performed the action.
* **Deployment:** a specific deployment of the model or Chain.
* **API key:** the API key used to perform the action.
* **Date range:** defaults to **All time**.

Each filter is multi-select, and the filters combine: the log shows only entries that match every active filter. Select **Reset** to clear all filters at once.

## Audit log event types

Each audit log entry has an event type. Event types appear as the `action` field in [exported events](#audit-log-export-to-your-siem). In the dashboard, Baseten renders each event type as a human-readable description.

### Models and deployments

* `MODEL_DEPLOYED`
* `MODEL_DEPLOYMENT_ACTIVATED`
* `MODEL_DEPLOYMENT_DEACTIVATED`
* `MODEL_DEPLOYMENT_RETRIED`
* `MODEL_DEPLOYMENT_PROMOTED`
* `MODEL_DEPLOYMENT_AUTOSCALING_SETTINGS_CHANGED`
* `MODEL_DEPLOYMENT_INSTANCE_TYPE_CHANGED`
* `MODEL_DEPLOYMENT_DELETED`
* `MODEL_DELETED`
* `MODEL_PROMOTION_CONTROL_ACTION`
* `REPLICA_TERMINATED`

### Chains

* `CHAIN_DEPLOYED`
* `CHAIN_DEPLOYMENT_ACTIVATED`
* `CHAIN_DEPLOYMENT_DEACTIVATED`
* `CHAIN_DEPLOYMENT_PROMOTED`
* `CHAIN_DEPLOYMENT_DELETED`
* `CHAIN_DELETED`
* `CHAINLET_AUTOSCALING_SETTINGS_CHANGED`
* `CHAINLET_INSTANCE_TYPE_CHANGED`

### Environments

* `ENVIRONMENT_CREATED`
* `ENVIRONMENT_UPDATED`
* `ENVIRONMENT_DELETED`

### Credentials and secrets

* `API_KEY_CREATED`
* `API_KEY_DELETED`
* `SECRET_UPDATED`
* `SECRET_DELETED`
* `WEBHOOK_SIGNING_SECRET_CREATED`
* `WEBHOOK_SIGNING_SECRET_ROTATED`
* `WEBHOOK_SIGNING_SECRET_DELETED`
* `SSH_CERTIFICATE_SIGNED`

### Users

* `USER_INVITED`
* `USER_JOINED_ORGANIZATION`
* `USER_ROLE_UPDATED`
* `USER_REMOVED`

## Audit log export to your SIEM

For organizations that need audit events in an external system, Baseten can stream the audit log to [WorkOS Audit Logs](https://workos.com/docs/audit-logs), which forwards events to destinations you control.

Supported destinations include:

* Amazon S3
* Datadog
* Splunk

For the full list of destinations and their configuration options, see the [WorkOS Audit Logs documentation](https://workos.com/audit-logs).

<Note>
  Audit log export is available on the Enterprise plan. [Contact support](mailto:support@baseten.co) to enable export for your organization.
</Note>

### Enable audit log export

To enable audit log export:

1. [Contact support](mailto:support@baseten.co) with your organization name and the destination you want to forward events to.
2. Baseten enables export and walks you through configuring your destination, including any destination-specific credentials or webhook URLs.

Once your destination is verified, new audit events are exported on a recurring schedule and appear in your destination shortly after they're recorded. Events that occurred before you enabled export aren't backfilled.

To disable export, [contact support](mailto:support@baseten.co). The activity log in the dashboard continues to reflect every event for your organization regardless of export status.

### Event delivery

Baseten retries transient failures for up to 30 minutes when sending events to your destination. For details on destination-side retry and delivery guarantees, see the [WorkOS Audit Logs documentation](https://workos.com/docs/audit-logs).

## Considerations

* The activity log in the dashboard always reflects every recorded event for your organization, regardless of export status.
* For details on audit log retention, [contact support](mailto:support@baseten.co).
* If you need a custom event schema or a destination not supported by WorkOS, [contact support](mailto:support@baseten.co).
